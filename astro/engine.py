"""Deterministic Lahiri / whole-sign Vedic chart calculations.

Astronomical quantities are computed by Swiss Ephemeris. Traditional rules are
explicit, limited screens, not empirical predictions or a complete shastra.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from threading import RLock
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import math

import swisseph as swe

EPHE_PATH = Path(__file__).resolve().parents[1] / "data" / "ephe"
SWISS_LOCK = RLock()  # Swiss Ephemeris configuration is process-global.
YEAR_DAYS = 365.25
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishtha", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
DASHA_LORDS = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
DASHA_YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7, "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17}
PLANET_IDS = [("Sun", swe.SUN), ("Moon", swe.MOON), ("Mars", swe.MARS), ("Mercury", swe.MERCURY), ("Jupiter", swe.JUPITER), ("Venus", swe.VENUS), ("Saturn", swe.SATURN), ("Rahu", swe.MEAN_NODE)]


class CalculationError(ValueError):
    """Invalid or unsupported input; never replaced by a plausible value."""


def _iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def birth_datetime(profile: dict) -> tuple[datetime, datetime]:
    """Resolve local birth time without silently accepting a DST gap or fold."""
    try:
        day = date.fromisoformat(str(profile["date"]))
        clock = time.fromisoformat(str(profile["time"]))
        if clock.tzinfo is not None:
            raise CalculationError("Enter a local clock time without a UTC offset; select an IANA timezone separately.")
        zone = ZoneInfo(str(profile["timezone"]))
    except (KeyError, TypeError, ValueError, ZoneInfoNotFoundError) as exc:
        if isinstance(exc, CalculationError):
            raise
        raise CalculationError("A valid birth date, exact local time, and IANA timezone are required.") from exc
    if not 1900 <= day.year <= 2100:
        raise CalculationError("Supported birth years are 1900–2100.")
    naive = datetime.combine(day, clock)
    candidates = []
    for fold in (0, 1):
        local = naive.replace(tzinfo=zone, fold=fold)
        utc = local.astimezone(timezone.utc)
        if utc.astimezone(zone).replace(tzinfo=None) == naive:
            candidates.append((local, utc))
    if not candidates:
        raise CalculationError("This birth time did not occur because the timezone clock moved forward. Correct the recorded clock time.")
    if len({candidate[1] for candidate in candidates}) > 1:
        raise CalculationError("This local birth time occurred twice during a clock change. Use the equivalent unambiguous UTC date/time with timezone UTC after confirming the correct offset.")
    local, utc = candidates[0]
    if utc > datetime.now(timezone.utc):
        raise CalculationError("A birth date/time cannot be in the future.")
    return local, utc


def navamsa_sign(longitude: float) -> int:
    """D9 longitude multiplication; equivalent to movable/fixed/dual starts."""
    return int((longitude % 360) * 9 / 30) % 12


def lunar_details(longitude: float) -> dict:
    lon = longitude % 360
    nak_fraction = lon * 27 / 360
    index = min(int(nak_fraction), 26)
    return {"longitude": round(lon, 9), "degree": round(lon % 30, 7), "sign_index": int(lon // 30), "sign": SIGNS[int(lon // 30)], "nakshatra_index": index, "nakshatra": NAKSHATRAS[index], "pada": min(int((nak_fraction - index) * 4) + 1, 4)}


def vimshottari(birth_utc: datetime, moon_longitude: float) -> list[dict]:
    """MD/AD intervals from birth through 120 fixed 365.25-day years.

    A 365.25-day year is deliberately fixed for reproducibility. The first
    visible MD and AD are clipped at birth, but their true starts are retained.
    Every AD is computed from the *unclipped* MD start and duration.
    """
    fraction = (moon_longitude % 360) * 27 / 360
    index = int(fraction)
    starting_lord_index = index % 9
    starting_lord = DASHA_LORDS[starting_lord_index]
    elapsed = (fraction - index) * DASHA_YEARS[starting_lord] * YEAR_DAYS
    cursor = birth_utc - timedelta(days=elapsed)
    horizon = birth_utc + timedelta(days=120 * YEAR_DAYS)
    result = []
    for offset in range(11):
        lord_index = (starting_lord_index + offset) % 9
        lord = DASHA_LORDS[lord_index]
        duration_days = DASHA_YEARS[lord] * YEAR_DAYS
        end = cursor + timedelta(days=duration_days)
        if cursor >= horizon:
            break
        item = {"lord": lord, "start": _iso(max(cursor, birth_utc)), "end": _iso(min(end, horizon)), "full_start": _iso(cursor), "full_end": _iso(end), "years": DASHA_YEARS[lord], "antardashas": []}
        ad_cursor = cursor
        for ad_offset in range(9):
            ad_lord = DASHA_LORDS[(lord_index + ad_offset) % 9]
            ad_end = ad_cursor + timedelta(days=duration_days * DASHA_YEARS[ad_lord] / 120)
            if ad_offset == 8:
                ad_end = end
            if ad_end > birth_utc and ad_cursor < horizon:
                item["antardashas"].append({"lord": ad_lord, "start": _iso(max(ad_cursor, birth_utc)), "end": _iso(min(ad_end, horizon)), "full_start": _iso(ad_cursor), "full_end": _iso(ad_end)})
            ad_cursor = ad_end
        if end > birth_utc:
            result.append(item)
        cursor = end
    return result


def _houses(asc_sign: int, planets: list[dict], division: int = 1) -> dict:
    sign_key = "sign_index" if division == 1 else "navamsa_sign_index"
    return {"ascendant_sign_index": asc_sign, "ascendant_sign": SIGNS[asc_sign], "houses": [{"number": house + 1, "sign_index": (asc_sign + house) % 12, "sign": SIGNS[(asc_sign + house) % 12], "planets": [p["name"] for p in planets if p[sign_key] == (asc_sign + house) % 12]} for house in range(12)]}


def _rule_screens(planets: list[dict], asc_sign: int) -> tuple[list, list]:
    positions = {p["name"]: p["sign_index"] for p in planets}
    mars = positions["Mars"]
    references = {"Ascendant": asc_sign, "Moon": positions["Moon"], "Venus": positions["Venus"]}
    mars_houses = {ref: (mars - sign) % 12 + 1 for ref, sign in references.items()}
    doshas = [{"key": "manglik", "name": "Manglik / Kuja", "present": any(h in (1, 2, 4, 7, 8, 12) for h in mars_houses.values()), "houses": mars_houses, "references": [{"name": ref, "house": house, "present": house in (1, 2, 4, 7, 8, 12)} for ref, house in mars_houses.items()], "detail": "Base screen: Mars in houses 1, 2, 4, 7, 8 or 12 from Ascendant, Moon or Venus. Each reference is shown separately. No cancellation, severity, health or partner outcome is inferred."}]
    yogas = []
    def add(key: str, name: str, present: bool, detail: str):
        yogas.append({"key": key, "name": name, "present": bool(present), "detail": detail})
    add("gaja_kesari", "Gaja Kesari (base geometry)", (positions["Jupiter"] - positions["Moon"]) % 12 in (0, 3, 6, 9), "Jupiter in a whole-sign kendra (1/4/7/10) from Moon. Strength, dignity, combustion and affliction qualifications are not evaluated for this label.")
    add("budha_aditya", "Budha Aditya (same-sign screen)", positions["Sun"] == positions["Mercury"], "Sun and Mercury share a sidereal sign. This is a conjunction screen; no strength or life outcome is assigned.")
    add("chandra_mangala", "Chandra Mangala (conjunction screen)", positions["Moon"] == positions["Mars"], "Moon and Mars share a sidereal sign. Other aspect-based variants are not included.")
    own_exalted = {"Mars": ({0, 7, 9}, "Ruchaka"), "Mercury": ({2, 5}, "Bhadra"), "Jupiter": ({8, 11, 3}, "Hamsa"), "Venus": ({1, 6, 11}, "Malavya"), "Saturn": ({9, 10, 6}, "Shasha")}
    for planet, (signs, label) in own_exalted.items():
        sign = positions[planet]
        add(label.lower(), label + " (base geometry)", sign in signs and (sign - asc_sign) % 12 in (0, 3, 6, 9), f"{planet} in its own or exaltation sign and a whole-sign kendra (1/4/7/10) from Ascendant. Degrees of exaltation, combustion and affliction qualifications are not evaluated.")
    return doshas, yogas


def chart(profile: dict) -> dict:
    """Compute one chart; raise CalculationError on missing/unsupported data."""
    if not isinstance(profile, dict):
        raise CalculationError("Profile must be an object.")
    local, utc = birth_datetime(profile)
    try:
        latitude = float(profile["latitude"])
        longitude = float(profile["longitude"])
    except (KeyError, ValueError, TypeError) as exc:
        raise CalculationError("Confirmed latitude and longitude are required.") from exc
    if not math.isfinite(latitude) or not -89 < latitude < 89 or not math.isfinite(longitude) or not -180 <= longitude <= 180:
        raise CalculationError("Latitude must be between -89 and 89; longitude must be between -180 and 180.")
    name = str(profile.get("name", "")).strip()
    if not name or len(name) > 100:
        raise CalculationError("Enter a name of 1–100 characters.")
    accuracy = profile.get("time_accuracy", "exact")
    if accuracy not in ("exact", "approximate"):
        raise CalculationError("Time accuracy must be exact or approximate; unknown birth times cannot produce a full chart.")
    for required in ("sepl_18.se1", "semo_18.se1"):
        if not (EPHE_PATH / required).is_file():
            raise CalculationError(f"Required Swiss Ephemeris data file is missing: {required}. Repair the data/ephe folder.")
    hour = utc.hour + utc.minute / 60 + (utc.second + utc.microsecond / 1e6) / 3600
    jd = swe.julday(utc.year, utc.month, utc.day, hour, swe.GREG_CAL)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    with SWISS_LOCK:
        swe.set_ephe_path(str(EPHE_PATH))
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        ayanamsa = swe.get_ayanamsa_ut(jd)
        planets = []
        for name_planet, body in PLANET_IDS:
            try:
                computed = swe.calc_ut(jd, body, flags)
                values, returned_flags = computed[:2]
                # pysweph additionally returns a Swiss warning string.
                if len(computed) > 2 and computed[2]:
                    raise CalculationError(f"Swiss Ephemeris warning: {computed[2]}")
            except swe.Error as exc:
                raise CalculationError("Swiss Ephemeris could not calculate the requested date. Check the bundled ephemeris files.") from exc
            if body != swe.MEAN_NODE and not (returned_flags & swe.FLG_SWIEPH):
                raise CalculationError("Swiss Ephemeris attempted a fallback calculation; the chart was stopped. Repair the ephemeris files.")
            lon = values[0] % 360
            planets.append({"name": name_planet, "longitude": round(lon, 9), "latitude": round(values[1], 7), "speed": round(values[3], 8), "retrograde": bool(values[3] < 0), "sign_index": int(lon // 30), "sign": SIGNS[int(lon // 30)], "degree": round(lon % 30, 7), "navamsa_sign_index": navamsa_sign(lon), "navamsa_sign": SIGNS[navamsa_sign(lon)]})
        rahu = next(p for p in planets if p["name"] == "Rahu")
        ketu_lon = (rahu["longitude"] + 180) % 360
        planets.append({**rahu, "name": "Ketu", "longitude": round(ketu_lon, 9), "sign_index": int(ketu_lon // 30), "sign": SIGNS[int(ketu_lon // 30)], "degree": round(ketu_lon % 30, 7), "navamsa_sign_index": navamsa_sign(ketu_lon), "navamsa_sign": SIGNS[navamsa_sign(ketu_lon)]})
        try:
            _, ascmc = swe.houses_ex(jd, latitude, longitude, b"W", swe.FLG_SIDEREAL)
        except swe.Error as exc:
            raise CalculationError("Ascendant calculation is unsupported for these coordinates/time.") from exc
    asc = ascmc[0] % 360
    asc_sign = int(asc // 30)
    d9_asc = navamsa_sign(asc)
    for planet in planets:
        planet["house"] = (planet["sign_index"] - asc_sign) % 12 + 1
        planet["navamsa_house"] = (planet["navamsa_sign_index"] - d9_asc) % 12 + 1
    moon = lunar_details(next(p["longitude"] for p in planets if p["name"] == "Moon"))
    dashas = vimshottari(utc, moon["longitude"])
    current = None
    now = datetime.now(timezone.utc)
    for md in dashas:
        for ad in md["antardashas"]:
            if datetime.fromisoformat(ad["start"]) <= now < datetime.fromisoformat(ad["end"]):
                current = {"mahadasha": md["lord"], "antardasha": ad["lord"], "start": ad["start"], "end": ad["end"]}
    doshas, yogas = _rule_screens(planets, asc_sign)
    cautions = ["Astronomical positions are calculated; astrology interpretations are traditional and are not scientifically established predictions.", "Yoga and dosha labels mean only that the displayed base rule was met. Cancellation and strength rules are not automatically inferred.", "The location timezone is a database lookup. For historical births, confirm the actual civil time used in the birth record; regional local mean times may differ from the modern timezone history."]
    if accuracy == "approximate":
        cautions.append("Birth time is marked approximate. Ascendant, houses, D9, dasha dates and marriage timing may change; confirm the recorded time before interpreting them.")
    clean_profile = {key: profile[key] for key in ("name", "gender", "date", "time", "timezone", "latitude", "longitude", "place", "time_accuracy") if key in profile}
    clean_profile["name"] = name
    clean_profile["time_accuracy"] = accuracy
    return {"profile": clean_profile, "birth": {"local": _iso(local), "utc": _iso(utc), "timezone": str(local.tzinfo), "julian_day": jd}, "ayanamsa_deg": round(ayanamsa, 8), "ascendant": {"longitude": round(asc, 9), "sign_index": asc_sign, "sign": SIGNS[asc_sign], "degree": round(asc % 30, 7)}, "moon": moon, "planets": planets, "d1": _houses(asc_sign, planets), "d9": _houses(d9_asc, planets, 9), "dashas": dashas, "current_dasha": current, "doshas": doshas, "yogas": yogas, "cautions": cautions, "methodology": {"version": "VEDA-1", "ephemeris": f"Swiss Ephemeris {swe.version}; bundled Swiss files required; no Moshier fallback", "zodiac": "sidereal", "ayanamsa": "Lahiri (Swiss SIDM_LAHIRI)", "houses": "whole sign", "nodes": "mean Rahu; Ketu exactly opposite", "division": "D1 and D9 (longitude ×9 modulo360)", "dasha": "Vimshottari; Moon nakshatra; 365.25-day year; first MD/AD clipped at birth; 120-year horizon", "dosha_scope": "Manglik base screen from Ascendant, Moon, Venus; no cancellations", "yoga_scope": "Eight named base screens; not an exhaustive yoga engine", "unsupported": ["Birth-time rectification", "All classical cancellation and strength rules", "Medical or lifespan predictions", "Guaranteed past or future events"]}}
