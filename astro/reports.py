"""VR-3: five stateless, evidence-bearing Vedic report sections.

Positions and periods are computed. Interpretations are limited traditional
symbols, never diagnoses, relationship verdicts or occupational guarantees.
No filesystem, database or network writes occur in this module.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from .engine import CalculationError
from .interpretation import (
    temporal_context, dosha_report, career_report, dignity, lang, note,
    PLANET_LABELS, SIGN_LABELS, SIGN_LORDS, _base_report, _planet_fact, _sector_section,
)
from .marriage import personal_marriage_report, _windows
from .matching import ashtakoota

RULE_VERSION = 'VR-3'
LANGS = ('en','hi','mr')
CLASSICAL = ('Sun','Moon','Mars','Mercury','Jupiter','Venus','Saturn')


def _section(key, title, text, evidence=None, advice=None, **extra):
    return {'key':key, 'title':title, 'text':text, 'evidence':evidence or [], 'advice':advice or [], **extra}


def _age(profile, selected):
    born=date.fromisoformat(profile['date']); day=date.fromisoformat(selected)
    return day.year-born.year-((day.month,day.day)<(born.month,born.day))


def kalsarpa_geometry(chart):
    """Inclusive 180-degree nodal-hemisphere screen, no severity/cancellation.

    A planet exactly on either mean-node endpoint counts inside both arcs.
    tolerance=1e-7 degrees only avoids floating-point endpoint disagreement.
    Neither ascendant nor outer planets are included.
    """
    planets={p['name']:p for p in chart['planets']}
    rahu=planets['Rahu']['longitude']%360
    offsets={name:(planets[name]['longitude']-rahu)%360 for name in CLASSICAL}
    eps=1e-7
    first=all(value<=180+eps or value>=360-eps for value in offsets.values())
    second=all(value>=180-eps or value<=eps for value in offsets.values())
    return {'present':bool(first or second),'arc':'Rahu_to_Ketu' if first else 'Ketu_to_Rahu' if second else None,
            'offsets_from_rahu':offsets,'endpoint_policy':'inclusive, tolerance 1e-7 degrees',
            'node_model':'mean Rahu; opposite Ketu','rule_version':'KS-BASE-1'}


def _kalsarpa_section(chart):
    geometry=kalsarpa_geometry(chart)
    state=lang('Base geometric condition present. ' if geometry['present'] else 'Base geometric condition absent. ',
               'मूल ज्यामितीय शर्त मौजूद है। ' if geometry['present'] else 'मूल ज्यामितीय शर्त नहीं मिली। ',
               'मूळ भूमितीय अट आढळली. ' if geometry['present'] else 'मूळ भूमितीय अट आढळली नाही. ')
    meaning=lang('All seven classical planets must lie in the same 180° half of the mean Rahu–Ketu axis. This convention includes planets exactly on a node. Traditions differ about this yoga and its exceptions. The screen does not establish misfortune, illness, delay or a need to buy a remedy.',
                 'सातों पारंपरिक ग्रह माध्य राहु–केतु अक्ष के एक ही 180° अर्धभाग में होने चाहिए। इस पद्धति में नोड पर स्थित ग्रह भी शामिल हैं। इस योग और अपवादों पर परंपराएँ भिन्न हैं। यह जाँच दुर्भाग्य, रोग, विलंब या उपाय खरीदने की आवश्यकता सिद्ध नहीं करती।',
                 'सातही पारंपरिक ग्रह मध्यम राहू–केतू अक्षाच्या एकाच 180° अर्धभागात असावेत. या पद्धतीत नोडवरचे ग्रहही समाविष्ट आहेत. या योगाबद्दल व अपवादांबद्दल परंपरांमध्ये फरक आहे. ही तपासणी दुर्दैव, आजार, विलंब किंवा उपाय विकत घेण्याची गरज सिद्ध करत नाही.')
    evidence=[note('axis_geometry',lang('Measured nodal geometry','गणना की गई नोड-ज्यामिति','मोजलेली नोड-भूमिती'),
        lang(f"Selected arc: {geometry['arc'] or 'none'}. Seven classical planets checked; ascending degree is not added to the rule.",
             f"चुना अर्धभाग: {geometry['arc'] or 'कोई नहीं'}। सात पारंपरिक ग्रह जाँचे गए; लग्न का अंश इस नियम में नहीं जोड़ा गया।",
             f"निवडलेला अर्धभाग: {geometry['arc'] or 'नाही'}. सात पारंपरिक ग्रह तपासले; लग्नाचा अंश या नियमात जोडलेला नाही."),
        [f"{name}: offset from mean Rahu {offset:.7f}°" for name,offset in geometry['offsets_from_rahu'].items()])]
    return _section('kalsarpa',lang('Kalsarpa: base geometric screen','कालसर्प: मूल ज्यामितीय जाँच','कालसर्प: मूळ भूमितीय तपासणी'),
        {l:state[l]+meaning[l] for l in LANGS},evidence,present=geometry['present'],geometry=geometry)


def _dignity_section(chart):
    rows=[]
    for p in chart['planets']:
        d=dignity(p)
        tags=[]
        if d['evaluated']:
            if d['own_sign']:tags.append(lang('own sign','स्वराशि','स्वराशी'))
            if d['exaltation_sign']:tags.append(lang('exaltation sign','उच्च राशि','उच्च राशी'))
            if d['debilitation_sign']:tags.append(lang('debilitation sign','नीच राशि','नीच राशी'))
            if not tags:tags.append(lang('other sign','अन्य राशि','इतर राशी'))
        else:tags.append(lang('node dignity not scored','नोड की राशि-गरिमा नहीं आँकी गई','नोडची राशीप्रतिष्ठा मोजलेली नाही'))
        n=PLANET_LABELS[p['name']];s=SIGN_LABELS[p['sign_index']]
        rows.append(note('dignity_'+p['name'].lower(),n,lang(
            f"{n['en']} in {s['en']}, house {p['house']}: {', '.join(t['en'] for t in tags)}. Retrograde: {p['retrograde']}. These are position labels, not a complete strong/weak ranking.",
            f"{n['hi']} {s['hi']} में, भाव {p['house']}: {', '.join(t['hi'] for t in tags)}। वक्री: {'हाँ' if p['retrograde'] else 'नहीं'}। ये स्थिति के नाम हैं, पूर्ण बलवान/कमजोर क्रम नहीं।",
            f"{n['mr']} {s['mr']} मध्ये, भाव {p['house']}: {', '.join(t['mr'] for t in tags)}. वक्री: {'होय' if p['retrograde'] else 'नाही'}. ही स्थितीची नावे आहेत; संपूर्ण बलवान/दुर्बल क्रम नाही."),
            [f"sidereal_longitude={p['longitude']}",f"sign_dignity={d}"],planet=p['name'],dignity=d))
    return _section('planet_dignities',lang('Planetary strengths and qualifications','ग्रह-स्थिति और बल की शर्तें','ग्रहस्थिती व बलाच्या अटी'),
        lang('Own and exaltation signs are traditionally supportive dignity labels; debilitation is a condition needing a fuller assessment. Neither alone measures effectiveness. Shadbala, exact exaltation strength, combustion, aspects, cancellations and complete divisional strength are not evaluated here. Rahu/Ketu dignity rules vary and are not scored.',
             'स्वराशि और उच्च राशि पारंपरिक अनुकूल गरिमा-नाम हैं; नीच राशि का पूरा आकलन आवश्यक होता है। अकेले इनसे प्रभावशीलता नहीं मापी जाती। यहाँ षड्बल, उच्चता का अंश-बल, अस्तंगतता, दृष्टि, दोषभंग और सभी वर्गों का बल नहीं जाँचा गया। राहु/केतु की गरिमा के नियम भिन्न हैं और उन्हें अंक नहीं दिए गए।',
             'स्वराशी व उच्च राशी ही पारंपरिक अनुकूल प्रतिष्ठेची नावे; नीच राशीचे पूर्ण मूल्यमापन आवश्यक असते. यांवरूनच प्रभावीपणा मोजला जात नाही. येथे षड्बल, उच्चतेचे अंशबल, अस्तंगतता, दृष्टी, दोषभंग व सर्व वर्गांचे बल तपासलेले नाही. राहू/केतूच्या प्रतिष्ठेचे नियम वेगवेगळे असल्यामुळे गुण दिलेले नाहीत.'),rows)


def _personal(profile,as_of,months):
    report=dosha_report(profile,as_of,months)
    c=report['chart']; asc=SIGN_LABELS[c['ascendant']['sign_index']];moon=SIGN_LABELS[c['moon']['sign_index']]
    nature=_section('nature_reflection',lang('Nature and overall reflection','स्वभाव और समग्र चिंतन','स्वभाव व एकूण चिंतन'),
        lang(f"Lagna is {asc['en']} and Moon is {moon['en']}. Traditional chart reading uses Lagna for outward approach and Moon for subjective experience. These are cultural reflection lenses, not a measured personality test, evidence of character, or a verdict about strengths and weaknesses.",
             f"लग्न {asc['hi']} और चंद्र राशि {moon['hi']} है। पारंपरिक अध्ययन में लग्न बाहरी दृष्टिकोण और चंद्र व्यक्तिगत अनुभव का संदर्भ है। ये सांस्कृतिक चिंतन के माध्यम हैं; व्यक्तित्व-परीक्षण, चरित्र का प्रमाण या गुण-दोष का निर्णय नहीं।",
             f"लग्न {asc['mr']} व चंद्रराशी {moon['mr']} आहे. पारंपरिक अभ्यासात लग्न बाह्य दृष्टिकोनाचा तर चंद्र वैयक्तिक अनुभवाचा संदर्भ आहे. ही सांस्कृतिक चिंतनाची साधने आहेत; व्यक्तिमत्त्वाची चाचणी, चारित्र्याचा पुरावा किंवा गुण-दोषांचा निकाल नाही."),
        [note('personal_anchors',lang('Calculated chart anchors','गणना के आधार','गणिती आधार'),
          lang(f"Ascendant {c['ascendant']['degree']:.2f}° in {asc['en']}; Moon nakshatra {c['moon']['nakshatra']}, pada {c['moon']['pada']}.",
               f"लग्न {asc['hi']} में {c['ascendant']['degree']:.2f}°; चंद्र नक्षत्र {c['moon']['nakshatra']}, चरण {c['moon']['pada']}।",
               f"लग्न {asc['mr']} मध्ये {c['ascendant']['degree']:.2f}°; चंद्र नक्षत्र {c['moon']['nakshatra']}, चरण {c['moon']['pada']}.") )],
        [note('strengths_in_practice',lang('Check strengths in real life','वास्तविक जीवन में क्षमता देखें','प्रत्यक्ष जीवनात क्षमता तपासा'),
          lang('Compare the reflection with your own experience, feedback and habits. A useful strength is something you can demonstrate and practise; a chart label does not establish ability or a permanent weakness.',
               'इस चिंतन की तुलना अपने अनुभव, प्रतिक्रिया और आदतों से करें। उपयोगी क्षमता वह है जिसे अभ्यास और व्यवहार से दिखाया जा सके; कुंडली का नाम योग्यता या स्थायी कमजोरी तय नहीं करता।',
               'या चिंतनाची स्वतःचे अनुभव, अभिप्राय व सवयींशी तुलना करा. उपयोगी क्षमता प्रत्यक्ष कृती व सरावातून दिसते; कुंडलीतील नाव योग्यता किंवा कायमची कमजोरी ठरवत नाही.'))])
    element_themes = [
        lang('initiative and direct engagement','पहल और सीधे जुड़ना','पुढाकार व थेट सहभाग'),
        lang('practical routines and steady effort','व्यावहारिक दिनचर्या और निरंतर प्रयास','व्यावहारिक दिनचर्या व सातत्यपूर्ण प्रयत्न'),
        lang('communication and exchanging ideas','संवाद और विचारों का आदान-प्रदान','संवाद व विचारांची देवाणघेवाण'),
        lang('receptivity and attention to emotional context','ग्रहणशीलता और भावनात्मक संदर्भ पर ध्यान','ग्रहणशीलता व भावनिक संदर्भाकडे लक्ष'),
    ]
    ai=c['ascendant']['sign_index']%4;mi=c['moon']['sign_index']%4
    nature['evidence'].append(note('element_reflection',lang('Traditional element themes','पारंपरिक तत्त्व-विषय','पारंपरिक तत्त्व-विषय'),
        lang(f"The Lagna element is associated with {element_themes[ai]['en']}; the Moon-sign element with {element_themes[mi]['en']}. Compare these broad traditional themes with your own experience; they do not classify your personality or establish ability.",
             f"लग्न-तत्त्व का प्रतीक {element_themes[ai]['hi']}; चंद्र-राशि तत्त्व का प्रतीक {element_themes[mi]['hi']} है। इन व्यापक पारंपरिक विषयों की अपने अनुभव से तुलना करें; ये व्यक्तित्व या योग्यता तय नहीं करते।",
             f"लग्नतत्त्वाचा संकेत {element_themes[ai]['mr']}; चंद्रराशी तत्त्वाचा संकेत {element_themes[mi]['mr']} आहे. या व्यापक पारंपरिक विषयांची स्वतःच्या अनुभवाशी तुलना करा; ते व्यक्तिमत्त्व किंवा क्षमता ठरवत नाहीत."),
        [f"ascendant sign_index={c['ascendant']['sign_index']}; element_index={ai}",f"Moon sign_index={c['moon']['sign_index']}; element_index={mi}"]))
    report['sections']=[_dignity_section(c),nature,_kalsarpa_section(c)]+report['sections']
    report['kalsarpa']=kalsarpa_geometry(c)
    report['planet_dignities']=[{'name':p['name'],**dignity(p)} for p in c['planets']]
    report['methodology'].append(note('ks_base_convention',lang('KS-BASE-1 convention','KS-BASE-1 पद्धति','KS-BASE-1 पद्धत'),
        lang('KS-BASE-1 checks either inclusive 180-degree node-bounded half using seven classical planets and mean nodes. It does not distinguish named Kalsarpa/Kalamrita variants, partial forms, cancellations or severity.',
             'KS-BASE-1 सात पारंपरिक ग्रहों और माध्य नोड से दोनों में से किसी समावेशी 180-अंश अर्धभाग की जाँच करता है। कालसर्प/कालामृत के नामित प्रकार, आंशिक रूप, दोषभंग या तीव्रता अलग नहीं आँकी गई।',
             'KS-BASE-1 सात पारंपरिक ग्रह व मध्यम नोड वापरून दोन्हींपैकी कोणताही समावेशक 180-अंश अर्धभाग तपासतो. कालसर्प/कालामृतचे नावाचे प्रकार, अंशतः रूपे, दोषभंग किंवा तीव्रता स्वतंत्र मोजलेली नाही.')))
    report['sources'].append({'title':'Conventional node-axis definition; KS-BASE-1 endpoint/half conventions are specific to this app, not a complete classical judgment','url':'https://www.kalsarpa.com/download/kalsarpa.pdf'})
    report['summary'].insert(0,note('personal_overview',lang('Personal Kundali overview','व्यक्तिगत कुंडली समीक्षा','वैयक्तिक कुंडली आढावा'),
        lang('Review nine planetary positions and sign-dignity labels, D1/D9 charts, Manglik and Kalsarpa base geometry, and eight named yoga conditions with short significance notes. The report separates calculated positions from traditional interpretation and incomplete strength qualifications.',
             'नौ ग्रहस्थितियाँ और राशि-गरिमा, D1/D9, मांगलिक व कालसर्प की मूल ज्यामिति और आठ नामित योगों के संक्षिप्त अर्थ देखें। रिपोर्ट गणना को पारंपरिक व्याख्या और अधूरी बल-शर्तों से अलग रखती है।',
             'नऊ ग्रहस्थिती व राशीप्रतिष्ठा, D1/D9, मांगलिक व कालसर्पची मूळ भूमिती आणि आठ नावांच्या योगांचे संक्षिप्त अर्थ पाहा. अहवाल गणना, पारंपरिक अर्थ व अपूर्ण बल-अटी स्वतंत्र ठेवतो.')))
    report['report_type']='personal';report['rule_version']=RULE_VERSION
    return report


MEETING_THEMES={
 1:('Self-directed activities and mutual introductions','स्वयं की गतिविधियाँ और परस्पर परिचय','स्वतःचे उपक्रम व परस्पर ओळखी'),
 2:('Family circles or shared-resource discussions','परिवार का परिचय या साझा संसाधनों पर चर्चा','कुटुंबाची ओळख किंवा सामायिक साधनांवरील चर्चा'),
 3:('Local groups, communication or short courses','स्थानीय समूह, संवाद या छोटे पाठ्यक्रम','स्थानिक गट, संवाद किंवा लहान अभ्यासक्रम'),
 4:('Home, community or family networks','घर, समुदाय या पारिवारिक संपर्क','घर, समुदाय किंवा कौटुंबिक संपर्क'),
 5:('Study, creative activities or shared interests','अध्ययन, रचनात्मक गतिविधियाँ या समान रुचि','अभ्यास, सर्जनशील उपक्रम किंवा समान आवड'),
 6:('Routine work, service or organised activities','दैनिक काम, सेवा या संगठित गतिविधियाँ','दैनंदिन काम, सेवा किंवा संघटित उपक्रम'),
 7:('Introductions, partnerships or public-facing groups','परिचय, साझेदारी या सार्वजनिक समूह','ओळखी, भागीदारी किंवा सार्वजनिक गट'),
 8:('Shared research or deeper personal conversations','साझा शोध या गहरी व्यक्तिगत बातचीत','सामायिक संशोधन किंवा सखोल वैयक्तिक संवाद'),
 9:('Higher learning, travel interests or mentoring','उच्च शिक्षा, यात्रा की रुचि या मार्गदर्शन','उच्च शिक्षण, प्रवासाची आवड किंवा मार्गदर्शन'),
 10:('Professional networks or public activities','पेशेवर संपर्क या सार्वजनिक गतिविधियाँ','व्यावसायिक संपर्क किंवा सार्वजनिक उपक्रम'),
 11:('Friends, communities or interest networks','मित्र, समुदाय या रुचि के संपर्क','मित्र, समुदाय किंवा आवडीचे संपर्क'),
 12:('Remote, cross-cultural or reflective settings','दूरस्थ, अंतर-सांस्कृतिक या चिंतन के संदर्भ','दूरस्थ, आंतरसांस्कृतिक किंवा चिंतनाचे संदर्भ'),
}


def _love(profile,as_of,months):
    report=personal_marriage_report(profile,as_of,months)
    report['report_type']='love';report['rule_version']=RULE_VERSION
    if _age(profile,report['as_of'])<18:return report
    c=report['chart'];lord=SIGN_LORDS[(c['ascendant']['sign_index']+6)%12]
    p=next(x for x in c['planets'] if x['name']==lord);themes=lang(*MEETING_THEMES[p['house']])
    meeting=_section('meeting_medium',lang('Possible introduction themes','परिचय के संभावित प्रतीक','ओळखीचे संभाव्य प्रतीक'),
       lang(f"The seventh lord is {lord} in house {p['house']}. This app maps that house to: {themes['en']}. This is an openly declared symbolic association, not knowledge of the actual meeting place, platform, person or direction.",
            f"सप्तमेश {PLANET_LABELS[lord]['hi']} भाव {p['house']} में है। ऐप इस भाव को इन विषयों से जोड़ता है: {themes['hi']}। यह घोषित प्रतीकात्मक संबंध है; वास्तविक मिलने का स्थान, मंच, व्यक्ति या दिशा का ज्ञान नहीं।",
            f"सप्तमेश {PLANET_LABELS[lord]['mr']} भाव {p['house']} मध्ये आहे. अॅप हा भाव या विषयांशी जोडतो: {themes['mr']}. हा स्पष्ट केलेला प्रतीकात्मक संबंध आहे; प्रत्यक्ष भेटीचे ठिकाण, माध्यम, व्यक्ती किंवा दिशा यांचे ज्ञान नाही."),[_planet_fact(p)],
       [note('meeting_practical',lang('Use your preferences and consent','अपनी पसंद और सहमति को आधार बनाएँ','पसंती व संमतीला आधार द्या'),
        lang('Choose safe, consensual introductions suited to your interests. A horoscope cannot identify a specific future partner or tell whether the first meeting has already happened.',
             'अपनी रुचि के अनुसार सुरक्षित और सहमति वाले परिचय चुनें। कुंडली किसी निश्चित भावी साथी की पहचान या पहली मुलाकात पहले हो चुकी है या नहीं, नहीं बताती।',
             'आवडीनुसार सुरक्षित व संमतीने होणाऱ्या ओळखी निवडा. कुंडली एखाद्या ठरावीक भावी जोडीदाराची ओळख किंवा पहिली भेट आधीच झाली आहे का हे सांगत नाही.'))])
    first=_section('first_meeting_window',lang('First meeting: what can be assessed','पहली मुलाकात: क्या जाँचा जा सकता है','पहिली भेट: काय तपासता येते'),
        lang('A first meeting date cannot be inferred reliably. The month/year groups below are the same PM-1 relationship-review samples, not a separate prediction of first contact. They can be used as calendar prompts to review your own social plans, with no guarantee that a relationship or wedding will occur.',
             'पहली मुलाकात की तिथि विश्वसनीय रूप से नहीं निकाली जा सकती। नीचे के माह/वर्ष समूह वही PM-1 संबंध-समीक्षा नमूने हैं, प्रथम परिचय की अलग भविष्यवाणी नहीं। उन्हें अपनी सामाजिक योजनाओं की समीक्षा का कैलेंडर-संदर्भ मान सकते हैं; संबंध या विवाह होने की गारंटी नहीं।',
             'पहिल्या भेटीची तारीख विश्वसनीयपणे काढता येत नाही. खालील महिना/वर्ष गट हेच PM-1 नातेसमीक्षेचे नमुने आहेत; पहिल्या संपर्काचे स्वतंत्र भाकीत नाही. सामाजिक योजनांच्या पुनरावलोकनासाठी ते दिनदर्शिकेतील संदर्भ ठरू शकतात; नाते किंवा विवाह होण्याची हमी नाही.'))
    dosha_section=_couple_dosha_section(c,1)
    dosha_section['key']='love_doshas'
    dosha_section['title']=lang('Doshas in relationship context','संबंध के संदर्भ में दोष','नात्याच्या संदर्भातील दोष')
    report['sections'] += [meeting,first,dosha_section]
    report['meeting_windows']=deepcopy(report.get('windows',[]))
    return report


EMPLOYMENT_SECTOR={'key':'private_employment','title':lang('Private employment & structured jobs','निजी क्षेत्र और संगठित नौकरी','खासगी क्षेत्र व संघटित नोकरी'),
 'planets':{'Saturn','Mercury','Sun'},'house':6,'growth':10,
 'meaning':lang('House 6 is used for service and daily work, house 10 for public responsibility; Saturn/systems, Mercury/communication and Sun/responsibility are the declared association set. These symbols do not determine public-versus-private employment or selection in a job.',
                'भाव 6 सेवा व दैनिक काम, भाव 10 सार्वजनिक दायित्व; शनि/प्रणाली, बुध/संवाद और सूर्य/जिम्मेदारी चुने प्रतीक हैं। ये सार्वजनिक या निजी नौकरी अथवा चयन तय नहीं करते।',
                'भाव 6 सेवा व दैनंदिन काम, भाव 10 सार्वजनिक जबाबदारी; शनी/प्रणाली, बुध/संवाद व सूर्य/जबाबदारी हे निवडलेले प्रतीक. हे सरकारी की खासगी नोकरी किंवा निवड ठरवत नाहीत.'),
 'advice':lang('Compare working conditions, qualifications, role requirements, learning opportunities and your own preferences before accepting a position.',
               'नौकरी स्वीकारने से पहले काम की स्थिति, पात्रता, भूमिका की जरूरत, सीखने के अवसर और अपनी पसंद की तुलना करें।',
               'नोकरी स्वीकारण्यापूर्वी कामाच्या अटी, पात्रता, भूमिकेच्या गरजा, शिकण्याच्या संधी व स्वतःची पसंती तपासा.')}


def _career(profile,as_of,months):
    report=career_report(profile,as_of,months)
    report['report_type']='career';report['rule_version']=RULE_VERSION
    report['sections'].insert(2,_sector_section(report['chart'],report['context']['current_dasha'],EMPLOYMENT_SECTOR))
    for section in report['sections']:
        if section['key']=='education_advisory':section['title']=lang('Consultancy, education & advisory','परामर्श, शिक्षा और सलाह','कन्सल्टन्सी, शिक्षण व सल्ला')
    report['summary'].append(note('work_mode_scope',lang('Government, private, job or business','सरकारी, निजी, नौकरी या व्यवसाय','सरकारी, खासगी, नोकरी की व्यवसाय'),
        lang('These work modes overlap: consultancy can be salaried or independent, and technical work can be public or private. Compare the disclosed sector conditions, then test the options against education, skills, opportunity and financial constraints. The chart cannot select the best career as a fact.',
             'ये कार्य-पद्धतियाँ साथ हो सकती हैं: परामर्श वेतनभोगी या स्वतंत्र, तकनीकी काम सरकारी या निजी हो सकता है। स्पष्ट क्षेत्र-नियमों की तुलना के बाद शिक्षा, कौशल, अवसर और आर्थिक सीमाएँ जाँचें। कुंडली तथ्य के रूप में श्रेष्ठ करियर नहीं चुन सकती।',
             'या कामपद्धती एकत्र असू शकतात: सल्लागार वेतनभोगी किंवा स्वतंत्र असू शकतो; तांत्रिक काम सरकारी किंवा खासगी असू शकते. स्पष्ट क्षेत्रनियमांची तुलना करून शिक्षण, कौशल्य, संधी व आर्थिक मर्यादा तपासा. कुंडली तथ्य म्हणून सर्वोत्तम करियर निवडू शकत नाही.')))
    return report


def _health(profile,as_of,months):
    ctx=temporal_context(profile,as_of,months)
    report=_base_report(ctx,'health');report['report_type']='health';report['rule_version']=RULE_VERSION
    # Generic transit conditions are deliberately NOT plotted as health risks.
    report['timeline']=[];report['highlights']={'supportive':[],'demanding':[]}
    c=ctx['chart'];asc=c['ascendant']['sign_index'];sixth=(asc+5)%12;lord=SIGN_LORDS[sixth]
    p=next(p for p in c['planets'] if p['name']==lord)
    boundary=note('health_boundary',lang('Wellbeing reflection, not a health assessment','कल्याण-चिंतन, स्वास्थ्य-जाँच नहीं','स्वास्थ्यचिंतन; वैद्यकीय तपासणी नाही'),
        lang('A horoscope cannot diagnose illness, estimate health status, predict lifespan, assess fertility or replace medical care. This section does not classify any month as medically safe, dangerous, high or low. For symptoms or concerns, seek a qualified healthcare professional.',
             'कुंडली रोग का निदान, स्वास्थ्य-स्तर, आयु, प्रजनन क्षमता या चिकित्सा का विकल्प नहीं बता सकती। यह भाग किसी महीने को चिकित्सकीय रूप से सुरक्षित, खतरनाक, ऊँचा या नीचा नहीं बताता। लक्षण या चिंता हो तो योग्य स्वास्थ्य-पेशेवर से सलाह लें।',
             'कुंडली आजाराचे निदान, आरोग्यस्थिती, आयुर्मान, प्रजननक्षमता किंवा वैद्यकीय सेवेचा पर्याय सांगू शकत नाही. हा भाग कोणताही महिना वैद्यकीयदृष्ट्या सुरक्षित, धोकादायक, उच्च किंवा नीच ठरवत नाही. लक्षणे किंवा चिंता असल्यास पात्र आरोग्यतज्ज्ञांचा सल्ला घ्या.'))
    report['summary']=[boundary]
    report['cautions'].insert(0,deepcopy(boundary))
    report['sections']=[_section('health_chart_context',lang('Traditional routine and service symbolism','दिनचर्या और सेवा का पारंपरिक संदर्भ','दिनचर्या व सेवेचा पारंपरिक संदर्भ'),
        lang(f"The whole-sign sixth house is {SIGN_LABELS[sixth]['en']}; its lord {lord} is in house {p['house']}. In this educational view these are symbols for routines, service and managing obligations—not evidence about an organ, disease or medical vulnerability.",
             f"पूर्ण-राशि छठा भाव {SIGN_LABELS[sixth]['hi']} है; उसका स्वामी {PLANET_LABELS[lord]['hi']} भाव {p['house']} में है। इस शैक्षिक दृष्टि में ये दिनचर्या, सेवा और दायित्व सँभालने के प्रतीक हैं; अंग, रोग या चिकित्सा-संबंधी कमजोरी के प्रमाण नहीं।",
             f"पूर्णराशी सहावा भाव {SIGN_LABELS[sixth]['mr']}; त्याचा स्वामी {PLANET_LABELS[lord]['mr']} भाव {p['house']} मध्ये आहे. या शैक्षणिक दृष्टिकोनात हे दिनचर्या, सेवा व जबाबदाऱ्या सांभाळण्याचे प्रतीक आहेत; अवयव, आजार किंवा वैद्यकीय दुर्बलतेचे पुरावे नाहीत."),[_planet_fact(p)]),
       _section('wellbeing_prompts',lang('General wellbeing planning','सामान्य कल्याण-योजना','सामान्य स्वास्थ्य-नियोजन'),
        lang('Keep a routine that suits your circumstances: adequate sleep, appropriate activity, regular meals, rest and supportive social contact. These are general reflection prompts for everyone, not personalised treatment advice or remedies for a planetary condition.',
             'अपनी स्थिति के अनुरूप पर्याप्त नींद, उचित गतिविधि, नियमित भोजन, आराम और सहयोगी सामाजिक संपर्क की दिनचर्या रखें। ये सभी के लिए सामान्य चिंतन-बिंदु हैं; व्यक्तिगत उपचार या ग्रहस्थिति के उपाय नहीं।',
             'परिस्थितीनुसार पुरेशी झोप, योग्य हालचाल, नियमित जेवण, विश्रांती व आधार देणारा सामाजिक संपर्क यांची दिनचर्या ठेवा. हे सर्वांसाठी सामान्य चिंतनाचे मुद्दे आहेत; वैयक्तिक उपचार किंवा ग्रहस्थितीवरील उपाय नाहीत.')),
       _section('care_decisions',lang('Use real health information','वास्तविक स्वास्थ्य जानकारी का उपयोग करें','प्रत्यक्ष आरोग्य-माहिती वापरा'),
        lang('Use symptoms, medical history, examinations and professional advice for health decisions. Do not delay care, change prescribed medication or buy a remedy because of any yoga, dosha, dasha or transit shown in Vedika.',
             'स्वास्थ्य के निर्णय लक्षण, चिकित्सकीय इतिहास, जाँच और पेशेवर सलाह के आधार पर लें। वेदिका के योग, दोष, दशा या गोचर के कारण देखभाल न टालें, निर्धारित दवा न बदलें और उपाय न खरीदें।',
             'आरोग्याचे निर्णय लक्षणे, वैद्यकीय इतिहास, तपासण्या व तज्ज्ञांच्या सल्ल्यावर घ्या. वेदिकेतील योग, दोष, दशा किंवा गोचरामुळे सेवा पुढे ढकलू नका, लिहून दिलेली औषधे बदलू नका किंवा उपाय विकत घेऊ नका.'))]
    report['methodology']=[note('health_scope',boundary['title'],boundary['text'])]
    return report


def _couple_dosha_section(chart,index):
    manglik=next(x for x in chart['doshas'] if x['key']=='manglik')
    ks=kalsarpa_geometry(chart)
    refs=', '.join(f"{r['name']}={r['house']}" for r in manglik['references'])
    return _section(f'person_{index}_doshas',lang(f'Person {index}: dosha base checks',f'व्यक्ति {index}: दोष की मूल जाँच',f'व्यक्ती {index}: दोषांच्या मूळ तपासण्या'),
        lang(f"Manglik base screen: {'present' if manglik['present'] else 'absent'}. Kalsarpa hemisphere screen: {'present' if ks['present'] else 'absent'}. Neither flag assigns severity, harm or separation. Matching Manglik flags do not automatically cancel anything in this build.",
             f"मांगलिक मूल शर्त: {'मिली' if manglik['present'] else 'नहीं मिली'}। कालसर्प अर्धभाग शर्त: {'मिली' if ks['present'] else 'नहीं मिली'}। कोई संकेत तीव्रता, हानि या अलगाव नहीं तय करता। दोनों के मांगलिक होने से इस ऐप में अपने-आप दोषभंग नहीं माना जाता।",
             f"मांगलिक मूळ अट: {'आढळली' if manglik['present'] else 'आढळली नाही'}. कालसर्प अर्धभाग अट: {'आढळली' if ks['present'] else 'आढळली नाही'}. कोणताही संकेत तीव्रता, हानी किंवा विभक्त होणे ठरवत नाही. दोघे मांगलिक असल्यास या अॅपमध्ये आपोआप दोषभंग मानलेला नाही."),
        [note('manglik_references',lang('Mars from three references','तीन संदर्भों से मंगल','तीन संदर्भांपासून मंगळ'),
          lang('Selected houses are 1/2/4/7/8/12 from Lagna, Moon or Venus. Each reference is retained separately; no severity or cancellation rule is applied.',
               'चुने भाव लग्न, चंद्र या शुक्र से 1/2/4/7/8/12 हैं। हर संदर्भ अलग रखा गया है; तीव्रता या दोषभंग का नियम लागू नहीं।',
               'निवडलेले भाव लग्न, चंद्र किंवा शुक्रापासून 1/2/4/7/8/12 आहेत. प्रत्येक संदर्भ स्वतंत्र ठेवला आहे; तीव्रता किंवा दोषभंगाचा नियम लागू नाही.'),[refs]),
         note('kalsarpa_geometry',lang('Nodal hemisphere result','नोड अर्धभाग का परिणाम','नोड अर्धभागाचा निकाल'),
          lang('Seven classical planets, mean nodes and inclusive endpoints; alternate conventions may differ.',
               'सात पारंपरिक ग्रह, माध्य नोड और समावेशी अंतिम बिंदु; दूसरी पद्धतियों में अंतर हो सकता है।',
               'सात पारंपरिक ग्रह, मध्यम नोड व समावेशक अंतिम बिंदू; इतर पद्धतींमध्ये फरक असू शकतो.'),[str(ks)])],person_index=index,manglik=deepcopy(manglik),kalsarpa=ks)


def _compatibility(profile,as_of,months,person_b,status):
    if person_b is None:raise CalculationError('A second birth profile is required for compatibility.')
    if status not in {'considering','married'}:raise CalculationError('Relationship status must be considering or married.')
    ctx=temporal_context(profile,as_of,months)
    other=temporal_context(person_b,ctx['as_of'],months)
    report=_base_report(ctx,'compatibility');report['report_type']='compatibility';report['rule_version']=RULE_VERSION
    charts=[ctx['chart'],other['chart']]
    score=ashtakoota(charts[0]['moon']['longitude'],charts[1]['moon']['longitude'])
    # Keep numeric matching and audit data, but rich cautions/methodology stay localized.
    for key in ('score','max_score','traditional_threshold','threshold_met','decision','kootas'):
        report[key]=score[key]
    report['matching_methodology']=score['methodology'];report['matching_cautions']=score['cautions']
    report['charts']=charts;report['relationship_status']=status
    doshas=[_couple_dosha_section(c,i+1) for i,c in enumerate(charts)]
    basic_flags=sum(int(s['manglik']['present'])+int(s['kalsarpa']['present']) for s in doshas)
    basic_flags+=sum(k['score']==0 for k in score['kootas'] if k['key'] in {'nadi','bhakoot'})
    report['base_flag_count']=basic_flags
    met=score['threshold_met']
    summary=note('couple_one_line',lang('One-line review','एक पंक्ति की समीक्षा','एका ओळीतील आढावा'),
        lang(f"{score['score']:g}/36: the selected 18-point rule {'is met' if met else 'is not met'}; {basic_flags} displayed base flags need individual review; the score cannot decide married life or separation.",
             f"{score['score']:g}/36: चुना 18-अंक नियम {'पूरा हुआ' if met else 'पूरा नहीं हुआ'}; {basic_flags} दिखाए मूल संकेत अलग समीक्षा चाहते हैं; अंक वैवाहिक जीवन या अलगाव तय नहीं करते।",
             f"{score['score']:g}/36: निवडलेला 18-गुण नियम {'जुळतो' if met else 'जुळत नाही'}; {basic_flags} दाखवलेल्या मूळ संकेतांचा स्वतंत्र आढावा आवश्यक; गुण वैवाहिक जीवन किंवा विभक्त होणे ठरवत नाहीत."))
    report['summary']=[summary]
    strengths=[];review=[]
    for k in score['kootas']:
        n=note('koota_'+k['key'],lang(k['name'],k['name'],k['name']),
            lang(f"Selected {k['name']} score: {k['score']:g}/{k['max']}. This is a symbolic rule result, not a measured relationship quality.",
                 f"चुना {k['name']} अंक: {k['score']:g}/{k['max']}। यह प्रतीकात्मक नियम का परिणाम है; वास्तविक संबंध-गुणवत्ता का माप नहीं।",
                 f"निवडलेला {k['name']} गुण: {k['score']:g}/{k['max']}. हा प्रतीकात्मक नियमाचा निकाल आहे; प्रत्यक्ष नात्याच्या गुणवत्तेचे मोजमाप नाही."),[k['detail']])
        if k['score']==k['max']:strengths.append(n)
        else:review.append(n)
    status_text=lang('For an existing marriage, use these as discussion prompts alongside the relationship you actually experience.' if status=='married' else 'For a prospective marriage, use these as discussion prompts alongside consent, shared values and practical compatibility.',
                     'मौजूदा विवाह में वास्तविक अनुभव के साथ इन बिंदुओं पर चर्चा करें।' if status=='married' else 'संभावित विवाह में सहमति, साझा मूल्य और व्यावहारिक अनुकूलता के साथ इन बिंदुओं पर चर्चा करें।',
                     'विद्यमान विवाहात प्रत्यक्ष अनुभवाबरोबर या मुद्द्यांवर चर्चा करा.' if status=='married' else 'संभाव्य विवाहात संमती, समान मूल्ये व व्यावहारिक सुसंगतीबरोबर या मुद्द्यांवर चर्चा करा.')
    report['sections']=[
        _section('couple_pros',lang('Full-point factors: traditional positives','पूर्ण अंक वाले पक्ष: पारंपरिक अनुकूलता','पूर्ण गुणांचे घटक: पारंपरिक अनुकूलता'),status_text,strengths),
        _section('couple_cons',lang('Factors requiring review','समीक्षा की जरूरत वाले पक्ष','पुनरावलोकन आवश्यक असलेले घटक'),
          lang('Less than full points means only that a selected koota rule is incomplete. It does not establish a defect in either person. Individual zero-point Nadi/Bhakoot rules remain visible even if the total crosses 18.',
               'पूर्ण से कम अंक का अर्थ केवल चुना कूट नियम पूरा न होना है। यह किसी व्यक्ति में कमी सिद्ध नहीं करता। कुल 18 से अधिक होने पर भी नाड़ी/भकूट के शून्य अंक अलग दिखते हैं।',
               'पूर्ण गुणांपेक्षा कमी म्हणजे फक्त निवडलेला कूट नियम पूर्ण न होणे. यावरून कोणत्याही व्यक्तीत दोष सिद्ध होत नाही. एकूण 18 पेक्षा अधिक असले तरी नाडी/भकूटचे शून्य गुण स्वतंत्र दिसतात.'),review),
        *doshas,
        _section('separation',lang('Separation cannot be determined','अलगाव निश्चित नहीं किया जा सकता','विभक्त होणे निश्चित करता येत नाही'),
          lang('A horoscope or guna score cannot establish whether this couple will separate, divorce or have a successful marriage. No yes/no separation verdict is generated. Use actual behaviour, communication, circumstances and qualified relationship support when needed.',
               'कुंडली या गुण-अंक यह सिद्ध नहीं करते कि दंपति अलग होगा, तलाक लेगा या सफल विवाह होगा। अलगाव पर हाँ/नहीं का निर्णय नहीं दिया जाता। वास्तविक व्यवहार, संवाद, परिस्थितियों और आवश्यक योग्य संबंध-परामर्श को आधार बनाएँ।',
               'कुंडली किंवा गुणांवरून हे जोडपे विभक्त होईल, घटस्फोट घेईल किंवा यशस्वी विवाह होईल असे सिद्ध होत नाही. विभक्त होण्याचा होय/नाही निर्णय दिलेला नाही. प्रत्यक्ष वर्तन, संवाद, परिस्थिती व आवश्यक पात्र नातेसमुपदेशनाला आधार द्या.')),
    ]
    adults=all(_age(p,ctx['as_of'])>=18 for p in (profile,person_b))
    report['timeline']=[];report['windows']=[];report['highlights']={'supportive':[],'demanding':[]}
    if adults:
        a=personal_marriage_report(profile,ctx['as_of'],months)
        b=personal_marriage_report(person_b,ctx['as_of'],months)
        for x,y in zip(a['timeline'],b['timeline']):
            assert x['month']==y['month']
            joint=bool(x['supportive_sample'] and y['supportive_sample'])
            evidence=note('joint_month',lang('Both profiles at their local samples','दोनों की स्थानीय समय पर जाँच','दोघांची स्थानिक वेळी तपासणी'),
                lang('A joint candidate requires each person to have a Venus/seventh-lord MD or AD link and Jupiter in 2/5/7/9/11 from their natal Moon. Saturn 12/1/2 counts are separate pressure screens; they do not predict marriage failure.',
                     'संयुक्त संदर्भ के लिए दोनों में शुक्र/सप्तमेश की MD या AD और अपने जन्मचंद्र से गुरु 2/5/7/9/11 में होना आवश्यक है। शनि 12/1/2 की गिनती अलग चुनौती-जाँच है; यह वैवाहिक असफलता नहीं बताती।',
                     'संयुक्त संदर्भासाठी दोघांत शुक्र/सप्तमेशाची MD किंवा AD व स्वतःच्या जन्मचंद्रापासून गुरू 2/5/7/9/11 मध्ये असणे आवश्यक. शनी 12/1/2 ची मोजणी स्वतंत्र आव्हान-तपासणी आहे; ती वैवाहिक अपयश सांगत नाही.'),
                [f"person_a_supportive_sample={x['supportive_sample']}; person_b_supportive_sample={y['supportive_sample']}",f"person_a_sample={x['sample_at']}; person_b_sample={y['sample_at']}"])
            report['timeline'].append({'month':x['month'],'sample_at':x['sample_at'],'person_b_sample_at':y['sample_at'],
                'mahadasha':x['mahadasha'],'antardasha':x['antardasha'],'person_b_mahadasha':y['mahadasha'],'person_b_antardasha':y['antardasha'],
                'support_count':x['support_count']+y['support_count'],'pressure_count':x['pressure_count']+y['pressure_count'],
                'indicator_count':8,'supportive_sample':joint,'signals':[evidence]+x['signals']+y['signals']})
        report['windows']=_windows(report['timeline'],date.fromisoformat(ctx['as_of']),months)
        report['highlights']={'supportive':[r['month'] for r in report['timeline'] if r['supportive_sample']],
                              'demanding':[r['month'] for r in report['timeline'] if r['pressure_count']>0]}
    else:
        report['cautions'].append(note('adult_screen',lang('Educational compatibility view','शैक्षिक अनुकूलता समीक्षा','शैक्षणिक सुसंगती आढावा'),
            lang('At least one profile is under 18 on the selected date. No marriage-timing or partner interpretation is generated.',
                 'चुनी तिथि पर कम से कम एक प्रोफ़ाइल 18 वर्ष से कम है। विवाह-समय या साथी की व्याख्या नहीं दी जाती।',
                 'निवडलेल्या तारखेला किमान एक व्यक्ती 18 वर्षांखालील आहे. विवाहाची वेळ किंवा जोडीदाराचे विश्लेषण दिलेले नाही.')))
    report['sections'].append(_section('couple_timing',lang('Joint month/year review windows','संयुक्त माह/वर्ष समीक्षा-अवधि','संयुक्त महिना/वर्ष पुनरावलोकन कालखंड'),
        lang('Listed month groups are intersections of the two personal PM-1 sample screens. Each profile uses its own birth-place timezone at local noon, so these are common calendar labels rather than simultaneous event windows. They are not guaranteed wedding dates or complete muhurta intervals. No listed group means no match in these limited filters, not that marriage is impossible.',
             'महीनों के समूह दोनों व्यक्तिगत PM-1 नमूना-जाँचों का साझा भाग हैं। दोनों की जाँच अपने जन्म-स्थान के समयक्षेत्र की दोपहर पर है; इसलिए ये साझा कैलेंडर नाम हैं, एक ही क्षण की घटना-अवधि नहीं। ये निश्चित विवाहतिथि या पूर्ण मुहूर्त नहीं। समूह न मिलने का अर्थ सीमित नियमों में मेल न होना है, विवाह असंभव होना नहीं।',
             'महिन्यांचे गट हे दोन्ही वैयक्तिक PM-1 नमुना-तपासण्यांचा समान भाग आहेत. प्रत्येकाची तपासणी जन्मठिकाणच्या वेळक्षेत्रातील दुपारी आहे; म्हणून ही समान दिनदर्शिका नावे आहेत, एकाच क्षणाची घटनावेळ नाही. या निश्चित लग्नतारखा किंवा पूर्ण मुहूर्त नाहीत. गट न मिळणे म्हणजे मर्यादित नियमांत जुळणी नाही; विवाह अशक्य नाही.')))
    report['methodology'].append(note('couple_method',lang('AK-1 plus two PM-1 screens','AK-1 और दो PM-1 जाँच','AK-1 व दोन PM-1 तपासण्या'),
        lang('Guna uses directional A/groom-role and B/bride-role tables regardless of gender labels. Raw points are not adjusted for dosha cancellations. Relationship status changes wording only, never astronomical positions or the 36-point score. The joint graph has eight equal rule checks, four per person; it is not a probability.',
             'गुण-अंक में लिंग नाम के बजाय A/वर-स्थान और B/वधू-स्थान की दिशात्मक तालिका है। दोषभंग से मूल अंक बदले नहीं जाते। संबंध-स्थिति केवल शब्द बदलती है, ग्रहस्थिति या 36-अंक नहीं। संयुक्त ग्राफ में आठ समान नियम, चार प्रति व्यक्ति हैं; यह संभावना नहीं।',
             'गुणांमध्ये लिंगनावांऐवजी A/वर-स्थान व B/वधू-स्थानाचे दिशात्मक तक्ते वापरले आहेत. दोषभंगामुळे मूळ गुण बदललेले नाहीत. नातेस्थितीमुळे फक्त शब्द बदलतात; ग्रहस्थिती किंवा 36 गुण नाही. संयुक्त आलेखात आठ समान नियम, प्रत्येकासाठी चार आहेत; ही संभाव्यता नाही.')))
    report['sources'] += [{'title':'AK-1 Ashtakoota tables and selected regional convention','url':u} for u in score['methodology']['sources']]
    return report


def build_report(section,profile,as_of=None,horizon_months=24,person_b=None,relationship_status='considering'):
    """Build one of exactly five report sections without saving birth data."""
    if section not in {'personal','love','career','health','compatibility'}:
        raise CalculationError('Unknown report section. Choose personal, love, career, health or compatibility.')
    if section=='compatibility':
        report=_compatibility(profile,as_of,horizon_months,person_b,relationship_status)
    else:
        report={'personal':_personal,'love':_love,'career':_career,'health':_health}[section](profile,as_of,horizon_months)
    report['application_version']='2.0.0'
    return report
