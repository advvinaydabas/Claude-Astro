"""Markdown renderers for the fact files (no interpretation)."""
from .astro import fmt_dms


def _t(rows, header):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for r in rows:
        out.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(out)


def input_audit(out_dir, m):
    i, c = m["input"], m["civil_time"]
    L = ["# Input audit", "", "## Original user-entered values (unmodified)", ""]
    L += [f"- **{k}:** {v}" for k, v in i["original"].items()]
    L += ["", "## Normalized", ""]
    n = i["normalized"]
    L += [f"- Gregorian civil date: **{n['date']}** ({c['weekday']})",
          f"- Local time (24 h): **{n['time_24h']}**; certainty: {n['time_certainty']}; ensemble interval ±{n['uncertainty_minutes']} min",
          f"- Calendar: {n['calendar']}",
          f"- Gender: {n['gender']}",
          f"- Birthplace: {i['location']['name']} — {i['location']['lat']}° N, {i['location']['lon']}° E, elevation {i['location']['elevation_m']} m",
          f"- Coordinate source: {i['location']['coordinate_source']}",
          f"- Current residence: {i['current_residence']['name']} ({i['current_residence']['lat']}, {i['current_residence']['lon']}, {i['current_residence']['iana_zone']})" if i.get("current_residence") else "",
          "", "## Civil-time audit", "",
          f"- IANA zone: **{c['iana_zone']}** (coordinate lookup → {c['tz_lookup_from_coordinates']}); tzdata {c['tzdata_package']} = IANA **{c['iana_release']}**",
          f"- Historical UTC offset: **{c['utc_offset']}**, DST active: {c['dst_active']}, ambiguous: {c['ambiguous_fold']}, non-existent: {c['nonexistent_gap']}",
          f"- Local instant: `{c['local_iso']}` → UTC instant: **`{c['utc_iso']}`**",
          f"- Post-1970 tzdb coverage: {c['post_1970_tzdb_reliable']}" + ("" if c['post_1970_tzdb_reliable'] else " — pre-1970 civil time may be unreliable; seek a local historical source"),
          f"- JD(UT) {c['jd_ut']:.6f}; JD(TT) {c['jd_tt']:.6f}; ΔT {c['delta_t_seconds']:.2f} s",
          f"- Local mean time: {c['local_mean_time']}  (LMT − civil = {c['lmt_minus_civil_minutes']:.2f} min)",
          f"- Local apparent solar time: **{c['local_apparent_time']}**  (equation of time {c['equation_of_time_minutes']:+.2f} min; LAT − civil = {c['lat_minus_civil_minutes']:.2f} min)",
          f"- Sunrise {c['sunrise_local']}; sunset {c['sunset_local']}",
          "", "## Boundary audit", ""]
    rows = []
    for b in m["boundaries"]:
        detail = {k: v for k, v in b.items() if k not in ("boundary", "affects", "nearest_minutes")}
        dd = "; ".join(f"{k}={(f'{v:.2f}' if isinstance(v, float) else v)}" for k, v in detail.items() if not isinstance(v, dict))
        for k, v in detail.items():
            if isinstance(v, dict):
                dd += "; " + k + ": " + ", ".join(f"{kk}={(f'{vv:.3f}' if isinstance(vv, float) else vv)}" for kk, vv in v.items())
        rows.append([b["boundary"], f"{b['nearest_minutes']:.1f}", b["affects"], dd])
    L.append(_t(rows, ["Boundary", "Nearest distance (min)", "Outputs that would change", "Detail"]))
    tu = m["time_uncertainty"]
    L += ["", "## Time-uncertainty ensemble", "", tu["rationale"], "",
          f"Primary interval: {tu['primary_interval_minutes']} min. Vimshottari period boundaries shift at the interval edges by: "
          + ", ".join(f"birth {int(k):+d} min → {v / 1440:+.2f} days" for k, v in tu["vimshottari_date_shift_minutes_at_interval_edges"].items()), ""]
    rows = []
    for k, v in tu["stability_primary"].items():
        rows.append([k, v, ", ".join(f"{o:+d}" for o in tu["diagnostic_changes"][k]["changes_at_offsets_min"]) or "none"])
    L.append(_t(rows, ["Output", "Stability over primary interval", "Diagnostic offsets (min) at which it changes"]))
    lu = m["location_uncertainty"]
    if lu["stability"]:
        L += ["", "## Location-uncertainty check", "", lu["rationale"], ""]
        L.append(_t([[k, v] for k, v in lu["stability"].items()], ["Output", "Stability across birthplace coordinate box"]))
        sens = [k for k, v in lu["stability"].items() if v == "sensitive"]
        for k in sens:
            L.append(f"\n- `{k}` by corner: " + "; ".join(f"{c}: {lu['snapshots'][c][k]}" for c in lu["snapshots"]))
    (out_dir / "INPUT_AUDIT.md").write_text("\n".join(x for x in L if x is not None) + "\n")


def master_md(out_dir, m):
    L = ["# Master dataset (facts only)", "", "Generated from MASTER_DATASET.json. No interpretation.", ""]
    j = m["jyotisha"]["d1"]
    L += ["## Jyotisha — D1 (sidereal Lahiri, whole-sign, true node)", "",
          f"Lagna **{fmt_dms(j['lagna']['lon'])}** — {j['lagna']['nakshatra']['name']} pada {j['lagna']['nakshatra']['pada']}; D9 Lagna {j['lagna']['d9_sign']}; D10 Lagna {j['lagna']['d10_sign']}. Ayanamsha {m['astronomy']['ayanamsha_lahiri']:.6f}°", ""]
    rows = []
    for p, g in j["grahas"].items():
        comb = g["combustion"]["combust"] if g["combustion"] else "—"
        rows.append([p, fmt_dms(g["lon"]), g["house"], "R" if g["retrograde"] and p not in ("Rahu", "Ketu") else "",
                     f"{g['nakshatra']['name']} {g['nakshatra']['pada']}", g["dignity"]["status"], comb,
                     ",".join(map(str, g["owns_houses"])) or "—", g["functional"]["nature"], g["d9_sign"], g["d10_sign"]])
    L.append(_t(rows, ["Graha", "Longitude", "H", "R", "Nakshatra pada", "Dignity", "Combust", "Owns", "Functional (FN-1)", "D9", "D10"]))
    L += ["", f"Planetary war: {j['planetary_war']['wars'] or 'none'} (closest pair {j['planetary_war']['closest_pair']['pair']} at {j['planetary_war']['closest_pair']['separation']:.3f}°)", "",
          "### Yogas (whitelist Y-1)", ""]
    L.append(_t([[y["id"], y["name"], y["present"], y["rule"]] for y in m["jyotisha"]["yogas"]], ["ID", "Yoga", "Present", "Rule"]))
    v = m["jyotisha"]["vimshottari"]
    L += ["", f"### Vimshottari (Moon in {v['moon_nakshatra']['name']} pada {v['moon_nakshatra']['pada']}, lord {v['moon_nakshatra']['lord']}; balance {v['balance_years_at_birth']:.4f} y)", ""]
    L.append(_t([[p["lord"], p["start"], p["end"]] for p in v["periods"][:10]], ["Mahadasha", "Start", "End"]))

    b = m["bazi"]
    L += ["", "## BaZi", "", f"Pillars (apparent solar time): **{' '.join(b['primary_pillars'])}**; civil-time track: {' '.join(b['tracks']['civil_time']['pillars'])}", ""]
    rows = []
    for p in b["pillars"]:
        rows.append([p["pillar"], p["ganzhi"], f"{p['stem']['element']} {p['stem']['polarity']}", p["stem"]["ten_god"] or "Day Master",
                     f"{p['branch']['element']} {p['branch']['polarity']}",
                     " ".join(f"{h['char']}({h['ten_god']})" for h in p["hidden_stems"]), p["na_yin_traditional_attribute"]])
    L.append(_t(rows, ["Pillar", "GZ", "Stem", "Stem Ten God", "Branch", "Hidden stems (Ten God)", "Na Yin (traditional attribute)"]))
    s = b["strength"]
    L += ["", f"Day Master {b['day_master']['char']} {b['day_master']['element']} — WEC-1 support ratio {s['support_ratio']:.3f} → **{s['verdict']}**; seasonal state {s['seasonal_state_of_day_master']}",
          f"Useful-element schools: " + "; ".join(f"{k}: {v.get('favorable')}" for k, v in s["useful_element_schools"].items()) + f" — agreement: {s['schools_agree_on'] or 'none'}", "",
          "Interactions: " + "; ".join(f"{x['type']} {x['chars']}" + (f" ({'/'.join(x['pillars'])})" if 'pillars' in x else "") for x in b["interactions"]), "",
          "Da Yun (exact): " + "; ".join(f"{p['ganzhi']} {p['start'][:10]}→{p['end'][:10]}" for p in b["da_yun"]["exact"]["periods"][:6]), ""]

    w = m["western"]
    L += ["## Western / Hellenistic (tropical, whole-sign)", "",
          f"Asc **{fmt_dms(w['asc']['lon'])}**; MC {fmt_dms(w['mc']['lon'])} (whole-sign house {w['mc']['whole_sign_house_of_mc']}); sect: {'day' if w['sect']['is_day'] else 'night'} (Sun altitude {w['sect']['sun_altitude_deg']:.2f}°)", ""]
    rows = []
    for p, x in w["planets"].items():
        e = x["essential"]
        rows.append([p, fmt_dms(x["lon"]), x["house"], x["angularity"], "R" if x["retrograde"] else "", ", ".join(e["dignities"]) or "peregrine",
                     ", ".join(e["debilities"]) or "—", x["solar_phase"] or "—", x["sect"] or "—"])
    L.append(_t(rows, ["Planet", "Longitude", "H", "Angularity", "R", "Dignities", "Debilities", "Solar phase", "Sect"]))
    L += ["", "Lots: " + "; ".join(f"{k} {fmt_dms(v['lon'])} (H{v['house']}, ruler {v['ruler']})" for k, v in w["lots"].items()),
          "", "Aspects (≤3°): " + "; ".join(f"{a['a']} {a['aspect']} {a['b']} {a['orb']:.2f}° {'applying' if a['applying'] else 'separating'}" for a in w["aspects"]),
          "", f"Final dispositor(s): {w['final_dispositors'] or 'none (loop)'}", ""]

    z = m["ziwei"]["astrolabe"]
    L += ["## Zi Wei Dou Shu", "", f"Lunar date {z['lunarDate']}; Ming {z['earthlyBranchOfSoulPalace']}, Shen {z['earthlyBranchOfBodyPalace']}; life ruler {z['soul']}, body ruler {z['body']}; bureau {z['fiveElementsClass']}", ""]
    rows = []
    for p in z["palaces"]:
        rows.append([p["heavenlyStem"] + p["earthlyBranch"], p["name"] + (" (身)" if p["isBodyPalace"] else ""),
                     " ".join(f"{s['name']}{s.get('brightness') or ''}{('化' + s['mutagen']) if s.get('mutagen') else ''}" for s in p["majorStars"]) or "—",
                     " ".join(f"{s['name']}{('化' + s['mutagen']) if s.get('mutagen') else ''}" for s in p["minorStars"]) or "—",
                     f"{p['decadal']['range'][0]}–{p['decadal']['range'][1]}"])
    L.append(_t(rows, ["Palace", "Name", "Major stars", "Minor stars", "Decadal (nominal age)"]))
    my = m["maya"]["computed"]
    L += ["", "## Maya calendar", "", f"Long Count **{my['long_count']}**, Tzolkʼin **{my['tzolkin']}**, Haabʼ **{my['haab']}** (GMT 584283). Round-trip: {m['maya']['round_trip']['pass']}", "",
          "## Tibetan", "", f"{m['tibetan']['label']} year ({m['tibetan']['method']}); Mewa/Parkha/personal forces: unavailable.", "",
          "## Excluded methods", ""]
    L += [f"- {e['method']}: {e['reason']}" for e in m["excluded_methods"]]
    (out_dir / "MASTER_DATASET.md").write_text("\n".join(L) + "\n")


def verification_md(out_dir, rows, summary):
    L = ["# Verification report", "",
         f"Rows: {summary['rows']} — pass {summary['pass']}, alert {summary['alert']}, FAIL {summary['fail']}.",
         f"Largest planetary-longitude difference: {summary['max_planet_diff_arcsec']:.3f}″ (threshold {summary['thresholds']['planet_lon_deg'] * 3600:.0f}″). "
         f"Largest angle difference: {summary['max_angle_diff_deg']:.5f}° (threshold {summary['thresholds']['angle_deg']}°). "
         f"Largest solar-term difference: {summary['max_solar_term_diff_seconds']:.2f} s (threshold {summary['thresholds']['solar_term_seconds']} s).", ""]
    tab = []
    for r in rows:
        def f(v):
            if isinstance(v, float):
                return f"{v:.6f}"
            if isinstance(v, dict):
                return ", ".join(f"{k}:{vv}" for k, vv in v.items())
            return str(v)
        tab.append([r["system"], r["datum"], f(r["primary_value"]), r["validator"] or "—", f(r["validator_value"]),
                    f(r["difference"]) + (" " + r.get("difference_unit", "") if r.get("difference_unit") else ""),
                    r["confidence"], r["status"], r.get("note", "")])
    L.append(_t(tab, ["System", "Datum", "Primary", "Validator", "Validator value", "Diff", "Confidence", "Status", "Note"]))
    (out_dir / "VERIFICATION_REPORT.md").write_text("\n".join(L) + "\n")
