"""Synthesis without double-counting. Reads MASTER_DATASET.json, writes MAPPING_REGISTRY.json, SYNTHESIS.json,
FINAL_READING.md. Every rule is declared in REGISTRY before any projection is made."""
import datetime as dt
import json
import sys
from pathlib import Path

DOMAINS = {"D1": "Self/identity", "D2": "Career/status", "D3": "Wealth/gains", "D4": "Partnership",
           "D5": "Family/roots/home", "D6": "Children/creation", "D7": "Health/routine",
           "D8": "Mind/education/craft", "D9": "Fortune/spirituality/worldview"}
AXES = {"T1": "Leadership/visibility", "T2": "Drive/initiative", "T3": "Nurturing/service",
        "T4": "Intellect/craft", "T5": "Adaptability", "T6": "Discipline/structure"}
CLUSTERS = ["jyotisha", "western", "sinic"]

REGISTRY = {
    "version": "MR-1",
    "house_to_domain": {"1": "D1", "2": "D3", "3": "D8", "4": "D5", "5": "D6", "6": "D7", "7": "D4",
                        "8": None, "9": "D9", "10": "D2", "11": "D3", "12": None},
    "house_exclusions": {"8": "longevity/death significations are out of scope", "12": "loss/expenditure is not one of the nine domains"},
    "ziwei_palace_to_domain": {"命宫": "D1", "官禄": "D2", "财帛": "D3", "夫妻": "D4", "田宅": "D5", "父母": "D5",
                               "子女": "D6", "疾厄": "D7", "福德": "D9", "兄弟": None, "仆役": None, "迁移": None},
    "bazi_family_to_domain": {"companion": ["D1"], "resource": ["D8"], "output": ["D6"], "wealth": ["D3"], "officer": ["D2"]},
    "bazi_gender_specific": {"male": {"wealth": ["D4"], "officer": ["D6"]},
                             "basis": "classical male spouse star = wealth; male children star = officer"},
    "bazi_pillar_interaction_domain": {"year": "D5", "month": "D5", "day": "D4", "hour": "D6"},
    "rules": {
        "J-HOUSE": "Jyotisha house domain. Prominence: occupants (nodes 0.5) ≥2 high, ≥1 medium, else low. Polarity score: occupant exalted/own/MT +1, debilitated −1 (0 if Nīcabhaṅga present), combust −0.5, FN benefic/yogakaraka +0.5, FN malefic −0.5; lord in kendra/trikona +1, in 6/8/12 −1; lord exalted/own/MT +1, debilitated −1 (0 with Nīcabhaṅga), lord combust −0.5.",
        "J-YOGA": "Whitelisted yogas project: Rāja → D2 +1; Parivartana (Maha) → domains of both houses +1; Chandra-Maṅgala → D3 +1; Kemadruma → D1 −1; Pañca Mahāpuruṣa → D1 +1; Gajakesari → D9 +1. Budhāditya excluded (low specificity).",
        "W-HOUSE": "Western whole-sign house domain. Prominence as J-HOUSE (7 traditional planets). Polarity score: occupant domicile/exaltation +1, detriment/fall −1, benefic of sect +1, benefic contrary +0.5, malefic contrary to sect −1, malefic of sect −0.5, combust −0.5; ruler in houses 1/2/4/5/7/9/10/11 +0.5, in 6/8/12 −1; ruler domicile/exaltation +1, detriment/fall −1.",
        "W-LOT": "Lot of Fortune → D3, Lot of Spirit → D2 (prominence medium); polarity from the Lot ruler's condition per W-HOUSE ruler terms.",
        "B-FAMILY": "BaZi Ten-God family weight (WEC-1) ≥3.0 high, ≥1.5 medium, else low → mapped domains. Polarity from the support-suppress (扶抑) favorable/unfavorable element; if the climate (调候) school contradicts, polarity = mixed.",
        "B-INTERACT": "Clash/harm/punishment/destruction touching a pillar → that pillar's domain −1; six-combination → +0.5 (no transformation asserted).",
        "Z-PALACE": "Zi Wei palace domain. Prominence: ≥2 major stars, or 1 major plus a transformation or ≥2 auspicious/malefic minors → high; 1 major → medium; empty → low (empty palace is not scored negative). Polarity: brightness 庙/旺 +1, 得/利 +0.5, 平 0, 不/陷 −1; 化禄/化权/化科 +1, 化忌 −1; 左辅/右弼/文昌/文曲/天魁/天钺 +0.5; 擎羊/陀罗/火星/铃星/地空/地劫 −0.5; 禄存 +0.5.",
        "POLARITY": "score ≥ +1 positive; ≤ −1 negative; otherwise mixed if any factor exists, neutral if none.",
        "SINIC-MERGE": "BaZi and Zi Wei are merged into ONE Sinic vote per domain: both speak with the same polarity → that polarity (internally corroborated); opposite polarities → mixed (internal conflict); one speaks → its polarity.",
        "SPEAKS": "A cluster speaks on a domain when prominence ≥ medium and polarity ≠ neutral.",
        "GRADE": "DIVERGENT if any two speaking clusters are positive vs negative; else STRONG if 3 speaking clusters share a polarity, MODERATE if 2 share, WEAK if only one speaks or speaking clusters share no polarity, INSUFFICIENT if none speak.",
        "TJ-1": "Jyotisha timing: active domains = houses owned and occupied by the Antardaśā lord + house occupied by the Mahādaśā lord.",
        "TW-1": "Western timing: profected house domain + domain of the house occupied natally by the Lord of the Year; solar-return Asc house counts only if birthplace and current-residence returns agree.",
        "TS-1": "Sinic timing: Da Yun stem family domains + annual-pillar stem family domains (year from 立春) + Zi Wei decadal palace domain + Zi Wei annual palace domain (year from Chinese New Year); union inside the cluster, one vote.",
        "WINDOW": "Moderate window: two clusters activate the same domain at the same time; Strong: all three. Exact overlap = latest start to earliest end of the constraining periods.",
    },
    "temperament_indicators": {
        "T1": {"jyotisha": "Sun in kendra (1/4/7/10) from Lagna", "western": "Sun angular",
               "sinic": "officer family ≥1.5 (WEC-1) OR 紫微/太阳 in 命宫"},
        "T2": {"jyotisha": "Mars in kendra OR Mars own/exalted/MT", "western": "Mars angular OR ≥4 of 7 planets in fire signs",
               "sinic": "companion family ≥1.5 OR 七杀/破军 in 命宫"},
        "T3": {"jyotisha": "Moon or Jupiter in kendra/trikona", "western": "Moon or Venus angular",
               "sinic": "resource family ≥1.5 OR 天同/天梁/太阴 in 命宫"},
        "T4": {"jyotisha": "Mercury in kendra/trikona", "western": "Mercury angular",
               "sinic": "output family ≥1.5 OR 天机/文昌/文曲 in 命宫"},
        "T5": {"jyotisha": "≥3 grahas (of 7) in dual signs", "western": "≥4 of 7 planets in mutable signs",
               "sinic": "Water element weight ≥3.0 OR 天机/天同 in 命宫"},
        "T6": {"jyotisha": "Saturn in kendra/trikona OR own/exalted/MT", "western": "Saturn angular OR in domicile/exaltation",
               "sinic": "officer family ≥1.5 OR 天府/天相/武曲 in 命宫"},
        "axis_grade": "3 clusters → STRONG, 2 → MODERATE, 1 → WEAK, 0 → not indicated",
        "overlays": "Maya and Tibetan meanings may only corroborate/soften/dissent and only with a named source; none attached → overlay not applied.",
    },
}


def polarity(score, n):
    if n == 0:
        return "neutral"
    if score >= 1:
        return "positive"
    if score <= -1:
        return "negative"
    return "mixed"


def prom_level(x):
    return "high" if x >= 2 else "medium" if x >= 1 else "low"


def main(master_path):
    master_path = Path(master_path).resolve()
    out = master_path.parent
    M = json.loads(master_path.read_text())
    (out / "MAPPING_REGISTRY.json").write_text(json.dumps(REGISTRY, ensure_ascii=False, indent=1))
    male = M["input"]["normalized"]["gender"] == "male"
    projections = []
    removed = []

    def proj(domain, system, cluster, prominence, pol, conf, basis, rule, score=None, factors=None):
        projections.append({"domain": domain, "system": system, "cluster": cluster, "prominence": prominence,
                            "polarity": pol, "confidence": conf, "basis": basis, "mapping_rule": rule,
                            "score": score, "factors": factors or []})

    # ------------------------------------------------------------ Jyotisha
    d1 = M["jyotisha"]["d1"]
    g = d1["grahas"]
    yog = {y["id"]: y for y in M["jyotisha"]["yogas"]}
    nbh = {y["placements"]["debilitated"] for y in M["jyotisha"]["yogas"] if y["id"].startswith("Y-NBH") and y["present"]}

    def j_planet_terms(p, as_lord=False):
        f = []
        st = g[p]["dignity"]["status"]
        if st in ("exalted", "own", "moolatrikona"):
            f.append((f"{p} {st}", 1))
        if st == "debilitated":
            f.append((f"{p} debilitated" + (" (Nīcabhaṅga → 0)" if p in nbh else ""), 0 if p in nbh else -1))
        if g[p]["combustion"] and g[p]["combustion"]["combust"]:
            f.append((f"{p} combust", -0.5))
        if not as_lord:
            fn = g[p]["functional"]["nature"]
            if fn in ("benefic", "yogakaraka"):
                f.append((f"{p} functional {fn}", 0.5))
            if fn == "malefic":
                f.append((f"{p} functional malefic", -0.5))
        return f

    jdom = {}
    for h, dom in REGISTRY["house_to_domain"].items():
        if dom is None:
            continue
        hd = d1["houses"][h]
        occ = hd["occupants"]
        cnt = sum(0.5 if p in ("Rahu", "Ketu") else 1 for p in occ)
        f = []
        for p in occ:
            if p in ("Rahu", "Ketu"):
                f.append((f"{p} in house {h}", 0))
            else:
                f.extend(j_planet_terms(p))
        lord = hd["lord"]
        lh = hd["lord_house"]
        if lh in (1, 4, 7, 10, 5, 9):
            f.append((f"lord {lord} in house {lh} (kendra/trikona)", 1))
        elif lh in (6, 8, 12):
            f.append((f"lord {lord} in house {lh} (dusthana)", -1))
        else:
            f.append((f"lord {lord} in house {lh}", 0))
        f.extend([(t.replace(lord, f"lord {lord}", 1), s) for t, s in j_planet_terms(lord, as_lord=True)])
        jdom.setdefault(dom, []).append({"house": int(h), "count": cnt, "factors": f})
    for y in M["jyotisha"]["yogas"]:
        if not y["present"]:
            continue
        if y["id"] == "Y-BUDHA":
            removed.append({"claim": "Budhāditya yoga", "reason": "low specificity (Mercury always within 28° of the Sun)"})
            continue
        targets = []
        if y["id"] == "Y-RAJA":
            targets = [("D2", 1)]
        elif y["id"].startswith("Y-PARI") and "Maha" in y["name"]:
            hs = [v["house"] for v in y["placements"].values()]
            targets = [(REGISTRY["house_to_domain"][str(x)], 1) for x in hs if REGISTRY["house_to_domain"][str(x)]]
        elif y["id"] == "Y-CHMA":
            targets = [("D3", 1)]
        elif y["id"] == "Y-KEMA":
            targets = [("D1", -1)]
        elif y["id"].startswith("Y-PMP"):
            targets = [("D1", 1)]
        elif y["id"] == "Y-GAJA":
            targets = [("D9", 1)]
        elif y["id"].startswith("Y-NBH"):
            continue  # applied inside J-HOUSE scoring
        for dom, s in targets:
            jdom.setdefault(dom, []).append({"house": None, "count": 1, "factors": [(f"yoga {y['name']}", s)]})
    for dom, items in jdom.items():
        cnt = max(i["count"] for i in items if i["house"] is not None) if any(i["house"] for i in items) else 1
        yoga_bonus = any(i["house"] is None for i in items)
        f = [x for i in items for x in i["factors"]]
        score = sum(s for _, s in f)
        nz = sum(1 for _, s in f if s != 0)
        prom = prom_level(cnt + (1 if yoga_bonus and cnt < 1 else 0))
        proj(dom, "jyotisha", "jyotisha", prom, polarity(score, nz), "medium",
             "; ".join(f"{t} ({s:+g})" for t, s in f), "J-HOUSE/J-YOGA", score, f)

    # ------------------------------------------------------------ Western
    W = M["western"]
    wp = W["planets"]
    sect = W["sect"]

    def w_planet_terms(p, as_ruler=False):
        f = []
        e = wp[p]["essential"]
        for d in e["dignities"]:
            if d in ("domicile", "exaltation"):
                f.append((f"{p} {d}", 1))
        for d in e["debilities"]:
            f.append((f"{p} {d}", -1))
        if not as_ruler:
            if p == sect["benefic_of_sect"]:
                f.append((f"{p} benefic of sect", 1))
            elif p == sect["benefic_contrary"]:
                f.append((f"{p} benefic contrary to sect", 0.5))
            elif p == sect["malefic_contrary"]:
                f.append((f"{p} malefic contrary to sect", -1))
            elif p == sect["malefic_of_sect"]:
                f.append((f"{p} malefic of sect", -0.5))
        if wp[p]["solar_phase"] == "combust":
            f.append((f"{p} combust", -0.5))
        return f

    def w_ruler_terms(r):
        f = []
        rh = wp[r]["house"]
        if rh in (1, 2, 4, 5, 7, 9, 10, 11):
            f.append((f"ruler {r} in good house {rh}", 0.5))
        elif rh in (6, 8, 12):
            f.append((f"ruler {r} in house {rh}", -1))
        f.extend([(f"ruler {t}", s) for t, s in w_planet_terms(r, as_ruler=True)])
        return f

    wdom = {}
    for h, dom in REGISTRY["house_to_domain"].items():
        if dom is None:
            continue
        hd = W["houses"][h]
        f = []
        for p in hd["occupants"]:
            f.extend(w_planet_terms(p))
        f.extend(w_ruler_terms(hd["ruler"]))
        wdom.setdefault(dom, []).append({"count": len(hd["occupants"]), "factors": f, "house": int(h)})
    for lot, dom in (("Fortune", "D3"), ("Spirit", "D2")):
        L = W["lots"][lot]
        wdom.setdefault(dom, []).append({"count": 1, "factors": [(f"Lot of {lot} in {L['sign']}", 0)] + w_ruler_terms(L["ruler"]), "house": None})
    for dom, items in wdom.items():
        house_counts = [i["count"] for i in items if i["house"] is not None]
        cnt = max(house_counts) if house_counts else 0
        if any(i["house"] is None for i in items):
            cnt = max(cnt, 1)
        f = [x for i in items for x in i["factors"]]
        score = sum(s for _, s in f)
        nz = sum(1 for _, s in f if s != 0)
        proj(dom, "western", "western", prom_level(cnt), polarity(score, nz), "medium",
             "; ".join(f"{t} ({s:+g})" for t, s in f), "W-HOUSE/W-LOT", score, f)

    # ------------------------------------------------------------ BaZi
    B = M["bazi"]
    st = B["strength"]
    fuyi = st["useful_element_schools"]["扶抑 support-suppress (WEC-1 based)"]
    tiao = st["useful_element_schools"]["调候 climate-regulation (simplified seasonal rule)"]
    gen = {"Wood": "Fire", "Fire": "Earth", "Earth": "Metal", "Metal": "Water", "Water": "Wood"}
    ctrl = {"Wood": "Earth", "Earth": "Water", "Water": "Fire", "Fire": "Metal", "Metal": "Wood"}
    dm_el = B["day_master"]["element"]
    fam_el = {"companion": dm_el, "resource": [k for k, v in gen.items() if v == dm_el][0], "output": gen[dm_el],
              "wealth": ctrl[dm_el], "officer": [k for k, v in ctrl.items() if v == dm_el][0]}
    bdom = {}
    for fam, w in st["family_weights"].items():
        el = fam_el[fam]
        prom = "high" if w >= 3 else "medium" if w >= 1.5 else "low"
        if el in fuyi.get("favorable", []):
            pol, s = "positive", 1
        elif el in fuyi.get("unfavorable", []):
            pol, s = "negative", -1
        else:
            pol, s = "neutral", 0
        note = f"{fam} ({el}) weight {w:.2f}; 扶抑 → {pol}"
        if el in tiao.get("favorable", []) and pol == "negative":
            pol, note = "mixed", note + "; 调候 favors it → mixed"
        doms = list(REGISTRY["bazi_family_to_domain"][fam])
        if male:
            doms += REGISTRY["bazi_gender_specific"]["male"].get(fam, [])
        for d in doms:
            bdom.setdefault(d, []).append({"prom": prom, "pol": pol, "factors": [(note, s if pol != "mixed" else 0)]})
    for it in B["interactions"]:
        if "pillars" not in it:
            continue
        neg = any(k in it["type"] for k in ("clash", "harm", "punishment", "destruction"))
        pos = "six combination" in it["type"]
        if not (neg or pos):
            continue
        s = -1 if neg else 0.5
        for pl in set(it["pillars"]):
            d = REGISTRY["bazi_pillar_interaction_domain"][pl]
            bdom.setdefault(d, []).append({"prom": "medium", "pol": None, "factors": [(f"{it['type']} {it['chars']} touching {pl} pillar", s)]})
    b_proj = {}
    for d, items in bdom.items():
        f = [x for i in items for x in i["factors"]]
        proms = [i["prom"] for i in items]
        prom = "high" if "high" in proms else "medium" if "medium" in proms else "low"
        mixed_flag = any(i["pol"] == "mixed" for i in items)
        score = sum(s for _, s in f)
        nz = sum(1 for _, s in f if s != 0)
        pol = polarity(score, nz)
        if mixed_flag and pol != "neutral" and abs(score) < 2:
            pol = "mixed"
        if mixed_flag and nz == 0:
            pol = "mixed"
        b_proj[d] = {"prominence": prom, "polarity": pol, "score": score, "factors": f}
        proj(d, "bazi", "sinic", prom, pol, "low", "; ".join(f"{t} ({s:+g})" for t, s in f), "B-FAMILY/B-INTERACT", score, f)

    # ------------------------------------------------------------ Zi Wei
    Z = M["ziwei"]["astrolabe"]
    bright = {"庙": 1, "旺": 1, "得": 0.5, "利": 0.5, "平": 0, "不": -1, "陷": -1}
    good_minor = set("左辅 右弼 文昌 文曲 天魁 天钺".split())
    bad_minor = set("擎羊 陀罗 火星 铃星 地空 地劫".split())
    z_proj = {}
    for p in Z["palaces"]:
        d = REGISTRY["ziwei_palace_to_domain"].get(p["name"])
        if d is None:
            continue
        f = []
        for s in p["majorStars"]:
            if s.get("brightness"):
                f.append((f"{s['name']} {s['brightness']}", bright.get(s["brightness"], 0)))
            if s.get("mutagen"):
                f.append((f"{s['name']} 化{s['mutagen']}", -1 if s["mutagen"] == "忌" else 1))
        nminor = 0
        for s in p["minorStars"]:
            if s["name"] in good_minor:
                f.append((s["name"], 0.5)); nminor += 1
            elif s["name"] in bad_minor:
                f.append((s["name"], -0.5)); nminor += 1
            elif s["name"] == "禄存":
                f.append((s["name"], 0.5))
            if s.get("mutagen"):
                f.append((f"{s['name']} 化{s['mutagen']}", -1 if s["mutagen"] == "忌" else 1))
        nmaj = len(p["majorStars"])
        has_mut = any(s.get("mutagen") for s in p["majorStars"] + p["minorStars"])
        prom = "high" if nmaj >= 2 or (nmaj == 1 and (has_mut or nminor >= 2)) else "medium" if nmaj == 1 else "low"
        if p["isBodyPalace"] and prom == "medium":
            prom = "high"
            f.append(("Body palace (身宫) here", 0))
        score = sum(s for _, s in f)
        nz = sum(1 for _, s in f if s != 0)
        pol = polarity(score, nz)
        prev = z_proj.get(d)
        rec = {"prominence": prom, "polarity": pol, "score": score, "factors": f, "palace": p["name"]}
        proj(d, "ziwei", "sinic", prom, pol, "medium", f"{p['name']}: " + "; ".join(f"{t} ({s:+g})" for t, s in f), "Z-PALACE", score, f)
        if prev:  # D5 has two palaces: combine by summing
            rec = {"prominence": max(prev["prominence"], prom, key=["low", "medium", "high"].index),
                   "polarity": polarity(prev["score"] + score, nz + sum(1 for _, s in prev["factors"] if s)),
                   "score": prev["score"] + score, "factors": prev["factors"] + f, "palace": prev["palace"] + "+" + p["name"]}
        z_proj[d] = rec

    # ------------------------------------------------------------ cluster votes
    def speaks(pr):
        return pr and pr["prominence"] in ("medium", "high") and pr["polarity"] != "neutral"

    cluster_view = {}
    for d in DOMAINS:
        jv = next((p for p in projections if p["domain"] == d and p["cluster"] == "jyotisha"), None)
        wv = next((p for p in projections if p["domain"] == d and p["cluster"] == "western"), None)
        bv, zv = b_proj.get(d), z_proj.get(d)
        bs, zs = speaks(bv), speaks(zv)
        if bs and zs:
            if bv["polarity"] == zv["polarity"]:
                sv = {"prominence": max(bv["prominence"], zv["prominence"], key=["low", "medium", "high"].index),
                      "polarity": bv["polarity"], "internal": "BaZi and Zi Wei agree"}
            elif {bv["polarity"], zv["polarity"]} == {"positive", "negative"}:
                sv = {"prominence": "medium", "polarity": "mixed", "internal": "BaZi and Zi Wei conflict"}
            else:
                sv = {"prominence": max(bv["prominence"], zv["prominence"], key=["low", "medium", "high"].index),
                      "polarity": "mixed", "internal": f"BaZi {bv['polarity']} / Zi Wei {zv['polarity']}"}
        elif bs or zs:
            src = bv if bs else zv
            sv = {"prominence": src["prominence"], "polarity": src["polarity"], "internal": ("BaZi" if bs else "Zi Wei") + " only"}
        else:
            sv = {"prominence": "low", "polarity": "neutral", "internal": "neither speaks"}
        cluster_view[d] = {
            "jyotisha": {"prominence": jv["prominence"], "polarity": jv["polarity"]} if jv else {"prominence": "low", "polarity": "neutral"},
            "western": {"prominence": wv["prominence"], "polarity": wv["polarity"]} if wv else {"prominence": "low", "polarity": "neutral"},
            "sinic": sv,
        }
    grades = {}
    for d, cv in cluster_view.items():
        sp = {c: v for c, v in cv.items() if speaks(v)}
        pols = [v["polarity"] for v in sp.values()]
        if "positive" in pols and "negative" in pols:
            grade = "DIVERGENT"
            theme = None
        elif not sp:
            grade, theme = "INSUFFICIENT", None
        else:
            best = max(set(pols), key=pols.count)
            n = pols.count(best)
            grade = "STRONG" if n == 3 else "MODERATE" if n == 2 else "WEAK"
            theme = best if n >= 2 else None
        prom_agree = sum(1 for v in cv.values() if v["prominence"] == "high")
        grades[d] = {"domain": DOMAINS[d], "grade": grade, "shared_polarity": theme,
                     "speaking_clusters": sorted(sp), "clusters_with_high_prominence": prom_agree, "cluster_view": cv}
    n_div = sum(1 for g_ in grades.values() if g_["grade"] == "DIVERGENT")
    n_suff = sum(1 for g_ in grades.values() if g_["grade"] != "INSUFFICIENT")
    divergence = {"divergent_domains": n_div, "of_all_nine": f"{n_div}/9", "rate_all": n_div / 9,
                  "domains_with_sufficient_evidence": n_suff,
                  "of_sufficient": f"{n_div}/{n_suff}", "rate_sufficient": n_div / n_suff if n_suff else None}

    # ------------------------------------------------------------ temperament
    ming = next(p for p in Z["palaces"] if p["name"] == "命宫")
    ming_stars = {s["name"] for s in ming["majorStars"] + ming["minorStars"]}
    fw = st["family_weights"]
    ew = st["element_weights"]
    sid_sign = {p: g[p]["sign_index"] for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]}
    trop_sign = {p: ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"].index(wp[p]["sign"]) for p in wp}
    KT = (1, 4, 7, 10, 5, 9)
    ind = {
        "T1": {"jyotisha": g["Sun"]["house"] in (1, 4, 7, 10), "western": wp["Sun"]["angularity"] == "angular",
               "sinic": fw["officer"] >= 1.5 or bool({"紫微", "太阳"} & ming_stars)},
        "T2": {"jyotisha": g["Mars"]["house"] in (1, 4, 7, 10) or g["Mars"]["dignity"]["status"] in ("own", "exalted", "moolatrikona"),
               "western": wp["Mars"]["angularity"] == "angular" or sum(1 for s in trop_sign.values() if s % 4 == 0) >= 4,
               "sinic": fw["companion"] >= 1.5 or bool({"七杀", "破军"} & ming_stars)},
        "T3": {"jyotisha": g["Moon"]["house"] in KT or g["Jupiter"]["house"] in KT,
               "western": wp["Moon"]["angularity"] == "angular" or wp["Venus"]["angularity"] == "angular",
               "sinic": fw["resource"] >= 1.5 or bool({"天同", "天梁", "太阴"} & ming_stars)},
        "T4": {"jyotisha": g["Mercury"]["house"] in KT, "western": wp["Mercury"]["angularity"] == "angular",
               "sinic": fw["output"] >= 1.5 or bool({"天机", "文昌", "文曲"} & ming_stars)},
        "T5": {"jyotisha": sum(1 for s in sid_sign.values() if s % 3 == 2) >= 3,
               "western": sum(1 for s in trop_sign.values() if s % 3 == 2) >= 4,
               "sinic": ew["Water"] >= 3.0 or bool({"天机", "天同"} & ming_stars)},
        "T6": {"jyotisha": g["Saturn"]["house"] in KT or g["Saturn"]["dignity"]["status"] in ("own", "exalted", "moolatrikona"),
               "western": wp["Saturn"]["angularity"] == "angular" or bool({"domicile", "exaltation"} & set(wp["Saturn"]["essential"]["dignities"])),
               "sinic": fw["officer"] >= 1.5 or bool({"天府", "天相", "武曲"} & ming_stars)},
    }
    temperament = {}
    for t, v in ind.items():
        n = sum(v.values())
        temperament[t] = {"axis": AXES[t], "indicated_by": [c for c, x in v.items() if x],
                          "grade": {3: "STRONG", 2: "MODERATE", 1: "WEAK", 0: "not indicated"}[n],
                          "rules": REGISTRY["temperament_indicators"][t]}
    overlays = {"maya": {"datum": M["maya"]["computed"]["tzolkin"], "applied": False,
                         "reason": "no named historical or living Maya source attached for day-sign meaning"},
                "tibetan": {"datum": M["tibetan"]["label"], "applied": False,
                            "reason": "no sourced, lineage-specific meaning method validated"}}
    removed.append({"claim": "Maya day-sign personality description", "reason": "no named source"})
    removed.append({"claim": "Tibetan element-animal personality description", "reason": "no validated sourced method"})

    # ------------------------------------------------------------ chronology
    an = dt.date.fromisoformat(M["input"]["analysis_date"])
    t0, t1 = dt.date(an.year - 2, 1, 1), dt.date(an.year + 10, 12, 31)
    H2D = REGISTRY["house_to_domain"]

    def d_(s):
        return dt.date.fromisoformat(s[:10])

    j_segs = []
    for md in M["jyotisha"]["vimshottari"]["periods"]:
        if d_(md["end"]) < t0 or d_(md["start"]) > t1:
            continue
        for ad in md["antardashas"]:
            if d_(ad["end"]) < t0 or d_(ad["start"]) > t1:
                continue
            doms = set()
            L = ad["lord"]
            for h in g[L]["owns_houses"] + [g[L]["house"]]:
                if H2D[str(h)]:
                    doms.add(H2D[str(h)])
            if H2D[str(g[md["lord"]]["house"])]:
                doms.add(H2D[str(g[md["lord"]]["house"])])
            j_segs.append({"start": ad["start"], "end": ad["end"], "label": f"{md['lord']}–{L} daśā", "domains": sorted(doms)})
    w_segs = []
    sr_by_year = {}
    for r in W["solar_returns"]:
        if not r["convention_changes_result"]:
            hh = next(iter(r["locations"].values()))["sr_asc_in_natal_whole_sign_house"]
            sr_by_year[r["year"]] = H2D[str(hh)]
    for p in W["profections"]:
        if d_(p["end"]) < t0 or d_(p["start"]) > t1:
            continue
        doms = set(x for x in (H2D[str(p["house"])], H2D[str(p["lord_natal_house"])]) if x)
        lab = f"profection age {p['age']} (house {p['house']}, {p['sign']}, Lord {p['lord_of_year']})"
        sry = d_(p["start"]).year
        if sry in sr_by_year and sr_by_year[sry]:
            doms.add(sr_by_year[sry])
            lab += " + solar return (locations agree)"
        w_segs.append({"start": p["start"], "end": p["end"], "label": lab, "domains": sorted(doms)})
    fam_dom = {}
    for fam, ds in REGISTRY["bazi_family_to_domain"].items():
        fam_dom[fam] = list(ds) + (REGISTRY["bazi_gender_specific"]["male"].get(fam, []) if male else [])
    from sixc.bazi import ten_god, TEN_GOD_FAMILY
    dm = B["day_master"]["char"]
    s_segs_src = []
    for p in B["da_yun"]["exact"]["periods"]:
        fam = TEN_GOD_FAMILY[ten_god(dm, p["ganzhi"][0])]
        s_segs_src.append({"start": p["start"], "end": p["end"], "label": f"Da Yun {p['ganzhi']} ({ten_god(dm, p['ganzhi'][0])})", "domains": fam_dom[fam]})
    for a in B["annual_pillars"]:
        fam = TEN_GOD_FAMILY[a["stem_ten_god"]]
        s_segs_src.append({"start": a["lichun_utc"], "end": a["end_utc"], "label": f"year {a['ganzhi']} ({a['stem_ten_god']})", "domains": fam_dom[fam]})
    for dcd in M["ziwei"]["decadal_periods"]:
        dom = REGISTRY["ziwei_palace_to_domain"].get(dcd["natal_palace_name"])
        s_segs_src.append({"start": dcd["start"], "end": dcd["end"], "label": f"Zi Wei decadal {dcd['decadal_stem_branch']} in {dcd['natal_palace_name']}", "domains": [dom] if dom else []})
    for a in M["ziwei"]["annual_periods"]:
        dom = REGISTRY["ziwei_palace_to_domain"].get(a["natal_palace_at_yearly_ming"])
        s_segs_src.append({"start": a["start"], "end": a["end"], "label": f"Zi Wei year {a['ganzhi']} in {a['natal_palace_at_yearly_ming']}", "domains": [dom] if dom else []})

    def active(segs, day):
        return [s for s in segs if d_(s["start"]) <= day < d_(s["end"]) and s["domains"]]

    def doms_of(segs):
        return set(x for s in segs for x in s["domains"])

    windows = []
    open_w = {}
    d = t0
    seg_sets = {"jyotisha": j_segs, "western": w_segs, "sinic": s_segs_src}
    while d <= t1 + dt.timedelta(days=1):
        act = {c: active(seg_sets[c], d) for c in CLUSTERS} if d <= t1 else {c: [] for c in CLUSTERS}
        keys_today = set()
        for dom in DOMAINS:
            cl = tuple(c for c in CLUSTERS if dom in doms_of(act[c]))
            if len(cl) >= 2:
                labs = tuple((c, tuple(s["label"] for s in act[c] if dom in s["domains"])) for c in cl)
                keys_today.add((dom, cl, labs))
        for key in keys_today - set(open_w):
            open_w[key] = d
        for key in set(open_w) - keys_today:
            start = open_w.pop(key)
            dom, cl, labs = key
            windows.append({"domain": dom, "domain_name": DOMAINS[dom], "clusters": list(cl),
                            "grade": "STRONG ⭐" if len(cl) == 3 else "MODERATE",
                            "start": start.isoformat(), "end": d.isoformat() if d <= t1 else f"≥{t1.isoformat()} (horizon)",
                            "activating_periods": {c: list(l) for c, l in labs}})
        d += dt.timedelta(days=1)
    windows.sort(key=lambda x: (x["start"], x["domain"]))
    # merged view: contiguous windows with the same domain and cluster set (sub-periods listed in order)
    merged = []
    for w in sorted(windows, key=lambda x: (x["domain"], tuple(x["clusters"]), x["start"])):
        last = merged[-1] if merged else None
        if last and last["domain"] == w["domain"] and last["clusters"] == w["clusters"] and last["end"] == w["start"]:
            last["end"] = w["end"]
            last["segments"].append({"start": w["start"], "end": w["end"], "activating_periods": w["activating_periods"]})
        else:
            merged.append({"domain": w["domain"], "domain_name": w["domain_name"], "clusters": w["clusters"], "grade": w["grade"],
                           "start": w["start"], "end": w["end"],
                           "segments": [{"start": w["start"], "end": w["end"], "activating_periods": w["activating_periods"]}]})
    merged.sort(key=lambda x: (x["start"], x["domain"]))
    current = [w for w in merged if dt.date.fromisoformat(w["start"]) <= an and (w["end"].startswith("≥") or an < dt.date.fromisoformat(w["end"]))]
    nxt_moderate = [w for w in merged if dt.date.fromisoformat(w["start"]) > an]
    nxt_moderate = [w for w in nxt_moderate if w["start"] == nxt_moderate[0]["start"]] if nxt_moderate else []
    nxt_strong = next((w for w in windows if dt.date.fromisoformat(w["start"]) > an and w["grade"].startswith("STRONG")), None)
    now_active = {c: sorted(doms_of(active(seg_sets[c], an))) for c in CLUSTERS}
    now_labels = {c: [f"{s['label']} → {s['domains']}" for s in active(seg_sets[c], an)] for c in CLUSTERS}

    # low-confidence removals for the reading
    n_low_bazi = sum(1 for p in projections if p["system"] == "bazi")
    removed.append({"claim": f"{n_low_bazi} BaZi element-polarity projections as stand-alone statements",
                    "reason": "useful-element schools disagree (confidence low); used only inside the Sinic vote, never quoted alone"})
    removed.append({"claim": "D10 (Daśāṁśa) career statements", "reason": "D10 Lagna within 3.3 min of a boundary — stable over ±1 min but low margin; not used"})
    removed.append({"claim": "Specific health/medical inferences from D7 indicators", "reason": "out of scope by safety rule; D7 graded symbolically only"})

    synthesis = {
        "registry_version": REGISTRY["version"], "analysis_date": an.isoformat(),
        "projections": projections, "cluster_view": cluster_view, "domain_grades": grades,
        "divergence": divergence, "temperament": temperament, "overlays": overlays,
        "chronology": {"horizon": [t0.isoformat(), t1.isoformat()], "segments": {"jyotisha": j_segs, "western": w_segs, "sinic": s_segs_src},
                       "windows": windows, "merged_windows": merged, "current_windows": current, "next_windows": nxt_moderate, "next_strong_window": nxt_strong,
                       "active_now": now_active, "active_now_periods": now_labels},
        "removed_candidate_claims": removed, "removed_count": len(removed),
    }
    (out / "SYNTHESIS.json").write_text(json.dumps(synthesis, ensure_ascii=False, indent=1, default=str))
    from sixc.reading import write_reading
    write_reading(out, M, synthesis)
    print(json.dumps({"grades": {d: (v["grade"], v["shared_polarity"]) for d, v in grades.items()}, "divergence": divergence,
                      "temperament": {t: v["grade"] for t, v in temperament.items()}, "now": now_active,
                      "current": [(w["domain"], w["grade"], w["start"], w["end"]) for w in current],
                      "next": [(w["domain"], w["grade"], w["start"], w["end"]) for w in nxt_moderate],
                      "next_strong": nxt_strong and (nxt_strong["domain"], nxt_strong["start"], nxt_strong["end"])},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
