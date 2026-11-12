"""IR-1: evidence-bearing, multilingual traditional interpretation screens.

Every temporal statement uses the selected local civil date. Counts are counts
of named symbolic conditions, never measured strength or outcome probabilities.
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo
import swisseph as swe

from . import engine

RULE_VERSION = "IR-1"
SIGN_LORDS = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]
OWN_SIGNS = {"Sun": {4}, "Moon": {3}, "Mars": {0,7}, "Mercury": {2,5}, "Jupiter": {8,11}, "Venus": {1,6}, "Saturn": {9,10}}
EXALTED = {"Sun":0, "Moon":1, "Mars":9, "Mercury":5, "Jupiter":3, "Venus":11, "Saturn":6}
GOCHAR_SUPPORT = {"Jupiter":{2,5,7,9,11}, "Saturn":{3,6,11}, "Mercury":{2,4,6,8,10,11}, "Mars":{3,6,11}}
SOURCES = [
    {"title":"P. V. R. Narasimha Rao, Vedic Astrology: An Integrated Approach; Moon-based gochara Tables 55–59 and 63", "url":"https://www.vedicastrologer.org/articles/vedic_astro_textbook.pdf"},
    {"title":"Mantreswara, Phaladeepika, G. S. Kapoor translation: Chapters 1, 5, 6 and 26 (a different edition from the uploaded Sastri translation)", "url":"https://www.panchanga.lv/wp-content/uploads/2020/06/Phaladipika_Shri-Mantreswara.pdf"},
    {"title":"Swiss Ephemeris programming interface", "url":"https://www.astro.com/swisseph/swephprg.htm"},
]


def lang(en: str, hi: str, mr: str) -> dict:
    return {"en":en, "hi":hi, "mr":mr}


def note(key: str, title: dict, text: dict, evidence: list[str] | None = None, **extras) -> dict:
    result = {"key":key, "title":title, "text":text, **extras}
    if evidence is not None:
        result["evidence"] = evidence
    return result


PLANET_LABELS = {
    "Sun":lang("Sun","सूर्य","सूर्य"), "Moon":lang("Moon","चंद्र","चंद्र"),
    "Mars":lang("Mars","मंगल","मंगळ"), "Mercury":lang("Mercury","बुध","बुध"),
    "Jupiter":lang("Jupiter","गुरु","गुरू"), "Venus":lang("Venus","शुक्र","शुक्र"),
    "Saturn":lang("Saturn","शनि","शनी"), "Rahu":lang("Rahu","राहु","राहू"), "Ketu":lang("Ketu","केतु","केतू")}
SIGN_LABELS = [lang(en,hi,mr) for en,hi,mr in zip(engine.SIGNS,
    ["मेष","वृषभ","मिथुन","कर्क","सिंह","कन्या","तुला","वृश्चिक","धनु","मकर","कुंभ","मीन"],
    ["मेष","वृषभ","मिथुन","कर्क","सिंह","कन्या","तूळ","वृश्चिक","धनु","मकर","कुंभ","मीन"])]


def dasha_at(c: dict, instant: datetime) -> dict | None:
    """Resolve exact half-open MD/AD interval at the requested instant."""
    utc = instant.astimezone(timezone.utc)
    for md in c["dashas"]:
        for ad in md["antardashas"]:
            if datetime.fromisoformat(ad["start"]) <= utc < datetime.fromisoformat(ad["end"]):
                return {"mahadasha":md["lord"], "antardasha":ad["lord"], "start":ad["start"], "end":ad["end"], "mahadasha_start":md["start"], "mahadasha_end":md["end"]}
    return None


def _noon(day: date, zone: ZoneInfo) -> datetime:
    naive = datetime.combine(day,time(12))
    candidates = []
    for fold in (0,1):
        local = naive.replace(tzinfo=zone,fold=fold)
        if local.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == naive:
            candidates.append(local)
    if not candidates or len({x.astimezone(timezone.utc) for x in candidates}) > 1:
        raise engine.CalculationError("Selected local noon is nonexistent or ambiguous in this timezone; select another date.")
    return candidates[0]


def _shift_month(day: date, offset: int, sample_day: int = 15) -> date:
    absolute = day.year*12+day.month-1+offset
    year, month_zero = divmod(absolute,12)
    return date(year,month_zero+1,min(sample_day,monthrange(year,month_zero+1)[1]))


def _transits(c: dict, instant: datetime) -> list[dict]:
    utc = instant.astimezone(timezone.utc)
    hour = utc.hour+utc.minute/60+(utc.second+utc.microsecond/1e6)/3600
    jd = swe.julday(utc.year,utc.month,utc.day,hour,swe.GREG_CAL)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    result = []
    with engine.SWISS_LOCK:
        swe.set_ephe_path(str(engine.EPHE_PATH))
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        for name, body in engine.PLANET_IDS:
            try:
                computed = swe.calc_ut(jd,body,flags)
            except swe.Error as exc:
                raise engine.CalculationError("Transit calculation failed; check the bundled Swiss Ephemeris data.") from exc
            values, returned = computed[:2]
            if (len(computed)>2 and computed[2]) or (body != swe.MEAN_NODE and not returned&swe.FLG_SWIEPH):
                raise engine.CalculationError("Swiss Ephemeris transit warning or fallback; report stopped rather than substituting positions.")
            longitude = values[0]%360
            sign = int(longitude//30)
            result.append({"name":name,"longitude":round(longitude,9),"sign_index":sign,"sign":engine.SIGNS[sign],"degree":round(longitude%30,7),"speed":round(values[3],8),"retrograde":values[3]<0,"house_from_moon":(sign-c["moon"]["sign_index"])%12+1,"house_from_lagna":(sign-c["ascendant"]["sign_index"])%12+1})
    rahu = next(p for p in result if p["name"]=="Rahu")
    longitude = (rahu["longitude"]+180)%360
    sign = int(longitude//30)
    result.append({**rahu,"name":"Ketu","longitude":round(longitude,9),"sign_index":sign,"sign":engine.SIGNS[sign],"degree":round(longitude%30,7),"house_from_moon":(sign-c["moon"]["sign_index"])%12+1,"house_from_lagna":(sign-c["ascendant"]["sign_index"])%12+1})
    return result


def temporal_context(profile: dict, as_of: str | None = None, horizon_months: int = 24) -> dict:
    """Shared local-noon context for all IR-1 reports; no wall-clock dasha."""
    if isinstance(horizon_months,bool) or not isinstance(horizon_months,int) or not 1<=horizon_months<=60:
        raise engine.CalculationError("Choose a whole-number horizon from 1 to 60 months.")
    c = engine.chart(profile)
    zone = ZoneInfo(c["birth"]["timezone"])
    try:
        day = date.fromisoformat(as_of) if as_of is not None else datetime.now(zone).date()
    except (TypeError,ValueError) as exc:
        raise engine.CalculationError("Choose a valid as-of date in YYYY-MM-DD format.") from exc
    if not 1900<=day.year<=2100:
        raise engine.CalculationError("As-of dates must be between 1900 and 2100.")
    final_sample = _shift_month(day,horizon_months-1) if horizon_months>1 else day
    if final_sample.year>2100:
        raise engine.CalculationError("The entire monthly horizon must remain within 1900–2100.")
    sample = _noon(day,zone)
    if sample.astimezone(timezone.utc)<datetime.fromisoformat(c["birth"]["utc"]):
        raise engine.CalculationError("The selected local-noon sample precedes the birth time; choose a date after birth.")
    period = dasha_at(c,sample)
    # Preserve schema while eliminating stale 'current' labels in the embedded chart.
    c["current_dasha"] = period
    c["current_dasha_as_of"] = day.isoformat()
    monthly = []
    for offset in range(horizon_months):
        monthly_day = day if offset==0 else _shift_month(day,offset)
        instant = _noon(monthly_day,zone)
        md = dasha_at(c,instant)
        monthly.append({"month":monthly_day.strftime("%Y-%m"),"sample_at":instant.isoformat(),"mahadasha":md["mahadasha"] if md else None,"antardasha":md["antardasha"] if md else None,"period_start":md["start"] if md else None,"period_end":md["end"] if md else None,"dasha_status":"available" if md else "outside_120_year_horizon","transits":_transits(c,instant)})
    return {"chart":c,"as_of":day.isoformat(),"as_of_timezone":str(zone),"sample_at":sample.isoformat(),"horizon_months":horizon_months,"horizon_end":monthly[-1]["sample_at"],"current_dasha":period,"dasha_status":"available" if period else "outside_120_year_horizon","transits":_transits(c,sample),"timeline":monthly}


def dignity(planet: dict) -> dict:
    name, sign = planet["name"],planet["sign_index"]
    if name not in OWN_SIGNS:
        return {"own_sign":None,"exaltation_sign":None,"debilitation_sign":None,"evaluated":False}
    return {"own_sign":sign in OWN_SIGNS[name],"exaltation_sign":sign==EXALTED[name],"debilitation_sign":sign==(EXALTED[name]+6)%12,"evaluated":True}


def _planet_fact(p: dict) -> dict:
    n,s = PLANET_LABELS[p["name"]],SIGN_LABELS[p["sign_index"]]
    return note("natal_"+p["name"].lower(),n,lang(
        f"{n['en']}: {s['en']} {p['degree']:.2f}°, D1 house {p['house']}.",
        f"{n['hi']}: {s['hi']} {p['degree']:.2f}°, जन्म D1 भाव {p['house']}।",
        f"{n['mr']}: {s['mr']} {p['degree']:.2f}°, जन्म D1 भाव {p['house']}।"),[f"sidereal_longitude={p['longitude']}",f"whole_sign_house={p['house']}"])


def _period_note(period: dict | None) -> dict:
    if not period:
        return note("dasha_unavailable",lang("Period unavailable","दशा उपलब्ध नहीं","दशा उपलब्ध नाही"),lang("The selected date falls outside the calculated birth-to-120-year dasha horizon. No period is guessed.","चुनी तिथि जन्म से 120 वर्ष की गणितीय दशा सीमा से बाहर है। दशा का अनुमान नहीं लगाया गया।","निवडलेली तारीख जन्मापासून 120 वर्षांच्या गणिती दशा मर्यादेबाहेर आहे. दशेचा अंदाज लावलेला नाही."))
    md,ad = PLANET_LABELS[period["mahadasha"]],PLANET_LABELS[period["antardasha"]]
    return note("selected_period",lang("Period on the selected date","चुनी तिथि की दशा","निवडलेल्या तारखेची दशा"),lang(f"{md['en']} mahadasha / {ad['en']} antardasha. This describes the calculated period, not an event guarantee.",f"{md['hi']} महादशा / {ad['hi']} अंतर्दशा। यह गणितीय अवधि है, घटना की गारंटी नहीं।",f"{md['mr']} महादशा / {ad['mr']} अंतर्दशा. हा गणिती कालखंड आहे; घटनेची हमी नाही."),[f"UTC interval {period['start']} ≤ sample < {period['end']}"])


def _transit_signal(p: dict) -> dict:
    name,h = p["name"],p["house_from_moon"]
    support = h in GOCHAR_SUPPORT[name]
    n = PLANET_LABELS[name]
    allowed = ", ".join(str(x) for x in sorted(GOCHAR_SUPPORT[name]))
    classification = lang("supportive base screen" if support else "pressure base screen","सहायक मूल संकेत" if support else "चुनौती का मूल संकेत","सहाय्यक मूळ संकेत" if support else "आव्हानाचा मूळ संकेत")
    return note("gochar_"+name.lower(),n,lang(
        f"{n['en']} is {h} from natal Moon: {classification['en']}. Selected supportive houses: {allowed}. Vedha and Ashtakavarga qualifications are not evaluated.",
        f"{n['hi']} जन्म चंद्र से भाव {h}: {classification['hi']}। चुने सहायक भाव: {allowed}। वेध और अष्टकवर्ग की शर्तें नहीं जाँची गई हैं।",
        f"{n['mr']} जन्मचंद्रापासून भाव {h}: {classification['mr']}. निवडलेले सहाय्यक भाव: {allowed}. वेध व अष्टकवर्गाच्या अटी तपासलेल्या नाहीत."),
        [f"sidereal_sign={p['sign']}",f"house_from_moon={h}",f"house_from_lagna={p['house_from_lagna']}"],polarity="supportive" if support else "pressure",source_rule="PVR Moon-gochara base table; other houses classified as pressure for this screen")


def _career_period_signal(c: dict, lord: str | None, level: str) -> dict:
    title = lang(f"{level} career link",f"{level} कार्य संबंध",f"{level} कार्य संबंध")
    if lord is None:
        return note("period_"+level.lower(),title,lang("Dasha unavailable; no career-period condition evaluated.","दशा उपलब्ध नहीं; कार्य-दशा की शर्त नहीं जाँची गई।","दशा उपलब्ध नाही; कार्य-दशेची अट तपासलेली नाही."),polarity="informational")
    tenth_lord = SIGN_LORDS[(c["ascendant"]["sign_index"]+9)%12]
    p = next(p for p in c["planets"] if p["name"]==lord)
    linked = lord==tenth_lord or p["house"] in {2,6,10,11}
    n = PLANET_LABELS[lord]
    return note("period_"+level.lower(),title,lang(
        f"{n['en']} rules the selected {level}; natal house {p['house']}. The IR-1 career link is {'met' if linked else 'not met'}: period lord is the 10th lord or occupies house 2/6/10/11. This is thematic emphasis, not promotion or income prediction.",
        f"चुनी {level} का स्वामी {n['hi']} है; जन्म भाव {p['house']}। IR-1 कार्य संबंध {'मिला' if linked else 'नहीं मिला'}: दशा स्वामी दशमेश हो या भाव 2/6/10/11 में हो। यह विषयगत संकेत है, पदोन्नति या आय का पूर्वानुमान नहीं।",
        f"निवडलेल्या {level} चा स्वामी {n['mr']}; जन्मभाव {p['house']}. IR-1 कार्य संबंध {'आढळला' if linked else 'आढळला नाही'}: दशास्वामी दशमेश असावा किंवा भाव 2/6/10/11 मध्ये असावा. हा विषयाचा संकेत आहे; पदोन्नती किंवा उत्पन्नाचा अंदाज नाही."),[f"period_lord={lord}",f"natal_house={p['house']}",f"tenth_lord={tenth_lord}"],polarity="supportive" if linked else "informational",source_rule="IR-1 disclosed house/period synthesis, not a verbatim classical event rule")


def _timeline(c: dict, monthly: list[dict], report_type: str) -> list[dict]:
    result = []
    names = ("Jupiter","Saturn","Mercury") if report_type=="career" else ("Jupiter","Saturn","Mars")
    for row in monthly:
        signals = [_transit_signal(p) for p in row["transits"] if p["name"] in names]
        if report_type=="career":
            signals.extend([_career_period_signal(c,row["mahadasha"],"MD"),_career_period_signal(c,row["antardasha"],"AD")])
        else:
            signals.append(note("period_context",lang("Period context","दशा संदर्भ","दशा संदर्भ"),_period_note({"mahadasha":row["mahadasha"],"antardasha":row["antardasha"],"start":row["period_start"],"end":row["period_end"]} if row["mahadasha"] else None)["text"],polarity="informational"))
        support = sum(n["polarity"]=="supportive" for n in signals)
        pressure = sum(n["polarity"]=="pressure" for n in signals)
        result.append({k:v for k,v in row.items() if k!="transits"} | {"support_count":support,"pressure_count":pressure,"indicator_count":support+pressure,"checked_rule_count":len(signals),"signals":signals})
    return result


def _highlights(timeline: list[dict]) -> dict:
    maximum = max(t["support_count"] for t in timeline)
    pressure_maximum = max(t["pressure_count"] for t in timeline)
    minimum = min(t["support_count"] for t in timeline)
    support_ties = [t["month"] for t in timeline if t["support_count"]==maximum]
    pressure_ties = [t["month"] for t in timeline if t["pressure_count"]==pressure_maximum]
    least_ties = [t["month"] for t in timeline if t["support_count"]==minimum]
    return {"supportive":support_ties[:3] if maximum>0 else [],"demanding":pressure_ties[:3] if pressure_maximum>0 else [],"least_support":least_ties[:3],"supportive_ties":support_ties,"demanding_ties":pressure_ties,"least_support_ties":least_ties,"max_support_count":maximum,"max_pressure_count":pressure_maximum,"min_support_count":minimum,"tie_info":lang("Only the first three chronological months tied at each extreme are highlighted. Full tie groups are retained. These are extremes of rule counts within this searched horizon, not real-world career or relationship peaks.","हर चरम संख्या पर बराबर वाले पहले तीन महीनों को समयक्रम में दिखाया गया है; सभी बराबर महीने भी उपलब्ध हैं। ये खोज अवधि के नियम-गणना के चरम हैं, वास्तविक जीवन की सफलता या विफलता के शिखर नहीं।","प्रत्येक टोकाच्या संख्येला समान असलेले पहिले तीन महिने कालक्रमाने दाखवले आहेत; सर्व समान महिनेही उपलब्ध आहेत. हे शोधकालातील नियमगणनेचे टोक आहेत; प्रत्यक्ष जीवनातील यश-अपयशाचे शिखर नाहीत.")}


def _base_report(ctx: dict, kind: str) -> dict:
    tl = _timeline(ctx["chart"],ctx["timeline"],kind)
    cautions = [note("traditional_limits",lang("Interpretation limits","व्याख्या की सीमा","अर्थ लावण्याच्या मर्यादा"),lang("Astrology is a traditional interpretive system. These symbolic screens cannot establish future events, job suitability, personal behaviour or relationship outcomes.","ज्योतिष पारंपरिक व्याख्या पद्धति है। ये प्रतीकात्मक संकेत भविष्य की घटनाएँ, नौकरी की योग्यता, व्यवहार या रिश्ते का परिणाम सिद्ध नहीं करते।","ज्योतिष ही पारंपरिक अर्थलावणी पद्धत आहे. हे प्रतीकात्मक संकेत भावी घटना, नोकरीची योग्यता, वर्तन किंवा नात्याचा परिणाम सिद्ध करत नाहीत.")),note("screen_qualifications",lang("Qualifications not assessed","अनजाँची शर्तें","न तपासलेल्या अटी"),lang("No Shadbala, D10, complete combustion/affliction/cancellation assessment, gochara Vedha or Ashtakavarga strength is claimed. A sign-level dignity is not complete planetary strength.","षड्बल, D10, पूर्ण अस्तंगतता/पीड़ा/दोषभंग, गोचर वेध या अष्टकवर्ग बल का दावा नहीं है। राशि-स्तर की स्थिति पूर्ण ग्रहबल नहीं है।","षड्बल, D10, संपूर्ण अस्तंगतता/पीडा/दोषभंग, गोचर वेध किंवा अष्टकवर्ग बलाचा दावा नाही. राशीपातळीवरील स्थिती म्हणजे संपूर्ण ग्रहबल नाही."))]
    if ctx["chart"]["profile"].get("time_accuracy")=="approximate":
        cautions.insert(0,note("approximate_birth_time",lang("Approximate birth time","जन्म समय अनुमानित है","जन्मवेळ अंदाजे आहे"),lang("This profile marks birth time approximate. Ascendant, house lordships, D9 and dasha boundaries can change. Treat the detailed report and monthly emphasis as provisional until the recorded time is confirmed.","इस प्रोफाइल का जन्म समय अनुमानित है। लग्न, भाव स्वामित्व, D9 और दशा सीमाएँ बदल सकती हैं। समय की पुष्टि तक विस्तृत रिपोर्ट और मासिक संकेत अस्थायी मानें।","या प्रोफाइलची जन्मवेळ अंदाजे आहे. लग्न, भावस्वामित्व, D9 व दशांच्या सीमा बदलू शकतात. नोंदवलेली वेळ निश्चित होईपर्यंत सविस्तर अहवाल व मासिक संकेत तात्पुरते समजा.")))
    if any(r["dasha_status"]!="available" for r in ctx["timeline"]):
        cautions.append(_period_note(None))
    methods = [note("time_basis",lang("Selected-date calculation","चुनी तिथि की गणना","निवडलेल्या तारखेची गणना"),lang(f"As-of {ctx['as_of']}, local noon in {ctx['as_of_timezone']}. The first monthly sample is this date; later samples use the 15th at local noon. Dasha periods are looked up at each sample, not at the computer's current time.",f"आधार तिथि {ctx['as_of']}, {ctx['as_of_timezone']} में स्थानीय दोपहर। पहला मासिक नमूना इसी तिथि पर; अगले हर महीने की 15 तारीख दोपहर पर। हर नमूने की दशा उसी समय पर खोजी जाती है।",f"आधार तारीख {ctx['as_of']}, {ctx['as_of_timezone']} मधील स्थानिक दुपार. पहिला मासिक नमुना याच तारखेला; पुढील प्रत्येक महिन्याच्या 15 तारखेला दुपारी. प्रत्येक नमुन्याची दशा त्याच वेळेनुसार शोधली जाते.")),note("count_method",lang("What the graph counts","ग्राफ क्या गिनता है","आलेख काय मोजतो"),lang("One count per displayed passed supportive or pressure condition; no weights or percentages. Three Moon-based gochara tables are screened without Vedha. Career adds separate MD/AD career links. Informational notes do not change counts. One sample is not a complete month forecast.","दिखाई गई हर सहायक या चुनौती की शर्त पर एक गिनती; कोई भार या प्रतिशत नहीं। चंद्र-आधारित तीन गोचर तालिकाएँ बिना वेध जाँची जाती हैं। कार्य रिपोर्ट में MD/AD कार्य संबंध अलग जुड़ते हैं। सूचनात्मक बातें गिनती नहीं बदलतीं। एक नमूना पूरे महीने का पूर्वानुमान नहीं।","दाखवलेल्या प्रत्येक सहाय्यक किंवा आव्हानात्मक अटीस एक गणना; वजन किंवा टक्केवारी नाही. चंद्राधारित तीन गोचर तक्ते वेधाशिवाय तपासले जातात. कार्य अहवालात MD/AD कार्य संबंध स्वतंत्र जोडले जातात. माहितीपर नोंदी गणना बदलत नाहीत. एक नमुना संपूर्ण महिन्याचा अंदाज नाही."))]
    return {"report_type":kind,"rule_version":RULE_VERSION,"as_of":ctx["as_of"],"as_of_timezone":ctx["as_of_timezone"],"chart":ctx["chart"],"context":{k:ctx[k] for k in ("current_dasha","transits","sample_at","dasha_status")},"summary":[],"sections":[],"timeline":tl,"highlights":_highlights(tl),"methodology":methods,"cautions":cautions,"sources":list(SOURCES)}


SECTORS = [
    {"key":"government_public_service","title":lang("Government & public service","सरकारी व सार्वजनिक सेवा","सरकारी व सार्वजनिक सेवा"),"planets":{"Sun","Saturn","Jupiter"},"house":6,"growth":9,
     "meaning":lang("Sun/authority, Saturn/structured service and Jupiter/advice are the disclosed symbolic associations. They do not establish selection in an examination, administrative power, political success or suitability for a political party.","सूर्य/प्राधिकार, शनि/संगठित सेवा और गुरु/परामर्श यहाँ चुने प्रतीक हैं। इनसे परीक्षा चयन, प्रशासनिक अधिकार, राजनीतिक सफलता या दल की उपयुक्तता सिद्ध नहीं होती।","सूर्य/अधिकार, शनी/संघटित सेवा व गुरू/सल्ला हे निवडलेले प्रतीक आहेत. यावरून परीक्षा निवड, प्रशासकीय अधिकार, राजकीय यश किंवा पक्षाची योग्यता सिद्ध होत नाही."),
     "advice":lang("Compare eligibility, examination preparation, public communication and service values against an actual recruitment path.","वास्तविक भर्ती के लिए पात्रता, परीक्षा तैयारी, जनसंवाद और सेवा-मूल्यों की तुलना करें।","प्रत्यक्ष भरतीसाठी पात्रता, परीक्षेची तयारी, जनसंवाद व सेवामूल्ये तपासा.")},
    {"key":"technical_engineering_data","title":lang("Technology, engineering & data","तकनीक, अभियांत्रिकी व डेटा","तंत्रज्ञान, अभियांत्रिकी व डेटा"),"planets":{"Mars","Mercury","Saturn"},"house":6,"growth":5,
     "meaning":lang("Mars/action and tools, Mercury/analysis and Saturn/systems are mapped to modern technical work as an IR-1 interpretation. A chart cannot verify mathematical aptitude, coding ability or engineering qualifications.","मंगल/क्रिया व उपकरण, बुध/विश्लेषण और शनि/प्रणाली का आधुनिक तकनीकी कार्य से संबंध IR-1 की व्याख्या है। कुंडली गणित, कोडिंग या अभियांत्रिकी योग्यता प्रमाणित नहीं करती।","मंगळ/कृती व साधने, बुध/विश्लेषण व शनी/प्रणाली यांचा आधुनिक तांत्रिक कामाशी संबंध ही IR-1 अर्थलावणी आहे. कुंडली गणित, कोडिंग किंवा अभियांत्रिकी पात्रता सिद्ध करत नाही."),
     "advice":lang("Use a small coding, mechanical-design or data project and an aptitude assessment to test interest and competence.","रुचि व क्षमता जाँचने के लिए छोटा कोडिंग, यांत्रिक डिजाइन या डेटा प्रोजेक्ट और योग्यता परीक्षण करें।","आवड व क्षमता तपासण्यासाठी छोटा कोडिंग, यांत्रिक रचना किंवा डेटा प्रकल्प व योग्यता चाचणी वापरा.")},
    {"key":"business_entrepreneurship","title":lang("Business & entrepreneurship","व्यवसाय व उद्यमिता","व्यवसाय व उद्योजकता"),"planets":{"Mercury","Venus","Mars"},"house":7,"growth":11,
     "meaning":lang("Mercury/trade, Venus/value and Mars/initiative connect symbolically with commerce; houses 7 and 11 frame clients and gains. These rule matches do not measure profit, creditworthiness or the safety of taking business risk.","बुध/व्यापार, शुक्र/मूल्य और मंगल/पहल वाणिज्य के प्रतीक हैं; भाव 7 व 11 ग्राहक और लाभ के संदर्भ हैं। नियमों का मिलना लाभ, ऋण-योग्यता या व्यावसायिक जोखिम की सुरक्षा नहीं मापता।","बुध/व्यापार, शुक्र/मूल्य व मंगळ/पुढाकार हे वाणिज्याचे प्रतीक; भाव 7 व 11 ग्राहक व लाभांचा संदर्भ देतात. नियम जुळणे म्हणजे नफा, पतपात्रता किंवा व्यावसायिक जोखीम सुरक्षित असल्याचे मोजमाप नाही."),
     "advice":lang("Validate customer demand, contracts, cash flow and a capped pilot budget before considering a business commitment.","व्यवसाय का निर्णय लेने से पहले ग्राहक माँग, अनुबंध, नकदी प्रवाह और सीमित परीक्षण बजट जाँचें।","व्यवसायाचा निर्णय घेण्यापूर्वी ग्राहकांची मागणी, करार, रोख प्रवाह व मर्यादित प्रायोगिक बजेट तपासा.")},
    {"key":"education_advisory","title":lang("Education, research & advisory","शिक्षा, शोध व परामर्श","शिक्षण, संशोधन व सल्ला"),"planets":{"Jupiter","Mercury","Moon"},"house":9,"growth":5,
     "meaning":lang("Jupiter/teaching, Mercury/explanation and Moon/receptivity are the selected learning and advisory symbols; houses 5 and 9 add study and higher-learning themes. Professional credentials and subject expertise must be assessed independently.","गुरु/शिक्षण, बुध/व्याख्या और चंद्र/ग्रहणशीलता सीखने व परामर्श के चुने प्रतीक हैं; भाव 5 व 9 अध्ययन और उच्च शिक्षा के विषय जोड़ते हैं। पेशेवर पात्रता और विषय-विशेषज्ञता अलग जाँचें।","गुरू/अध्यापन, बुध/स्पष्टीकरण व चंद्र/ग्रहणशीलता हे शिक्षण व सल्ल्याचे निवडलेले प्रतीक; भाव 5 व 9 अभ्यास व उच्च शिक्षणाचा संदर्भ देतात. व्यावसायिक पात्रता व विषयातील कौशल्य स्वतंत्रपणे तपासा."),
     "advice":lang("Try teaching a topic, publishing a short explanation or completing a supervised research task; compare the feedback with your qualifications.","किसी विषय को पढ़ाकर, संक्षिप्त व्याख्या लिखकर या निर्देशित शोध करके प्रतिक्रिया की तुलना अपनी पात्रता से करें।","एखादा विषय शिकवून, संक्षिप्त स्पष्टीकरण लिहून किंवा मार्गदर्शित संशोधन करून अभिप्रायाची पात्रतेशी तुलना करा.")},
    {"key":"creative_service","title":lang("Creative work & people services","रचनात्मक कार्य व जनसेवा","सर्जनशील काम व लोकसेवा"),"planets":{"Venus","Moon","Mercury"},"house":7,"growth":5,
     "meaning":lang("Venus/aesthetics, Moon/public contact and Mercury/communication form the selected creative and service symbolism. This does not establish artistic talent, popularity or client demand.","शुक्र/सौंदर्य, चंद्र/जनसंपर्क और बुध/संवाद चुने रचनात्मक व सेवा प्रतीक हैं। इससे कला-कौशल, लोकप्रियता या ग्राहक माँग सिद्ध नहीं होती।","शुक्र/सौंदर्य, चंद्र/जनसंपर्क व बुध/संवाद हे निवडलेले सर्जनशील व सेवेचे प्रतीक आहेत. यावरून कलागुण, लोकप्रियता किंवा ग्राहकांची मागणी सिद्ध होत नाही."),
     "advice":lang("Build a small portfolio or service trial, request independent feedback and assess training, working conditions and demand.","छोटा पोर्टफोलियो या सेवा परीक्षण बनाकर स्वतंत्र प्रतिक्रिया, प्रशिक्षण, कार्य-स्थितियाँ और माँग जाँचें।","छोटा पोर्टफोलिओ किंवा सेवेची चाचणी करून स्वतंत्र अभिप्राय, प्रशिक्षण, कामाच्या अटी व मागणी तपासा.")},
]


def _sector_section(c: dict, period: dict | None, sector: dict) -> dict:
    ps = {p["name"]:p for p in c["planets"]}
    asc = c["ascendant"]["sign_index"]
    tenth = SIGN_LORDS[(asc+9)%12]
    main = sector["house"]
    growth = sector["growth"]
    associated = sector["planets"]
    names = ", ".join(sorted(associated))
    main_lord = SIGN_LORDS[(asc+main-1)%12]
    strong = [name for name in associated if dignity(ps[name])["own_sign"] or dignity(ps[name])["exaltation_sign"]]
    conditions = [
        ("tenth_lord",tenth in associated,lang("10th lord is an associated planet","दशमेश संबंधित ग्रह है","दशमेश संबंधित ग्रह आहे"),f"10th lord={tenth}; associated={names}"),
        ("occupies_tenth",any(ps[n]["house"]==10 for n in associated),lang("Associated planet occupies house 10","संबंधित ग्रह भाव 10 में है","संबंधित ग्रह भाव 10 मध्ये आहे"),f"Natal houses: {', '.join(n+'='+str(ps[n]['house']) for n in sorted(associated))}"),
        ("occupies_main",any(ps[n]["house"]==main for n in associated),lang(f"Associated planet occupies house {main}",f"संबंधित ग्रह भाव {main} में है",f"संबंधित ग्रह भाव {main} मध्ये आहे"),f"sector reference house={main}"),
        ("main_lord",main_lord in associated,lang(f"House {main} lord is associated",f"भाव {main} स्वामी संबंधित है",f"भाव {main} स्वामी संबंधित आहे"),f"house {main} lord={main_lord}"),
        ("sign_dignity",bool(strong),lang("At least one associated planet is in own/exaltation sign","कम से कम एक संबंधित ग्रह स्वराशि/उच्च राशि में है","किमान एक संबंधित ग्रह स्वराशी/उच्च राशीत आहे"),f"own/exaltation sign planets={', '.join(sorted(strong)) or 'none'}; sign-level only"),
        ("md_link",bool(period and period["mahadasha"] in associated),lang("Selected mahadasha lord is associated","चुनी महादशा स्वामी संबंधित है","निवडलेल्या महादशेचा स्वामी संबंधित आहे"),f"MD={period['mahadasha'] if period else 'unavailable'}"),
        ("ad_link",bool(period and period["antardasha"] in associated),lang("Selected antardasha lord is associated","चुनी अंतर्दशा स्वामी संबंधित है","निवडलेल्या अंतर्दशेचा स्वामी संबंधित आहे"),f"AD={period['antardasha'] if period else 'unavailable'}"),
        ("growth_house",any(ps[n]["house"]==growth for n in associated),lang(f"Associated planet occupies house {growth}",f"संबंधित ग्रह भाव {growth} में है",f"संबंधित ग्रह भाव {growth} मध्ये आहे"),f"sector supporting house={growth}"),
    ]
    count = sum(bool(v[1]) for v in conditions)
    evidence = [_planet_fact(ps[n]) for n in sorted(associated)]
    evidence.extend(note("condition_"+key,title,lang(f"{'Met' if matched else 'Not met'}. {fact}",f"{'मिला' if matched else 'नहीं मिला'}। {fact}",f"{'आढळले' if matched else 'आढळले नाही'}. {fact}"),[fact],matched=bool(matched)) for key,matched,title,fact in conditions)
    if period is None:
        evidence.append(_period_note(None))
    count_text = lang(f"{count}/8 disclosed symbolic conditions matched. ",f"8 में से {count} घोषित प्रतीकात्मक शर्तें मिलीं। ",f"8 पैकी {count} जाहीर प्रतीकात्मक अटी जुळल्या. ")
    return {"key":sector["key"],"title":sector["title"],"text":{l:count_text[l]+sector["meaning"][l] for l in ("en","hi","mr")},"evidence":evidence,"advice":[note("try_before_deciding",lang("Practical next step","व्यावहारिक अगला कदम","व्यावहारिक पुढचे पाऊल"),sector["advice"])],"match_count":count,"rule_count":8,"associated_planets":sorted(associated),"conditions":[{"key":k,"matched":bool(m),"title":t,"evidence":lang(f,f,f)} for k,m,t,f in conditions]}


def career_report(profile: dict, as_of: str | None = None, horizon_months: int = 24) -> dict:
    ctx = temporal_context(profile,as_of,horizon_months)
    c = ctx["chart"]
    report = _base_report(ctx,"career")
    asc = c["ascendant"]["sign_index"]
    tenth_sign = (asc+9)%12
    tenth_lord = SIGN_LORDS[tenth_sign]
    p = next(p for p in c["planets"] if p["name"]==tenth_lord)
    n,s = PLANET_LABELS[tenth_lord],SIGN_LABELS[tenth_sign]
    d = dignity(p)
    report["summary"] = [note("career_basis",lang("Career framework","कार्य-क्षेत्र का आधार","कार्य-क्षेत्राचा आधार"),lang(f"Whole-sign 10th house is {s['en']}; its lord {n['en']} is in natal house {p['house']}. Compare five sector association counts below; none is a career-choice verdict.",f"पूर्ण-राशि दशम भाव {s['hi']} है; दशमेश {n['hi']} जन्म भाव {p['house']} में है। नीचे पाँच क्षेत्रों की संकेत-गणना की तुलना करें; कोई भी करियर-चयन का निर्णय नहीं है।",f"पूर्णराशी दशम भाव {s['mr']}; दशमेश {n['mr']} जन्मभाव {p['house']} मध्ये आहे. खालील पाच क्षेत्रांच्या संकेतगणनांची तुलना करा; कोणताही निकाल करियर-निवडीचा निर्णय नाही.")),_period_note(ctx["current_dasha"])]
    overview = {"key":"career_foundation","title":lang("10th lord, houses & dignity","दशमेश, भाव व राशि स्थिति","दशमेश, भाव व राशीस्थिती"),"text":lang("The 10th frames work and public responsibility; 6th service, 7th clients/partnership, 2nd resources, 11th gains, 5th learning/creation and 9th higher learning are secondary contexts. IR-1 combines these symbols openly; the eight-condition sector matrix is an application convention, not a quoted classical job formula.","दशम भाव कार्य व सार्वजनिक दायित्व का संदर्भ है; भाव 6 सेवा, 7 ग्राहक/साझेदारी, 2 संसाधन, 11 लाभ, 5 अध्ययन/रचना और 9 उच्च शिक्षा के सहायक संदर्भ हैं। IR-1 इन प्रतीकों को खुलकर जोड़ता है; आठ-शर्त क्षेत्र तालिका ऐप का नियम है, शास्त्र का उद्धृत नौकरी-सूत्र नहीं।","दशम भाव काम व सार्वजनिक जबाबदारीचा संदर्भ; भाव 6 सेवा, 7 ग्राहक/भागीदारी, 2 साधनसंपत्ती, 11 लाभ, 5 शिक्षण/निर्मिती व 9 उच्च शिक्षण हे दुय्यम संदर्भ आहेत. IR-1 हे प्रतीक उघडपणे एकत्र करतो; आठ-अटींचा क्षेत्रतक्ता हा अॅपचा नियम आहे, शास्त्रातील उद्धृत नोकरीसूत्र नाही."),"evidence":[_planet_fact(p),note("tenth_lord_dignity",lang("Sign-level dignity of the 10th lord","दशमेश की राशि-स्तर की स्थिति","दशमेशाची राशीपातळीवरील स्थिती"),lang(f"Own sign: {d['own_sign']}; exaltation sign: {d['exaltation_sign']}; debilitation sign: {d['debilitation_sign']}. Both own and exaltation can be true for Mercury in Virgo. This is not a Shadbala result or a final strong/weak verdict.",f"स्वराशि: {d['own_sign']}; उच्च राशि: {d['exaltation_sign']}; नीच राशि: {d['debilitation_sign']}। कन्या में बुध के लिए स्वराशि व उच्च दोनों हो सकते हैं। यह षड्बल या अंतिम बलवान/कमजोर निर्णय नहीं।",f"स्वराशी: {d['own_sign']}; उच्चराशी: {d['exaltation_sign']}; नीचराशी: {d['debilitation_sign']}. कन्येतील बुधासाठी स्वराशी व उच्च दोन्ही खरे असू शकतात. हा षड्बल किंवा अंतिम बलवान/दुर्बल निर्णय नाही."),[f"planet={tenth_lord}",f"sign={p['sign']}"])],"advice":[note("career_choice",lang("Keep the decision practical","निर्णय व्यावहारिक रखें","निर्णय व्यावहारिक ठेवा"),lang("Compare interest, demonstrated skills, qualifications, recruitment criteria and available opportunities. Do not choose a job, investment or political affiliation from these counts.","रुचि, प्रमाणित कौशल, पात्रता, भर्ती मानदंड और उपलब्ध अवसरों की तुलना करें। इन गिनतियों से नौकरी, निवेश या राजनीतिक दल न चुनें।","आवड, सिद्ध कौशल्ये, पात्रता, भरतीचे निकष व उपलब्ध संधींची तुलना करा. या गणनांवरून नोकरी, गुंतवणूक किंवा राजकीय पक्ष निवडू नका."))],"tenth_lord":tenth_lord,"dignity":d}
    report["sections"] = [overview]+[_sector_section(c,ctx["current_dasha"],sector) for sector in SECTORS]
    report["sections"].append({"key":"career_timing","title":lang("Monthly work themes","मासिक कार्य संदर्भ","मासिक कार्य संदर्भ"),"text":lang("Read each month's visible Jupiter, Saturn and Mercury Moon-based screens with its own MD/AD career links. More supportive matches means only more selected rules passed at that sample; pressure matches are prompts to review plans, not predictions of loss or unemployment.","हर महीने के दिखाए गुरु, शनि व बुध के चंद्र-आधारित संकेत और उसी समय के MD/AD कार्य संबंध पढ़ें। अधिक सहायक गिनती का अर्थ उस नमूने पर अधिक चुने नियम मिले; चुनौती संकेत योजना की समीक्षा का संदर्भ हैं, हानि या बेरोजगारी का पूर्वानुमान नहीं।","प्रत्येक महिन्याचे दाखवलेले गुरू, शनी व बुधाचे चंद्राधारित संकेत आणि त्याच वेळचे MD/AD कार्य संबंध वाचा. अधिक सहाय्यक गणना म्हणजे त्या नमुन्यावर अधिक निवडलेले नियम जुळले; आव्हानात्मक संकेत योजना पाहण्याचे संदर्भ आहेत, नुकसान किंवा बेरोजगारीचे भाकीत नाही."),"evidence":[_period_note(ctx["current_dasha"])] + [_transit_signal(p) for p in ctx["transits"] if p["name"] in ("Jupiter","Saturn","Mercury")],"advice":[note("planning",lang("Use dates for a review rhythm","तिथियाँ समीक्षा के लिए उपयोग करें","तारखा आढाव्यासाठी वापरा"),lang("Schedule learning, application tracking and mentor feedback using real deadlines. Do not postpone a concrete opportunity solely because a month has fewer symbolic matches.","वास्तविक समय-सीमा के अनुसार सीखने, आवेदनों और मार्गदर्शक प्रतिक्रिया की योजना बनाएँ। कम प्रतीकात्मक संकेत के कारण वास्तविक अवसर न टालें।","प्रत्यक्ष मुदतींनुसार शिक्षण, अर्जांचा मागोवा व मार्गदर्शकाचा अभिप्राय नियोजित करा. कमी प्रतीकात्मक संकेतांमुळे प्रत्यक्ष संधी पुढे ढकलू नका."))]})
    return report


YOGA_INFO = {
    "gaja_kesari":({"Jupiter","Moon"},lang("Learning, counsel and emotional perspective are its conventional themes. The base condition is Jupiter in a whole-sign kendra from Moon.","ज्ञान, परामर्श और भावनात्मक दृष्टि इसके पारंपरिक विषय हैं। मूल शर्त चंद्र से गुरु का पूर्ण-राशि केंद्र में होना है।","ज्ञान, सल्ला व भावनिक दृष्टिकोन हे पारंपरिक विषय. मूळ अट म्हणजे चंद्रापासून गुरू पूर्णराशी केंद्रात असणे.")),
    "budha_aditya":({"Sun","Mercury"},lang("Communication with authority and intellectual expression are conventional themes. The screen requires Sun and Mercury in one sign; their proximity alone does not establish strength.","प्राधिकार के साथ संवाद और बौद्धिक अभिव्यक्ति पारंपरिक विषय हैं। शर्त सूर्य-बुध की एक राशि है; केवल निकटता बल सिद्ध नहीं करती।","अधिकारासह संवाद व बौद्धिक अभिव्यक्ती हे पारंपरिक विषय. सूर्य-बुध एकाच राशीत असणे ही अट; केवळ जवळीक बल सिद्ध करत नाही.")),
    "chandra_mangala":({"Moon","Mars"},lang("Initiative linked to feeling and activity is a conventional theme. This variant tests only Moon–Mars in the same sign, without aspect variants or claims about wealth or temperament.","भावना से जुड़ी पहल व सक्रियता पारंपरिक विषय है। इस रूप में केवल चंद्र-मंगल की एक राशि जाँची जाती है; दृष्टि-रूप या धन/स्वभाव के निष्कर्ष नहीं।","भावनांशी जोडलेला पुढाकार व सक्रियता हा पारंपरिक विषय. यात फक्त चंद्र-मंगळ एकाच राशीत आहेत का ते तपासले जाते; दृष्टिप्रकार किंवा धन/स्वभावाचे निष्कर्ष नाहीत.")),
    "ruchaka":({"Mars"},lang("Action, organisation and technical initiative are conventional Mars themes. The base rule needs Mars in its own/exaltation sign and a kendra from Lagna.","क्रिया, संगठन और तकनीकी पहल मंगल के पारंपरिक विषय हैं। मूल नियम: मंगल स्वराशि/उच्च राशि और लग्न से केंद्र में।","कृती, संघटन व तांत्रिक पुढाकार हे मंगळाचे पारंपरिक विषय. मूळ नियम: मंगळ स्वराशी/उच्च राशीत व लग्नापासून केंद्रात.")),
    "bhadra":({"Mercury"},lang("Analysis, language and trade are conventional Mercury themes. The base rule needs Mercury in its own/exaltation sign and a kendra from Lagna.","विश्लेषण, भाषा और व्यापार बुध के पारंपरिक विषय हैं। मूल नियम: बुध स्वराशि/उच्च राशि और लग्न से केंद्र में।","विश्लेषण, भाषा व व्यापार हे बुधाचे पारंपरिक विषय. मूळ नियम: बुध स्वराशी/उच्च राशीत व लग्नापासून केंद्रात.")),
    "hamsa":({"Jupiter"},lang("Study, guidance and ethical reflection are conventional Jupiter themes. The base rule needs Jupiter in its own/exaltation sign and a kendra from Lagna.","अध्ययन, मार्गदर्शन और नैतिक चिंतन गुरु के पारंपरिक विषय हैं। मूल नियम: गुरु स्वराशि/उच्च राशि और लग्न से केंद्र में।","अभ्यास, मार्गदर्शन व नैतिक चिंतन हे गुरूचे पारंपरिक विषय. मूळ नियम: गुरू स्वराशी/उच्च राशीत व लग्नापासून केंद्रात.")),
    "malavya":({"Venus"},lang("Aesthetics, amenities and relating are conventional Venus themes. The base rule needs Venus in its own/exaltation sign and a kendra from Lagna.","सौंदर्य, सुविधाएँ और संबंध शुक्र के पारंपरिक विषय हैं। मूल नियम: शुक्र स्वराशि/उच्च राशि और लग्न से केंद्र में।","सौंदर्य, सुविधा व संबंध हे शुक्राचे पारंपरिक विषय. मूळ नियम: शुक्र स्वराशी/उच्च राशीत व लग्नापासून केंद्रात.")),
    "shasha":({"Saturn"},lang("Discipline, sustained work and structures are conventional Saturn themes. The base rule needs Saturn in its own/exaltation sign and a kendra from Lagna.","अनुशासन, लगातार कार्य और व्यवस्था शनि के पारंपरिक विषय हैं। मूल नियम: शनि स्वराशि/उच्च राशि और लग्न से केंद्र में।","शिस्त, सातत्यपूर्ण काम व रचना हे शनीचे पारंपरिक विषय. मूळ नियम: शनी स्वराशी/उच्च राशीत व लग्नापासून केंद्रात.")),
}
YOGA_TITLES = {"gaja_kesari":lang("Gaja Kesari","गजकेसरी","गजकेसरी"),"budha_aditya":lang("Budha Aditya","बुधादित्य","बुधादित्य"),"chandra_mangala":lang("Chandra Mangala","चंद्र-मंगल","चंद्र-मंगळ"),"ruchaka":lang("Ruchaka","रुचक","रुचक"),"bhadra":lang("Bhadra","भद्र","भद्र"),"hamsa":lang("Hamsa","हंस","हंस"),"malavya":lang("Malavya","मालव्य","मालव्य"),"shasha":lang("Shasha","शश","शश")}


def _activation_note(ctx: dict, participants: set[str], key: str) -> dict:
    period = ctx["current_dasha"]
    active = sorted(participants & {period["mahadasha"],period["antardasha"]}) if period else []
    active_text = lang(", ".join(PLANET_LABELS[n]["en"] for n in active) or "none",", ".join(PLANET_LABELS[n]["hi"] for n in active) or "कोई नहीं",", ".join(PLANET_LABELS[n]["mr"] for n in active) or "कोणी नाही")
    months = [r["month"] for r in ctx["timeline"] if participants & {r["mahadasha"],r["antardasha"]}]
    month_text = ", ".join(months) or "—"
    return note(key+"_period_relevance",lang("Period relevance","दशा में प्रासंगिकता","दशेतील संदर्भ"),lang(f"Participants also governing the selected MD/AD: {active_text['en']}. Monthly samples with a participant as MD/AD lord: {month_text}. This is a thematic link, not proof that this yoga/dosha will produce an event.",f"चुनी MD/AD में भी स्वामी बने संबंधित ग्रह: {active_text['hi']}। संबंधित ग्रह की MD/AD वाले मासिक नमूने: {month_text}। यह विषयगत संबंध है, योग/दोष से घटना होने का प्रमाण नहीं।",f"निवडलेल्या MD/AD चे स्वामी असलेले संबंधित ग्रह: {active_text['mr']}. संबंधित ग्रहाची MD/AD असलेले मासिक नमुने: {month_text}. हा विषयाचा संबंध आहे; योग/दोषामुळे घटना घडेल याचा पुरावा नाही."),[f"participants={','.join(sorted(participants))}",f"active_participants={','.join(active)}"],active_participants=active,months=months)


def _same_sign_transit_note(ctx: dict, participants: set[str], key: str) -> dict:
    natal = {p["name"]:p for p in ctx["chart"]["planets"]}
    links = [(tr["name"],n) for tr in ctx["transits"] if tr["name"] in {"Jupiter","Saturn","Mars"} for n in sorted(participants) if tr["sign_index"]==natal[n]["sign_index"]]
    facts = [f"transit {tr} shares natal {n} sign {natal[n]['sign']}" for tr,n in links]
    body = lang("; ".join(facts) if facts else "No selected Jupiter/Saturn/Mars transit shares the natal sign of a participant at this sample.","; ".join(facts) if facts else "इस नमूने पर चुने गुरु/शनि/मंगल गोचर संबंधित जन्म ग्रह की राशि में नहीं हैं।","; ".join(facts) if facts else "या नमुन्यावर निवडलेले गुरू/शनी/मंगळ गोचर संबंधित जन्मग्रहाच्या राशीत नाहीत.")
    end = lang(" Sign contact is a geometric monitoring fact, not a cancellation, strength measurement or event trigger."," राशि संपर्क ज्यामितीय तथ्य है, दोषभंग, बल-मापन या घटना का संकेतक नहीं।"," राशीसंपर्क हे भूमितीय तथ्य आहे; दोषभंग, बलमापन किंवा घटनेचा कारक नाही.")
    return note(key+"_transit_contact",lang("Selected-date transit contacts","चुनी तिथि के गोचर संपर्क","निवडलेल्या तारखेचे गोचर संपर्क"),{l:body[l]+end[l] for l in ("en","hi","mr")},facts)


def dosha_report(profile: dict, as_of: str | None = None, horizon_months: int = 24) -> dict:
    ctx = temporal_context(profile,as_of,horizon_months)
    c = ctx["chart"]
    report = _base_report(ctx,"dosha")
    present_yogas = sum(x["present"] for x in c["yogas"])
    report["summary"] = [note("dosha_scope",lang("What is assessed","क्या जाँचा गया है","काय तपासले आहे"),lang(f"One Manglik screen and eight yoga geometries are explained individually; {present_yogas} yoga base conditions are present. Their natal geometry does not switch on and off each month. Periods and transits below add selected-date context, not inevitable effects.",f"एक मांगलिक संकेत और आठ योगों की ज्यामितीय शर्तें अलग समझाई गई हैं; {present_yogas} योगों की मूल शर्तें मिली हैं। जन्म की ज्यामिति हर महीने चालू-बंद नहीं होती। नीचे की दशा व गोचर चुनी तिथि का संदर्भ जोड़ते हैं, अनिवार्य फल नहीं।",f"एक मांगलिक संकेत व आठ योगांच्या भूमितीय अटी स्वतंत्र स्पष्ट केल्या आहेत; {present_yogas} योगांच्या मूळ अटी आढळल्या. जन्माची भूमिती दर महिन्याला चालू-बंद होत नाही. खालील दशा व गोचर निवडलेल्या तारखेचा संदर्भ देतात; अटळ परिणाम नाहीत.")),_period_note(ctx["current_dasha"])]
    mars = next(p for p in c["planets"] if p["name"]=="Mars")
    for rule in c["doshas"]+c["yogas"]:
        present = rule["present"]
        state = lang("Base condition present. " if present else "Base condition absent. ","मूल शर्त मौजूद है। " if present else "मूल शर्त नहीं मिली। ","मूळ अट आढळली. " if present else "मूळ अट आढळली नाही. ")
        if rule["key"]=="manglik":
            participants = {"Mars"}
            meaning = lang("Mars in house 1/2/4/7/8/12 from Lagna, Moon or Venus meets this selected Kuja screen. Its conventional relationship themes concern initiative, boundaries and managing disagreement; it cannot establish aggression, harm, divorce or a partner's character. No severity or cancellation is assigned.","लग्न, चंद्र या शुक्र से मंगल का भाव 1/2/4/7/8/12 में होना इस चुनी कुज शर्त को पूरा करता है। इसके पारंपरिक संबंध-विषय पहल, सीमाएँ और असहमति सँभालना हैं; इससे आक्रामकता, हानि, तलाक या साथी का चरित्र सिद्ध नहीं होता। तीव्रता या दोषभंग तय नहीं है।","लग्न, चंद्र किंवा शुक्रापासून मंगळ भाव 1/2/4/7/8/12 मध्ये असल्यास ही निवडलेली कुज अट जुळते. पुढाकार, मर्यादा व मतभेद हाताळणे हे पारंपरिक नातेसंदर्भ; यावरून आक्रमकता, हानी, घटस्फोट किंवा जोडीदाराचे चारित्र्य सिद्ध होत नाही. तीव्रता किंवा दोषभंग ठरवलेला नाही.")
            facts = [_planet_fact(mars)]
            for ref in rule["references"]:
                facts.append(note("mars_from_"+ref["name"].lower(),lang("Mars reference","मंगल का संदर्भ","मंगळाचा संदर्भ"),lang(f"From {ref['name']}: Mars house {ref['house']}; selected condition {'met' if ref['present'] else 'not met'}.",f"{ref['name']} से: मंगल भाव {ref['house']}; चुनी शर्त {'मिली' if ref['present'] else 'नहीं मिली'}।",f"{ref['name']} पासून: मंगळ भाव {ref['house']}; निवडलेली अट {'आढळली' if ref['present'] else 'आढळली नाही'}."),[f"reference={ref['name']};house={ref['house']};present={ref['present']}"]))
            advice = lang("Use respectful discussion of boundaries and conflict handling. Neither a positive nor a negative Manglik screen replaces consent, real behaviour, compatibility discussions or qualified counselling when needed. No gemstone, payment or ritual is required by this app.","सीमाओं और मतभेद सँभालने पर सम्मानपूर्वक चर्चा करें। मांगलिक शर्त मिलना या न मिलना सहमति, वास्तविक व्यवहार, अनुकूलता पर बातचीत या आवश्यक योग्य परामर्श का विकल्प नहीं। ऐप रत्न, भुगतान या अनुष्ठान अनिवार्य नहीं करता।","मर्यादा व मतभेद हाताळण्याबाबत आदराने संवाद साधा. मांगलिक अट जुळणे अथवा न जुळणे हे संमती, प्रत्यक्ष वर्तन, सुसंगतीवरील चर्चा किंवा आवश्यक तज्ज्ञ समुपदेशनाला पर्याय नाही. अॅप रत्न, शुल्क किंवा विधी बंधनकारक करत नाही.")
            title = lang("Manglik / Kuja significance","मांगलिक / कुज का अर्थ","मांगलिक / कुज अर्थ")
        else:
            participants,meaning = YOGA_INFO[rule["key"]]
            facts = [_planet_fact(p) for p in c["planets"] if p["name"] in participants]
            advice = lang("Treat the named theme as a reflection prompt and compare it with demonstrated skills and behaviour. Do not assume special status, guaranteed wealth or immunity from difficulties because a base yoga condition is present.","नामित विषय को आत्मचिंतन का संदर्भ मानकर वास्तविक कौशल व व्यवहार से तुलना करें। मूल योग मिलने से विशेष दर्जा, निश्चित धन या कठिनाइयों से सुरक्षा न मानें।","नावातील विषय आत्मचिंतनाचा संदर्भ मानून प्रत्यक्ष कौशल्य व वर्तनाशी तुलना करा. मूळ योग जुळल्याने विशेष दर्जा, निश्चित धन किंवा अडचणींपासून संरक्षण गृहीत धरू नका.")
            title = YOGA_TITLES[rule["key"]]
        qualifications = lang(" Full strength, combustion, affliction, exact exaltation strength and cancellation qualifications are not assessed. Absence of this one base condition does not imply a bad chart."," पूर्ण बल, अस्तंगतता, पीड़ा, उच्चता का अंश-बल और दोषभंग नहीं जाँचे गए। इस एक मूल शर्त का न मिलना खराब कुंडली का अर्थ नहीं।"," संपूर्ण बल, अस्तंगतता, पीडा, उच्चतेचे अंशबल व दोषभंग तपासलेले नाहीत. ही एक मूळ अट न जुळणे म्हणजे कुंडली वाईट असा अर्थ नाही.")
        facts.extend([_activation_note(ctx,participants,rule["key"]),_same_sign_transit_note(ctx,participants,rule["key"])])
        report["sections"].append({"key":rule["key"],"name":rule["name"],"title":title,"present":present,"text":{l:state[l]+meaning[l]+qualifications[l] for l in ("en","hi","mr")},"evidence":facts,"advice":[note("practical_response",lang("Practical response","व्यावहारिक दृष्टिकोण","व्यावहारिक दृष्टिकोन"),advice)],"participants":sorted(participants)})
    return report
