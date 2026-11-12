"""In-memory, shaped Unicode reports for Vedika's five sections.

No report, birth details or PDF bytes are written to disk. Bundled Noto fonts
and HarfBuzz provide proper Devanagari shaping in Hindi and Marathi.
"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import re
from fpdf import FPDF
from fpdf.enums import XPos, YPos, MethodReturnValue
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / 'assets' / 'fonts'
FOREST = (23, 63, 53)
GOLD = (177, 132, 68)
INK = (43, 61, 52)
MUTED = (101, 111, 100)
PAPER = (249, 247, 239)
LANGUAGES = ('en', 'hi', 'mr')
T = {
 'personal':('Personal Kundali','व्यक्तिगत कुंडली','वैयक्तिक कुंडली'),
 'love':('Love & Marriage','प्रेम और विवाह','प्रेम आणि विवाह'),
 'personal_marriage':('Love & Marriage','प्रेम और विवाह','प्रेम आणि विवाह'),
 'career':('Career & Timeline','करियर और समयरेखा','करिअर आणि कालरेषा'),
 'health':('Health & Wellbeing','स्वास्थ्य और दिनचर्या','आरोग्य आणि दिनचर्या'),
 'compatibility':('Compatibility Review','गुणमिलान समीक्षा','गुणमिलन आढावा'),
 'dosha':('Doshas & Yogas','दोष और योग','दोष आणि योग'),
 'report':('Vedic interpretation report','वैदिक विश्लेषण रिपोर्ट','वैदिक विश्लेषण अहवाल'),
 'review':('Review date','समीक्षा तिथि','आढावा तारीख'),
 'birth':('Birth details','जन्म विवरण','जन्म तपशील'),
 'date':('Birth date / time','जन्म तिथि / समय','जन्मतारीख / वेळ'),
 'place':('Birthplace','जन्म स्थान','जन्मस्थळ'),
 'zone':('Time zone','समय क्षेत्र','वेळ क्षेत्र'),
 'coordinates':('Latitude / longitude','अक्षांश / देशांतर','अक्षांश / रेखांश'),
 'accuracy':('Recorded time','दर्ज समय','नोंदवलेली वेळ'),
 'exact':('Exact to entered minute','दर्ज मिनट तक सटीक','नोंदवलेल्या मिनिटापर्यंत अचूक'),
 'approximate':('Approximate: timing and houses can change','अनुमानित: दशा और भाव बदल सकते हैं','अंदाजे: दशा आणि भाव बदलू शकतात'),
 'summary':('At a glance','संक्षिप्त आढावा','थोडक्यात आढावा'),
 'chart':('Kundali charts','कुंडली चित्र','कुंडली आकृती'),
 'planets':('Calculated planetary positions','गणना की गई ग्रह स्थितियाँ','गणिती ग्रहस्थिती'),
 'planet':('Planet','ग्रह','ग्रह'),
 'sign':('Sign','राशि','राशी'),
 'house':('House','भाव','भाव'),
 'ascendant':('Ascendant','लग्न','लग्न'),
 'nakshatra':('Moon nakshatra / pada','चंद्र नक्षत्र / चरण','चंद्र नक्षत्र / चरण'),
 'ayanamsa':('Lahiri ayanamsa','लाहिड़ी अयनांश','लाहिरी अयनांश'),
 'degree':('Degree','अंश','अंश'),
 'dignity':('Sign condition','राशि स्थिति','राशीतील स्थिती'),
 'evidence':('Chart evidence','कुंडली के आधार','कुंडलीतील आधार'),
 'reflection':('Practical reflection','व्यावहारिक विचार','व्यावहारिक विचार'),
 'timeline':('Monthly traditional indicators','मासिक पारंपरिक संकेत','मासिक पारंपरिक संकेत'),
 'month':('Month','महीना','महिना'),
 'support':('Support','सहायक','सहाय्यक'),
 'pressure':('Demanding','चुनौती','आव्हान'),
 'period':('Dasha / antardasha','दशा / अंतर्दशा','दशा / अंतर्दशा'),
 'highlights':('Periods within the selected outlook','चुनी अवधि के समयखंड','निवडलेल्या कालावधीतील टप्पे'),
 'favorable':('More supportive indicators','अधिक सहायक संकेत','अधिक सहाय्यक संकेत'),
 'demanding':('More demanding indicators','अधिक चुनौती के संकेत','अधिक आव्हानांचे संकेत'),
 'guna':('Ashtakoota: raw guna score','अष्टकूट: मूल गुण मिलान','अष्टकूट: मूळ गुणमिलन'),
 'koota':('Koota','कूट','कूट'),
 'points':('Points / maximum','गुण / अधिकतम','गुण / कमाल'),
 'context':('Selected-date context','चुनी तिथि का संदर्भ','निवडलेल्या तारखेचा संदर्भ'),
 'cautions':('Scope & qualifications','सीमाएँ और आवश्यक संदर्भ','मर्यादा आणि आवश्यक संदर्भ'),
 'sources':('Sources & calculation method','स्रोत और गणना पद्धति','स्रोत आणि गणना पद्धती'),
 'page':('Page','पृष्ठ','पृष्ठ'),
 'privacy':('Generated in memory. Vedika does not save the entered birth details. Your downloaded PDF is a separate file under your control.','स्मृति में तैयार। वेदिका दर्ज जन्म विवरण सहेजता नहीं है। डाउनलोड की गई PDF आपके नियंत्रण में अलग फ़ाइल है।','स्मृतीत तयार. वेदिका नोंदवलेले जन्मतपशील जतन करत नाही. डाउनलोड केलेली PDF तुमच्या नियंत्रणातील स्वतंत्र फाइल आहे.'),
 'notice':('Calculated chart positions and traditional interpretations are different. Astrology cannot establish health diagnoses, marriage outcomes, separation, a partner’s real location, or certain career peaks.','गणिती ग्रह स्थितियाँ और पारंपरिक व्याख्या अलग हैं। ज्योतिष से स्वास्थ्य निदान, विवाह परिणाम, अलगाव, साथी का वास्तविक स्थान या निश्चित करियर शिखर सिद्ध नहीं होते।','गणिती ग्रहस्थिती आणि पारंपरिक अर्थ वेगळे आहेत. ज्योतिषावरून आरोग्यनिदान, वैवाहिक परिणाम, विभक्तता, जोडीदाराचे वास्तविक स्थान किंवा निश्चित करिअर शिखर सिद्ध होत नाही.'),
 'sample':('Counts show named traditional conditions at monthly sample instants. They are not probabilities, income forecasts, health predictions or exact event dates.','संख्या मासिक नमूना समय पर मिले पारंपरिक नियम दर्शाती है। यह संभावना, आय पूर्वानुमान, स्वास्थ्य भविष्यवाणी या घटना की सटीक तिथि नहीं है।','संख्या मासिक नमुना वेळी जुळलेले पारंपरिक नियम दर्शवते. ही संभाव्यता, उत्पन्नाचा अंदाज, आरोग्याचे भाकीत किंवा घटनेची अचूक तारीख नाही.'),
 'chartLegend':('North Indian layout: houses stay fixed; small numbers identify sidereal signs (1=Aries … 12=Pisces). D1/D9 use Lahiri, whole signs and mean lunar nodes.','उत्तर भारतीय शैली: भाव स्थिर; छोटे अंक निरयण राशियाँ बताते हैं (1=मेष … 12=मीन)। D1/D9 में लाहिड़ी, पूर्ण राशि भाव और मध्यम चंद्र पात हैं।','उत्तर भारतीय मांडणी: भाव स्थिर; लहान अंक निरयण राशी दर्शवतात (1=मेष … 12=मीन). D1/D9 मध्ये लाहिरी, पूर्ण राशी भाव व मध्यम चंद्रपात आहेत.'),
}
PLANETS = {
 'Sun':('Sun','सूर्य','सूर्य'), 'Moon':('Moon','चंद्र','चंद्र'), 'Mars':('Mars','मंगल','मंगळ'),
 'Mercury':('Mercury','बुध','बुध'), 'Jupiter':('Jupiter','गुरु','गुरू'), 'Venus':('Venus','शुक्र','शुक्र'),
 'Saturn':('Saturn','शनि','शनी'), 'Rahu':('Rahu','राहु','राहू'), 'Ketu':('Ketu','केतु','केतू'),
}
SIGNS = [('Aries','मेष','मेष'),('Taurus','वृषभ','वृषभ'),('Gemini','मिथुन','मिथुन'),('Cancer','कर्क','कर्क'),('Leo','सिंह','सिंह'),('Virgo','कन्या','कन्या'),('Libra','तुला','तूळ'),('Scorpio','वृश्चिक','वृश्चिक'),('Sagittarius','धनु','धनु'),('Capricorn','मकर','मकर'),('Aquarius','कुंभ','कुंभ'),('Pisces','मीन','मीन')]


def _value(value, language):
    if isinstance(value, dict):
        result = value.get(language) or value.get('en')
        return str(result) if result is not None else ''
    if value is None:
        return ''
    return str(value)


class _Report(FPDF):
    def __init__(self, language, kind):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.language = language
        self.index = LANGUAGES.index(language)
        self.kind = kind
        for style, name in [('', 'Regular'),('B', 'Bold')]:
            self.add_font('Vedika', style=style, fname=str(FONTS / f'NotoSansDevanagari-{name}.ttf'))
        self.set_text_shaping(True)
        self.cmap = set(TTFont(FONTS / 'NotoSansDevanagari-Regular.ttf').getBestCmap())
        self.set_margins(19, 39, 19)
        self.set_auto_page_break(True, margin=19)
        self.alias_nb_pages()
        self.set_title(self.tr(kind))
        self.set_author('Vedika')
        self.set_creator('Vedika 2.0 / fpdf2 / HarfBuzz')
        self.set_lang({'en':'en-IN','hi':'hi-IN','mr':'mr-IN'}[language])

    def tr(self, key):
        return T.get(key, (key,key,key))[self.index]

    def clean(self, value):
        text = _value(value, self.language)
        text = text.replace('\r',' ').replace('\t',' ').replace('\x00','')
        for before, after in {'≤':'<=','≥':'>=','→':' to ','↔':' / ','✓':'yes','✗':'no','−':'-'}.items():
            text = text.replace(before, after)
        # Preserve uncommon names as explicit code points instead of silently
        # dropping characters or letting a missing glyph abort the report.
        return ''.join(ch if ch in '\n' or ord(ch) in self.cmap else f'[U+{ord(ch):04X}]' for ch in text)

    def header(self):
        self.set_draw_color(*GOLD)
        self.set_line_width(.25)
        self.rect(11, 10, self.w-22, self.h-20)
        self.set_draw_color(220, 212, 190)
        self.rect(12.3, 11.3, self.w-24.6, self.h-22.6)
        logo = ROOT / 'static' / 'lotus.svg'
        if logo.is_file():
            self.image(str(logo), x=18.5, y=14, w=18, h=18)
        self.set_xy(40, 14)
        self.set_font('Vedika','B',20)
        self.set_text_color(*FOREST)
        self.cell(130, 10, self.clean('Vedika · वेदिका'))
        self.set_xy(40, 25)
        self.set_font('Vedika','',8)
        self.set_text_color(*MUTED)
        self.cell(150, 6, self.clean(self.tr(self.kind)+'  /  '+self.tr('report')))
        self.set_draw_color(*GOLD)
        self.line(19, 35, self.w-19, 35)
        self.set_y(40)

    def footer(self):
        self.set_y(-16)
        self.set_x(19)
        self.set_font('Vedika','',7)
        self.set_text_color(*MUTED)
        self.cell(self.epw, 5, self.clean(f"Vedika · {self.tr('page')} {self.page_no()} / {{nb}}"), align='R')

    def paragraph(self, text, size=9.6, bold=False, color=INK, gap=2):
        if not text:
            return
        self.set_x(self.l_margin)
        self.set_font('Vedika','B' if bold else '',size)
        self.set_text_color(*color)
        self.multi_cell(self.epw, 5.2 if size>=9 else 4.5, self.clean(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(gap)

    def heading(self, text, level=1):
        if self.y > self.h - 38:
            self.add_page()
        self.ln(3)
        self.paragraph(text, 13 if level==1 else 10.5, True, FOREST, gap=2)
        if level==1:
            self.set_draw_color(*GOLD)
            self.line(self.l_margin, self.y-1, self.l_margin+25, self.y-1)
            self.ln(2)

    def note(self, item, evidence=True):
        if isinstance(item,str):
            self.paragraph(item)
            return
        if not isinstance(item,dict):
            return
        if self.y > self.h - 36:
            self.add_page()
        if item.get('title'):
            self.paragraph(item['title'],10,True,FOREST,gap=.8)
        if item.get('text'):
            self.paragraph(item['text'])
        if evidence:
            for fact in item.get('evidence',[]) or []:
                self.paragraph('- '+_value(fact,self.language),8.2,color=MUTED,gap=.5)
        self.ln(1)

    def table(self, headers, rows, widths=None):
        widths = widths or [self.epw/len(headers)]*len(headers)
        def row(cells, header=False):
            self.set_font('Vedika','B' if header else '',8.2 if header else 8.4)
            text = [self.clean(v) for v in cells]
            heights=[self.multi_cell(w-4,4.9,t,dry_run=True,output=MethodReturnValue.HEIGHT) for w,t in zip(widths,text)]
            height=max(7,max(heights)+3)
            if self.y+height>self.h-self.b_margin:
                self.add_page()
                if not header and any(headers):
                    row(headers,True)
                self.set_font('Vedika','B' if header else '',8.2 if header else 8.4)
            x,y=self.l_margin,self.y
            for width,t in zip(widths,text):
                self.set_fill_color(*(FOREST if header else PAPER))
                self.set_draw_color(226,224,214)
                self.rect(x,y,width,height,style='DF')
                self.set_xy(x+2,y+1.5)
                self.set_text_color(*((255,252,242) if header else INK))
                self.multi_cell(width-4,4.9,t,new_x=XPos.LEFT,new_y=YPos.TOP)
                x+=width
            self.set_xy(self.l_margin,y+height)
        if any(headers):
            row(headers,True)
        for cells in rows:
            row(cells)
        self.ln(3)

    def birth(self, chart):
        p=chart.get('profile',{})
        self.heading(p.get('name') or self.tr('birth'))
        rows=[(self.tr('date'),f"{p.get('date','')}  {p.get('time','')}"),
              (self.tr('place'),p.get('place','')),
              (self.tr('zone'),p.get('timezone','')),
              (self.tr('coordinates'),f"{p.get('latitude','')} / {p.get('longitude','')}"),
              (self.tr('accuracy'),self.tr(p.get('time_accuracy','exact')))]
        if chart.get('ascendant'):
            asc=chart['ascendant'];idx=asc.get('sign_index',0);rows.append((self.tr('ascendant'),SIGNS[idx][self.index] if isinstance(idx,int) and 0<=idx<12 else asc.get('sign','')))
        if chart.get('moon'):
            moon=chart['moon'];rows.append((self.tr('nakshatra'),f"{moon.get('nakshatra','')} / {moon.get('pada','')}"))
        if isinstance(chart.get('ayanamsa_deg'),(int,float)):
            rows.append((self.tr('ayanamsa'),f"{chart['ayanamsa_deg']:.6f}"))
        self.table(['',''],rows,[48,self.epw-48])

    def kundali(self, chart):
        if not chart.get('d1') or not chart.get('d9'):
            return
        if self.y+102>self.h-self.b_margin:
            self.add_page()
        self.heading(self.tr('chart'))
        top=self.y+5
        size=77
        centers=[(.5,.25),(.25,.105),(.105,.25),(.25,.5),(.105,.75),(.25,.895),(.5,.75),(.75,.895),(.895,.75),(.75,.5),(.895,.25),(.75,.105)]
        abbr={'Sun':('Su','सू','सू'),'Moon':('Mo','चं','चं'),'Mars':('Ma','मं','मं'),'Mercury':('Me','बु','बु'),'Jupiter':('Ju','गु','गु'),'Venus':('Ve','शु','शु'),'Saturn':('Sa','श','श'),'Rahu':('Ra','रा','रा'),'Ketu':('Ke','के','के')}
        for i,key in enumerate(['d1','d9']):
            left=self.l_margin+i*(self.epw-size)
            self.set_xy(left,top-7);self.set_font('Vedika','B',9);self.set_text_color(*FOREST);self.cell(size,5,key.upper(),align='C')
            self.set_draw_color(*GOLD);self.set_line_width(.25);self.rect(left,top,size,size)
            for a,b in [((0,0),(1,1)),((1,0),(0,1)),((.5,0),(1,.5)),((1,.5),(.5,1)),((.5,1),(0,.5)),((0,.5),(.5,0))]:
                self.line(left+a[0]*size,top+a[1]*size,left+b[0]*size,top+b[1]*size)
            for house,center in zip(chart[key].get('houses',[]),centers):
                cx,cy=left+center[0]*size,top+center[1]*size
                self.set_font('Vedika','',6);self.set_text_color(*MUTED)
                self.set_xy(cx-7,cy-5);self.cell(14,3,self.clean(str(house.get('sign_index',0)+1)),align='C')
                names=' '.join(abbr.get(p,(p,p,p))[self.index] for p in house.get('planets',[]))
                self.set_font('Vedika','B',6.3);self.set_text_color(*FOREST)
                self.set_xy(cx-10,cy-1);self.multi_cell(20,3.2,self.clean(names),align='C')
        self.set_xy(self.l_margin,top+size+4)
        self.paragraph(self.tr('chartLegend'),8,color=MUTED)


def _planet_name(value, language):
    return PLANETS.get(value,(value,value,value))[LANGUAGES.index(language)]


def render_pdf(report: dict, language: str = 'en') -> bytes:
    """Return a complete PDF byte string; never create a report file."""
    if language not in LANGUAGES:
        raise ValueError('PDF language must be en, hi or mr.')
    if not isinstance(report,dict) or not report:
        raise ValueError('A calculated report is required.')
    kind=report.get('report_type','report')
    pdf=_Report(language,kind)
    pdf.add_page()
    pdf.paragraph(pdf.tr(kind),21,True,FOREST,gap=2)
    pdf.paragraph(f"{pdf.tr('review')}: {report.get('as_of','')}  ·  {report.get('as_of_timezone','')}",9,color=MUTED,gap=4)
    pdf.paragraph(pdf.tr('notice'),9,color=MUTED,gap=4)
    charts=report.get('charts') or ([report['chart']] if report.get('chart') else [])
    for chart in charts:
        pdf.birth(chart)
    if report.get('summary'):
        pdf.heading(pdf.tr('summary'))
        for item in report['summary']:
            pdf.note(item)
    context=report.get('context') or {}
    period=context.get('current_dasha')
    if period:
        pdf.heading(pdf.tr('context'))
        pdf.paragraph(f"{_planet_name(period.get('mahadasha',''),language)} / {_planet_name(period.get('antardasha',''),language)} · {period.get('start','')[:10]} — {period.get('end','')[:10]}")
    if report.get('kootas'):
        koota_labels={'varna':('Varna','वर्ण','वर्ण'),'vashya':('Vashya','वश्य','वश्य'),'tara':('Tara','तारा','तारा'),'yoni':('Yoni','योनि','योनी'),'graha_maitri':('Graha Maitri','ग्रह मैत्री','ग्रह मैत्री'),'gana':('Gana','गण','गण'),'bhakoot':('Bhakoot','भकूट','भकूट'),'nadi':('Nadi','नाड़ी','नाडी')}
        pdf.heading(pdf.tr('guna')+f"  {report.get('score','')} / 36")
        pdf.table([pdf.tr('koota'),pdf.tr('points')],[(koota_labels.get(k.get('key'),(k.get('name',''),)*3)[pdf.index],f"{k.get('score','')} / {k.get('max','')}") for k in report['kootas']],[110,pdf.epw-110])
    for chart in charts:
        pdf.kundali(chart)
        if chart.get('planets'):
            pdf.heading(pdf.tr('planets'))
            rows=[]
            for p in chart['planets']:
                sign=SIGNS[p['sign_index']][pdf.index] if isinstance(p.get('sign_index'),int) and 0<=p['sign_index']<12 else p.get('sign','')
                rows.append([_planet_name(p.get('name',''),language),sign,str(p.get('house','')),f"{p.get('degree',0):.2f}"])
            pdf.table([pdf.tr('planet'),pdf.tr('sign'),pdf.tr('house'),pdf.tr('degree')],rows,[48,55,31,pdf.epw-134])
    for section in report.get('sections',[]) or []:
        pdf.heading(section.get('title') or section.get('key',''))
        pdf.paragraph(section.get('text',''))
        if section.get('evidence'):
            pdf.heading(pdf.tr('evidence'),2)
            for item in section['evidence']:
                pdf.note(item)
        for condition in section.get('conditions',[]) or []:
            pdf.paragraph(condition.get('title') or condition.get('key',''),9.5,True)
            pdf.paragraph(condition.get('evidence',''),8.5,color=MUTED)
        if section.get('advice'):
            pdf.heading(pdf.tr('reflection'),2)
            for item in section['advice']:
                pdf.note(item)
    timeline=report.get('timeline') or []
    if timeline:
        pdf.heading(pdf.tr('timeline'))
        pdf.paragraph(pdf.tr('sample'),8.5,color=MUTED)
        highlights=report.get('highlights') or {}
        for key,label in [('supportive','favorable'),('demanding','demanding')]:
            if highlights.get(key):
                pdf.paragraph(pdf.tr(label)+': '+', '.join(str(x) for x in highlights[key]),8.5)
        rows=[]
        for row in timeline:
            md=_planet_name(row.get('mahadasha') or '-',language)
            ad=_planet_name(row.get('antardasha') or '-',language)
            rows.append([row.get('month',''),str(row.get('support_count',0)),str(row.get('pressure_count',0)),md+' / '+ad])
        pdf.table([pdf.tr('month'),pdf.tr('support'),pdf.tr('pressure'),pdf.tr('period')],rows,[30,30,32,pdf.epw-92])
        for window in report.get('windows',[]) or []:
            pdf.paragraph(f"{window.get('start','')} — {window.get('end','')}",9,True)
            if window.get('label'):
                pdf.paragraph(window['label'],8.5)
    if report.get('cautions'):
        pdf.heading(pdf.tr('cautions'))
        for item in report['cautions']:
            pdf.note(item)
    if report.get('methodology') or report.get('sources'):
        pdf.heading(pdf.tr('sources'))
        for item in report.get('methodology',[]) or []:
            pdf.note(item)
        for item in report.get('sources',[]) or []:
            if isinstance(item,dict):
                pdf.paragraph(item.get('title',''),8.2,True,color=MUTED,gap=.5)
                pdf.paragraph(str(item.get('url','')),7.2,color=MUTED,gap=2)
            else:
                pdf.paragraph(str(item),7.5,color=MUTED)
    pdf.heading('Vedika',2)
    pdf.paragraph(pdf.tr('privacy'),8,color=MUTED)
    return bytes(pdf.output())
