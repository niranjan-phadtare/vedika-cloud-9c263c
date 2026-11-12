"""Auditable AK-1 North Indian Ashtakoota variant.

Some traditional tables vary between regions/software. AK-1 fixes every table
and does not silently add Nadi/Bhakoot cancellation points. See RULEBOOK.md.
Yoni, Vashya, Gana and Graha Maitri tables adapted from PyJHora compatibility.py
commit be344af506590b6e4c79942d84b958495dee4766, AGPL-3.0-or-later;
Copyright (C) Open Astro Technologies, USA. Modified by Sundar Sundaresan,
USA, carnaticmusicguru2015@comcast.net (see THIRD_PARTY_NOTICES).
"""
from __future__ import annotations

import math
from .engine import chart, lunar_details, CalculationError

VARNA_NAMES = ["Brahmin", "Kshatriya", "Vaishya", "Shudra"]
# Drik Panchang element convention: water, fire, earth, air respectively.
VARNA_BY_SIGN = [1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0]
VASHYA_NAMES = ["Chatushpada", "Manava", "Jalachara", "Vanachara", "Keeta"]
VASHYA = [[2, .5, 1, 0, 2], [.5, 2, 0, 0, 0], [1, 0, 2, 2, 2], [0, 0, 2, 2, 0], [1, 0, 1, 0, 2]]
YONI_NAMES = ["Horse", "Elephant", "Sheep", "Serpent", "Dog", "Cat", "Rat", "Cow", "Buffalo", "Tiger", "Deer", "Monkey", "Mongoose", "Lion"]
YONI_BY_NAK = [0, 1, 2, 3, 3, 4, 5, 2, 5, 6, 6, 7, 8, 9, 8, 9, 10, 10, 4, 11, 12, 11, 13, 0, 13, 7, 1]
YONI = [
 [4,2,2,3,2,2,2,1,0,1,1,3,2,1],
 [2,4,3,3,2,2,2,2,3,1,2,3,2,0],
 [2,3,4,2,1,2,1,3,3,1,2,0,3,1],
 [3,3,2,4,2,1,1,1,1,2,2,2,0,2],
 [2,2,1,2,4,2,1,2,2,1,0,2,1,1],
 [2,2,2,1,2,4,0,2,2,1,3,3,2,1],
 [2,2,1,1,1,0,4,2,2,2,2,2,1,2],
 [1,2,3,1,2,2,2,4,3,0,3,2,2,1],
 [0,3,3,1,2,2,2,3,4,1,2,2,2,1],
 [1,1,1,2,1,1,2,0,1,4,1,1,2,1],
 [1,2,2,2,0,3,2,3,2,1,4,2,2,1],
 [3,3,0,2,2,3,2,2,2,1,2,4,3,2],
 [2,2,3,0,1,2,1,2,2,2,2,3,4,2],
 [1,0,1,2,1,1,2,1,1,1,1,2,2,4],
]
GANA_NAMES = ["Deva", "Manushya", "Rakshasa"]
GANA = [[6,6,0], [5,6,0], [1,0,6]]
LORD_NAMES = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
LORD_BY_SIGN = [2,5,3,1,0,3,5,2,4,6,6,4]
MAITRI = [[5,5,5,4,5,0,0], [5,5,4,1,4,.5,.5], [5,4,5,.5,5,3,.5], [4,1,.5,5,.5,5,4], [5,4,5,.5,5,.5,3], [0,.5,3,5,.5,5,5], [0,.5,.5,4,3,5,5]]
NADI_NAMES = ["Adi", "Madhya", "Antya"]
NADI_BY_NAK = [0,1,2,2,1,0,0,1,2,2,1,0,0,1,2,2,1,0,0,1,2,2,1,0,0,1,2]


def vashya_category(longitude: float) -> int:
    lon = longitude % 360
    sign, degree = int(lon // 30), lon % 30
    if sign in (0, 1) or (sign == 8 and degree >= 15) or (sign == 9 and degree < 15):
        return 0
    if sign in (2, 5, 6, 10) or (sign == 8 and degree < 15):
        return 1
    if sign in (3, 11) or (sign == 9 and degree >= 15):
        return 2
    if sign == 4:
        return 3
    return 4


def gana_category(nakshatra_index: int) -> int:
    if nakshatra_index in (0,4,6,7,12,14,16,21,26):
        return 0
    if nakshatra_index in (1,3,5,10,11,19,20,24,25):
        return 1
    return 2


def ashtakoota(moon_longitude_a: float, moon_longitude_b: float) -> dict:
    """Score first/groom-role and second/bride-role Moon longitudes.

    Role matters for directional tables. Gender and name are never inferred
    from birth data. Inputs are sidereal ecliptic longitudes in degrees.
    """
    if not all(isinstance(x, (int, float)) and math.isfinite(x) for x in (moon_longitude_a, moon_longitude_b)):
        raise CalculationError("Two finite sidereal Moon longitudes are required.")
    a = lunar_details(moon_longitude_a)
    b = lunar_details(moon_longitude_b)
    sa, sb = a["sign_index"], b["sign_index"]
    na, nb = a["nakshatra_index"], b["nakshatra_index"]
    va, vb = VARNA_BY_SIGN[sa], VARNA_BY_SIGN[sb]
    wa, wb = vashya_category(moon_longitude_a), vashya_category(moon_longitude_b)
    ya, yb = YONI_BY_NAK[na], YONI_BY_NAK[nb]
    ga, gb = gana_category(na), gana_category(nb)
    la, lb = LORD_BY_SIGN[sa], LORD_BY_SIGN[sb]
    da, db = NADI_BY_NAK[na], NADI_BY_NAK[nb]
    count_ab, count_ba = (nb - na) % 27 + 1, (na - nb) % 27 + 1
    tara_ab = 1.5 if count_ab % 9 not in (3,5,7) else 0
    tara_ba = 1.5 if count_ba % 9 not in (3,5,7) else 0
    relative_ab, relative_ba = (sb - sa) % 12 + 1, (sa - sb) % 12 + 1
    bhakoot_adverse = relative_ab in (2,5,6,8,9,12)
    kootas = []
    def add(key, name, score, maximum, detail, value_a=None, value_b=None):
        kootas.append({"key":key, "name":name, "score":float(score), "max":maximum, "detail":detail, "value_a":value_a, "value_b":value_b})
    add("varna", "Varna", int(va <= vb), 1, "Moon-sign elements map water→Brahmin, fire→Kshatriya, earth→Vaishya, air→Shudra. The historical ordered category rule awards 1 when A/groom-role category is equal to or precedes B/bride-role. These are historical labels, not social identity or human worth.", VARNA_NAMES[va], VARNA_NAMES[vb])
    add("vashya", "Vashya", VASHYA[wb][wa], 2, "Fixed AK-1/PyJHora VasiyaArray, row B/bride-role, column A/groom-role. Sagittarius and Capricorn are split at the actual 15° Moon longitude, not approximate nakshatra padas.", VASHYA_NAMES[wa], VASHYA_NAMES[wb])
    add("tara", "Tara", tara_ab + tara_ba, 3, f"Inclusive nakshatra counts A→B={count_ab}, B→A={count_ba}; remainders modulo9={count_ab % 9}/{count_ba % 9}. Each direction earns 1.5 unless its remainder is 3, 5 or 7.", a["nakshatra"], b["nakshatra"])
    add("yoni", "Yoni", YONI[yb][ya], 4, "Fixed 14-animal AK-1/PyJHora YoniArray; nakshatra animal mapping; no biological or sexual outcome is inferred.", YONI_NAMES[ya], YONI_NAMES[yb])
    add("graha_maitri", "Graha Maitri", MAITRI[lb][la], 5, "Natural friendship matrix for sidereal Moon-sign lords; fixed scores 0, 0.5, 1, 3, 4 or 5. Temporary friendship is not added.", LORD_NAMES[la], LORD_NAMES[lb])
    add("gana", "Gana", GANA[gb][ga], 6, "Fixed directional AK-1/PyJHora North Gana table, row B/bride-role and column A/groom-role. These symbolic categories are not measured personality traits.", GANA_NAMES[ga], GANA_NAMES[gb])
    add("bhakoot", "Bhakoot", 0 if bhakoot_adverse else 7, 7, f"Moon-sign inclusive relation A→B={relative_ab}, B→A={relative_ba}. Pairs 2/12, 5/9 or 6/8 score 0; all others score 7. No cancellation points.", a["sign"], b["sign"])
    add("nadi", "Nadi", 0 if da == db else 8, 8, "Same Nadi scores 0; different Nadi scores 8. Fixed 27-nakshatra mapping. No same-star/pada cancellation. Nadi does not diagnose health, fertility or genetics.", NADI_NAMES[da], NADI_NAMES[db])
    score = sum(k["score"] for k in kootas)
    cautions = ["18/36 is an explicitly selected traditional screening threshold, not a scientific relationship prediction or marriage recommendation.", "AK-1 fixes one documented North Indian variant. Other regional/app tables and cancellation rules can give different totals.", "Role A uses historical groom-role tables and role B bride-role tables. Names and gender labels do not change the astronomical calculation."]
    if da == db:
        cautions.append("Nadi base rule is present (0/8); the total score does not override this individual rule. No cancellation is assumed.")
    if bhakoot_adverse:
        cautions.append("Bhakoot base rule is present (0/7); no cancellation is assumed.")
    return {"kootas":kootas, "score":score, "max_score":36, "traditional_threshold":18, "threshold_met":score >= 18, "decision":"meets_threshold" if score >= 18 else "below_threshold", "cautions":cautions, "methodology":{"version":"AK-1", "system":"North Indian Ashtakoota, explicit fixed variant", "role_order":"A=groom-role; B=bride-role", "cancellations":"Not applied", "varna":"Drik Panchang element mapping", "tables":"PyJHora compatibility.py @ be344af506590b6e4c79942d84b958495dee4766: VasiyaArray, YoniArray, gana_array, raasi_adhipathi_array", "tara":"Inclusive counts each direction; 1.5 if count mod9 is not 3/5/7 (Saravali Dina rule)", "vashya_split":"Actual Moon sign longitude at15° for Sagittarius/Capricorn", "sources":["https://www.drikpanchang.com/tutorials/jyotisha/kundali-match/ashta-kuta/varna-kuta.html", "https://www.drikpanchang.com/tutorials/jyotisha/kundali-match/ashta-kuta/vashya-kuta.html", "https://saravali.github.io/astrology/koota_dina.html", "https://github.com/ArkOne-Softwares/pyjhora/blob/be344af506590b6e4c79942d84b958495dee4766/src/jhora/horoscope/match/compatibility.py"]}}


def match(person_a: dict, person_b: dict) -> dict:
    ca, cb = chart(person_a), chart(person_b)
    result = ashtakoota(ca["moon"]["longitude"], cb["moon"]["longitude"])
    result["charts"] = [ca, cb]
    for c in (ca, cb):
        if c["profile"].get("time_accuracy") == "approximate":
            result["cautions"].append(f"{c['profile']['name']}: approximate birth time can change Moon nakshatra/sign near a boundary and therefore this score; confirm the recorded time.")
    return result
