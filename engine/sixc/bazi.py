"""BaZi (Four Pillars), Ziping track. lunar_python computes calendar pillars; interaction tables declared here."""
import datetime as dt
from lunar_python import Solar

STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
STEM_PINYIN = ["Jia", "Yi", "Bing", "Ding", "Wu", "Ji", "Geng", "Xin", "Ren", "Gui"]
BRANCH_PINYIN = ["Zi", "Chou", "Yin", "Mao", "Chen", "Si", "Wu", "Wei", "Shen", "You", "Xu", "Hai"]
STEM_ELEM = ["Wood", "Wood", "Fire", "Fire", "Earth", "Earth", "Metal", "Metal", "Water", "Water"]
BRANCH_ELEM = ["Water", "Earth", "Wood", "Wood", "Earth", "Fire", "Fire", "Earth", "Metal", "Metal", "Earth", "Water"]
# Hidden stems: main, middle, residual (standard 藏干 table)
HIDDEN = {"子": "癸", "丑": "己癸辛", "寅": "甲丙戊", "卯": "乙", "辰": "戊乙癸", "巳": "丙庚戊",
          "午": "丁己", "未": "己丁乙", "申": "庚壬戊", "酉": "辛", "戌": "戊辛丁", "亥": "壬甲"}
HIDDEN_WEIGHTS = [1.0, 0.5, 0.3]
GEN = {"Wood": "Fire", "Fire": "Earth", "Earth": "Metal", "Metal": "Water", "Water": "Wood"}
CTRL = {"Wood": "Earth", "Earth": "Water", "Water": "Fire", "Fire": "Metal", "Metal": "Wood"}
TEN_GOD_EN = {"比肩": "Friend (Companion)", "劫财": "Rob Wealth", "食神": "Eating God", "伤官": "Hurting Officer",
              "偏财": "Indirect Wealth", "正财": "Direct Wealth", "七杀": "Seven Killings", "正官": "Direct Officer",
              "偏印": "Indirect Resource", "正印": "Direct Resource"}
TEN_GOD_FAMILY = {"比肩": "companion", "劫财": "companion", "食神": "output", "伤官": "output",
                  "偏财": "wealth", "正财": "wealth", "七杀": "officer", "正官": "officer",
                  "偏印": "resource", "正印": "resource"}

STEM_COMBOS = {frozenset("甲己"): "Earth", frozenset("乙庚"): "Metal", frozenset("丙辛"): "Water",
               frozenset("丁壬"): "Wood", frozenset("戊癸"): "Fire"}
STEM_CLASH = [frozenset(x) for x in ("甲庚", "乙辛", "丙壬", "丁癸")]
SIX_COMBO = {frozenset("子丑"): "Earth", frozenset("寅亥"): "Wood", frozenset("卯戌"): "Fire",
             frozenset("辰酉"): "Metal", frozenset("巳申"): "Water", frozenset("午未"): "Fire/Earth"}
THREE_HARMONY = {"申子辰": "Water", "亥卯未": "Wood", "寅午戌": "Fire", "巳酉丑": "Metal"}
DIRECTIONAL = {"寅卯辰": "Wood", "巳午未": "Fire", "申酉戌": "Metal", "亥子丑": "Water"}
SIX_CLASH = [frozenset(x) for x in ("子午", "丑未", "寅申", "卯酉", "辰戌", "巳亥")]
SIX_HARM = [frozenset(x) for x in ("子未", "丑午", "寅巳", "卯辰", "申亥", "酉戌")]
DESTRUCTION = [frozenset(x) for x in ("子酉", "卯午", "辰丑", "未戌", "寅亥", "巳申")]
PUNISH_GROUPS = ["寅巳申", "丑戌未"]
PUNISH_PAIR = [frozenset("子卯")]
SELF_PUNISH = set("辰午酉亥")
PILLARS = ["year", "month", "day", "hour"]


def ten_god(dm, other):
    d, o = STEMS.index(dm), STEMS.index(other)
    de, oe = STEM_ELEM[d], STEM_ELEM[o]
    same_pol = (d % 2) == (o % 2)
    if de == oe:
        return "比肩" if same_pol else "劫财"
    if GEN[de] == oe:
        return "食神" if same_pol else "伤官"
    if CTRL[de] == oe:
        return "偏财" if same_pol else "正财"
    if CTRL[oe] == de:
        return "七杀" if same_pol else "正官"
    if GEN[oe] == de:
        return "偏印" if same_pol else "正印"
    raise ValueError


def seasonal_state(month_branch, element):
    season = {"寅": "Wood", "卯": "Wood", "巳": "Fire", "午": "Fire", "申": "Metal", "酉": "Metal",
              "亥": "Water", "子": "Water", "辰": "Earth", "未": "Earth", "戌": "Earth", "丑": "Earth"}[month_branch]
    if element == season:
        return "旺 (prosperous)"
    if GEN[season] == element:
        return "相 (assisted)"
    if GEN[element] == season:
        return "休 (resting)"
    if CTRL[element] == season:
        return "囚 (confined)"
    return "死 (dead)"


def pillars_for(y, m, d, hh, mi, ss=0):
    s = Solar.fromYmdHms(y, m, d, hh, mi, ss)
    lun = s.getLunar()
    e = lun.getEightChar()
    e.setSect(2)  # sect 2: day pillar changes at 00:00 (23:00-24:00 keeps current day; 'late Zi' convention)
    return lun, e


def build(local_civil, local_apparent, gender_male, now_utc):
    """local_civil/local_apparent: naive datetimes (wall-clock at birthplace)."""
    tracks = {}
    for label, t in (("civil_time", local_civil), ("apparent_solar_time", local_apparent)):
        lun, e = pillars_for(t.year, t.month, t.day, t.hour, t.minute, t.second)
        tracks[label] = {"input": t.isoformat(timespec="seconds"),
                         "pillars": [e.getYear(), e.getMonth(), e.getDay(), e.getTime()]}
    primary = tracks["apparent_solar_time"]["pillars"]
    alt_differs = tracks["civil_time"]["pillars"] != primary
    t = local_apparent
    lun, e = pillars_for(t.year, t.month, t.day, t.hour, t.minute, t.second)
    dm = primary[2][0]
    pillars = []
    for i, gz in enumerate(primary):
        st, br = gz[0], gz[1]
        hid = list(HIDDEN[br])
        pillars.append({
            "pillar": PILLARS[i], "ganzhi": gz,
            "stem": {"char": st, "pinyin": STEM_PINYIN[STEMS.index(st)], "element": STEM_ELEM[STEMS.index(st)],
                     "polarity": "Yang" if STEMS.index(st) % 2 == 0 else "Yin",
                     "ten_god": None if i == 2 else ten_god(dm, st)},
            "branch": {"char": br, "pinyin": BRANCH_PINYIN[BRANCHES.index(br)],
                       "element": BRANCH_ELEM[BRANCHES.index(br)],
                       "polarity": "Yang" if BRANCHES.index(br) % 2 == 0 else "Yin"},
            "hidden_stems": [{"char": h, "element": STEM_ELEM[STEMS.index(h)], "weight": HIDDEN_WEIGHTS[k],
                              "ten_god": ten_god(dm, h)} for k, h in enumerate(hid)],
        })
    nayin = [e.getYearNaYin(), e.getMonthNaYin(), e.getDayNaYin(), e.getTimeNaYin()]
    for p, ny in zip(pillars, nayin):
        p["na_yin_traditional_attribute"] = ny
    # library cross-check of hidden stems / ten gods
    lib_hidden = [e.getYearHideGan(), e.getMonthHideGan(), e.getDayHideGan(), e.getTimeHideGan()]
    lib_tg = [e.getYearShiShenZhi(), e.getMonthShiShenZhi(), e.getDayShiShenZhi(), e.getTimeShiShenZhi()]
    table_check = all([list(lh) == [h["char"] for h in p["hidden_stems"]] for lh, p in zip(lib_hidden, pillars)]) and \
        all([list(lt) == [h["ten_god"] for h in p["hidden_stems"]] for lt, p in zip(lib_tg, pillars)])

    strength = day_master_strength(pillars, dm)
    interactions = find_interactions(primary)
    yun = da_yun(lun, e, gender_male)
    return {
        "school": "Ziping (子平) four-pillar track; hour pillar from local apparent solar time (primary), civil time retained",
        "day_boundary_rule": "lunar_python sect 2: civil-day change at 00:00 local; 23:00-24:00 uses next-day Zi-hour stem rules per library (late-Zi). Birth far from this boundary.",
        "tracks": tracks, "civil_vs_solar_pillars_differ": alt_differs,
        "primary_pillars": primary, "day_master": {"char": dm, "element": STEM_ELEM[STEMS.index(dm)],
                                                    "polarity": "Yang" if STEMS.index(dm) % 2 == 0 else "Yin"},
        "pillars": pillars, "hidden_stem_table_matches_library": table_check,
        "lunar_date": {"year": lun.getYear(), "month": lun.getMonth(), "day": lun.getDay(),
                       "is_leap_month": lun.getMonth() < 0, "text": lun.toString()},
        "strength": strength, "interactions": interactions, "da_yun": yun,
    }


def day_master_strength(pillars, dm):
    """Declared rule WEC-1 (weighted element count):
    visible stems 1.0 (Day Master excluded); hidden stems main/middle/residual 1.0/0.5/0.3;
    month-branch hidden stems doubled (月令). Support = companion + resource families;
    against = output + wealth + officer. ratio >0.55 strong, <0.45 weak, else balanced."""
    fam = {"companion": 0.0, "resource": 0.0, "output": 0.0, "wealth": 0.0, "officer": 0.0}
    elem = {k: 0.0 for k in GEN}
    for i, p in enumerate(pillars):
        if i != 2:
            tg = p["stem"]["ten_god"]
            fam[TEN_GOD_FAMILY[tg]] += 1.0
            elem[p["stem"]["element"]] += 1.0
        mult = 2.0 if p["pillar"] == "month" else 1.0
        for h in p["hidden_stems"]:
            fam[TEN_GOD_FAMILY[h["ten_god"]]] += h["weight"] * mult
            elem[h["element"]] += h["weight"] * mult
    sup = fam["companion"] + fam["resource"]
    tot = sum(fam.values())
    ratio = sup / tot
    verdict = "strong" if ratio > 0.55 else "weak" if ratio < 0.45 else "balanced"
    month_branch = pillars[1]["branch"]["char"]
    dm_el = STEM_ELEM[STEMS.index(dm)]
    roots = [p["pillar"] for p in pillars if any(h["element"] == dm_el for h in p["hidden_stems"])]
    res_el = [k for k, v in GEN.items() if v == dm_el][0]
    res_roots = [p["pillar"] for p in pillars if any(h["element"] == res_el for h in p["hidden_stems"])]
    out_el = GEN[dm_el]
    wealth_el = CTRL[dm_el]
    off_el = [k for k, v in CTRL.items() if v == dm_el][0]
    # Useful-element judgments by two declared schools (displayed, not merged)
    if verdict == "weak":
        fuyi = {"favorable": [res_el, dm_el], "unfavorable": [out_el, wealth_el, off_el]}
    elif verdict == "strong":
        fuyi = {"favorable": [out_el, wealth_el, off_el], "unfavorable": [res_el, dm_el]}
    else:
        fuyi = {"favorable": [], "unfavorable": [], "note": "balanced: support-suppress school gives no clear direction"}
    winter = month_branch in "亥子丑"
    summer = month_branch in "巳午未"
    tiaohou = {"favorable": ["Fire"], "basis": "born in winter month (亥/子/丑): climate-regulation principle calls for warmth"} if winter else \
        {"favorable": ["Water"], "basis": "born in summer month (巳/午/未): climate-regulation principle calls for moisture"} if summer else \
        {"favorable": [], "basis": "spring/autumn month: climate regulation not decisive under this simplified rule"}
    agree = sorted(set(fuyi["favorable"]) & set(tiaohou["favorable"]))
    return {
        "rule": "WEC-1", "family_weights": fam, "element_weights": elem,
        "support": sup, "total": tot, "support_ratio": ratio, "verdict": verdict,
        "seasonal_state_of_day_master": seasonal_state(month_branch, dm_el),
        "same_element_roots_in_branches": roots, "resource_roots_in_branches": res_roots,
        "useful_element_schools": {
            "扶抑 support-suppress (WEC-1 based)": fuyi,
            "调候 climate-regulation (simplified seasonal rule)": tiaohou,
        },
        "schools_agree_on": agree,
        "useful_element_confidence": "medium" if agree else "low",
    }


def find_interactions(gz4):
    stems = [g[0] for g in gz4]
    brs = [g[1] for g in gz4]
    out = []
    for i in range(4):
        for j in range(i + 1, 4):
            pair = frozenset((stems[i], stems[j]))
            adj = j == i + 1
            if pair in STEM_COMBOS and len(pair) == 2:
                out.append({"type": "stem combination (天干五合)", "pillars": [PILLARS[i], PILLARS[j]],
                            "chars": stems[i] + stems[j], "potential_element": STEM_COMBOS[pair], "adjacent": adj,
                            "transformation_asserted": False,
                            "transformation_note": "Transformation requires the month to support the target element and no contesting stem; not asserted without that evaluation."})
            if pair in STEM_CLASH:
                out.append({"type": "stem clash", "pillars": [PILLARS[i], PILLARS[j]], "chars": stems[i] + stems[j], "adjacent": adj})
            bp = frozenset((brs[i], brs[j]))
            for tbl, name in ((SIX_CLASH, "six clash (六冲)"), (SIX_HARM, "six harm (六害)"),
                              (DESTRUCTION, "destruction (破)"), (PUNISH_PAIR, "punishment (刑)")):
                if bp in tbl:
                    out.append({"type": name, "pillars": [PILLARS[i], PILLARS[j]], "chars": brs[i] + brs[j], "adjacent": adj})
            if bp in SIX_COMBO and len(bp) == 2:
                out.append({"type": "six combination (六合)", "pillars": [PILLARS[i], PILLARS[j]],
                            "chars": brs[i] + brs[j], "potential_element": SIX_COMBO[bp], "adjacent": adj,
                            "transformation_asserted": False})
            if brs[i] == brs[j] and brs[i] in SELF_PUNISH:
                out.append({"type": "self-punishment (自刑)", "pillars": [PILLARS[i], PILLARS[j]], "chars": brs[i] + brs[j], "adjacent": adj})
    present = set(brs)
    for trio, el in THREE_HARMONY.items():
        n = len(set(trio) & present)
        if n == 3:
            out.append({"type": "three harmony (三合) full", "chars": trio, "element": el})
        elif n == 2 and trio[1] in present:
            out.append({"type": "three harmony half (半合, includes the cardinal branch)", "chars": "".join(c for c in trio if c in present), "element": el})
    for trio, el in DIRECTIONAL.items():
        if set(trio) <= present:
            out.append({"type": "directional combination (三会) full", "chars": trio, "element": el})
    for grp in PUNISH_GROUPS:
        hit = set(grp) & present
        if len(hit) >= 2:
            out.append({"type": "punishment group (三刑) partial" if len(hit) == 2 else "punishment group (三刑) full",
                        "chars": "".join(sorted(hit, key=grp.index))})
    return out


def da_yun(lun, e, male):
    yun = e.getYun(1 if male else 0, 2)  # sect 2: precise minute-level start (1 day=4 months? see lunar_python)
    start = yun.getStartSolar()
    out = {"direction": "forward" if yun.isForward() else "backward",
           "rule": "Yang-year male / Yin-year female forward; otherwise backward. Start age = time to the next (forward) or previous (backward) sectional term ×120 (3 days = 1 year).",
           "library_start_solar": start.toYmdHms(),
           "library_start_offset": {"years": yun.getStartYear(), "months": yun.getStartMonth(),
                                    "days": yun.getStartDay(), "hours": yun.getStartHour()},
           "pillars": []}
    for d in yun.getDaYun(10)[1:]:
        out["pillars"].append({"ganzhi": d.getGanZhi(), "start_age_nominal": d.getStartAge(),
                               "start_year": d.getStartYear(), "end_year": d.getEndYear()})
    return out


def annual_pillars(year_from, year_to):
    """Year pillar changes at 立春 (Start of Spring). Returns (gz, start ISO Beijing-time as given by lunar_python)."""
    out = []
    for y in range(year_from, year_to + 1):
        l = Solar.fromYmd(y, 6, 1).getLunar()
        jq = l.getJieQiTable()["立春"]
        out.append({"year": y, "ganzhi": l.getYearInGanZhiByLiChun(), "lichun_beijing": jq.toYmdHms()})
    return out
