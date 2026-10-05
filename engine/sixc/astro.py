"""Shared astronomical base: civil-time audit, Swiss Ephemeris primary, Skyfield/JPL validator.

Facts only. No interpretation.
"""
import math
import datetime as dt
import zoneinfo
from pathlib import Path

import swisseph as swe
from skyfield.api import load_file, load, wgs84
from skyfield.framelib import ecliptic_frame
from skyfield import almanac

# Force the pinned tzdata package (not the OS database) so the IANA release is recorded exactly.
zoneinfo.reset_tzpath([])
import tzdata  # noqa: E402

ENGINE_DIR = Path(__file__).resolve().parent.parent
EPHE_DIR = ENGINE_DIR / "ephe"
swe.set_ephe_path(str(EPHE_DIR))

TS = load.timescale(builtin=True)
JPL = load_file(str(EPHE_DIR / "de421.bsp"))
EARTH = JPL["earth"]

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
         "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

PLANETS = {
    "Sun": (swe.SUN, "sun"),
    "Moon": (swe.MOON, "moon"),
    "Mercury": (swe.MERCURY, "mercury"),
    "Venus": (swe.VENUS, "venus"),
    "Mars": (swe.MARS, "mars barycenter"),
    "Jupiter": (swe.JUPITER, "jupiter barycenter"),
    "Saturn": (swe.SATURN, "saturn barycenter"),
    "Uranus": (swe.URANUS, "uranus barycenter"),
    "Neptune": (swe.NEPTUNE, "neptune barycenter"),
    "Pluto": (swe.PLUTO, "pluto barycenter"),
}
TRADITIONAL = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]

SE_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED  # geocentric apparent, true equinox of date


def norm(x):
    return x % 360.0


def angdiff(a, b):
    """Signed smallest difference a-b in degrees, in (-180, 180]."""
    d = (a - b + 180.0) % 360.0 - 180.0
    return d


def sign_of(lon):
    return int(norm(lon) // 30)


def fmt_dms(lon):
    lon = norm(lon)
    s = int(lon // 30)
    d = lon - 30 * s
    deg = int(d)
    m = (d - deg) * 60
    return f"{deg:02d}°{int(m):02d}'{(m - int(m)) * 60:04.1f}\" {SIGNS[s]}"


# ---------------------------------------------------------------- time
def civil_audit(inp):
    tzname = inp["location"]["iana_zone"]
    z = zoneinfo.ZoneInfo(tzname)
    y, mo, d = map(int, inp["normalized"]["date"].split("-"))
    hh, mm = map(int, inp["normalized"]["time_24h"].split(":"))
    local = dt.datetime(y, mo, d, hh, mm, tzinfo=z)
    # ambiguity / gap check (fold)
    alt = local.replace(fold=1)
    ambiguous = alt.utcoffset() != local.utcoffset()
    roundtrip = local.astimezone(dt.timezone.utc).astimezone(z)
    gap = (roundtrip.hour, roundtrip.minute) != (hh, mm)
    utc = local.astimezone(dt.timezone.utc)
    return {
        "iana_zone": tzname,
        "tzdata_package": tzdata.__version__,
        "iana_release": tzdata.IANA_VERSION,
        "utc_offset": str(local.utcoffset()),
        "utc_offset_hours": local.utcoffset().total_seconds() / 3600,
        "dst_active": bool(local.dst()),
        "ambiguous_fold": ambiguous,
        "nonexistent_gap": gap,
        "local_iso": local.isoformat(),
        "utc_iso": utc.isoformat(),
        "weekday": local.strftime("%A"),
        "post_1970_tzdb_reliable": y >= 1970,
    }, utc


def jd_ut(utc):
    h = utc.hour + utc.minute / 60 + utc.second / 3600 + utc.microsecond / 3.6e9
    return swe.julday(utc.year, utc.month, utc.day, h, swe.GREG_CAL)


def jd_to_utc(jd):
    y, m, d, h = swe.revjul(jd, swe.GREG_CAL)
    base = dt.datetime(y, m, d, tzinfo=dt.timezone.utc)
    return base + dt.timedelta(hours=h)


def solar_times(jd, lon, lat, alt, tz_offset_h):
    """Local mean and apparent solar time."""
    utc = jd_to_utc(jd)
    lmt = utc + dt.timedelta(hours=lon / 15.0)
    eot_days = swe.time_equ(jd)  # LAT - LMT, in days
    if isinstance(eot_days, tuple):
        eot_days = eot_days[0]
    lat_t = lmt + dt.timedelta(days=eot_days)
    return {
        "local_mean_time": lmt.replace(tzinfo=None).isoformat(timespec="seconds"),
        "local_apparent_time": lat_t.replace(tzinfo=None).isoformat(timespec="seconds"),
        "equation_of_time_minutes": eot_days * 1440,
        "lmt_minus_civil_minutes": (lon / 15.0 - tz_offset_h) * 60,
        "lat_minus_civil_minutes": (lon / 15.0 - tz_offset_h) * 60 + eot_days * 1440,
    }


def sunrise_sunset_se(jd_birth, lon, lat, alt):
    """Swiss Ephemeris: upper limb, standard refraction. Returns events for the civil day around birth."""
    geopos = (lon, lat, alt)
    out = {}
    start = jd_birth - 0.75
    for name, flag in (("sunrise", swe.CALC_RISE), ("sunset", swe.CALC_SET)):
        res = swe.rise_trans(start, swe.SUN, flag, geopos, 1013.25, 15.0, swe.FLG_SWIEPH)
        out[name] = res[1][0]
    # next sunset after birth too
    res = swe.rise_trans(jd_birth, swe.SUN, swe.CALC_SET, geopos, 1013.25, 15.0, swe.FLG_SWIEPH)
    out["next_sunset"] = res[1][0]
    res = swe.rise_trans(jd_birth - 1.0, swe.SUN, swe.CALC_RISE, geopos, 1013.25, 15.0, swe.FLG_SWIEPH)
    out["prev_sunrise"] = res[1][0]
    return out


def sunrise_sunset_sf(utc, lon, lat, alt):
    topos = wgs84.latlon(lat, lon, elevation_m=alt)
    t0 = TS.from_datetime(utc - dt.timedelta(hours=18))
    t1 = TS.from_datetime(utc + dt.timedelta(hours=18))
    f = almanac.sunrise_sunset(JPL, topos)
    times, events = almanac.find_discrete(t0, t1, f)
    return [(t.utc_datetime(), "sunrise" if e else "sunset") for t, e in zip(times, events)]


def sun_altitude(jd, lon, lat, alt):
    xx, _ = swe.calc_ut(jd, swe.SUN, SE_FLAGS | swe.FLG_EQUATORIAL)
    az = swe.azalt(jd, swe.EQU2HOR, (lon, lat, alt), 1013.25, 15.0, (xx[0], xx[1], xx[2]))
    return {"true_altitude": az[1], "apparent_altitude": az[2], "azimuth": az[0]}


def sun_altitude_sf(utc, lon, lat, alt):
    topos = EARTH + wgs84.latlon(lat, lon, elevation_m=alt)
    t = TS.from_datetime(utc)
    a = topos.at(t).observe(JPL["sun"]).apparent()
    altd, az, _ = a.altaz()
    return altd.degrees


# ---------------------------------------------------------------- positions
def se_positions(jd, sidereal=False, ayanamsha=swe.SIDM_LAHIRI):
    flags = SE_FLAGS
    if sidereal:
        swe.set_sid_mode(ayanamsha, 0, 0)
        flags |= swe.FLG_SIDEREAL
    out = {}
    for name, (pid, _) in PLANETS.items():
        xx, _ = swe.calc_ut(jd, pid, flags)
        out[name] = {"lon": xx[0], "lat": xx[1], "dist_au": xx[2], "speed": xx[3], "retrograde": xx[3] < 0}
    for name, pid in (("TrueNode", swe.TRUE_NODE), ("MeanNode", swe.MEAN_NODE)):
        xx, _ = swe.calc_ut(jd, pid, flags)
        out[name] = {"lon": xx[0], "lat": xx[1], "speed": xx[3], "retrograde": xx[3] < 0}
    return out


def ayanamsha(jd, mode=swe.SIDM_LAHIRI):
    swe.set_sid_mode(mode, 0, 0)
    return swe.get_ayanamsa_ex_ut(jd, swe.FLG_SWIEPH)[1]


def sf_positions(utc):
    t = TS.from_datetime(utc)
    e = EARTH.at(t)
    out = {}
    for name, (_, key) in PLANETS.items():
        app = e.observe(JPL[key]).apparent()
        lat, lon, dist = app.frame_latlon(ecliptic_frame)
        out[name] = {"lon": lon.degrees, "lat": lat.degrees}
    return out


def se_houses(jd, lat, lon, hsys=b"W", sidereal=False, ayan=swe.SIDM_LAHIRI):
    if sidereal:
        swe.set_sid_mode(ayan, 0, 0)
        cusps, ascmc = swe.houses_ex(jd, lat, lon, hsys, swe.FLG_SIDEREAL)
    else:
        cusps, ascmc = swe.houses_ex(jd, lat, lon, hsys)
    return {"cusps": list(cusps), "asc": ascmc[0], "mc": ascmc[1], "armc": ascmc[2], "vertex": ascmc[3]}


def sf_asc_mc(utc, lat, lon):
    """Independent angle computation: Skyfield GAST + true obliquity, spherical-trig formulae."""
    t = TS.from_datetime(utc)
    gast_h = t.gast
    ramc = math.radians(norm(gast_h * 15.0 + lon))
    # true obliquity of date from Skyfield nutation machinery
    from skyfield.nutationlib import iau2000b_radians, mean_obliquity
    dpsi, deps = iau2000b_radians(t)
    eps = math.radians(mean_obliquity(t.tdb) / 3600.0) + deps
    phi = math.radians(lat)
    mc = math.degrees(math.atan2(math.sin(ramc), math.cos(ramc) * math.cos(eps)))
    asc = math.degrees(math.atan2(math.cos(ramc), -(math.sin(ramc) * math.cos(eps) + math.tan(phi) * math.sin(eps))))
    return {"asc": norm(asc), "mc": norm(mc), "ramc": math.degrees(ramc), "true_obliquity": math.degrees(eps)}


def mean_node_meeus(jd_ut_val):
    """Independent mean lunar ascending node (Meeus, Astronomical Algorithms 2nd ed., eq. 47.7)."""
    jde = jd_ut_val + swe.deltat(jd_ut_val)
    T = (jde - 2451545.0) / 36525.0
    om = 125.0445479 - 1934.1362891 * T + 0.0020754 * T * T + T ** 3 / 467441 - T ** 4 / 60616000
    return norm(om)


# ---------------------------------------------------------------- solar longitude events
def se_sun_lon(jd):
    return swe.calc_ut(jd, swe.SUN, SE_FLAGS)[0][0]


def sf_sun_lon(jd):
    t = TS.ut1_jd(jd)
    app = EARTH.at(t).observe(JPL["sun"]).apparent()
    return app.frame_latlon(ecliptic_frame)[1].degrees


def find_sun_crossing(target, jd_guess, fn, window=20.0):
    """Bisection for instant when apparent solar longitude == target (deg)."""
    a, b = jd_guess - window, jd_guess + window
    fa = angdiff(fn(a), target)
    fb = angdiff(fn(b), target)
    if fa * fb > 0:
        raise ValueError("crossing not bracketed")
    for _ in range(60):
        m = (a + b) / 2
        fm = angdiff(fn(m), target)
        if fa * fm <= 0:
            b, fb = m, fm
        else:
            a, fa = m, fm
    return (a + b) / 2


def crossing_near(lon_target, jd_birth, fn):
    """Guess the day of crossing from the Sun's ~0.9856°/day mean motion, then refine."""
    cur = fn(jd_birth)
    d = angdiff(lon_target, cur)
    guess = jd_birth + d / 0.9856
    return find_sun_crossing(lon_target, guess, fn, window=3.0)


def find_root(fn, a, b, iters=60):
    fa = fn(a)
    for _ in range(iters):
        m = (a + b) / 2
        fm = fn(m)
        if fa * fm <= 0:
            b = m
        else:
            a, fa = m, fm
    return (a + b) / 2


def boundary_crossings(value_fn, jd0, partition_deg, span_days=0.25, step_days=1 / 1440):
    """Nearest earlier/later instants at which value_fn(jd) crosses a multiple of partition_deg."""
    def cell(jd):
        return int(norm(value_fn(jd)) // partition_deg)

    c0 = cell(jd0)
    res = {"cell": c0, "prev": None, "next": None}
    for direction in ("next", "prev"):
        sgn = 1 if direction == "next" else -1
        jd = jd0
        while abs(jd - jd0) < span_days:
            jd2 = jd + sgn * step_days
            if cell(jd2) != c0:
                # refine
                lo, hi = (jd, jd2) if sgn > 0 else (jd2, jd)
                for _ in range(40):
                    m = (lo + hi) / 2
                    if (cell(m) == c0) == (sgn > 0):
                        lo = m
                    else:
                        hi = m
                res[direction] = (lo + hi) / 2
                break
            jd = jd2
    return res


def sun_return(natal_lon, jd_after, fn=se_sun_lon):
    """First instant after jd_after when the Sun returns to natal tropical longitude."""
    cur = fn(jd_after)
    d = (natal_lon - cur) % 360.0
    guess = jd_after + d / 0.9856
    return find_sun_crossing(natal_lon, guess, fn, window=3.0)
