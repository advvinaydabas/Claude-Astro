"""FINAL_READING.md generator. Every sentence is templated from SYNTHESIS.json / MASTER_DATASET.json fields."""
from .astro import fmt_dms

POL_TEXT = {"positive": "on balance supported", "negative": "on balance complicated (more challenging than supportive factors)",
            "mixed": "emphasized with both supportive and complicating factors", "neutral": "without scored factors"}
CL_NAME = {"jyotisha": "Jyotisha", "western": "Western/Hellenistic", "sinic": "Sinic (BaZi + Zi Wei, one vote)"}


def _basis(S, dom, cluster):
    rows = [p for p in S["projections"] if p["domain"] == dom and p["cluster"] == cluster]
    return " | ".join(f"{p['system']}: {p['basis']}" for p in rows) or "no projection"


def write_reading(out, M, S):
    c = M["civil_time"]
    vs = M["verification_summary"]
    L = ["# Six-culture verified chart — final reading", "",
         "> This is a computed comparison of traditional symbolic systems. It is not a scientifically validated forecast, "
         "and nothing below is a prediction of fate, health, money, legal or life events.", ""]
    # 1 input & sensitivity
    L += ["## 1. Input and sensitivity", "",
          f"- Birth instant: **{c['local_iso']}** ({c['weekday']}), {c['iana_zone']} UTC+{c['utc_offset']} (DST {'active' if c['dst_active'] else 'not active'}; IANA {c['iana_release']}) → **{c['utc_iso']}**.",
          f"- Location: {M['input']['location']['name']}, {M['input']['location']['lat']}° N {M['input']['location']['lon']}° E (city-level).",
          f"- Local apparent solar time {c['local_apparent_time'][11:]}; sunrise {c['sunrise_local'][11:19]}, sunset {c['sunset_local'][11:19]}.",
          f"- Time-uncertainty interval: ±{M['input']['normalized']['uncertainty_minutes']} min (recorded to the minute). "
          + (f"All {len(M['time_uncertainty']['stability_primary'])} tracked time-sensitive outputs are **stable** across that interval"
             if all(v == "stable" for v in M["time_uncertainty"]["stability_primary"].values())
             else "Sensitive outputs: " + ", ".join(k for k, v in M["time_uncertainty"]["stability_primary"].items() if v != "stable"))
          + ("; all are also stable across the birthplace coordinate box." if all(v == "stable" for v in M["location_uncertainty"]["stability"].values())
             else "; location-sensitive: " + ", ".join(k for k, v in M["location_uncertainty"]["stability"].items() if v != "stable") + "."),
          "- Material boundaries:"]
    for b in M["boundaries"]:
        L.append(f"  - {b['boundary']}: nearest {b['nearest_minutes']:.1f} min — affects {b['affects']}.")
    tu = M["time_uncertainty"]
    sens_diag = {k: v["changes_at_offsets_min"] for k, v in tu["diagnostic_changes"].items() if v["changes_at_offsets_min"]}
    L.append(f"- Diagnostic only (beyond the stated precision): " + "; ".join(f"{k} would change at {v} min" for k, v in sens_diag.items()) + ".")
    shift = list(tu["vimshottari_date_shift_minutes_at_interval_edges"].values())[0] / 1440
    L.append(f"- Vimshottari boundaries carry ±{abs(shift):.1f} days from the ±1 min interval; Da Yun start carries ±{M['bazi']['da_yun']['exact']['uncertainty_shift_days']:.2f} days.")
    L.append("")
    # 2 verification
    L += ["## 2. Verification summary", "",
          f"- {vs['rows']} checks: {vs['pass']} pass, {vs['alert']} alert, {vs['fail']} fail.",
          f"- Swiss Ephemeris vs Skyfield/JPL DE421: largest planetary difference {vs['max_planet_diff_arcsec']:.2f}″; Ascendant/MC {vs['max_angle_diff_deg'] * 3600:.1f}″; solar terms {vs['max_solar_term_diff_seconds']:.2f} s.",
          "- Disclosed dependencies: Swiss Ephemeris files derive from JPL DE431, so the astronomical check confirms implementation rather than the dynamical model; py-iztro wraps iztro and is not independent; DE440/441 could not be downloaded (HTTP 403), so DE421 was used.",
          "- Unavailable / not computed: " + "; ".join(f"{e['method']} ({e['reason']})" for e in M["excluded_methods"]) + ".", ""]
    # 3 divergence
    dv = S["divergence"]
    L += ["## 3. Divergence rate (read this before the themes)", "",
          f"- Divergent domains: **{dv['of_all_nine']}** of all nine domains ({dv['rate_all']:.0%}); **{dv['of_sufficient']}** of domains with sufficient evidence ({dv['rate_sufficient']:.0%}).",
          "- Divergent: " + ", ".join(f"{d} {g['domain']}" for d, g in S["domain_grades"].items() if g["grade"] == "DIVERGENT") + ".", ""]
    # 4 strongest themes
    L += ["## 4. Strongest cross-cultural themes", ""]
    for grade in ("STRONG", "MODERATE"):
        for d, g in S["domain_grades"].items():
            if g["grade"] != grade:
                continue
            agreeing = [cl for cl, v in g["cluster_view"].items() if v["polarity"] == g["shared_polarity"] and cl in g["speaking_clusters"]]
            L.append(f"### {d} {g['domain']} — {grade} ({g['shared_polarity']})")
            L.append(f"{len(agreeing)} primary cluster(s) ({', '.join(CL_NAME[x] for x in agreeing)}) mark this domain as {POL_TEXT[g['shared_polarity']]}. "
                     f"Clusters with high prominence: {g['clusters_with_high_prominence']}/3. Prominence is not outcome.")
            for cl in CLUSTERS_ORDER:
                v = g["cluster_view"][cl]
                L.append(f"- **{CL_NAME[cl]}** ({v['prominence']} prominence, {v['polarity']}{', ' + v['internal'] if 'internal' in v else ''}): {_basis(S, d, cl)}")
            L.append("")
    # 5 disagreements
    L += ["## 5. Disagreements", ""]
    for d, g in S["domain_grades"].items():
        if g["grade"] != "DIVERGENT":
            continue
        cv = g["cluster_view"]
        L.append(f"### {d} {g['domain']} — DIVERGENT")
        L.append("; ".join(f"{CL_NAME[cl]} reads **{cv[cl]['polarity']}** ({cv[cl]['prominence']} prominence)" for cl in CLUSTERS_ORDER) + ". These are not averaged.")
        for cl in CLUSTERS_ORDER:
            L.append(f"- {CL_NAME[cl]}: {_basis(S, d, cl)}")
        L.append("")
    internal = [(d, g["cluster_view"]["sinic"]["internal"]) for d, g in S["domain_grades"].items() if "conflict" in g["cluster_view"]["sinic"].get("internal", "")]
    if internal:
        L.append("Inside the Sinic cluster, BaZi and Zi Wei conflict on: " + ", ".join(f"{d}" for d, _ in internal) + " (counted as mixed, one vote).")
    st = M["bazi"]["strength"]
    L.append(f"BaZi useful-element schools disagree: support-suppress favors {st['useful_element_schools']['扶抑 support-suppress (WEC-1 based)']['favorable']}, climate-regulation favors {st['useful_element_schools']['调候 climate-regulation (simplified seasonal rule)']['favorable']} (confidence {st['useful_element_confidence']}).")
    L.append("")
    # 6 weak & insufficient
    L += ["## 6. Weak and insufficient areas — do not over-read", ""]
    for d, g in S["domain_grades"].items():
        if g["grade"] in ("WEAK", "INSUFFICIENT"):
            cv = g["cluster_view"]
            L.append(f"- **{d} {g['domain']} — {g['grade']}**: " + "; ".join(f"{CL_NAME[cl]} {cv[cl]['prominence']}/{cv[cl]['polarity']}" for cl in CLUSTERS_ORDER)
                     + (". D7 is a symbolic routine/health emphasis only; no medical inference is made." if d == "D7" else "."))
    L.append("")
    # 7 temperament
    L += ["## 7. Temperament overlay", ""]
    for t, v in S["temperament"].items():
        L.append(f"- {t} {v['axis']}: **{v['grade']}** — indicated by {', '.join(CL_NAME[x] for x in v['indicated_by']) or 'none'}. "
                 f"Rules: " + "; ".join(f"{k}: {r}" for k, r in v["rules"].items()))
    ov = S["overlays"]
    L += [f"- Maya ({ov['maya']['datum']}, Long Count {M['maya']['computed']['long_count']}, Haabʼ {M['maya']['computed']['haab']}): symbolic overlay **not applied** — {ov['maya']['reason']}.",
          f"- Tibetan ({ov['tibetan']['datum']}): symbolic overlay **not applied** — {ov['tibetan']['reason']}.", ""]
    # 8 timing
    ch = S["chronology"]
    L += ["## 8. Timing", "", f"Analysis date {S['analysis_date']}. Active now:"]
    for cl in CLUSTERS_ORDER:
        L.append(f"- {CL_NAME[cl]}: " + "; ".join(ch["active_now_periods"][cl]))
    L.append("")
    if ch["current_windows"]:
        for w in ch["current_windows"]:
            L.append(f"**Current window:** {w['domain']} {w['domain_name']} — {w['grade']} ({' + '.join(CL_NAME[x] for x in w['clusters'])}), {w['start']} → {w['end']}.")
            for sgm in w["segments"]:
                L.append(f"  - {sgm['start']} → {sgm['end']}: " + "; ".join(f"{CL_NAME[k]}: {', '.join(v)}" for k, v in sgm["activating_periods"].items()))
    else:
        L.append("**No current moderate or strong window.**")
    for w in ch["next_windows"]:
        L.append(f"**Next window:** {w['domain']} {w['domain_name']} — {w['grade']} ({' + '.join(CL_NAME[x] for x in w['clusters'])}), {w['start']} → {w['end']}.")
    ns = ch["next_strong_window"]
    if ns:
        L.append(f"**Next strong (⭐, all three clusters) window:** {ns['domain']} {ns['domain_name']}, {ns['start']} → {ns['end']} — " +
                 "; ".join(f"{CL_NAME[k]}: {', '.join(v)}" for k, v in ns["activating_periods"].items()) + ".")
    L.append(f"Window edges set by Vimshottari boundaries carry ±{abs(shift):.1f} days from the birth-time interval; edges set by profections, 立春 or Chinese New Year are calendar-exact (±1 day for time-zone date rounding).")
    srs = M["western"]["solar_returns"]
    if any(r["convention_changes_result"] for r in srs):
        L.append("Solar returns were excluded from timing votes for years where the birthplace and current-residence returns put the return Ascendant in different signs: "
                 + "; ".join(f"{r['year']}: " + ", ".join(f"{k} {v['asc_sign']}" for k, v in r["locations"].items()) for r in srs if r["convention_changes_result"]) + ".")
    L.append("")
    # 9 closing
    L += ["## 9. Closing frame", "",
          "Everything above is computed symbolic corroboration among traditional systems, scored by rules declared in MAPPING_REGISTRY.json before projection. "
          "Agreement between traditions is not evidence that an event will happen, and prominence is not outcome.",
          f"Candidate claims removed: {S['removed_count']} (" + "; ".join(f"{r['claim']} — {r['reason']}" for r in S["removed_candidate_claims"]) + ")."]
    (out / "FINAL_READING.md").write_text("\n".join(L) + "\n")


CLUSTERS_ORDER = ["jyotisha", "western", "sinic"]
