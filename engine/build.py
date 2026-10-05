"""Six-culture deterministic dataset builder.

Usage: python build.py <path/to/BIRTH_INPUT.json>
Writes INPUT_AUDIT.md, CALCULATION_MANIFEST.json, MASTER_DATASET.{json,md}, VERIFICATION_REPORT.{json,md}
next to the input file. Facts only; interpretation lives in synth.py.
"""
import datetime as dt
import hashlib
import importlib.metadata as md
import json
import platform
import sys
from pathlib import Path

import swisseph as swe
from lunar_python import Solar, Lunar

from sixc import astro as A
from sixc import jyotisha as J
from sixc import bazi as B
from sixc import western as W
from sixc import calendars as C

ENGINE = Path(__file__).resolve().parent
THRESH = {"planet_lon_deg": 0.01, "angle_deg": 0.05, "solar_term_seconds": 120}
BRANCH_ORDER = "子丑寅卯辰巳午未申酉戌亥"


def iso(jd, tz=None):
    u = A.jd_to_utc(jd)
    if tz:
        import zoneinfo
        u = u.astimezone(zoneinfo.ZoneInfo(tz))
    return u.isoformat(timespec="seconds")


def zw_time_index(hh, mm):
    """iztro: 0 early-Zi (00-01), 1 Chou (01-03) ... 11 Hai (21-23), 12 late-Zi (23-24)."""
    m = hh * 60 + mm
    if m < 60:
        return 0
    if m >= 23 * 60:
        return 12
    return (m - 60) // 120 + 1


def snapshot(jd, utc, inp, lat, lon, alt):
    """Time-sensitive facts at one instant (for the uncertainty / location ensembles)."""
    trop = A.se_positions(jd)
    sid = A.se_positions(jd, sidereal=True)
    h_t = A.se_houses(jd, lat, lon)
    h_s = A.se_houses(jd, lat, lon, sidereal=True)
    off = inp["_tz_offset_h"]
    st = A.solar_times(jd, lon, lat, alt, off)
    lat_dt = dt.datetime.fromisoformat(st["local_apparent_time"])
    civ = (utc + dt.timedelta(hours=off)).replace(tzinfo=None)
    d1 = J.build_d1(sid, h_s["asc"])
    sun_alt = A.sun_altitude(jd, lon, lat, alt)["true_altitude"]
    wb = W.build(trop, h_t["asc"], h_t["mc"], sun_alt, sun_alt > 0)
    _, e_civ = B.pillars_for(civ.year, civ.month, civ.day, civ.hour, civ.minute, civ.second)
    _, e_lat = B.pillars_for(lat_dt.year, lat_dt.month, lat_dt.day, lat_dt.hour, lat_dt.minute, lat_dt.second)
    moon_nk = J.nakshatra(sid["Moon"]["lon"])
    return {
        "western_asc_sign": A.SIGNS[A.sign_of(h_t["asc"])], "western_asc_lon": h_t["asc"],
        "western_mc_sign": A.SIGNS[A.sign_of(h_t["mc"])],
        "western_house_of_planets": {p: wb["planets"][p]["house"] for p in W.SEVEN},
        "lot_fortune_sign": wb["lots"]["Fortune"]["sign"], "lot_spirit_sign": wb["lots"]["Spirit"]["sign"],
        "sect_day": sun_alt > 0,
        "jyotisha_lagna_sign": d1["lagna"]["sign"], "jyotisha_lagna_lon": h_s["asc"],
        "jyotisha_d9_lagna": d1["lagna"]["d9_sign"], "jyotisha_d10_lagna": d1["lagna"]["d10_sign"],
        "jyotisha_d9_planets": {p: d1["grahas"][p]["d9_sign"] for p in J.GRAHAS},
        "jyotisha_d10_planets": {p: d1["grahas"][p]["d10_sign"] for p in J.GRAHAS},
        "moon_nakshatra_pada": f"{moon_nk['name']} {moon_nk['pada']}",
        "bazi_civil": [e_civ.getYear(), e_civ.getMonth(), e_civ.getDay(), e_civ.getTime()],
        "bazi_apparent": [e_lat.getYear(), e_lat.getMonth(), e_lat.getDay(), e_lat.getTime()],
        "ziwei_time_index_civil": zw_time_index(civ.hour, civ.minute),
        "ziwei_time_index_apparent": zw_time_index(lat_dt.hour, lat_dt.minute),
    }


def classify(snaps, key):
    vals = [json.dumps(s[key], ensure_ascii=False, sort_keys=True) for s in snaps.values()]
    return "stable" if len(set(vals)) == 1 else "sensitive"


def new_moons_around(jd):
    def elong(j):
        return A.angdiff(swe.calc_ut(j, swe.MOON, A.SE_FLAGS)[0][0], swe.calc_ut(j, swe.SUN, A.SE_FLAGS)[0][0])
    # step back/forward to find sign changes of elongation through 0
    res = {}
    for direction in (-1, 1):
        j = jd
        prev = elong(j)
        while True:
            j2 = j + direction * 0.5
            cur = elong(j2)
            if prev * cur < 0 and abs(prev - cur) < 90:
                lo, hi = sorted((j, j2))
                res["prev" if direction < 0 else "next"] = A.find_root(elong, lo, hi)
                break
            j, prev = j2, cur
    return res


def main(input_path):
    input_path = Path(input_path).resolve()
    out_dir = input_path.parent
    inp = json.loads(input_path.read_text())
    loc = inp["location"]
    lat, lon, alt = loc["lat"], loc["lon"], loc.get("elevation_m", 0)
    analysis_date = dt.date.fromisoformat(inp["analysis_date"])

    # ---------------------------------------------------------------- Step 2: civil time audit
    civil, utc = A.civil_audit(inp)
    inp["_tz_offset_h"] = civil["utc_offset_hours"]
    jd = A.jd_ut(utc)
    jd_tt = jd + swe.deltat(jd)
    st = A.solar_times(jd, lon, lat, alt, civil["utc_offset_hours"])
    rs_se = A.sunrise_sunset_se(jd, lon, lat, alt)
    rs_sf = A.sunrise_sunset_sf(utc, lon, lat, alt)
    sf_rise = [t for t, e in rs_sf if e == "sunrise"][0]
    sf_set = [t for t, e in rs_sf if e == "sunset" and t > utc][0]
    sun_alt = A.sun_altitude(jd, lon, lat, alt)
    sun_alt_sf = A.sun_altitude_sf(utc, lon, lat, alt)
    tz = civil["iana_zone"]
    from timezonefinder import TimezoneFinder
    tz_lookup = TimezoneFinder().timezone_at(lat=lat, lng=lon)

    # ---------------------------------------------------------------- Step 4A: astronomy
    trop = A.se_positions(jd)
    sid = A.se_positions(jd, sidereal=True)
    sf = A.sf_positions(utc)
    ayan = A.ayanamsha(jd)
    h_trop = A.se_houses(jd, lat, lon)
    h_sid = A.se_houses(jd, lat, lon, sidereal=True)
    sf_ang = A.sf_asc_mc(utc, lat, lon)
    meeus_node = A.mean_node_meeus(jd)

    verification = []

    def vrow(system, datum, pe, pv, val, vv, conv, thresh, stability="stable", boundary=None, conf=None, note=None):
        diff = abs(A.angdiff(pv, vv)) if isinstance(pv, float) and isinstance(vv, float) else None
        status = "pass" if diff is None or diff <= thresh else "alert"
        if conf is None:
            conf = "high" if status == "pass" and stability == "stable" else "low"
        row = {"system": system, "datum": datum, "primary_engine": pe, "primary_value": pv,
               "validator": val, "validator_value": vv, "difference": diff, "convention": conv,
               "boundary_distance": boundary, "uncertainty_stability": stability, "confidence": conf,
               "status": status}
        if note:
            row["note"] = note
        verification.append(row)
        return row

    for p in A.PLANETS:
        vrow("shared", f"{p} tropical longitude", "Swiss Ephemeris 2.10.03 (sepl/semo_18)", trop[p]["lon"],
             "Skyfield 1.55 + JPL DE421", sf[p]["lon"], "geocentric apparent, true ecliptic & equinox of date",
             THRESH["planet_lon_deg"],
             note="Shared lineage: SE files are compressed from JPL DE431; reduction code (precession, nutation, aberration, light-time) is independent." if p == "Sun" else None)
    vrow("shared", "Ascendant (tropical)", "Swiss Ephemeris houses_ex", h_trop["asc"],
         "Skyfield GAST + IAU2000B true obliquity, independent spherical-trig formula", sf_ang["asc"],
         "tropical, true obliquity", THRESH["angle_deg"])
    vrow("shared", "MC (tropical)", "Swiss Ephemeris houses_ex", h_trop["mc"],
         "Skyfield GAST + IAU2000B true obliquity, independent spherical-trig formula", sf_ang["mc"],
         "tropical, true obliquity", THRESH["angle_deg"])
    vrow("shared", "Mean lunar node (tropical)", "Swiss Ephemeris MEAN_NODE", trop["MeanNode"]["lon"],
         "Meeus AA eq. 47.7 polynomial (independent code)", meeus_node, "mean node of date", 0.01)
    vrow("shared", "True lunar node (tropical)", "Swiss Ephemeris TRUE_NODE", trop["TrueNode"]["lon"],
         None, None, "osculating true node", 0, conf="medium",
         note="No independent validator available for the osculating node; single-engine.")
    vrow("shared", "Lahiri ayanamsha", "Swiss Ephemeris SIDM_LAHIRI", ayan, None, None,
         "Lahiri (Chitrapaksha), SE definition", 0, conf="medium",
         note="Convention-defined quantity; single implementation.")
    vrow("shared", "Sun true altitude at birth", "Swiss Ephemeris azalt", sun_alt["true_altitude"],
         "Skyfield topocentric altaz", sun_alt_sf, "geometric altitude (no refraction)", 0.05)
    rise_diff_s = abs((A.jd_to_utc(rs_se["sunrise"]) - sf_rise).total_seconds())
    set_diff_s = abs((A.jd_to_utc(rs_se["next_sunset"]) - sf_set).total_seconds())
    verification.append({"system": "shared", "datum": "Sunrise (birth day)", "primary_engine": "Swiss Ephemeris rise_trans",
                         "primary_value": iso(rs_se["sunrise"], tz), "validator": "Skyfield almanac.sunrise_sunset",
                         "validator_value": sf_rise.astimezone(dt.timezone(dt.timedelta(hours=civil["utc_offset_hours"]))).isoformat(timespec="seconds"),
                         "difference": rise_diff_s, "difference_unit": "seconds", "convention": "upper limb, standard refraction",
                         "boundary_distance": None, "uncertainty_stability": "stable",
                         "confidence": "high" if rise_diff_s < 60 else "medium", "status": "pass" if rise_diff_s < 60 else "alert"})
    verification.append({"system": "shared", "datum": "Sunset (birth day)", "primary_engine": "Swiss Ephemeris rise_trans",
                         "primary_value": iso(rs_se["next_sunset"], tz), "validator": "Skyfield almanac.sunrise_sunset",
                         "validator_value": sf_set.astimezone(dt.timezone(dt.timedelta(hours=civil["utc_offset_hours"]))).isoformat(timespec="seconds"),
                         "difference": set_diff_s, "difference_unit": "seconds", "convention": "upper limb, standard refraction",
                         "boundary_distance": None, "uncertainty_stability": "stable",
                         "confidence": "high" if set_diff_s < 60 else "medium", "status": "pass" if set_diff_s < 60 else "alert"})

    # ---------------------------------------------------------------- solar terms (3 sources)
    terms = {}
    for name, lonT in (("立冬 Lidong (sectional, 225°)", 225), ("小雪 Xiaoxue (mid, 240°)", 240),
                       ("大雪 Daxue (sectional, 255°)", 255), ("冬至 Dongzhi (mid, 270°)", 270)):
        j_se = A.crossing_near(lonT, jd, A.se_sun_lon)
        j_sf = A.crossing_near(lonT, jd, A.sf_sun_lon)
        terms[name] = {"lon": lonT, "se_jd": j_se, "sf_jd": j_sf, "se_utc": iso(j_se), "sf_utc": iso(j_sf),
                       "diff_seconds": abs(j_se - j_sf) * 86400}
    lun_here = Solar.fromYmdHms(utc.year, utc.month, utc.day, 12, 0, 0).getLunar()
    lp_table = lun_here.getJieQiTable()
    for name in terms:
        key = name.split(" ")[0]
        if key in lp_table:
            s = lp_table[key]
            bj = dt.datetime(s.getYear(), s.getMonth(), s.getDay(), s.getHour(), s.getMinute(), s.getSecond(),
                             tzinfo=dt.timezone(dt.timedelta(hours=8)))
            terms[name]["lunar_python_beijing"] = bj.isoformat()
            terms[name]["lunar_python_utc"] = bj.astimezone(dt.timezone.utc).isoformat()
            terms[name]["lunar_python_vs_se_seconds"] = abs((bj.astimezone(dt.timezone.utc) - A.jd_to_utc(terms[name]["se_jd"])).total_seconds())
        verification.append({"system": "bazi", "datum": f"Solar term {name}", "primary_engine": "Swiss Ephemeris (bisection on apparent solar longitude)",
                             "primary_value": terms[name]["se_utc"], "validator": "Skyfield/DE421 bisection; lunar_python (Shouxing algorithm) as third source",
                             "validator_value": terms[name]["sf_utc"], "difference": terms[name]["diff_seconds"], "difference_unit": "seconds",
                             "third_source_value": terms[name].get("lunar_python_utc"), "third_source_difference_seconds": terms[name].get("lunar_python_vs_se_seconds"),
                             "convention": "geocentric apparent solar longitude", "boundary_distance": None,
                             "uncertainty_stability": "stable",
                             "confidence": "high" if terms[name]["diff_seconds"] <= THRESH["solar_term_seconds"] else "low",
                             "status": "pass" if terms[name]["diff_seconds"] <= THRESH["solar_term_seconds"] else "alert"})
    jie_prev = terms["立冬 Lidong (sectional, 225°)"]["se_jd"]
    jie_next = terms["大雪 Daxue (sectional, 255°)"]["se_jd"]

    # ---------------------------------------------------------------- uncertainty ensemble
    unc = inp["normalized"]["uncertainty_minutes"]
    offsets_primary = [-unc, 0, unc]
    offsets_diag = [-30, -15, -5, 5, 15, 30]
    snaps = {}
    for o in sorted(set(offsets_primary + offsets_diag)):
        u = utc + dt.timedelta(minutes=o)
        snaps[o] = snapshot(A.jd_ut(u), u, inp, lat, lon, alt)
    prim = {o: snaps[o] for o in offsets_primary}
    keys = list(snaps[0].keys())
    stability = {k: classify(prim, k) for k in keys if not k.endswith("_lon")}
    diag = {}
    for k in keys:
        if k.endswith("_lon"):
            continue
        changed = [o for o in offsets_diag if json.dumps(snaps[o][k], sort_keys=True, ensure_ascii=False) != json.dumps(snaps[0][k], sort_keys=True, ensure_ascii=False)]
        diag[k] = {"changes_at_offsets_min": changed}

    # location ensemble (birthplace given as city only)
    loc_ens = {}
    for nm, (la, lo) in loc.get("location_uncertainty_box", {}).items():
        loc_ens[nm] = snapshot(jd, utc, inp, la, lo, alt)
    loc_stability = {k: classify(loc_ens, k) for k in keys if not k.endswith("_lon")} if loc_ens else {}

    # ---------------------------------------------------------------- boundary audit
    def asc_fn(sidereal):
        return lambda j: A.se_houses(j, lat, lon, sidereal=sidereal)["asc"]

    def moon_sid(j):
        swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
        return swe.calc_ut(j, swe.MOON, A.SE_FLAGS | swe.FLG_SIDEREAL)[0][0]

    def bdist(name, fn, part, span=0.25, affects=""):
        b = A.boundary_crossings(fn, jd, part, span_days=span)
        rec = {"boundary": name, "partition_deg": part, "current_cell_index": b["cell"], "affects": affects}
        for k in ("prev", "next"):
            if b[k] is not None:
                rec[f"{k}_crossing_local"] = iso(b[k], tz)
                rec[f"{k}_crossing_minutes_from_birth"] = (b[k] - jd) * 1440
            else:
                rec[f"{k}_crossing_local"] = f"none within ±{span * 24:.0f} h"
        nearest = min(abs(rec.get(f"{k}_crossing_minutes_from_birth", 1e9)) for k in ("prev", "next"))
        rec["nearest_minutes"] = nearest
        return rec

    boundaries = [
        bdist("Western Ascendant sign (tropical, 30°)", asc_fn(False), 30, affects="Western Ascendant sign, all whole-sign houses, Lots, profections"),
        bdist("Jyotisha Lagna sign (sidereal Lahiri, 30°)", asc_fn(True), 30, affects="Lagna, all bhāvas, house lordships, yogas, functional natures"),
        bdist("Jyotisha D9 Lagna (3°20')", asc_fn(True), 30 / 9, affects="Navāṁśa Lagna"),
        bdist("Jyotisha D10 Lagna (3°)", asc_fn(True), 3, affects="Daśāṁśa Lagna"),
        bdist("Moon nakshatra (13°20' sidereal)", moon_sid, 360 / 27, span=1.5, affects="Vimshottari starting lord"),
        bdist("Moon pada (3°20' sidereal)", moon_sid, 360 / 108, span=1.0, affects="Moon pada, Moon D9 sign"),
    ]
    sunrise_min = (jd - rs_se["sunrise"]) * 1440
    boundaries.append({"boundary": "Sunrise / sect (day–night)", "sunrise_local": iso(rs_se["sunrise"], tz),
                       "sunset_local": iso(rs_se["next_sunset"], tz), "minutes_after_sunrise": sunrise_min,
                       "nearest_minutes": sunrise_min, "affects": "Western sect, Lot formulas, triplicity ruler selection"})
    lat_dt = dt.datetime.fromisoformat(st["local_apparent_time"])
    civ_dt = dt.datetime.fromisoformat(civil["local_iso"]).replace(tzinfo=None)

    def two_hour(t):
        m = t.hour * 60 + t.minute + t.second / 60
        start = ((m - 60) // 120) * 120 + 60
        return m - start, start + 120 - m

    for lab, t in (("civil", civ_dt), ("apparent solar", lat_dt)):
        a_, b_ = two_hour(t)
        boundaries.append({"boundary": f"Chinese two-hour (時辰) boundary, {lab} time", "local_time": t.isoformat(timespec="seconds"),
                           "minutes_since_start": a_, "minutes_to_end": b_, "nearest_minutes": min(a_, b_),
                           "affects": "BaZi hour pillar, Zi Wei time index (all palace/star placements)"})
    mins_from_midnight = civ_dt.hour * 60 + civ_dt.minute
    boundaries.append({"boundary": "Civil midnight / late-Zi (23:00) day boundary", "minutes_after_midnight": mins_from_midnight,
                       "minutes_before_23h": 23 * 60 - mins_from_midnight, "nearest_minutes": min(mins_from_midnight, 23 * 60 - mins_from_midnight),
                       "affects": "BaZi day pillar, Zi Wei day, Maya day, Gregorian date"})
    boundaries.append({"boundary": "BaZi sectional solar term (month pillar)",
                       "previous_jie": {"name": "立冬", "utc": iso(jie_prev), "days_before_birth": jd - jie_prev},
                       "next_jie": {"name": "大雪", "utc": iso(jie_next), "days_after_birth": jie_next - jd},
                       "nearest_minutes": min(jd - jie_prev, jie_next - jd) * 1440,
                       "affects": "BaZi month pillar, Da Yun start"})
    nm = new_moons_around(jd)
    from lunar_python import LunarYear
    _bl = Solar.fromYmdHms(civ_dt.year, civ_dt.month, civ_dt.day, civ_dt.hour, civ_dt.minute, 0).getLunar()
    _leap = LunarYear.fromYear(_bl.getYear()).getLeapMonth()
    leap_note = (f"Chinese lunar year {_bl.getYear()} has leap month {_leap}; " if _leap else f"Chinese lunar year {_bl.getYear()} has no leap month; ") + \
        (f"birth is in leap month {abs(_bl.getMonth())}." if _bl.getMonth() < 0 else f"birth is in month {_bl.getMonth()}, not a leap month.")
    boundaries.append({"boundary": "Lunar month / lunar day (new moons)", "prev_new_moon_utc": iso(nm["prev"]),
                       "next_new_moon_utc": iso(nm["next"]), "days_since_new_moon": jd - nm["prev"],
                       "days_to_next_new_moon": nm["next"] - jd, "nearest_minutes": min(jd - nm["prev"], nm["next"] - jd) * 1440,
                       "leap_month_note": leap_note,
                       "affects": "Zi Wei lunar month/day, Five-Elements Bureau, star placements"})

    # ---------------------------------------------------------------- Jyotisha
    d1 = J.build_d1(sid, h_sid["asc"], "TrueNode")
    d1_mean = J.build_d1(sid, h_sid["asc"], "MeanNode")
    node_sign_same = d1["grahas"]["Rahu"]["sign"] == d1_mean["grahas"]["Rahu"]["sign"]
    yog = J.yogas(d1)
    vim = J.vimshottari(sid["Moon"]["lon"], jd, 365.25, depth=3)
    vim_alt = J.vimshottari(sid["Moon"]["lon"], jd, 365.256363, depth=2)
    # vimshottari at ensemble edges (MD/AD date shift)
    vim_shift = {}
    for o in (-unc, unc):
        u = utc + dt.timedelta(minutes=o)
        jj = A.jd_ut(u)
        v2 = J.vimshottari(moon_sid(jj), jj, 365.25, depth=1)
        vim_shift[o] = (v2["periods"][1]["start_jd"] - vim["periods"][1]["start_jd"]) * 1440
    rahu_ketu_sep = abs(A.angdiff(d1["grahas"]["Rahu"]["lon"], d1["grahas"]["Ketu"]["lon"]))
    verification.append({"system": "jyotisha", "datum": "Rahu–Ketu separation (true node)", "primary_engine": "derived",
                         "primary_value": rahu_ketu_sep, "validator": "invariant", "validator_value": 180.0,
                         "difference": abs(rahu_ketu_sep - 180), "convention": "true node", "boundary_distance": None,
                         "uncertainty_stability": "stable", "confidence": "high",
                         "status": "pass" if abs(rahu_ketu_sep - 180) < 1e-9 else "FAIL"})
    tot = sum(J.DASHA_YEARS.values())
    verification.append({"system": "jyotisha", "datum": "Vimshottari lord years total", "primary_engine": "table",
                         "primary_value": tot, "validator": "invariant", "validator_value": 120, "difference": tot - 120,
                         "convention": "Vimshottari", "boundary_distance": None, "uncertainty_stability": "stable",
                         "confidence": "high", "status": "pass" if tot == 120 else "FAIL"})

    def continuous(periods):
        return all(abs(periods[i]["end_jd"] - periods[i + 1]["start_jd"]) < 1e-6 for i in range(len(periods) - 1))
    vim_cont = continuous(vim["periods"]) and all(continuous(m["sub"]) and abs(m["sub"][-1]["end_jd"] - m["end_jd"]) < 1e-6 for m in vim["periods"])
    verification.append({"system": "jyotisha", "datum": "Vimshottari MD/AD continuity", "primary_engine": "derived",
                         "primary_value": vim_cont, "validator": "invariant", "validator_value": True, "difference": None,
                         "convention": "365.25-day year", "boundary_distance": None, "uncertainty_stability": "stable",
                         "confidence": "high", "status": "pass" if vim_cont else "FAIL"})

    def fmt_periods(v, levels=3, tzname=tz):
        out = []
        for m in v["periods"]:
            r = {"lord": m["lord"], "start": iso(m["start_jd"], tzname), "end": iso(m["end_jd"], tzname), "antardashas": []}
            for a in m["sub"]:
                ra = {"lord": a["lord"], "start": iso(a["start_jd"], tzname), "end": iso(a["end_jd"], tzname)}
                if levels >= 3:
                    ra["pratyantardashas"] = [{"lord": p["lord"], "start": iso(p["start_jd"], tzname), "end": iso(p["end_jd"], tzname)} for p in a["sub"]]
                r["antardashas"].append(ra)
            out.append(r)
        return out

    # ---------------------------------------------------------------- BaZi
    bz = B.build(civ_dt, lat_dt, inp["normalized"]["gender"] == "male", None)
    month_ok = jie_prev < jd < jie_next
    verification.append({"system": "bazi", "datum": "Birth between sectional terms 立冬 and 大雪 (month pillar 亥)",
                         "primary_engine": "Swiss Ephemeris", "primary_value": month_ok, "validator": "Skyfield/DE421",
                         "validator_value": terms["立冬 Lidong (sectional, 225°)"]["sf_jd"] < jd < terms["大雪 Daxue (sectional, 255°)"]["sf_jd"],
                         "difference": None, "convention": "sectional (節) terms", "boundary_distance": f"{(jie_next - jd):.3f} days to next jie",
                         "uncertainty_stability": "stable", "confidence": "high", "status": "pass" if month_ok else "FAIL"})
    verification.append({"system": "bazi", "datum": "Hidden-stem and Ten-God table vs lunar_python", "primary_engine": "declared table (bazi.py)",
                         "primary_value": bz["hidden_stem_table_matches_library"], "validator": "lunar_python getXHideGan/getXShiShenZhi",
                         "validator_value": True, "difference": None, "convention": "standard 藏干", "boundary_distance": None,
                         "uncertainty_stability": "stable", "confidence": "high", "status": "pass" if bz["hidden_stem_table_matches_library"] else "FAIL"})
    # exact Da Yun start: (time to next jie) × 120, forward for Yang-year male
    forward = bz["da_yun"]["direction"] == "forward"
    delta_days = (jie_next - jd) if forward else (jd - jie_prev)
    start_jd = jd + delta_days * 120
    dy_periods = []
    for i, p in enumerate(bz["da_yun"]["pillars"]):
        s = start_jd + i * 3652.5
        dy_periods.append({"ganzhi": p["ganzhi"], "start": iso(s, tz), "end": iso(s + 3652.5, tz), "start_jd": s, "end_jd": s + 3652.5})
    lp_start = dt.datetime.strptime(bz["da_yun"]["library_start_solar"], "%Y-%m-%d %H:%M:%S")
    own_start = A.jd_to_utc(start_jd).astimezone(dt.timezone(dt.timedelta(hours=civil["utc_offset_hours"]))).replace(tzinfo=None)
    dy_diff_days = abs((own_start - lp_start).total_seconds()) / 86400
    bz["da_yun"]["exact"] = {
        "convention": "start = birth + (UTC time to the governing sectional term) × 120; each pillar 10 Julian years (3652.5 d)",
        "days_to_governing_jie": delta_days, "start_local": iso(start_jd, tz), "periods": dy_periods,
        "lunar_python_start_local_wallclock": bz["da_yun"]["library_start_solar"],
        "difference_days_vs_lunar_python": dy_diff_days,
        "difference_explanation": (f"lunar_python compares the birthplace wall-clock time ({tz}) against term instants in Beijing time (UTC+8); "
                                   f"the {8 - civil['utc_offset_hours']:+.2f} h offset scales ×120 to ≈{abs(8 - civil['utc_offset_hours']) * 5:.1f} days, "
                                   "and it adds calendar months rather than exact days."),
        "uncertainty_shift_days": unc * 120 / 1440,
    }
    verification.append({"system": "bazi", "datum": "Da Yun start instant", "primary_engine": "exact UTC term-distance ×120 (this builder)",
                         "primary_value": iso(start_jd, tz), "validator": "lunar_python getYun(sect 2)",
                         "validator_value": bz["da_yun"]["library_start_solar"], "difference": dy_diff_days, "difference_unit": "days",
                         "convention": "3 days = 1 year", "boundary_distance": None, "uncertainty_stability": "stable",
                         "confidence": "medium", "status": "pass" if dy_diff_days < 40 else "alert",
                         "note": "Difference explained by time-zone handling inside lunar_python; the pillar sequence is identical."})
    dy_cont = all(abs(dy_periods[i]["end_jd"] - dy_periods[i + 1]["start_jd"]) < 1e-9 for i in range(len(dy_periods) - 1))
    # Annual pillars with Lichun instants computed astronomically (315°)
    annual = []
    for y in range(analysis_date.year - 6, analysis_date.year + 11):
        j0 = A.jd_ut(dt.datetime(y, 2, 4, tzinfo=dt.timezone.utc))
        lc = A.find_sun_crossing(315.0, j0, A.se_sun_lon, window=3.0)
        gz = Solar.fromYmd(y, 6, 1).getLunar().getYearInGanZhiByLiChun()
        annual.append({"year": y, "ganzhi": gz, "lichun_utc": iso(lc), "start_jd": lc})
    for i in range(len(annual) - 1):
        annual[i]["end_jd"] = annual[i + 1]["start_jd"]
        annual[i]["end_utc"] = iso(annual[i]["end_jd"])
    annual = annual[:-1]
    for a in annual:
        a["stem_ten_god"] = B.ten_god(bz["day_master"]["char"], a["ganzhi"][0])
        a["branch_main_ten_god"] = B.ten_god(bz["day_master"]["char"], B.HIDDEN[a["ganzhi"][1]][0])

    # ---------------------------------------------------------------- Western
    is_day = sun_alt["true_altitude"] > 0
    wst = W.build(trop, h_trop["asc"], h_trop["mc"], sun_alt["true_altitude"], is_day)
    bounds_tot = W.bounds_invariant()
    verification.append({"system": "western", "datum": "Egyptian bounds degree totals", "primary_engine": "declared table",
                         "primary_value": bounds_tot, "validator": "invariant",
                         "validator_value": {"Saturn": 57, "Jupiter": 79, "Mars": 66, "Venus": 82, "Mercury": 76},
                         "difference": None, "convention": "Egyptian bounds", "boundary_distance": None,
                         "uncertainty_stability": "stable", "confidence": "high",
                         "status": "pass" if bounds_tot == {"Saturn": 57, "Jupiter": 79, "Mars": 66, "Venus": 82, "Mercury": 76} or
                         sorted(bounds_tot.items()) == sorted({"Saturn": 57, "Jupiter": 79, "Mars": 66, "Venus": 82, "Mercury": 76}.items()) else "FAIL"})
    # profections: birthday to birthday
    bdate = dt.date.fromisoformat(inp["normalized"]["date"])
    prof = []
    for age in range(0, 50):
        start = bdate.replace(year=bdate.year + age)
        end = bdate.replace(year=bdate.year + age + 1)
        p = W.profection(A.sign_of(h_trop["asc"]), age)
        p["start"], p["end"] = start.isoformat(), end.isoformat()
        p["lord_natal_house"] = wst["planets"][p["lord_of_year"]]["house"]
        prof.append(p)
    age_now = analysis_date.year - bdate.year - ((analysis_date.month, analysis_date.day) < (bdate.month, bdate.day))
    # solar returns (birthplace + current residence)
    cur = inp.get("current_residence")
    returns = []
    for yr in (analysis_date.year - 1, analysis_date.year):
        jr = A.sun_return(trop["Sun"]["lon"], A.jd_ut(dt.datetime(yr, bdate.month, bdate.day, tzinfo=dt.timezone.utc)) - 3)
        jr_sf = A.find_sun_crossing(trop["Sun"]["lon"], jr, A.sf_sun_lon, window=0.5)
        rec = {"year": yr, "instant_utc": iso(jr), "skyfield_diff_seconds": abs(jr - jr_sf) * 86400, "locations": {}}
        for lname, (la, lo, zname) in {"birthplace": (lat, lon, tz),
                                       "current_residence": (cur["lat"], cur["lon"], cur["iana_zone"]) if cur else None}.items():
            if la is None:
                continue
            hh = A.se_houses(jr, la, lo)
            sr_asc_sign = A.sign_of(hh["asc"])
            rec["locations"][lname] = {"local": iso(jr, zname), "asc": A.fmt_dms(hh["asc"]), "asc_sign": A.SIGNS[sr_asc_sign],
                                       "sr_asc_in_natal_whole_sign_house": (sr_asc_sign - A.sign_of(h_trop["asc"])) % 12 + 1}
        locs = rec["locations"]
        rec["convention_changes_result"] = len({v["asc_sign"] for v in locs.values()}) > 1
        returns.append(rec)
    outer = {p: {"lon": trop[p]["lon"], "sign": A.SIGNS[A.sign_of(trop[p]["lon"])],
                 "house": (A.sign_of(trop[p]["lon"]) - A.sign_of(h_trop["asc"])) % 12 + 1,
                 "retrograde": trop[p]["retrograde"]} for p in ("Uranus", "Neptune", "Pluto")}

    # ---------------------------------------------------------------- Zi Wei
    ti = zw_time_index(lat_dt.hour, lat_dt.minute)
    ti_civ = zw_time_index(civ_dt.hour, civ_dt.minute)
    hdates = [f"{y}-07-01" for y in range(analysis_date.year - 6, analysis_date.year + 11)] + [analysis_date.isoformat()]
    zw, zw_check = C.ziwei(inp["normalized"]["date"], ti, "男" if inp["normalized"]["gender"] == "male" else "女", hdates)
    zw_inv = C.ziwei_invariants(zw)
    for k, v in zw_inv.items():
        verification.append({"system": "ziwei", "datum": f"Invariant: {k}", "primary_engine": f"iztro {zw['iztro_version']} (canonical JS)",
                             "primary_value": v, "validator": "invariant", "validator_value": True, "difference": None,
                             "convention": "iztro default (全书 school config)", "boundary_distance": None,
                             "uncertainty_stability": "stable", "confidence": "medium", "status": "pass" if v else "FAIL"})
    verification.append({"system": "ziwei", "datum": "Canonical iztro vs py-iztro wrapper (all palaces, stars, brightness, transformations, decadals)",
                         "primary_engine": f"iztro {zw['iztro_version']}", "primary_value": "astrolabe",
                         "validator": f"py-iztro {zw_check['wrapper_version']} (bundles iztro {zw_check['wrapper_bundled_iztro']})",
                         "validator_value": "astrolabe", "difference": len(zw_check["mismatches"]), "difference_unit": "mismatching fields",
                         "convention": "same", "boundary_distance": None, "uncertainty_stability": "stable", "confidence": "medium",
                         "status": "pass" if zw_check["pass"] else "alert",
                         "note": "Same underlying method — counts as ONE method, not independent corroboration."})
    lunar_match = (zw["rawDates"]["lunarDate"]["lunarYear"], zw["rawDates"]["lunarDate"]["lunarMonth"], zw["rawDates"]["lunarDate"]["lunarDay"]) == \
        (bz["lunar_date"]["year"], bz["lunar_date"]["month"], bz["lunar_date"]["day"])
    verification.append({"system": "ziwei", "datum": "Lunar date (iztro vs lunar_python)", "primary_engine": "iztro (lunar-lite)",
                         "primary_value": zw["lunarDate"], "validator": "lunar_python", "validator_value": bz["lunar_date"]["text"],
                         "difference": None if lunar_match else "mismatch", "convention": "Chinese lunisolar calendar (UTC+8 reference)",
                         "boundary_distance": f"{jd - nm['prev']:.2f} d after new moon; {nm['next'] - jd:.2f} d before next",
                         "uncertainty_stability": "stable", "confidence": "high" if lunar_match else "low",
                         "status": "pass" if lunar_match else "FAIL"})
    # decadal/annual timeline in dates. Nominal age n spans Chinese New Year of (birth_year + n - 1) → next CNY.
    def cny(y):
        s = Lunar.fromYmd(y, 1, 1).getSolar()
        return dt.date(s.getYear(), s.getMonth(), s.getDay())
    by = bdate.year

    def nominal_age_start(n):
        return bdate if n == 1 else cny(by + n - 1)
    zw_decadal = []
    for p in zw["palaces"]:
        a0, a1 = p["decadal"]["range"]
        zw_decadal.append({"palace_branch": p["earthlyBranch"], "natal_palace_name": p["name"],
                           "decadal_stem_branch": p["decadal"]["heavenlyStem"] + p["decadal"]["earthlyBranch"],
                           "nominal_age_range": [a0, a1], "start": nominal_age_start(a0).isoformat(),
                           "end": nominal_age_start(a1 + 1).isoformat()})
    zw_decadal.sort(key=lambda r: r["nominal_age_range"][0])
    zw_annual = []
    branch_to_palace = {p["earthlyBranch"]: p["name"] for p in zw["palaces"]}
    for y in range(analysis_date.year - 6, analysis_date.year + 10):
        gz = Lunar.fromYmd(y, 6, 1).getYearInGanZhi()
        zw_annual.append({"lunar_year": y, "ganzhi": gz, "start": cny(y).isoformat(), "end": cny(y + 1).isoformat(),
                          "yearly_palace_branch": gz[1], "natal_palace_at_yearly_ming": branch_to_palace[gz[1]]})
    # verify against iztro horoscope
    hz_ok = True
    for d, h in zw["horoscopes"].items():
        dd = dt.date.fromisoformat(d)
        ann = next((a for a in zw_annual if dt.date.fromisoformat(a["start"]) <= dd < dt.date.fromisoformat(a["end"])), None)
        dec = next((a for a in zw_decadal if dt.date.fromisoformat(a["start"]) <= dd < dt.date.fromisoformat(a["end"])), None)
        if ann and h["yearly"]["earthlyBranch"] != ann["yearly_palace_branch"]:
            hz_ok = False
        if dec and h["decadal"]["earthlyBranch"] != dec["palace_branch"]:
            hz_ok = False
    verification.append({"system": "ziwei", "datum": "Date-mapped decadal/annual periods vs iztro horoscope()",
                         "primary_engine": "builder (nominal-age → Chinese New Year mapping)", "primary_value": hz_ok,
                         "validator": "iztro horoscope() at mid-year sample dates", "validator_value": True, "difference": None,
                         "convention": "nominal age (虚岁) increments at Chinese New Year", "boundary_distance": None,
                         "uncertainty_stability": "stable", "confidence": "medium", "status": "pass" if hz_ok else "FAIL"})

    # ---------------------------------------------------------------- Maya, Tibetan
    y, m, d = map(int, inp["normalized"]["date"].split("-"))
    my = C.maya(y, m, d)
    verification.append({"system": "maya", "datum": "Long Count / Tzolkʼin / Haabʼ", "primary_engine": "builder arithmetic (Fliegel–Van Flandern JDN)",
                         "primary_value": my["computed"], "validator": "convertdate 2.5.1",
                         "validator_value": {k: my["validator_convertdate"][k] for k in ("long_count", "tzolkin", "haab")},
                         "difference": None, "convention": "GMT 584283", "boundary_distance": f"{mins_from_midnight} min after civil midnight",
                         "uncertainty_stability": "stable", "confidence": "high" if my["round_trip"]["pass"] and my["long_count_match"] else "low",
                         "status": "pass" if my["round_trip"]["pass"] and my["long_count_match"] else "FAIL"})
    cny_prev = cny(by) if bdate >= cny(by) else cny(by - 1)
    cny_next = cny(cny_prev.year + 1)
    tib = C.tibetan(bdate, bz["primary_pillars"][0], cny_prev, cny_next)
    verification.append({"system": "tibetan", "datum": "Element-animal year", "primary_engine": "sexagenary alignment",
                         "primary_value": tib["label"], "validator": None, "validator_value": None, "difference": None,
                         "convention": "Phugpa year ≈ Chinese sexagenary year away from New Year boundaries",
                         "boundary_distance": f"{tib['days_after_chinese_new_year']} d after CNY, {tib['days_before_next_chinese_new_year']} d before next",
                         "uncertainty_stability": "stable", "confidence": "medium" if tib["losar_boundary_stable"] else "low",
                         "status": "pass" if tib["losar_boundary_stable"] else "alert",
                         "note": "Single method; Mewa, Parkha and personal forces omitted as unvalidated."})

    # ---------------------------------------------------------------- independence disclosure
    verification.append({"system": "all", "datum": "Independence disclosure", "primary_engine": "—", "primary_value": None,
                         "validator": "—", "validator_value": None, "difference": None, "convention": "—",
                         "boundary_distance": None, "uncertainty_stability": "stable", "confidence": "high", "status": "pass",
                         "note": ("Swiss Ephemeris planetary files derive from JPL DE431; Skyfield used DE421 with independent "
                                  "reduction code, so the comparison checks implementation, not the underlying dynamical model. "
                                  "py-iztro wraps iztro (not independent). lunar_python and Swiss/Skyfield solar terms use different "
                                  "algorithms. DE440/DE441 could not be downloaded (HTTP 403 from JPL/NAIF in this environment).")})

    # ---------------------------------------------------------------- assemble
    master = {
        "schema": "six-culture-master-dataset/v2",
        "input": {"original": inp["original"], "normalized": inp["normalized"], "location": loc,
                  "current_residence": inp.get("current_residence"), "analysis_date": inp["analysis_date"]},
        "civil_time": {**civil, "tz_lookup_from_coordinates": tz_lookup, "jd_ut": jd, "jd_tt": jd_tt,
                       "delta_t_seconds": swe.deltat(jd) * 86400, **st,
                       "sunrise_local": iso(rs_se["sunrise"], tz), "sunset_local": iso(rs_se["next_sunset"], tz)},
        "conventions": {
            "astronomy": "geocentric apparent positions, true equinox/ecliptic of date; Swiss Ephemeris primary",
            "jyotisha": {"zodiac": "sidereal", "ayanamsha": "Lahiri (SE SIDM_LAHIRI)", "houses": "whole-sign from Lagna",
                         "node": "true node primary; mean node retained", "dasha_year": "365.25 days (alt 365.256363 retained)",
                         "aspects": "Parāśari graha dṛṣṭi; nodes cast no special aspect in this track",
                         "functional_nature_rule": "FN-1", "yoga_whitelist": "Y-1"},
            "western": {"zodiac": "tropical", "houses": "whole-sign", "planets": "seven traditional (outer planets in separate optional track)",
                        "sect": "Sun geometric altitude > 0", "bounds": "Egyptian", "triplicity": "Dorothean", "faces": "Chaldean",
                        "aspect_orb": f"{W.ASPECT_ORB}° for degree-based aspects; sign-based configuration primary",
                        "profection": "whole-sign annual, birthday to birthday", "solar_return": "computed for birthplace and current residence"},
            "bazi": {"school": bz["school"], "day_boundary": bz["day_boundary_rule"], "strength_rule": "WEC-1",
                     "da_yun": "3 days = 1 year, exact UTC term distance", "year_boundary": "立春 (Sun at 315°)"},
            "ziwei": {"implementation": f"iztro {zw['iztro_version']} (canonical) + py-iztro {zw_check['wrapper_version']}",
                      "configuration": "iztro defaults (全书 four-transformation table, default brightness table)",
                      "time_index": f"{ti} (辰) from local apparent solar time; civil-time index {ti_civ}",
                      "leap_month": "fixLeap=true (first half of leap month → previous month)",
                      "gender_encoding": "男", "age_convention": "nominal age (虚岁), increments at Chinese New Year",
                      "direction": "Yang-year male → clockwise decadals"},
            "maya": "GMT 584283; civil date", "tibetan": "element-animal year only (sexagenary alignment)",
        },
        "time_uncertainty": {
            "primary_interval_minutes": offsets_primary, "diagnostic_offsets_minutes": offsets_diag,
            "rationale": "Time recorded to the minute from a stated exact record; ±1 min covers truncation or rounding. Diagnostic offsets are informational only and do not affect confidence.",
            "snapshots": {str(k): v for k, v in snaps.items()}, "stability_primary": stability,
            "diagnostic_changes": diag,
            "vimshottari_date_shift_minutes_at_interval_edges": vim_shift,
        },
        "location_uncertainty": {"box": loc.get("location_uncertainty_box"), "snapshots": loc_ens,
                                 "stability": loc_stability,
                                 "rationale": f"Birthplace given at city level ({loc['name']}); the corners of the declared coordinate box test coordinate sensitivity."},
        "boundaries": boundaries,
        "astronomy": {"tropical": trop, "sidereal_lahiri": sid, "skyfield_tropical": sf, "ayanamsha_lahiri": ayan,
                      "houses_tropical_whole_sign": h_trop, "houses_sidereal_whole_sign": h_sid, "skyfield_angles": sf_ang,
                      "sun_altitude": sun_alt, "solar_terms": terms, "new_moons": {k: iso(v) for k, v in nm.items()}},
        "jyotisha": {"d1": d1, "mean_node_variant": {"rahu": d1_mean["grahas"]["Rahu"], "ketu": d1_mean["grahas"]["Ketu"],
                                                     "same_sign_as_true_node": node_sign_same},
                     "yogas": yog, "vimshottari": {"moon_nakshatra": vim["moon_nakshatra"], "balance_years_at_birth": vim["balance_years_at_birth"],
                                                   "year_length_days": 365.25, "periods": fmt_periods(vim, 3)},
                     "vimshottari_alt_sidereal_year": {"year_length_days": 365.256363, "periods": fmt_periods(vim_alt, 2)},
                     "shadbala": "unavailable — no validated implementation in this environment",
                     "ashtakavarga": "not computed — transit support not requested",
                     "d7_d12": "not computed — domain-specific divisional charts not requested",
                     "other_tracks": "Jaimini, KP, tropical-Vedic, alternative ayanamshas: not computed"},
        "bazi": {**bz, "annual_pillars": annual, "da_yun_continuous": dy_cont},
        "western": {**wst, "profections": prof, "age_completed_at_analysis_date": age_now, "solar_returns": returns,
                    "optional_modern_track": {"outer_planets": outer, "votes": "none — separate optional track"},
                    "zodiacal_releasing": "unavailable — no validated implementation"},
        "ziwei": {"astrolabe": {k: v for k, v in zw.items() if k != "horoscopes"}, "horoscope_samples": zw["horoscopes"],
                  "wrapper_check": zw_check, "invariants": zw_inv, "decadal_periods": zw_decadal, "annual_periods": zw_annual},
        "maya": my, "tibetan": tib,
        "excluded_methods": [
            {"method": "Shadbala", "reason": "no validated implementation available"},
            {"method": "Ashtakavarga", "reason": "transit support not requested"},
            {"method": "D7 / D12", "reason": "domain-specific divisional charts not requested"},
            {"method": "Zodiacal releasing", "reason": "no validated implementation"},
            {"method": "Transits", "reason": "not computed; timing uses periods, profections and solar returns only"},
            {"method": "Tibetan Mewa, Parkha, personal forces, annual obstacles", "reason": "no validated lineage-specific implementation"},
            {"method": "Maya day-sign meanings", "reason": "no named Maya source attached; meanings omitted"},
            {"method": "JPL DE440/DE441 validation", "reason": "download blocked (HTTP 403); DE421 used instead"},
            {"method": "BaZi annual/monthly beyond listed years", "reason": "not requested"},
        ],
    }
    verification_summary = {
        "rows": len(verification), "pass": sum(r["status"] == "pass" for r in verification),
        "alert": sum(r["status"] == "alert" for r in verification), "fail": sum(r["status"] == "FAIL" for r in verification),
        "max_planet_diff_arcsec": max(r["difference"] for r in verification if r["datum"].endswith("tropical longitude")) * 3600,
        "max_angle_diff_deg": max(r["difference"] for r in verification if r["datum"] in ("Ascendant (tropical)", "MC (tropical)")),
        "max_solar_term_diff_seconds": max(t["diff_seconds"] for t in terms.values()),
        "thresholds": THRESH,
    }
    master["verification_summary"] = verification_summary

    # ---------------------------------------------------------------- manifest
    src_hash = hashlib.sha256()
    for f in sorted(list((ENGINE / "sixc").glob("*.py")) + [ENGINE / "build.py", ENGINE / "synth.py", ENGINE / "js" / "ziwei.mjs"]):
        if f.exists():
            src_hash.update(f.read_bytes())
    pkgs = {}
    for n in ("pyswisseph", "skyfield", "jplephem", "numpy", "tzdata", "timezonefinder", "lunar_python", "convertdate",
              "py-iztro", "pythonmonkey", "pydantic"):
        try:
            pkgs[n] = md.version(n)
        except md.PackageNotFoundError:
            pkgs[n] = "not installed"
    import subprocess
    node_v = subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip()
    ephe = {f.name: {"bytes": f.stat().st_size, "sha256": hashlib.sha256(f.read_bytes()).hexdigest()}
            for f in sorted((ENGINE / "ephe").glob("*")) if f.is_file()}
    manifest = {
        "runtime": {"python": sys.version, "platform": platform.platform(), "node": node_v},
        "packages": pkgs, "npm": {"iztro": zw["iztro_version"]},
        "swiss_ephemeris_version": swe.version,
        "ephemeris_files": ephe,
        "ephemeris_sources": {"se1": "https://github.com/aloistr/swisseph (ephe/)", "de421.bsp": "skyfielders/python-skyfield ci/ (JPL DE421 copy)"},
        "iana": {"tzdata_package": civil["tzdata_package"], "iana_release": civil["iana_release"]},
        "conventions": master["conventions"], "thresholds": THRESH,
        "source_sha256": src_hash.hexdigest(),
        "executed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "input_file_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
    }

    (out_dir / "MASTER_DATASET.json").write_text(json.dumps(master, ensure_ascii=False, indent=1, default=str))
    (out_dir / "VERIFICATION_REPORT.json").write_text(json.dumps({"summary": verification_summary, "rows": verification}, ensure_ascii=False, indent=1, default=str))
    (out_dir / "CALCULATION_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1, default=str))
    from sixc import render
    render.input_audit(out_dir, master)
    render.master_md(out_dir, master)
    render.verification_md(out_dir, verification, verification_summary)
    print(json.dumps(verification_summary, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
