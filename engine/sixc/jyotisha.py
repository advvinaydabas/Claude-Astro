"""Jyotisha — Parāśari primary track: sidereal (Lahiri), whole-sign houses, true node.

Facts only. Rule tables are declared here so they can be audited.
"""
from .astro import SIGNS, norm, sign_of, angdiff

GRAHAS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
SEVEN = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

SIGN_LORD = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
             "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]
EXALT = {"Sun": (0, 10), "Moon": (1, 3), "Mars": (9, 28), "Mercury": (5, 15),
         "Jupiter": (3, 5), "Venus": (11, 27), "Saturn": (6, 20)}
DEBIL = {k: ((v[0] + 6) % 12, v[1]) for k, v in EXALT.items()}
# Moolatrikona: sign, start°, end° (BPHS ranges as commonly tabulated)
MOOLA = {"Sun": (4, 0, 20), "Moon": (1, 3, 30), "Mars": (0, 0, 12), "Mercury": (5, 15, 20),
         "Jupiter": (8, 0, 10), "Venus": (6, 0, 15), "Saturn": (10, 0, 20)}
NAT_FRIENDS = {
    "Sun": ({"Moon", "Mars", "Jupiter"}, {"Mercury"}, {"Venus", "Saturn"}),
    "Moon": ({"Sun", "Mercury"}, {"Mars", "Jupiter", "Venus", "Saturn"}, set()),
    "Mars": ({"Sun", "Moon", "Jupiter"}, {"Venus", "Saturn"}, {"Mercury"}),
    "Mercury": ({"Sun", "Venus"}, {"Mars", "Jupiter", "Saturn"}, {"Moon"}),
    "Jupiter": ({"Sun", "Moon", "Mars"}, {"Saturn"}, {"Mercury", "Venus"}),
    "Venus": ({"Mercury", "Saturn"}, {"Mars", "Jupiter"}, {"Sun", "Moon"}),
    "Saturn": ({"Mercury", "Venus"}, {"Jupiter"}, {"Sun", "Moon", "Mars"}),
}
NATURAL_BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}  # Mercury/Moon conditional; declared simplification
NATURAL_MALEFIC = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
COMBUST_ORB = {"Moon": 12, "Mars": 17, "Mercury": 14, "Mercury_R": 12, "Jupiter": 11,
               "Venus": 10, "Venus_R": 8, "Saturn": 15}
SPECIAL_ASPECTS = {"Mars": [4, 7, 8], "Jupiter": [5, 7, 9], "Saturn": [3, 7, 10]}

NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu",
              "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra",
              "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha",
              "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
DASHA_ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
DASHA_YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7, "Rahu": 18,
               "Jupiter": 16, "Saturn": 19, "Mercury": 17}
NAK_SPAN = 360 / 27
KENDRA = {1, 4, 7, 10}
TRIKONA = {1, 5, 9}
DUSTHANA = {6, 8, 12}


def nakshatra(lon):
    i = int(norm(lon) // NAK_SPAN)
    pada = int((norm(lon) - i * NAK_SPAN) // (NAK_SPAN / 4)) + 1
    return {"index": i, "name": NAKSHATRAS[i], "pada": pada, "lord": DASHA_ORDER[i % 9]}


def d9_sign(lon):
    s = sign_of(lon)
    n = int((norm(lon) - 30 * s) // (30 / 9))
    return (s * 9 + n) % 12


def d10_sign(lon):
    s = sign_of(lon)
    n = int((norm(lon) - 30 * s) // 3)
    return (s + n) % 12 if s % 2 == 0 else (s + 8 + n) % 12


def house_from(sign, lagna_sign):
    return (sign - lagna_sign) % 12 + 1


def dignity(planet, lon):
    if planet not in SEVEN:
        return {"status": "not assigned (node dignity is school-dependent)", "relation_to_sign_lord": None}
    s = sign_of(lon)
    deg = norm(lon) - 30 * s
    lord = SIGN_LORD[s]
    if EXALT[planet][0] == s:
        st = "exalted"
    elif DEBIL[planet][0] == s:
        st = "debilitated"
    elif MOOLA[planet][0] == s and MOOLA[planet][1] <= deg < MOOLA[planet][2]:
        st = "moolatrikona"
    elif lord == planet:
        st = "own"
    else:
        fr, ne, en = NAT_FRIENDS[planet]
        st = "friend" if lord in fr else "enemy" if lord in en else "neutral"
    return {"status": st, "sign_lord": lord}


def functional_nature(planet, owned_houses):
    """Declared rule chain FN-1 (Parāśari, simplified):
    owns 5 or 9 -> benefic (yogakaraka if also owns 4/7/10 and not 1);
    owns 1 -> benefic (lagna lord), mixed if also owns 6/8;
    owns only 3/6/8/11 among ownerships -> malefic;
    mixes 3/6/11/8 with a kendra -> mixed;
    pure kendra lord -> natural benefic becomes neutral (kendradhipati), natural malefic becomes neutral-to-good;
    2/12 only -> neutral (by association)."""
    h = set(owned_houses)
    if not h:
        return {"nature": "n/a (node, no lordship)", "rule": "FN-1"}
    bad = h & {3, 6, 8, 11}
    if h & {5, 9}:
        if h & {4, 7, 10} and 1 not in h:
            return {"nature": "yogakaraka", "rule": "FN-1"}
        return {"nature": "benefic", "rule": "FN-1"}
    if 1 in h:
        return {"nature": "mixed" if bad else "benefic", "rule": "FN-1"}
    if bad and not (h & KENDRA):
        return {"nature": "malefic", "rule": "FN-1"}
    if bad and (h & KENDRA):
        return {"nature": "mixed", "rule": "FN-1"}
    if h & KENDRA:
        return {"nature": "neutral (kendradhipati)" if planet in NATURAL_BENEFIC else "neutral-to-benefic",
                "rule": "FN-1"}
    return {"nature": "neutral", "rule": "FN-1"}


def build_d1(sid, asc_lon, node_key="TrueNode"):
    lagna = sign_of(asc_lon)
    lon = {p: sid[p]["lon"] for p in SEVEN}
    lon["Rahu"] = sid[node_key]["lon"]
    lon["Ketu"] = norm(sid[node_key]["lon"] + 180)
    speed = {p: sid[p]["speed"] for p in SEVEN}
    speed["Rahu"] = speed["Ketu"] = sid[node_key]["speed"]

    owned = {p: [] for p in GRAHAS}
    for s in range(12):
        owned[SIGN_LORD[s]].append(house_from(s, lagna))

    sun = lon["Sun"]
    rows = {}
    for p in GRAHAS:
        s = sign_of(lon[p])
        retro = speed[p] < 0 if p not in ("Rahu", "Ketu") else True
        comb = None
        if p in COMBUST_ORB or p in ("Mercury", "Venus"):
            key = f"{p}_R" if (p in ("Mercury", "Venus") and retro) else p
            orb = COMBUST_ORB.get(key)
            sep = abs(angdiff(lon[p], sun))
            comb = {"separation_from_sun": sep, "orb": orb, "combust": sep < orb}
        rows[p] = {
            "lon": lon[p], "sign": SIGNS[s], "sign_index": s, "deg_in_sign": lon[p] - 30 * s,
            "house": house_from(s, lagna), "speed": speed[p], "retrograde": retro,
            "nakshatra": nakshatra(lon[p]), "dignity": dignity(p, lon[p]),
            "owns_houses": sorted(owned[p]), "functional": functional_nature(p, owned[p]),
            "combustion": comb,
            "d9_sign": SIGNS[d9_sign(lon[p])], "d10_sign": SIGNS[d10_sign(lon[p])],
        }
    # planetary war: true planets Mars..Saturn within 1°
    wars = []
    tp = ["Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
    for i, a in enumerate(tp):
        for b in tp[i + 1:]:
            d = abs(angdiff(lon[a], lon[b]))
            if d < 1.0:
                wars.append({"pair": [a, b], "separation": d})
    closest = min(((abs(angdiff(lon[a], lon[b])), a, b) for i, a in enumerate(tp) for b in tp[i + 1:]))
    # sign aspects (graha drishti)
    aspects = []
    for p in SEVEN:
        for n in SPECIAL_ASPECTS.get(p, [7]):
            tgt_sign = (sign_of(lon[p]) + n - 1) % 12
            aspects.append({"from": p, "nth": n, "to_sign": SIGNS[tgt_sign],
                            "to_house": house_from(tgt_sign, lagna),
                            "receiving": [q for q in GRAHAS if sign_of(lon[q]) == tgt_sign]})
    houses = {}
    for h in range(1, 13):
        s = (lagna + h - 1) % 12
        lord = SIGN_LORD[s]
        houses[h] = {"sign": SIGNS[s], "lord": lord, "lord_house": rows[lord]["house"],
                     "occupants": [p for p in GRAHAS if rows[p]["house"] == h],
                     "aspected_by": sorted({a["from"] for a in aspects if a["to_house"] == h})}
    return {
        "lagna": {"lon": asc_lon, "sign": SIGNS[lagna], "deg_in_sign": asc_lon - 30 * lagna,
                  "nakshatra": nakshatra(asc_lon), "d9_sign": SIGNS[d9_sign(asc_lon)],
                  "d10_sign": SIGNS[d10_sign(asc_lon)]},
        "grahas": rows, "houses": houses, "graha_drishti": aspects,
        "planetary_war": {"rule": "Mars/Mercury/Jupiter/Venus/Saturn within 1.0° longitude",
                          "wars": wars, "closest_pair": {"pair": [closest[1], closest[2]], "separation": closest[0]}},
        "node_type": node_key,
    }


def yogas(d1):
    """Declared whitelist Y-1. Each entry stores rule text and satisfying placements."""
    g = d1["grahas"]
    H = lambda p: g[p]["house"]
    S = lambda p: g[p]["sign_index"]
    out = []

    def rel_house(a, b):
        return (S(b) - S(a)) % 12 + 1

    # 1 Pancha Mahapurusha
    names = {"Mars": "Ruchaka", "Mercury": "Bhadra", "Jupiter": "Hamsa", "Venus": "Malavya", "Saturn": "Sasa"}
    for p, nm in names.items():
        ok = g[p]["dignity"]["status"] in ("own", "exalted", "moolatrikona") and H(p) in KENDRA
        out.append({"id": f"Y-PMP-{nm}", "name": f"{nm} (Pañca Mahāpuruṣa)", "present": ok,
                    "rule": f"{p} in own/moolatrikona/exaltation sign AND in kendra (1/4/7/10) from Lagna",
                    "placements": {p: {"sign": g[p]["sign"], "house": H(p), "dignity": g[p]["dignity"]["status"]}}})
    # 2 Gajakesari
    rj = rel_house("Moon", "Jupiter")
    out.append({"id": "Y-GAJA", "name": "Gajakesari", "present": rj in KENDRA,
                "rule": "Jupiter in kendra (1/4/7/10) from Moon",
                "placements": {"Jupiter_from_Moon_house": rj}})
    # 3 Budhaditya (flagged low specificity)
    out.append({"id": "Y-BUDHA", "name": "Budhāditya", "present": S("Sun") == S("Mercury"),
                "rule": "Sun and Mercury in the same sign", "low_specificity": True,
                "note": "Mercury is never >28° from the Sun, so this occurs in a large share of charts; excluded from synthesis.",
                "placements": {"Sun": g["Sun"]["sign"], "Mercury": g["Mercury"]["sign"]}})
    # 4 Chandra-Mangala
    rm = rel_house("Moon", "Mars")
    out.append({"id": "Y-CHMA", "name": "Chandra-Maṅgala", "present": rm in (1, 7),
                "rule": "Moon and Mars conjoined (same sign) or in mutual 7th",
                "placements": {"Mars_from_Moon_house": rm}})
    # 5 Kemadruma
    flank = [p for p in ["Mars", "Mercury", "Jupiter", "Venus", "Saturn"] if rel_house("Moon", p) in (2, 12)]
    out.append({"id": "Y-KEMA", "name": "Kemadruma", "present": not flank,
                "rule": "No graha other than Sun/Rahu/Ketu in 2nd or 12th from Moon",
                "placements": {"planets_in_2nd_or_12th_from_Moon": flank}})
    # 6 Parivartana
    seen = set()
    for a in SEVEN:
        for b in SEVEN:
            if a >= b:
                continue
            if SIGN_LORD[S(a)] == b and SIGN_LORD[S(b)] == a:
                ha, hb = H(a), H(b)
                kind = "Dainya" if {ha, hb} & DUSTHANA else "Khala" if 3 in (ha, hb) else "Maha"
                out.append({"id": f"Y-PARI-{a}-{b}", "name": f"Parivartana ({kind})", "present": True,
                            "rule": "Mutual sign exchange; Dainya if a 6/8/12 house is involved, Khala if 3rd, else Maha",
                            "placements": {a: {"sign": g[a]["sign"], "house": ha}, b: {"sign": g[b]["sign"], "house": hb}}})
                seen.add((a, b))
    # 7 Raja yoga (kendra lord + trikona lord association)
    houses = d1["houses"]
    k_lords = {houses[h]["lord"] for h in KENDRA}
    t_lords = {houses[h]["lord"] for h in TRIKONA}
    ry = []
    for a in k_lords:
        for b in t_lords:
            if a == b:
                continue
            how = None
            if S(a) == S(b):
                how = "conjunction"
            elif rel_house(a, b) == 7:
                how = "mutual 7th aspect"
            elif SIGN_LORD[S(a)] == b and SIGN_LORD[S(b)] == a:
                how = "exchange"
            if how:
                key = tuple(sorted((a, b)))
                if key not in {tuple(sorted(r["pair"])) for r in ry}:
                    ry.append({"pair": [a, b], "how": how})
    out.append({"id": "Y-RAJA", "name": "Rāja yoga (kendra–trikona lord association)", "present": bool(ry),
                "rule": "A kendra lord and a different trikona lord conjoined, in mutual 7th, or in exchange",
                "placements": {"associations": ry,
                               "kendra_lords": sorted(k_lords), "trikona_lords": sorted(t_lords)}})
    # 8 Viparita raja yoga
    vr = [houses[h]["lord"] for h in DUSTHANA if H(houses[h]["lord"]) in DUSTHANA]
    out.append({"id": "Y-VIPA", "name": "Viparīta Rāja yoga", "present": bool(vr),
                "rule": "Lord of 6/8/12 placed in 6/8/12",
                "placements": {f"lord_of_{h}": {"lord": houses[h]["lord"], "in_house": H(houses[h]["lord"])} for h in DUSTHANA}})
    # 9 Neecha-bhanga (two declared classical conditions)
    for p in SEVEN:
        if g[p]["dignity"]["status"] != "debilitated":
            continue
        disp = SIGN_LORD[S(p)]
        exalt_lord = [q for q, (s, _) in EXALT.items() if s == S(p)]
        conds = []
        for q in [disp] + exalt_lord:
            if H(q) in KENDRA:
                conds.append(f"{q} in kendra from Lagna (house {H(q)})")
            if rel_house("Moon", q) in KENDRA:
                conds.append(f"{q} in kendra from Moon ({rel_house('Moon', q)})")
        out.append({"id": f"Y-NBH-{p}", "name": f"Nīcabhaṅga for {p}", "present": bool(conds),
                    "rule": "Lord of the debilitation sign, or the planet exalted in that sign, in kendra from Lagna or Moon",
                    "placements": {"debilitated": p, "sign_lord": disp, "exalted_in_sign": exalt_lord,
                                   "conditions_met": conds}})
    return out


def vimshottari(moon_sid_lon, birth_jd, year_days=365.25, depth=3):
    nk = nakshatra(moon_sid_lon)
    frac_elapsed = (norm(moon_sid_lon) - nk["index"] * NAK_SPAN) / NAK_SPAN
    lord0 = nk["lord"]
    start_idx = DASHA_ORDER.index(lord0)
    # MD start = birth - elapsed portion
    md_start = birth_jd - frac_elapsed * DASHA_YEARS[lord0] * year_days
    periods = []
    t = md_start
    for k in range(9 * 2):  # two full cycles covers any lifetime span used here
        md = DASHA_ORDER[(start_idx + k) % 9]
        md_len = DASHA_YEARS[md] * year_days
        md_end = t + md_len
        mdrec = {"level": "MD", "lord": md, "start_jd": t, "end_jd": md_end, "sub": []}
        if depth >= 2:
            ta = t
            ai = DASHA_ORDER.index(md)
            for j in range(9):
                ad = DASHA_ORDER[(ai + j) % 9]
                ad_len = md_len * DASHA_YEARS[ad] / 120
                adrec = {"level": "AD", "lord": ad, "start_jd": ta, "end_jd": ta + ad_len, "sub": []}
                if depth >= 3:
                    tp = ta
                    pi = DASHA_ORDER.index(ad)
                    for q in range(9):
                        pd = DASHA_ORDER[(pi + q) % 9]
                        pd_len = ad_len * DASHA_YEARS[pd] / 120
                        adrec["sub"].append({"level": "PD", "lord": pd, "start_jd": tp, "end_jd": tp + pd_len})
                        tp += pd_len
                mdrec["sub"].append(adrec)
                ta += ad_len
        periods.append(mdrec)
        t = md_end
    return {"moon_nakshatra": nk, "fraction_elapsed": frac_elapsed,
            "balance_years_at_birth": (1 - frac_elapsed) * DASHA_YEARS[lord0],
            "year_length_days": year_days, "periods": periods}
