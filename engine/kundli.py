"""Render a North-Indian-style kundli (D1 + D9) as a standalone HTML page from MASTER_DATASET.json.

Usage: python kundli.py path/to/MASTER_DATASET.json   → writes KUNDLI.html next to it.
"""
import html
import json
import sys
from pathlib import Path

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
         "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGNS_HI = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya", "Tula", "Vrishchika",
            "Dhanu", "Makara", "Kumbha", "Meena"]
ABBR = {"Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me", "Jupiter": "Ju",
        "Venus": "Ve", "Saturn": "Sa", "Rahu": "Ra", "Ketu": "Ke"}
# North-Indian fixed house geometry on a 400×400 square: polygon, label centre, sign-number anchor
GEOM = {
    1: ([(200, 0), (300, 100), (200, 200), (100, 100)], (200, 92), (200, 172)),
    2: ([(0, 0), (200, 0), (100, 100)], (100, 36), (100, 74)),
    3: ([(0, 0), (100, 100), (0, 200)], (34, 100), (74, 100)),
    4: ([(0, 200), (100, 100), (200, 200), (100, 300)], (100, 195), (172, 200)),
    5: ([(0, 200), (100, 300), (0, 400)], (34, 300), (74, 300)),
    6: ([(0, 400), (100, 300), (200, 400)], (100, 364), (100, 326)),
    7: ([(200, 400), (100, 300), (200, 200), (300, 300)], (200, 304), (200, 228)),
    8: ([(200, 400), (300, 300), (400, 400)], (300, 364), (300, 326)),
    9: ([(400, 400), (300, 300), (400, 200)], (366, 300), (326, 300)),
    10: ([(400, 200), (300, 300), (200, 200), (300, 100)], (300, 195), (228, 200)),
    11: ([(400, 200), (300, 100), (400, 0)], (366, 100), (326, 100)),
    12: ([(400, 0), (300, 100), (200, 0)], (300, 36), (300, 74)),
}


def dms(x):
    d = int(x)
    m = int(round((x - d) * 60))
    if m == 60:
        d, m = d + 1, 0
    return f"{d}°{m:02d}′"


def chart_svg(title, lagna_sign, placements, show_deg):
    """placements: list of (abbr, sign_index, label_extra)."""
    out = [f'<svg viewBox="-6 -6 412 412" role="img" aria-label="{html.escape(title)}">',
           '<rect x="0" y="0" width="400" height="400" class="frame"/>',
           '<line x1="0" y1="0" x2="400" y2="400" class="ln"/><line x1="400" y1="0" x2="0" y2="400" class="ln"/>',
           '<polygon points="200,0 400,200 200,400 0,200" class="ln" fill="none"/>']
    by_house = {h: [] for h in range(1, 13)}
    for ab, s, extra in placements:
        h = (s - lagna_sign) % 12 + 1
        by_house[h].append((ab, extra))
    for h, (poly, (cx, cy), (sx, sy)) in GEOM.items():
        sign = (lagna_sign + h - 1) % 12
        out.append(f'<polygon points="{" ".join(f"{x},{y}" for x, y in poly)}" class="house{" lagna" if h == 1 else ""}"/>')
        out.append(f'<text x="{sx}" y="{sy}" class="signno">{sign + 1}</text>')
        items = by_house[h]
        n = len(items)
        lh = 15 if show_deg else 16
        y0 = cy - (n - 1) * lh / 2
        for i, (ab, extra) in enumerate(items):
            cls = "pl asc" if ab == "As" else "pl"
            txt = html.escape(ab) + (f'<tspan class="deg"> {html.escape(extra)}</tspan>' if extra else "")
            out.append(f'<text x="{cx}" y="{y0 + i * lh + 4:.1f}" class="{cls}">{txt}</text>')
    out.append("</svg>")
    return "\n".join(out)


def main(path):
    path = Path(path).resolve()
    M = json.loads(path.read_text())
    d1 = M["jyotisha"]["d1"]
    g = d1["grahas"]
    lag = d1["lagna"]
    lagna_sign = SIGNS.index(lag["sign"])

    p1 = [("As", lagna_sign, dms(lag["deg_in_sign"]))]
    for p, x in g.items():
        tag = ABBR[p] + ("ᴿ" if x["retrograde"] and p not in ("Rahu", "Ketu") else "")
        p1.append((tag, x["sign_index"], dms(x["deg_in_sign"])))
    d9_lagna = SIGNS.index(lag["d9_sign"])
    p9 = [("As", d9_lagna, "")] + [(ABBR[p], SIGNS.index(x["d9_sign"]), "") for p, x in g.items()]
    moon_sign = g["Moon"]["sign_index"]
    pm = [("As", lagna_sign, "")] + [(ABBR[p], x["sign_index"], "") for p, x in g.items()]

    rows = []
    order = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    rows.append(f"<tr><td><b>Lagna</b></td><td>{SIGNS_HI[lagna_sign]} ({lag['sign']})</td><td>{dms(lag['deg_in_sign'])}</td>"
                f"<td>{lag['nakshatra']['name']} {lag['nakshatra']['pada']}</td><td>1</td><td>—</td><td>{lag['d9_sign']}</td></tr>")
    for p in order:
        x = g[p]
        st = x["dignity"]["status"]
        st = "—" if st.startswith("not assigned") else st
        flags = []
        if x["retrograde"] and p not in ("Rahu", "Ketu"):
            flags.append("retrograde")
        if x["combustion"] and x["combustion"]["combust"]:
            flags.append("combust")
        rows.append(f"<tr><td><b>{p}</b></td><td>{SIGNS_HI[x['sign_index']]} ({x['sign']})</td><td>{dms(x['deg_in_sign'])}</td>"
                    f"<td>{x['nakshatra']['name']} {x['nakshatra']['pada']} <span class='muted'>({x['nakshatra']['lord']})</span></td>"
                    f"<td>{x['house']}</td><td>{st}{(' · ' + ', '.join(flags)) if flags else ''}</td><td>{x['d9_sign']}</td></tr>")

    yogas = [y for y in M["jyotisha"]["yogas"] if y["present"]]
    an = M["input"]["analysis_date"]
    cur_md = cur_ad = None
    for md in M["jyotisha"]["vimshottari"]["periods"]:
        if md["start"][:10] <= an < md["end"][:10]:
            cur_md = md
            cur_ad = next(a for a in md["antardashas"] if a["start"][:10] <= an < a["end"][:10])
    dasha_rows = []
    for md in M["jyotisha"]["vimshottari"]["periods"][:6]:
        mark = " class='now'" if md is cur_md else ""
        dasha_rows.append(f"<tr{mark}><td>{md['lord']}</td><td>{md['start'][:10]}</td><td>{md['end'][:10]}</td></tr>")
    ad_rows = "".join(f"<tr{' class=now' if a is cur_ad else ''}><td>{cur_md['lord']}–{a['lord']}</td><td>{a['start'][:10]}</td><td>{a['end'][:10]}</td></tr>"
                      for a in cur_md["antardashas"]) if cur_md else ""
    c = M["civil_time"]
    loc = M["input"]["location"]
    vim = M["jyotisha"]["vimshottari"]

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Janma Kundli</title>
<style>
:root{{--bg:#fbf8f2;--card:#fff;--ink:#2b2118;--muted:#7a6a58;--line:#b4462b;--lagna:#fdecd6;--accent:#b4462b;--deg:#8a7562;--now:#fdecd6}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#1b1612;--card:#251e18;--ink:#f1e6d8;--muted:#b3a08a;--line:#e07a52;--lagna:#3a2a1d;--accent:#e9a07c;--deg:#b9a38d;--now:#3a2a1d}}}}
:root[data-theme="dark"]{{--bg:#1b1612;--card:#251e18;--ink:#f1e6d8;--muted:#b3a08a;--line:#e07a52;--lagna:#3a2a1d;--accent:#e9a07c;--deg:#b9a38d;--now:#3a2a1d}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:1040px;margin:0 auto;padding:24px 16px 48px}}
h1{{margin:0 0 4px;font-size:26px}}h2{{font-size:17px;margin:0 0 10px;color:var(--accent)}}.muted{{color:var(--muted)}}
.meta{{color:var(--muted);margin-bottom:20px}}
.charts{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;margin-bottom:16px}}
.card{{background:var(--card);border:1px solid color-mix(in srgb,var(--line) 25%,transparent);border-radius:12px;padding:16px}}
svg{{width:100%;height:auto;display:block}}
.frame{{fill:none;stroke:var(--line);stroke-width:2}}.ln{{stroke:var(--line);stroke-width:1.4}}
.house{{fill:transparent}}.house.lagna{{fill:var(--lagna)}}
.signno{{fill:var(--muted);font-size:12px;text-anchor:middle;dominant-baseline:middle}}
.pl{{fill:var(--ink);font-size:13.5px;font-weight:600;text-anchor:middle}}.pl.asc{{fill:var(--accent)}}
.deg{{fill:var(--deg);font-weight:400;font-size:11px}}
.tw{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{text-align:left;padding:6px 8px;border-bottom:1px solid color-mix(in srgb,var(--line) 18%,transparent);white-space:nowrap}}
th{{color:var(--muted);font-weight:600}}tr.now td{{background:var(--now)}}
.grid2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px;margin-top:16px}}
ul{{margin:0;padding-left:18px}}.note{{font-size:13px;color:var(--muted);margin-top:20px}}
</style></head><body><main>
<h1>Janma Kundli</h1>
<div class="meta">{html.escape(c['local_iso'][:10])} · {html.escape(c['local_iso'][11:16])} ({html.escape(c['weekday'])}) · {html.escape(loc['name'].split(' (')[0])} {loc['lat']}°N {loc['lon']}°E<br>
Lahiri ayanamsha {M['astronomy']['ayanamsha_lahiri']:.4f}° · whole-sign houses · true node · Lagna <b>{SIGNS_HI[lagna_sign]} {dms(lag['deg_in_sign'])}</b> · Rashi (Moon sign) <b>{SIGNS_HI[moon_sign]}</b> · Janma nakshatra <b>{vim['moon_nakshatra']['name']} pada {vim['moon_nakshatra']['pada']}</b></div>
<div class="charts">
<div class="card"><h2>Lagna chart (D1 · Rashi)</h2>{chart_svg('D1 chart', lagna_sign, p1, True)}</div>
<div class="card"><h2>Navamsa (D9)</h2>{chart_svg('D9 chart', d9_lagna, p9, False)}</div>
<div class="card"><h2>Chandra chart (Moon as lagna)</h2>{chart_svg('Moon chart', moon_sign, pm, False)}</div>
</div>
<p class="muted" style="margin:-4px 0 16px;font-size:13px">North-Indian layout: houses are fixed (1st at top centre, counted anticlockwise); small numbers are sign numbers (1 = Mesha … 12 = Meena). ᴿ = retrograde.</p>
<div class="card tw"><h2>Graha positions</h2><table><thead><tr><th>Graha</th><th>Rashi</th><th>Degree</th><th>Nakshatra pada (lord)</th><th>House</th><th>Dignity</th><th>D9</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<div class="grid2">
<div class="card tw"><h2>Vimshottari Mahadasha</h2><table><thead><tr><th>Lord</th><th>From</th><th>To</th></tr></thead><tbody>{''.join(dasha_rows)}</tbody></table>
<p class="muted" style="font-size:13px;margin:8px 0 0">Balance at birth: {vim['balance_years_at_birth']:.2f} years of {vim['moon_nakshatra']['lord']}. Dates ±5 days (birth-time precision).</p></div>
<div class="card tw"><h2>Current antardashas ({cur_md['lord'] if cur_md else '—'} Mahadasha)</h2><table><thead><tr><th>Period</th><th>From</th><th>To</th></tr></thead><tbody>{ad_rows}</tbody></table></div>
</div>
<div class="card" style="margin-top:16px"><h2>Yogas present (checked whitelist)</h2><ul>{''.join(f"<li><b>{html.escape(y['name'])}</b> — {html.escape(y['rule'])}</li>" for y in yogas)}</ul></div>
<p class="note">Computed with Swiss Ephemeris, cross-checked against JPL data (largest planet difference {M['verification_summary']['max_planet_diff_arcsec']:.2f}″). This is a calculated chart, not a prediction.</p>
</main></body></html>"""
    (path.parent / "KUNDLI.html").write_text(page)
    print(path.parent / "KUNDLI.html")


if __name__ == "__main__":
    main(sys.argv[1])
