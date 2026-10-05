"""Maya calendar (date-based), Tibetan element-animal year (limited), Zi Wei wrapper cross-check."""
import json
import subprocess
from pathlib import Path

import convertdate
from convertdate import mayan

ENGINE_DIR = Path(__file__).resolve().parent.parent

TZOLKIN_NAMES = ["Imix", "Ik'", "Ak'b'al", "K'an", "Chikchan", "Kimi", "Manik'", "Lamat", "Muluk", "Ok",
                 "Chuwen", "Eb'", "B'en", "Ix", "Men", "K'ib'", "Kab'an", "Etz'nab'", "Kawak", "Ajaw"]
HAAB_NAMES = ["Pop", "Wo'", "Sip", "Sotz'", "Sek", "Xul", "Yaxk'in", "Mol", "Ch'en", "Yax", "Sak'",
              "Keh", "Mak", "K'ank'in", "Muwan", "Pax", "K'ayab'", "Kumk'u", "Wayeb'"]


def gregorian_jdn(y, m, d):
    """Independent Gregorian → Julian Day Number (Fliegel & Van Flandern 1968)."""
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045


def jdn_gregorian(j):
    a = j + 32044
    b = (4 * a + 3) // 146097
    c = a - 146097 * b // 4
    d = (4 * c + 3) // 1461
    e = c - 1461 * d // 4
    m = (5 * e + 2) // 153
    return (100 * b + d - 4800 + m // 10, m + 3 - 12 * (m // 10), e - (153 * m + 2) // 5 + 1)


def maya(y, m, d, correlation=584283):
    jdn = gregorian_jdn(y, m, d)
    days = jdn - correlation
    lc = []
    r = days
    for unit in (144000, 7200, 360, 20, 1):
        lc.append(r // unit)
        r %= unit
    # Tzolk'in: 13 Ajaw at 0.0.0.0.0 ; Haab': 8 Kumk'u at 0.0.0.0.0
    tz_num = (days + 4 - 1) % 13 + 1
    tz_name = TZOLKIN_NAMES[(days + 19) % 20]
    hpos = (days + 348) % 365
    haab_day, haab_month = hpos % 20, HAAB_NAMES[hpos // 20]
    own = {"long_count": ".".join(map(str, lc)), "tzolkin": f"{tz_num} {tz_name}",
           "haab": f"{haab_day} {haab_month}", "days_since_epoch": days}
    # convertdate (validator); its EPOCH 584282.5 is the GMT 584283 constant at midnight
    lib_lc = mayan.from_gregorian(y, m, d)
    lib_tz = mayan.lc_to_tzolkin(*lib_lc)
    lib_haab = mayan.lc_to_haab(*lib_lc)
    rt = mayan.to_gregorian(*lib_lc)
    own_rt = jdn_gregorian(sum(v * u for v, u in zip(lc, (144000, 7200, 360, 20, 1))) + correlation)
    return {
        "correlation_constant": correlation, "correlation_name": "GMT (Goodman–Martínez–Thompson)",
        "calendar_day_rule": "civil date at birthplace (Maya day boundary conventions are not applied)",
        "computed": own,
        "validator_convertdate": {"version": convertdate.__version__ if hasattr(convertdate, "__version__") else "see manifest",
                                  "long_count": ".".join(map(str, lib_lc)),
                                  "tzolkin": f"{lib_tz[0]} {lib_tz[1]}", "haab": f"{lib_haab[0]} {lib_haab[1]}",
                                  "library_epoch": mayan.EPOCH},
        "round_trip": {"own": list(own_rt), "convertdate": list(rt), "source": [y, m, d],
                       "pass": tuple(own_rt) == (y, m, d) and tuple(rt) == (y, m, d)},
        "long_count_match": own["long_count"] == ".".join(map(str, lib_lc)),
    }


TIB_ELEM = ["Wood", "Wood", "Fire", "Fire", "Earth", "Earth", "Iron", "Iron", "Water", "Water"]
TIB_ANIMAL = ["Mouse", "Ox", "Tiger", "Rabbit", "Dragon", "Snake", "Horse", "Sheep", "Monkey", "Bird", "Dog", "Pig"]


def tibetan(birth_date, chinese_year_ganzhi, cny_prev, cny_next):
    """Element-animal year via sexagenary alignment of the Tibetan (Phugpa) year with the Chinese cycle.
    Losar can differ from Chinese New Year by up to about one lunar month; the birth must be > ~31 days
    from both Chinese New Year boundaries for the year to be treated as stable without a Phugpa engine."""
    stems = "甲乙丙丁戊己庚辛壬癸"
    branches = "子丑寅卯辰巳午未申酉戌亥"
    si, bi = stems.index(chinese_year_ganzhi[0]), branches.index(chinese_year_ganzhi[1])
    d_prev = (birth_date - cny_prev).days
    d_next = (cny_next - birth_date).days
    stable = d_prev > 31 and d_next > 31
    rabjung_year = None
    # Rabjung cycle 1 began 1027 (Fire-Female-Rabbit). Tibetan year number = Gregorian + 127 for most of the year.
    return {
        "method": "sexagenary alignment (Phugpa Losar not computed directly)",
        "element": TIB_ELEM[si], "gender": "Male" if si % 2 == 0 else "Female", "animal": TIB_ANIMAL[bi],
        "label": f"{TIB_ELEM[si]}-{'Male' if si % 2 == 0 else 'Female'}-{TIB_ANIMAL[bi]}",
        "days_after_chinese_new_year": d_prev, "days_before_next_chinese_new_year": d_next,
        "losar_boundary_stable": stable,
        "mewa": "unavailable — no validated lineage-specific implementation",
        "parkha": "unavailable — no validated lineage-specific implementation",
        "personal_forces_la_sok_lu_wangtang_lungta": "unavailable — formulas/anchors not validated in this environment",
        "annual_obstacles": "unavailable",
        "status": "limited symbolic overlay only",
    }


def ziwei(solar_date, time_index, gender_zh, horoscope_dates):
    args = {"solarDate": solar_date, "timeIndex": time_index, "gender": gender_zh, "fixLeap": True,
            "lang": "zh-CN", "horoscopeDates": horoscope_dates}
    out = subprocess.run(["node", str(ENGINE_DIR / "js" / "ziwei.mjs"), json.dumps(args)],
                         capture_output=True, text=True, check=True, cwd=ENGINE_DIR)
    canon = json.loads(out.stdout)
    # py-iztro wrapper (bundles an older iztro build) for serialization/interface cross-check
    from py_iztro import Astro
    import importlib.metadata as md
    py = Astro().by_solar(solar_date, time_index, gender_zh, True, "zh-CN")
    pyd = py.model_dump()
    mism = []
    pyp = {p["earthly_branch"]: p for p in pyd["palaces"]}
    for p in canon["palaces"]:
        q = pyp.get(p["earthlyBranch"])
        if q is None:
            mism.append(f"missing palace {p['earthlyBranch']} in wrapper")
            continue
        if p["name"] != q["name"]:
            mism.append(f"{p['earthlyBranch']}: name {p['name']} vs {q['name']}")
        a = sorted((s["name"], s.get("brightness") or "", s.get("mutagen") or "") for s in p["majorStars"])
        b = sorted((s["name"], s.get("brightness") or "", s.get("mutagen") or "") for s in q["major_stars"])
        if a != b:
            mism.append(f"{p['earthlyBranch']}: major {a} vs {b}")
        a = sorted(s["name"] for s in p["minorStars"])
        b = sorted(s["name"] for s in q["minor_stars"])
        if a != b:
            mism.append(f"{p['earthlyBranch']}: minor {a} vs {b}")
        if list(p["decadal"]["range"]) != list(q["decadal"]["range"]):
            mism.append(f"{p['earthlyBranch']}: decadal {p['decadal']['range']} vs {q['decadal']['range']}")
    for k_c, k_p in (("fiveElementsClass", "five_elements_class"), ("soul", "soul"), ("body", "body"),
                     ("earthlyBranchOfSoulPalace", "earthly_branch_of_soul_palace"),
                     ("earthlyBranchOfBodyPalace", "earthly_branch_of_body_palace"), ("chineseDate", "chinese_date")):
        if canon[k_c] != pyd[k_p]:
            mism.append(f"{k_c}: {canon[k_c]} vs {pyd[k_p]}")
    return canon, {"wrapper": "py-iztro", "wrapper_version": md.version("py-iztro"),
                   "wrapper_bundled_iztro": "2.5.0", "canonical_iztro": canon["iztro_version"],
                   "mismatches": mism, "pass": not mism,
                   "independence": "NOT independent — same underlying iztro algorithm; interface/serialization check only"}


def ziwei_invariants(canon):
    br = [p["earthlyBranch"] for p in canon["palaces"]]
    names = [p["name"] for p in canon["palaces"]]
    majors = [s["name"] for p in canon["palaces"] for s in p["majorStars"]]
    expected = {"紫微", "天机", "太阳", "武曲", "天同", "廉贞", "天府", "太阴", "贪狼", "巨门", "天相", "天梁", "七杀", "破军"}
    order = "子丑寅卯辰巳午未申酉戌亥"
    pos = {s["name"]: order.index(p["earthlyBranch"]) for p in canon["palaces"] for s in p["majorStars"]}
    zw, tf = pos.get("紫微"), pos.get("天府")
    # Zi Wei series offsets (counter-clockwise from 紫微): 天机 -1, 太阳 -3, 武曲 -4, 天同 -5, 廉贞 -8
    zw_series = {"天机": -1, "太阳": -3, "武曲": -4, "天同": -5, "廉贞": -8}
    tf_series = {"太阴": 1, "贪狼": 2, "巨门": 3, "天相": 4, "天梁": 5, "七杀": 6, "破军": 10}
    zw_ok = all((zw + off) % 12 == pos[s] for s, off in zw_series.items())
    tf_ok = all((tf + off) % 12 == pos[s] for s, off in tf_series.items())
    decs = sorted(tuple(p["decadal"]["range"]) for p in canon["palaces"])
    cont = all(decs[i][1] + 1 == decs[i + 1][0] for i in range(len(decs) - 1))
    return {
        "twelve_unique_branches": len(set(br)) == 12,
        "twelve_unique_palace_names": len(set(names)) == 12,
        "fourteen_major_stars_once_each": sorted(majors) == sorted(expected),
        "ziwei_tianfu_mirror_about_yin_shen": (zw + tf) % 12 == 4,
        "ziwei_series_offsets": zw_ok, "tianfu_series_offsets": tf_ok,
        "decadal_ranges_continuous": cont,
    }
