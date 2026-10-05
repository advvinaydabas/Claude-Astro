"""Western / Hellenistic primary track: tropical zodiac, whole-sign houses, seven traditional planets."""
from .astro import SIGNS, norm, sign_of, angdiff

SEVEN = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
DOMICILE = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
            "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]
EXALT = {"Sun": (0, 19), "Moon": (1, 3), "Mercury": (5, 15), "Venus": (11, 27),
         "Mars": (9, 28), "Jupiter": (3, 15), "Saturn": (6, 21)}
# Dorothean triplicity rulers: (day, night, participating)
TRIPLICITY = {"Fire": ("Sun", "Jupiter", "Saturn"), "Earth": ("Venus", "Moon", "Mars"),
              "Air": ("Saturn", "Mercury", "Jupiter"), "Water": ("Venus", "Mars", "Moon")}
SIGN_ELEMENT = ["Fire", "Earth", "Air", "Water"] * 3
# Egyptian bounds (Ptolemy, Tetrabiblos I.20 "Egyptian" table): (end_degree, ruler)
BOUNDS = [
    [(6, "Jupiter"), (12, "Venus"), (20, "Mercury"), (25, "Mars"), (30, "Saturn")],
    [(8, "Venus"), (14, "Mercury"), (22, "Jupiter"), (27, "Saturn"), (30, "Mars")],
    [(6, "Mercury"), (12, "Jupiter"), (17, "Venus"), (24, "Mars"), (30, "Saturn")],
    [(7, "Mars"), (13, "Venus"), (19, "Mercury"), (26, "Jupiter"), (30, "Saturn")],
    [(6, "Jupiter"), (11, "Venus"), (18, "Saturn"), (24, "Mercury"), (30, "Mars")],
    [(7, "Mercury"), (17, "Venus"), (21, "Jupiter"), (28, "Mars"), (30, "Saturn")],
    [(6, "Saturn"), (14, "Mercury"), (21, "Jupiter"), (28, "Venus"), (30, "Mars")],
    [(7, "Mars"), (11, "Venus"), (19, "Mercury"), (24, "Jupiter"), (30, "Saturn")],
    [(12, "Jupiter"), (17, "Venus"), (21, "Mercury"), (26, "Saturn"), (30, "Mars")],
    [(7, "Mercury"), (14, "Jupiter"), (22, "Venus"), (26, "Saturn"), (30, "Mars")],
    [(7, "Mercury"), (13, "Venus"), (20, "Jupiter"), (25, "Mars"), (30, "Saturn")],
    [(12, "Venus"), (16, "Jupiter"), (19, "Mercury"), (28, "Mars"), (30, "Saturn")],
]
CHALDEAN = ["Mars", "Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter"]
ASPECTS = {0: "conjunction", 60: "sextile", 90: "square", 120: "trine", 180: "opposition"}
ASPECT_ORB = 3.0  # declared degree orb for "close" configurations; sign-based configuration is primary
BENEFICS = {"Jupiter", "Venus"}
MALEFICS = {"Mars", "Saturn"}
COMBUST_DEG = 8.5        # declared: under the beams 15°, combust 8.5°, cazimi 17'
BEAMS_DEG = 15.0
CAZIMI_DEG = 17 / 60


def bounds_invariant():
    tot = {}
    for sgn in BOUNDS:
        prev = 0
        for end, r in sgn:
            tot[r] = tot.get(r, 0) + end - prev
            prev = end
    return tot  # expected Saturn 57, Jupiter 79, Mars 66, Venus 82, Mercury 76


def bound_ruler(lon):
    s = sign_of(lon)
    d = norm(lon) - 30 * s
    for end, r in BOUNDS[s]:
        if d < end:
            return r


def face_ruler(lon):
    s = sign_of(lon)
    dec = int((norm(lon) - 30 * s) // 10)
    return CHALDEAN[(s * 3 + dec) % 7]


def essential(p, lon, is_day):
    s = sign_of(lon)
    tri = TRIPLICITY[SIGN_ELEMENT[s]]
    dig = []
    if DOMICILE[s] == p:
        dig.append("domicile")
    if EXALT[p][0] == s:
        dig.append("exaltation")
    if p in tri:
        role = ["day", "night", "participating"][tri.index(p)]
        dig.append(f"triplicity ({role})")
    if bound_ruler(lon) == p:
        dig.append("bound")
    if face_ruler(lon) == p:
        dig.append("face")
    deb = []
    if DOMICILE[(s + 6) % 12] == p:
        deb.append("detriment")
    if EXALT[p][0] == (s + 6) % 12:
        deb.append("fall")
    return {"dignities": dig, "debilities": deb, "domicile_lord": DOMICILE[s],
            "exaltation_lord": next((q for q, (es, _) in EXALT.items() if es == s), None),
            "triplicity_lords": dict(zip(["day", "night", "participating"], tri)),
            "bound_lord": bound_ruler(lon), "face_lord": face_ruler(lon), "is_peregrine": not dig}


def build(trop, asc, mc, sun_alt, is_day):
    asc_s = sign_of(asc)
    H = lambda lon: (sign_of(lon) - asc_s) % 12 + 1
    sect_light = "Sun" if is_day else "Moon"
    sect_benefic = "Jupiter" if is_day else "Venus"
    sect_malefic = "Saturn" if is_day else "Mars"
    planets = {}
    for p in SEVEN:
        lon = trop[p]["lon"]
        h = H(lon)
        sep = abs(angdiff(lon, trop["Sun"]["lon"])) if p != "Sun" else None
        vis = None
        if sep is not None and p != "Moon":
            vis = "cazimi" if sep < CAZIMI_DEG else "combust" if sep < COMBUST_DEG else \
                "under the beams" if sep < BEAMS_DEG else "free of the beams"
        elif p == "Moon":
            vis = "under the beams" if sep < BEAMS_DEG else "free of the beams"
        sect_status = None
        if p in ("Mercury",):
            sect_status = "variable (Mercury: diurnal if rising before Sun)"
        elif p in ("Sun", "Jupiter", "Saturn"):
            sect_status = "of the sect" if is_day else "contrary to sect"
        elif p in ("Moon", "Venus", "Mars"):
            sect_status = "contrary to sect" if is_day else "of the sect"
        planets[p] = {
            "lon": lon, "sign": SIGNS[sign_of(lon)], "deg_in_sign": norm(lon) - 30 * sign_of(lon),
            "house": h, "angularity": "angular" if h in (1, 4, 7, 10) else "succedent" if h in (2, 5, 8, 11) else "cadent",
            "speed": trop[p]["speed"], "retrograde": trop[p]["retrograde"],
            "solar_phase": vis, "sun_separation": sep, "sect": sect_status,
            "essential": essential(p, lon, is_day),
        }
    # Mercury sect: oriental (rises before Sun => lon greater? no: oriental = earlier in zodiac order rising first)
    merc_east = angdiff(trop["Mercury"]["lon"], trop["Sun"]["lon"]) < 0
    planets["Mercury"]["sect"] = ("morning star (oriental) → diurnal" if merc_east else "evening star (occidental) → nocturnal")
    houses = {}
    for h in range(1, 13):
        s = (asc_s + h - 1) % 12
        ruler = DOMICILE[s]
        houses[h] = {"sign": SIGNS[s], "ruler": ruler, "ruler_in_house": planets[ruler]["house"],
                     "occupants": [p for p in SEVEN if planets[p]["house"] == h]}
    # dispositor chains
    chains = {}
    final = set()
    for p in SEVEN:
        seen = [p]
        cur = p
        while True:
            nxt = DOMICILE[sign_of(planets[cur]["lon"])]
            if nxt in seen:
                loop = seen[seen.index(nxt):]
                chains[p] = {"chain": seen + [nxt], "terminates_in": "final dispositor" if len(loop) == 1 else "mutual reception loop", "loop": loop}
                if len(loop) == 1:
                    final.add(nxt)
                break
            seen.append(nxt)
            cur = nxt
    # aspects (degree-based, Ptolemaic, declared orb) + sign-based configurations
    asp = []
    for i, a in enumerate(SEVEN):
        for b in SEVEN[i + 1:]:
            la, lb = planets[a]["lon"], planets[b]["lon"]
            sep = abs(angdiff(la, lb))
            sign_dist = min((sign_of(la) - sign_of(lb)) % 12, (sign_of(lb) - sign_of(la)) % 12)
            sign_conf = {0: "conjunction", 2: "sextile", 3: "square", 4: "trine", 6: "opposition"}.get(sign_dist)
            for ang, nm in ASPECTS.items():
                orb = abs(sep - ang)
                if orb <= ASPECT_ORB:
                    # applying if separation-to-exact decreases: numerical look-ahead with speeds
                    dt_ = 0.01
                    la2 = la + planets[a]["speed"] * dt_
                    lb2 = lb + planets[b]["speed"] * dt_
                    orb2 = abs(abs(angdiff(la2, lb2)) - ang)
                    asp.append({"a": a, "b": b, "aspect": nm, "orb": orb, "applying": orb2 < orb,
                                "sign_based_configuration": sign_conf,
                                "whole_sign_consistent": sign_conf == nm})
    # Lots
    sun, moon = trop["Sun"]["lon"], trop["Moon"]["lon"]
    if is_day:
        fortune = norm(asc + moon - sun)
        spirit = norm(asc + sun - moon)
    else:
        fortune = norm(asc + sun - moon)
        spirit = norm(asc + moon - sun)
    lots = {
        "Fortune": {"lon": fortune, "sign": SIGNS[sign_of(fortune)], "house": H(fortune), "ruler": DOMICILE[sign_of(fortune)],
                    "formula": "day: Asc + Moon − Sun" if is_day else "night: Asc + Sun − Moon"},
        "Spirit": {"lon": spirit, "sign": SIGNS[sign_of(spirit)], "house": H(spirit), "ruler": DOMICILE[sign_of(spirit)],
                   "formula": "day: Asc + Sun − Moon" if is_day else "night: Asc + Moon − Sun"},
    }
    return {
        "asc": {"lon": asc, "sign": SIGNS[asc_s], "deg_in_sign": asc - 30 * asc_s, "ruler": DOMICILE[asc_s]},
        "mc": {"lon": mc, "sign": SIGNS[sign_of(mc)], "deg_in_sign": norm(mc) - 30 * sign_of(mc),
               "whole_sign_house_of_mc": H(mc)},
        "sect": {"is_day": is_day, "sun_altitude_deg": sun_alt, "sect_light": sect_light,
                 "benefic_of_sect": sect_benefic, "malefic_of_sect": sect_malefic,
                 "benefic_contrary": "Venus" if is_day else "Jupiter", "malefic_contrary": "Mars" if is_day else "Saturn"},
        "planets": planets, "houses": houses, "dispositors": chains, "final_dispositors": sorted(final),
        "aspects": asp, "aspect_orb_deg": ASPECT_ORB, "lots": lots,
        "tables": {"bounds": "Egyptian (Ptolemy Tetrabiblos I.20)", "triplicity": "Dorothean",
                   "faces": "Chaldean decans", "exaltation_degrees": "traditional"},
    }


def profection(asc_sign_index, age_completed):
    s = (asc_sign_index + age_completed) % 12
    return {"age": age_completed, "house": age_completed % 12 + 1, "sign": SIGNS[s], "lord_of_year": DOMICILE[s]}
