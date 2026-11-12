"""PM-1: transparent personal marriage indicators, never an event prediction.

Uses the common temporal_context for actual selected-date dasha/transits.
All derived narrative is tied to visible geometry or explicitly general advice.
"""
from __future__ import annotations

from datetime import date, datetime
import calendar

from .engine import CalculationError, SIGNS
from .interpretation import temporal_context

RULE_VERSION = "PM-1"
LORDS = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]
ASPECTS = {"Mars": (4, 7, 8), "Jupiter": (5, 7, 9), "Saturn": (3, 7, 10)}
JUPITER_SUPPORT = {2, 5, 7, 9, 11}
SATURN_PRESSURE = {12, 1, 2}
SOURCES = [
    {"title": "P.V.R. Narasimha Rao: Vedic Astrology—An Integrated Approach, PDF 36 §2.2.8; PDF 112 §10.2; PDF 329 Table 57; PDF 330 Table 59", "url": "https://www.vedicastrologer.org/articles/vedic_astro_textbook.pdf"},
    {"title": "Journal of Astrology: Case Study of Predictions—Marriage and Children (seventh lord, Venus, family and timing)", "url": "https://www.journalofastrology.com/article.php?article_id=149&category_id=1"},
    {"title": "Journal of Astrology: Joe Biden, marriage section (practitioner example of fifth/seventh connections)", "url": "https://www.journalofastrology.com/page.php?page=joe_biden_2"},
]


def _lang(en: str, hi: str, mr: str) -> dict:
    return {"en": en, "hi": hi, "mr": mr}


def _note(key: str, title: dict, text: dict, evidence: list[str] | None = None) -> dict:
    result = {"key": key, "title": title, "text": text}
    if evidence:
        result["evidence"] = evidence
    return result


PLANET_LABELS = {
    "Sun": _lang("Sun", "सूर्य", "सूर्य"), "Moon": _lang("Moon", "चंद्र", "चंद्र"),
    "Mars": _lang("Mars", "मंगल", "मंगळ"), "Mercury": _lang("Mercury", "बुध", "बुध"),
    "Jupiter": _lang("Jupiter", "गुरु", "गुरू"), "Venus": _lang("Venus", "शुक्र", "शुक्र"),
    "Saturn": _lang("Saturn", "शनि", "शनी"), "Rahu": _lang("Rahu", "राहु", "राहू"),
    "Ketu": _lang("Ketu", "केतु", "केतू"),
}
SIGN_LABELS = [_lang(en, hi, mr) for en, hi, mr in zip(SIGNS,
    ["मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या", "तुला", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन"],
    ["मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या", "तूळ", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन"])]


def _aspect(source: dict, target: dict) -> bool:
    distance = (target["sign_index"] - source["sign_index"]) % 12 + 1
    return distance in ASPECTS.get(source["name"], (7,))


def _connection(first: dict, second: dict) -> list[str]:
    """Only reproducible same-sign, mutual full aspects, or sign exchange."""
    if first["name"] == second["name"]:
        return ["same_lord"]
    result = []
    if first["sign_index"] == second["sign_index"]:
        result.append("same_sign")
    if _aspect(first, second) and _aspect(second, first):
        result.append("mutual_full_aspect")
    if LORDS[first["sign_index"]] == second["name"] and LORDS[second["sign_index"]] == first["name"]:
        result.append("sign_exchange")
    return result


def _month_after(day: date, months: int) -> date:
    index = day.year * 12 + day.month - 1 + months
    year, zero_month = divmod(index, 12)
    month = zero_month + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def _windows(timeline: list[dict], selected: date, horizon_months: int) -> list[dict]:
    """Calendar bins around qualifying monthly samples, not ingress intervals."""
    groups: list[list[dict]] = []
    for row in timeline:
        if not row["supportive_sample"]:
            continue
        month = date.fromisoformat(row["month"] + "-01")
        if groups and _month_after(date.fromisoformat(groups[-1][-1]["month"] + "-01"), 1) == month:
            groups[-1].append(row)
        else:
            groups.append([row])
    end = _month_after(selected, horizon_months)
    return [{"start": max(selected, date.fromisoformat(group[0]["month"] + "-01")).isoformat(),
             "end": min(end, _month_after(date.fromisoformat(group[-1]["month"] + "-01"), 1)).isoformat(),
             "months": [row["month"] for row in group],
             "label": _lang("Months with converging base indicators", "मूल संकेत साथ मिलने वाले महीने", "मूल संकेत एकत्र दिसणारे महिने"),
             "boundary_type": "calendar_month_bins_not_event_or_ingress_boundaries"}
            for group in groups]


def _monthly_signals(row: dict, seventh_lord: str) -> tuple[list[dict], int, int, bool]:
    targets = {seventh_lord, "Venus"}
    main, sub = row.get("mahadasha"), row.get("antardasha")
    main_active, sub_active = main in targets, sub in targets
    transits = {item["name"]: item for item in row["transits"]}
    try:
        jupiter_house = int(transits["Jupiter"]["house_from_moon"])
        saturn_house = int(transits["Saturn"]["house_from_moon"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CalculationError("Calculated Jupiter and Saturn transits from the natal Moon are required.") from exc
    jupiter_active = jupiter_house in JUPITER_SUPPORT
    saturn_active = saturn_house in SATURN_PRESSURE
    main_labels = PLANET_LABELS.get(main, _lang("Unavailable", "अनुपलब्ध", "अनुपलब्ध"))
    sub_labels = PLANET_LABELS.get(sub, _lang("Unavailable", "अनुपलब्ध", "अनुपलब्ध"))
    signals = [
        _note("md_activation" if main_active else "md_no_activation",
              _lang("Main-period check", "महादशा जाँच", "महादशा तपासणी"),
              _lang(f"{main_labels['en']} mahadasha {'matches' if main_active else 'does not match'} the selected Venus/seventh-lord activation rule. Activation is a traditional topic marker, not a marriage promise.",
                    f"{main_labels['hi']} महादशा में चुना गया शुक्र/सप्तमेश सक्रियता नियम {'मिलता है' if main_active else 'नहीं मिलता'}। यह पारंपरिक विषय-संकेत है, विवाह का वादा नहीं।",
                    f"{main_labels['mr']} महादशेत निवडलेला शुक्र/सप्तमेश सक्रियतेचा नियम {'जुळतो' if main_active else 'जुळत नाही'}। हा पारंपरिक विषय-संकेत आहे; विवाहाचे आश्वासन नाही।"),
              [f"MD={main}; seventh_lord={seventh_lord}; targets={','.join(sorted(targets))}"]),
        _note("ad_activation" if sub_active else "ad_no_activation",
              _lang("Sub-period check", "अंतर्दशा जाँच", "अंतर्दशा तपासणी"),
              _lang(f"{sub_labels['en']} antardasha {'matches' if sub_active else 'does not match'} the selected activation rule. This is checked separately from the main period.",
                    f"{sub_labels['hi']} अंतर्दशा में चुना गया सक्रियता नियम {'मिलता है' if sub_active else 'नहीं मिलता'}। इसकी जाँच महादशा से अलग है।",
                    f"{sub_labels['mr']} अंतर्दशेत निवडलेला सक्रियतेचा नियम {'जुळतो' if sub_active else 'जुळत नाही'}। ही तपासणी महादशेपासून स्वतंत्र आहे।"),
              [f"AD={sub}; seventh_lord={seventh_lord}"]),
        _note("jupiter_support" if jupiter_active else "jupiter_no_support",
              _lang("Jupiter's Moon-relative transit", "चंद्र से गुरु का गोचर", "चंद्रापासून गुरूचे गोचर"),
              _lang(f"Jupiter is in house {jupiter_house} from the natal Moon. It {'meets' if jupiter_active else 'does not meet'} the general supportive transit set 2/5/7/9/11; this is not a marriage-specific forecast. Vedha and Ashtakavarga are not applied.",
                    f"गुरु जन्मचंद्र से भाव {jupiter_house} में है। सामान्य अनुकूल गोचर समूह 2/5/7/9/11 का नियम {'मिलता है' if jupiter_active else 'नहीं मिलता'}; यह केवल विवाह का पूर्वानुमान नहीं। वेध और अष्टकवर्ग लागू नहीं हैं।",
                    f"गुरू जन्मचंद्रापासून भाव {jupiter_house} मध्ये आहे। सामान्य अनुकूल गोचरसमूह 2/5/7/9/11 चा नियम {'जुळतो' if jupiter_active else 'जुळत नाही'}; हे विवाहाचे स्वतंत्र भाकीत नाही। वेध व अष्टकवर्ग लागू केलेले नाहीत।"),
              [f"Jupiter longitude={transits['Jupiter']['longitude']}; house_from_moon={jupiter_house}"]),
        _note("saturn_pressure" if saturn_active else "saturn_no_pressure",
              _lang("Saturn's Moon-relative transit", "चंद्र से शनि का गोचर", "चंद्रापासून शनीचे गोचर"),
              _lang(f"Saturn is in house {saturn_house} from the natal Moon. The selected 12/1/2 pressure screen {'is present' if saturn_active else 'is not present'}. It is a general traditional demand indicator, not proof of distress, delay or marital failure.",
                    f"शनि जन्मचंद्र से भाव {saturn_house} में है। चुना गया 12/1/2 दबाव-संकेत {'मिलता है' if saturn_active else 'नहीं मिलता'}। यह सामान्य पारंपरिक संकेत है; परेशानी, विलंब या वैवाहिक असफलता का प्रमाण नहीं।",
                    f"शनी जन्मचंद्रापासून भाव {saturn_house} मध्ये आहे। निवडलेला 12/1/2 ताण-संकेत {'दिसतो' if saturn_active else 'दिसत नाही'}। हा सामान्य पारंपरिक संकेत आहे; त्रास, विलंब किंवा वैवाहिक अपयशाचा पुरावा नाही।"),
              [f"Saturn longitude={transits['Saturn']['longitude']}; house_from_moon={saturn_house}"]),
    ]
    return signals, int(main_active) + int(sub_active) + int(jupiter_active), int(saturn_active), bool((main_active or sub_active) and jupiter_active)


def personal_marriage_report(profile: dict, as_of: str, horizon_months: int = 24) -> dict:
    """Return a localized, evidence-led report using actual selected-date data."""
    if isinstance(horizon_months, bool) or not isinstance(horizon_months, int) or not 1 <= horizon_months <= 60:
        raise CalculationError("Marriage horizon must be an integer from 1 to 60 months.")
    context = temporal_context(profile, as_of, horizon_months)
    natal = context["chart"]
    selected = date.fromisoformat(context["as_of"])
    birth = date.fromisoformat(profile["date"])
    age = selected.year - birth.year - ((selected.month, selected.day) < (birth.month, birth.day))
    caution = _note("interpretive_limits", _lang("Meaning of this report", "इस रिपोर्ट का अर्थ", "या अहवालाचा अर्थ"),
        _lang("Calculated positions and periods are facts under the chosen settings. Marriage, partner identity and love-versus-arranged outcomes are not determinable facts from a horoscope. These are limited traditional indicators, not probabilities or instructions to marry.",
              "चुनी गई गणना-पद्धति के अनुसार ग्रहस्थितियाँ और दशाएँ गणितीय परिणाम हैं। विवाह, साथी की पहचान और प्रेम या पारिवारिक परिचय से विवाह का वास्तविक परिणाम कुंडली से निश्चित नहीं होता। ये सीमित पारंपरिक संकेत हैं; संभावना-प्रतिशत या विवाह करने का निर्देश नहीं।",
              "निवडलेल्या गणनापद्धतीनुसार ग्रहस्थिती व दशा हे गणिती परिणाम आहेत। विवाह, जोडीदाराची ओळख आणि प्रेमविवाह की कुटुंबाच्या ओळखीतून विवाह हे वास्तविक निष्कर्ष कुंडलीतून निश्चित होत नाहीत। हे मर्यादित पारंपरिक संकेत आहेत; संभाव्यतेची टक्केवारी किंवा लग्नाचा आदेश नाही।"))
    report = {"report_type": "personal_marriage", "rule_version": RULE_VERSION,
              "as_of": context["as_of"], "as_of_timezone": context["as_of_timezone"], "chart": natal,
              "context": {"current_dasha": context["current_dasha"], "transits": context["transits"]},
              "summary": [], "sections": [], "timeline": [], "highlights": {"supportive": [], "demanding": []},
              "windows": [], "methodology": [], "cautions": [caution], "sources": [dict(source) for source in SOURCES]}
    if age < 18:
        limited = _note("adult_guard", _lang("Educational view only", "केवल शैक्षिक जानकारी", "केवळ शैक्षणिक माहिती"),
            _lang("The profile is under 18 on the selected date. Partner, marriage-style and marriage-timing interpretations are withheld. The chart remains available for general learning; no marriage timeline is generated.",
                  "चुनी हुई तारीख पर प्रोफ़ाइल की आयु 18 वर्ष से कम है। साथी, विवाह के प्रकार और विवाह के समय की व्याख्या नहीं दी जाती। सामान्य अध्ययन के लिए कुंडली उपलब्ध है; विवाह समयरेखा नहीं बनाई गई।",
                  "निवडलेल्या तारखेला प्रोफाइलचे वय 18 वर्षांपेक्षा कमी आहे। जोडीदार, विवाहाचा प्रकार व विवाहाची वेळ यांचे विश्लेषण दिलेले नाही। सामान्य अभ्यासासाठी कुंडली उपलब्ध आहे; विवाहाची कालरेषा तयार केलेली नाही।"),
            [f"age_at_as_of={age}; adult_screen=18"])
        report["summary"] = [limited]
        report["sections"] = [{"key": "education", "title": limited["title"], "text": limited["text"], "evidence": [], "advice": []}]
        report["methodology"] = [_note("scope_under18", limited["title"], limited["text"])]
        return report

    asc = natal["ascendant"]["sign_index"]
    planets = {p["name"]: p for p in natal["planets"]}
    fifth_sign, seventh_sign = (asc + 4) % 12, (asc + 6) % 12
    fifth_lord, seventh_lord = LORDS[fifth_sign], LORDS[seventh_sign]
    personal_links = _connection(planets[fifth_lord], planets[seventh_lord])
    if planets[fifth_lord]["house"] == 7:
        personal_links.append("fifth_lord_in_seventh")
    if planets[seventh_lord]["house"] == 5:
        personal_links.append("seventh_lord_in_fifth")
    if (seventh_sign - planets[fifth_lord]["sign_index"]) % 12 + 1 in ASPECTS.get(fifth_lord, (7,)):
        personal_links.append("fifth_lord_full_aspect_on_seventh")
    family_links = []
    for house in (2, 4):
        lord = LORDS[(asc + house - 1) % 12]
        for kind in _connection(planets[lord], planets[seventh_lord]):
            family_links.append(f"house{house}_{kind}")
    if personal_links and family_links:
        connection_state = "mixed_connections"
        state = _lang("Both connection groups are present", "दोनों प्रकार के संबंध मिलते हैं", "दोन्ही प्रकारचे संबंध दिसतात")
    elif personal_links:
        connection_state = "personal_choice_connections"
        state = _lang("Fifth/seventh connections are present", "पंचम/सप्तम संबंध मिलते हैं", "पंचम/सप्तम संबंध दिसतात")
    elif family_links:
        connection_state = "family_connections"
        state = _lang("Family-house connections are present", "परिवार-भाव के संबंध मिलते हैं", "कुटुंबभावांचे संबंध दिसतात")
    else:
        connection_state = "no_selected_connection"
        state = _lang("No connection in the selected small rule set", "चुने गए सीमित नियमों में संबंध नहीं मिला", "निवडलेल्या मर्यादित नियमांत संबंध दिसला नाही")
    style_text = _lang(
        f"{state['en']}. Fifth/seventh links are sometimes read as personal-choice symbolism; second/fourth-house links connect partnership with family/home themes. These categories can coexist. They do not decide love or family-introduced marriage, and an absent checked link does not rule either out.",
        f"{state['hi']}। पंचम/सप्तम संबंध को कभी-कभी स्वयं चुने संबंध का प्रतीक माना जाता है; द्वितीय/चतुर्थ भाव के संबंध परिवार और घर के विषय जोड़ते हैं। दोनों साथ हो सकते हैं। ये प्रेम या पारिवारिक परिचय से विवाह तय नहीं करते; जाँचा गया संबंध न मिलने से कोई विकल्प समाप्त नहीं होता।",
        f"{state['mr']}। पंचम/सप्तम संबंधांचा कधी स्वतः निवडलेल्या नात्याचे प्रतीक म्हणून विचार होतो; द्वितीय/चतुर्थ भावांचे संबंध कुटुंब व घराच्या विषयांना जोडतात। दोन्ही एकत्र असू शकतात। यावरून प्रेमविवाह किंवा कुटुंबाच्या ओळखीतून विवाह ठरत नाही; तपासलेला संबंध नसल्याने कोणताही पर्याय नाकारला जात नाही।")
    style_evidence = _note("natal_connections", state, _lang(
        f"Fifth lord {fifth_lord}, house {planets[fifth_lord]['house']}; seventh lord {seventh_lord}, house {planets[seventh_lord]['house']}. Personal-choice connection checks: {len(personal_links)}; family/home connection checks: {len(family_links)}. Counts describe geometry only, not preference strength.",
        f"पंचमेश {PLANET_LABELS[fifth_lord]['hi']}, भाव {planets[fifth_lord]['house']}; सप्तमेश {PLANET_LABELS[seventh_lord]['hi']}, भाव {planets[seventh_lord]['house']}। स्वयं-चयन संबंध जाँच: {len(personal_links)}; परिवार/घर संबंध जाँच: {len(family_links)}। गिनती केवल ज्यामिति बताती है, पसंद की तीव्रता नहीं।",
        f"पंचमेश {PLANET_LABELS[fifth_lord]['mr']}, भाव {planets[fifth_lord]['house']}; सप्तमेश {PLANET_LABELS[seventh_lord]['mr']}, भाव {planets[seventh_lord]['house']}। स्वतःच्या निवडीचे संबंध: {len(personal_links)}; कुटुंब/घर संबंध: {len(family_links)}। मोजणी केवळ भूमितीची आहे; पसंतीच्या तीव्रतेची नाही।"),
        [f"connection_state={connection_state}", f"personal_links={','.join(personal_links) or 'none_in_selected_rules'}", f"family_links={','.join(family_links) or 'none_in_selected_rules'}"])
    report["summary"].append(_note("personal_overview", _lang("Personal marriage overview", "व्यक्तिगत विवाह समीक्षा", "वैयक्तिक विवाह आढावा"), style_text))
    report["sections"].append({"key": "relationship_style", "title": _lang("Love or family-introduced marriage", "प्रेम या पारिवारिक परिचय से विवाह", "प्रेमविवाह की कुटुंबाच्या ओळखीतून विवाह"), "text": style_text, "evidence": [style_evidence], "advice": [_note("choice_advice", _lang("Keep personal choice explicit", "व्यक्तिगत पसंद स्पष्ट रखें", "वैयक्तिक निवड स्पष्ट ठेवा"), _lang("Discuss consent, the kind of introduction you want and family involvement directly. These decisions come from the people involved, not chart labels.", "सहमति, परिचय के पसंदीदा तरीके और परिवार की भूमिका पर सीधे बात करें। ये निर्णय संबंधित लोगों के हैं, कुंडली के लेबल के नहीं।", "संमती, ओळखीची आवडती पद्धत आणि कुटुंबाची भूमिका यावर थेट चर्चा करा। हे निर्णय संबंधित व्यक्तींचे आहेत; कुंडलीतील नावांचे नाहीत।"))]})

    seventh = planets[seventh_lord]
    venus = planets["Venus"]
    married_text = _lang("The seventh house, its lord and Venus are shown as traditional partnership references. Their placements provide discussion prompts, not a diagnosis of a spouse's character or a forecast of married-life quality.", "सप्तम भाव, सप्तमेश और शुक्र पारंपरिक साझेदारी-संदर्भ के रूप में दिखाए गए हैं। उनकी स्थिति चर्चा के बिंदु हैं; साथी के चरित्र का निदान या वैवाहिक जीवन की गुणवत्ता का पूर्वानुमान नहीं।", "सप्तम भाव, सप्तमेश व शुक्र हे पारंपरिक भागीदारीचे संदर्भ म्हणून दिले आहेत। त्यांच्या स्थिती चर्चेचे मुद्दे आहेत; जोडीदाराच्या चारित्र्याचे निदान किंवा वैवाहिक जीवनाच्या गुणवत्तेचे भाकीत नाही।")
    married_evidence = _note("partnership_geometry", _lang("Calculated partnership references", "गणना किए गए साझेदारी संदर्भ", "गणना केलेले भागीदारी संदर्भ"), _lang(
        f"Seventh sign {SIGNS[seventh_sign]}; its lord {seventh_lord} is in house {seventh['house']} and D9 house {seventh['navamsa_house']}. Venus is in house {venus['house']} and D9 house {venus['navamsa_house']}. D9 placements are displayed without a quality score.",
        f"सप्तम राशि {SIGN_LABELS[seventh_sign]['hi']}; उसका स्वामी {PLANET_LABELS[seventh_lord]['hi']} भाव {seventh['house']} और नवांश भाव {seventh['navamsa_house']} में है। शुक्र भाव {venus['house']} और नवांश भाव {venus['navamsa_house']} में है। नवांश स्थिति को गुणवत्ता-अंक नहीं दिया गया है।",
        f"सप्तम राशी {SIGN_LABELS[seventh_sign]['mr']}; तिचा स्वामी {PLANET_LABELS[seventh_lord]['mr']} भाव {seventh['house']} व नवांश भाव {seventh['navamsa_house']} मध्ये आहे। शुक्र भाव {venus['house']} व नवांश भाव {venus['navamsa_house']} मध्ये आहे। नवांशस्थितीला गुणवत्तेचे गुण दिलेले नाहीत।"),
        [f"seventh_lord={seventh_lord}; natal_longitude={seventh['longitude']}", f"Venus natal_longitude={venus['longitude']}"])
    report["sections"].append({"key": "married_life", "title": _lang("Married life and communication", "वैवाहिक जीवन और संवाद", "वैवाहिक जीवन व संवाद"), "text": married_text, "evidence": [married_evidence], "advice": [_note("communication", _lang("Useful conversation topics", "उपयोगी बातचीत के विषय", "उपयुक्त संवादाचे विषय"), _lang("Before commitment, discuss money, household work, career plans, family boundaries, children if desired and how disagreements will be handled. This is general planning advice, not a personality inference from the chart.", "प्रतिबद्धता से पहले धन, घरेलू काम, करियर, पारिवारिक सीमाओं, इच्छित संतान और मतभेद सुलझाने पर बात करें। यह सामान्य योजना-सुझाव है, कुंडली से व्यक्तित्व का निष्कर्ष नहीं।", "बांधिलकीपूर्वी पैसा, घरकाम, करिअर, कुटुंबाच्या मर्यादा, इच्छा असल्यास मुले व मतभेद सोडवण्याची पद्धत यांवर चर्चा करा। हा सामान्य नियोजनाचा सल्ला आहे; कुंडलीवरून व्यक्तिमत्त्वाचा निष्कर्ष नाही।"))]})

    for sample in context["timeline"]:
        signals, support, pressure, supportive = _monthly_signals(sample, seventh_lord)
        report["timeline"].append({"month": sample["month"], "sample_at": sample["sample_at"], "mahadasha": sample["mahadasha"], "antardasha": sample["antardasha"], "support_count": support, "pressure_count": pressure, "indicator_count": 4, "supportive_sample": supportive, "signals": signals})
    report["highlights"] = {"supportive": [row["month"] for row in report["timeline"] if row["supportive_sample"]], "demanding": [row["month"] for row in report["timeline"] if row["pressure_count"]]}
    report["windows"] = _windows(report["timeline"], selected, horizon_months)
    timing_text = _lang(f"The next {horizon_months} monthly samples combine Venus/seventh-lord MD or AD activation with Jupiter's general supportive Moon-relative transit. Saturn 12/1/2 is shown separately. Support and pressure can coexist. Counts are transparent rule counts, not probabilities; months without convergence do not deny marriage.", f"अगले {horizon_months} मासिक नमूनों में शुक्र/सप्तमेश की महादशा या अंतर्दशा सक्रियता और चंद्र से गुरु का सामान्य अनुकूल गोचर साथ जाँचा गया है। शनि 12/1/2 अलग दिखाया गया है। अनुकूलता और दबाव साथ हो सकते हैं। गिनती नियमों की है, संभावना की नहीं; संकेत न मिलने वाला महीना विवाह को नकारता नहीं।", f"पुढील {horizon_months} मासिक नमुन्यांत शुक्र/सप्तमेशाची महादशा किंवा अंतर्दशा आणि चंद्रापासून गुरूचे सामान्य अनुकूल गोचर एकत्र तपासले आहे। शनी 12/1/2 स्वतंत्र दाखवला आहे। अनुकूलता व ताण एकत्र असू शकतात। ही नियमांची मोजणी आहे; संभाव्यतेची नाही। संकेत न जुळणारा महिना विवाह नाकारत नाही।")
    report["sections"].append({"key": "timing", "title": _lang("Marriage timing indicators", "विवाह-समय के संकेत", "विवाहाच्या वेळेचे संकेत"), "text": timing_text, "evidence": [_note("horizon_counts", _lang("Within the selected horizon", "चुनी हुई अवधि में", "निवडलेल्या कालावधीत"), _lang(f"{len(report['highlights']['supportive'])} sampled months meet both activation and Jupiter conditions; {len(report['highlights']['demanding'])} meet the separate Saturn pressure screen. No dates beyond this horizon are ranked.", f"{len(report['highlights']['supportive'])} नमूना महीनों में सक्रियता और गुरु की दोनों शर्तें मिलती हैं; {len(report['highlights']['demanding'])} में शनि का अलग दबाव-संकेत मिलता है। इस अवधि से बाहर की तारीखों की रैंकिंग नहीं की गई।", f"{len(report['highlights']['supportive'])} नमुना महिन्यांत सक्रियता व गुरू या दोन्ही अटी जुळतात; {len(report['highlights']['demanding'])} महिन्यांत शनीचा स्वतंत्र ताण-संकेत दिसतो। या कालावधीबाहेरील तारखांचे क्रमांकन केलेले नाही।"))], "advice": []})

    direction_index = seventh_sign % 4
    direction = [_lang("East", "पूर्व", "पूर्व"), _lang("South", "दक्षिण", "दक्षिण"), _lang("West", "पश्चिम", "पश्चिम"), _lang("North", "उत्तर", "उत्तर")][direction_index]
    report["sections"].append({"key": "direction", "title": _lang("Symbolic direction and its limit", "प्रतीकात्मक दिशा और उसकी सीमा", "प्रतीकात्मक दिशा व तिची मर्यादा"), "text": _lang(f"The seventh sign, {SIGNS[seventh_sign]}, has the conventional symbolic direction {direction['en']}. This is only a sign correspondence. A real spouse's birthplace, home, meeting direction or distance is not determinable by this rule; do not restrict a search to that compass direction.", f"सप्तम राशि {SIGN_LABELS[seventh_sign]['hi']} की पारंपरिक प्रतीकात्मक दिशा {direction['hi']} है। यह केवल राशि का संबंध है। इस नियम से वास्तविक साथी का जन्मस्थान, घर, मिलने की दिशा या दूरी निश्चित नहीं होती; खोज को उस दिशा तक सीमित न करें।", f"सप्तम राशी {SIGN_LABELS[seventh_sign]['mr']}ची पारंपरिक प्रतीकात्मक दिशा {direction['mr']} आहे। हा केवळ राशीचा संबंध आहे। यावरून वास्तविक जोडीदाराचे जन्मस्थान, घर, भेटीची दिशा किंवा अंतर निश्चित होत नाही; शोध त्या दिशेपुरता मर्यादित करू नका।"), "evidence": [_note("direction_correspondence", _lang("Fixed sign correspondence", "राशि का निश्चित प्रतीकात्मक संबंध", "राशीचा निश्चित प्रतीकात्मक संबंध"), _lang("Fire signs→East; earth→South; air→West; water→North. Reference: Rao, section 2.2.8. Applying the seventh sign does not turn this correspondence into a location prediction.", "अग्नि राशियाँ→पूर्व; पृथ्वी→दक्षिण; वायु→पश्चिम; जल→उत्तर। संदर्भ: राव, खंड 2.2.8। सप्तम राशि का उपयोग इस संबंध को स्थान की भविष्यवाणी नहीं बनाता।", "अग्निराशी→पूर्व; पृथ्वी→दक्षिण; वायू→पश्चिम; जल→उत्तर। संदर्भ: राव, विभाग 2.2.8। सप्तम राशीचा वापर केल्याने हा संबंध स्थानाचे भाकीत ठरत नाही।"), [f"seventh_sign={SIGNS[seventh_sign]}; symbolic_direction={direction['en']}; actual_spouse_location=not_determinable"])], "advice": []})

    next_note = _note("next_step", _lang("Best practical next step", "अगला उपयोगी व्यावहारिक कदम", "पुढचे उपयुक्त व्यावहारिक पाऊल"), _lang("Confirm the recorded birth time, state your preferred way of meeting people, and assess mutual consent, values and practical compatibility with a real person. If you want a traditional review, take the displayed evidence to a practitioner; choose a wedding muhurta only after a partner, place and feasible date range are known.", "जन्म का दर्ज समय जाँचें, लोगों से मिलने का पसंदीदा तरीका स्पष्ट करें और वास्तविक व्यक्ति के साथ पारस्परिक सहमति, मूल्यों और व्यावहारिक अनुकूलता का आकलन करें। पारंपरिक समीक्षा चाहें तो ये प्रमाण किसी ज्योतिषी को दिखाएँ; साथी, स्थान और संभव तारीख-सीमा तय होने के बाद ही विवाह-मुहूर्त चुनें।", "नोंदवलेली जन्मवेळ तपासा, लोकांना भेटण्याची आवडती पद्धत स्पष्ट करा आणि वास्तविक व्यक्तीसोबत परस्पर संमती, मूल्ये व व्यावहारिक जुळवणूक तपासा। पारंपरिक आढावा हवा असल्यास हे तपशील अभ्यासकाला दाखवा; जोडीदार, ठिकाण व शक्य तारखांचा कालावधी ठरल्यानंतरच विवाहमुहूर्त निवडा।"))
    report["sections"].append({"key": "next_step", "title": next_note["title"], "text": next_note["text"], "evidence": [], "advice": []})
    report["methodology"] = [
        _note("monthly_method", _lang("Monthly sampling, not event boundaries", "मासिक नमूने, घटना की सीमाएँ नहीं", "मासिक नमुने; घटनेच्या सीमा नाहीत"), _lang("The selected date and one local-noon sample per following month use the profile's timezone and actual computed MD/AD and sidereal transits. Grouped windows are clipped calendar-month bins around qualifying samples. A dasha change or transit ingress between samples can change a reading inside a displayed month. These are not wedding dates or a complete muhurta.", "प्रोफ़ाइल के समय-क्षेत्र में चुनी तारीख और अगले हर महीने के एक स्थानीय दोपहर नमूने पर वास्तविक दशा और निरयण गोचर गणना की गई है। समूहित अवधि योग्य नमूनों के आसपास सीमित कैलेंडर-महीनों की है। नमूनों के बीच दशा या राशि परिवर्तन होने पर उसी महीने का संकेत बदल सकता है। ये विवाह की निश्चित तारीखें या पूर्ण मुहूर्त नहीं हैं।", "प्रोफाइलच्या वेळक्षेत्रानुसार निवडलेल्या दिवशी व पुढील प्रत्येक महिन्यात स्थानिक दुपारच्या एका नमुन्यावर वास्तविक दशा व निरयन गोचर मोजले आहे। एकत्रित कालखंड हे पात्र नमुन्यांभोवती मर्यादित केलेले कॅलेंडर-महिने आहेत। दोन नमुन्यांत दशा किंवा राशीबदल झाल्यास त्याच महिन्यात संकेत बदलू शकतो। या निश्चित लग्नतारखा किंवा संपूर्ण मुहूर्त नाहीत।")),
        _note("rule_counts", _lang("Four explicit checks", "चार स्पष्ट जाँच", "चार स्पष्ट तपासण्या"), _lang("Main period in {Venus, seventh lord}; sub-period in the same set; Jupiter in 2/5/7/9/11 from Moon; Saturn in 12/1/2 from Moon. Each check contributes at most one to its own support or pressure count. No strengths, cancellation, vedha, Ashtakavarga, full D9 judgment or partner chart are scored.", "महादशा शुक्र या सप्तमेश की; अंतर्दशा भी इसी समूह की; गुरु चंद्र से 2/5/7/9/11 में; शनि चंद्र से 12/1/2 में। हर जाँच अपनी अनुकूलता या दबाव गिनती में अधिकतम एक जोड़ती है। बल, निरस्तीकरण, वेध, अष्टकवर्ग, पूर्ण नवांश-विचार या साथी की कुंडली को अंक नहीं दिए गए।", "महादशा शुक्र किंवा सप्तमेशाची; अंतर्दशा त्याच समूहाची; गुरू चंद्रापासून 2/5/7/9/11 मध्ये; शनी चंद्रापासून 12/1/2 मध्ये। प्रत्येक तपासणी संबंधित अनुकूलता किंवा ताण मोजणीत जास्तीत जास्त एक भर घालते। बल, रद्द होणारे योग, वेध, अष्टकवर्ग, पूर्ण नवांशविचार किंवा जोडीदाराची कुंडली यांचे गुणांकन केलेले नाही।")),
    ]
    report["cautions"].append(_note("gender_neutral", _lang("Same method for every gender", "हर लिंग के लिए एक ही पद्धति", "प्रत्येक लिंगासाठी समान पद्धत"), _lang("Venus is used as a general traditional partnership significator for all profiles. Gender does not choose the rules or infer a partner's gender, orientation, appearance, character or sexual behavior.", "सभी प्रोफ़ाइलों में शुक्र सामान्य पारंपरिक साझेदारी-कारक है। लिंग से नियम नहीं बदलते, न साथी का लिंग, अभिविन्यास, रूप, चरित्र या यौन व्यवहार निकाला जाता है।", "सर्व प्रोफाइलमध्ये शुक्र हा सामान्य पारंपरिक भागीदारीचा कारक आहे। लिंगानुसार नियम बदलत नाहीत; जोडीदाराचे लिंग, अभिमुखता, रूप, चारित्र्य किंवा लैंगिक वर्तन ठरवले जात नाही।")))
    if profile.get("time_accuracy") == "approximate":
        report["cautions"].append(_note("approximate_time", _lang("Confirm the birth time", "जन्म समय की पुष्टि करें", "जन्मवेळ निश्चित करा"), _lang("Birth time is marked approximate. House lords, D9 and period boundaries may change; this report does not rectify the birth time.", "जन्म समय अनुमानित है। भावेश, नवांश और दशा-सीमाएँ बदल सकती हैं; यह रिपोर्ट जन्म समय शुद्ध नहीं करती।", "जन्मवेळ अंदाजे आहे। भावेश, नवांश व दशासीमा बदलू शकतात; हा अहवाल जन्मवेळ शुद्ध करत नाही।")))
    return report
