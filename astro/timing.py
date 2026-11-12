"""WP-1: deliberately limited, reproducible wedding-date screening.

A local-noon sample is not a wedding muhurta or a prediction of marriage.
All counts report passed filters, never probabilities of success.
"""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import swisseph as swe
from .engine import chart, SWISS_LOCK, EPHE_PATH, NAKSHATRAS

# Common 11-star selection. Named WP-1; local family traditions may differ.
WEDDING_STARS = {3,4,9,11,12,14,16,18,20,25,26}
WEEKDAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
KARANAS = ['Bava','Balava','Kaulava','Taitila','Garaja','Vanija','Vishti']


def karana_name(elongation):
    half = int((elongation % 360) // 6)
    if half == 0:
        return 'Kimstughna'
    if half >= 57:
        return ['Shakuni','Chatushpada','Naga'][half-57]
    return KARANAS[(half-1) % 7]


def candidate_dates(req: dict) -> dict:
    start, end = date.fromisoformat(req['start_date']), date.fromisoformat(req['end_date'])
    if not date(1900,1,1) <= start <= end <= date(2100,12,31):
        raise ValueError('Choose ordered dates between 1900 and 2100.')
    days=(end-start).days+1
    if days > 366:
        raise ValueError('Screen up to 366 days at a time.')
    try:
        zone = ZoneInfo(req['timezone'])
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError('A valid IANA event timezone is required.')
    charts=[chart(req['person_a']), chart(req['person_b'])]
    candidates=[]
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    with SWISS_LOCK:
        swe.set_ephe_path(str(EPHE_PATH))
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        for offset in range(days):
            day=start+timedelta(days=offset)
            local=datetime.combine(day,time(12),tzinfo=zone)
            utc=local.astimezone(timezone.utc)
            # A few historical timezone transitions skipped an entire day.
            if utc.astimezone(zone).replace(tzinfo=None) != local.replace(tzinfo=None):
                continue
            jd=swe.julday(utc.year,utc.month,utc.day,utc.hour+utc.minute/60+utc.second/3600)
            sr=swe.calc_ut(jd,swe.SUN,flags)
            mr=swe.calc_ut(jd,swe.MOON,flags)
            if not sr[1]&swe.FLG_SWIEPH or not mr[1]&swe.FLG_SWIEPH:
                raise RuntimeError('Required ephemeris unavailable; date screening stopped rather than using a fallback.')
            sun,moon=sr[0][0],mr[0][0]
            elongation=(moon-sun)%360
            tithi=int(elongation//12)+1
            fortnight_tithi=(tithi-1)%15+1
            nak=int(moon*27/360)%27
            sign=int(moon//30)%12
            karana=karana_name(elongation)
            checks=[
                {'rule':'wedding_nakshatra','passed':nak in WEDDING_STARS,'detail':NAKSHATRAS[nak]},
                {'rule':'non_rikta_tithi','passed':fortnight_tithi not in {4,9,14} and tithi!=30,'detail':str(tithi)},
                {'rule':'weekday','passed':day.weekday() in {0,2,3,4},'detail':WEEKDAYS[day.weekday()]},
                {'rule':'karana','passed':karana not in {'Vishti','Shakuni','Chatushpada','Naga'},'detail':karana},
            ]
            for i,c in enumerate(charts):
                tara=(nak-c['moon']['nakshatra_index'])%27+1
                chandra=(sign-c['moon']['sign_index'])%12+1
                checks.append({'rule':f'tara_person_{i+1}','passed':tara%9 in {0,2,4,6,8},'detail':f'Inclusive star count {tara}; remainder {tara%9}'})
                checks.append({'rule':f'chandra_person_{i+1}','passed':chandra in {1,3,6,7,10,11},'detail':f'Moon sign distance {chandra}'})
            # Date list passes the 3 named primary screens; secondary results remain visible.
            if checks[0]['passed'] and checks[1]['passed'] and checks[3]['passed']:
                candidates.append({'date':day.isoformat(),'local_time':'12:00','timezone':req['timezone'],'utc':utc.isoformat(),'tithi':tithi,'nakshatra':NAKSHATRAS[nak],'karana':karana,'weekday':WEEKDAYS[day.weekday()],'score':sum(c['passed'] for c in checks),'max_score':len(checks),'checks':checks})
    candidates.sort(key=lambda c:(-c['score'],c['date']))
    return {
        'intent':'preliminary_panchanga_filters', 'rule_version':'WP-1',
        'candidates':candidates,'searched_days':days,
        'event':{k:req[k] for k in ('place','latitude','longitude','timezone')},
        'charts':charts,
        'methodology':[
            'One geocentric Lahiri Sun/Moon sample at local 12:00 per civil date; 12:00 is a sampling time, not a muhurta.',
            'A listed date passes the 11-star wedding selection, non-Rikta/non-Amavasya tithi, and allowed karana at that sample.',
            'The 0–8 value counts passed filters equally: nakshatra, tithi, weekday, karana, Tara bala and Chandra bala for each person. It is not a probability or compatibility score.',
            'Wedding stars: Rohini, Mrigashira, Magha, Uttara Phalguni, Hasta, Swati, Anuradha, Mula, Uttara Ashadha, Uttara Bhadrapada, Revati.',
            'The event timezone fixes the UTC instant. These geocentric screens do not use the event coordinates; coordinates are retained for future full-muhurta work.',
            'No automatic marriage-date verdict is inferred from the 36-guna threshold.',
        ],
        'cautions':[
            'PRELIMINARY ONLY: a date can fail full muhurta rules even when every displayed filter passes.',
            'Not evaluated: sunrise boundaries, exact transition times, prohibited solar/lunar months, Adhika/Kshaya masa, Chaturmas, Holashtak, yoga exclusions, combustion, eclipses, event lagna, Navamsa, family/regional rules, or dasha/transit marriage promises.',
            'No full auspicious time window or guaranteed best marriage date is provided. Obtain a complete muhurta review before scheduling.',
            'Birth-time uncertainty and inaccurate birthplace details can change the underlying natal charts.',
        ],
        'sources':['https://www.drikpanchang.com/shubh-dates/info/choosing-auspicious-marriage-date.html?lang=en'],
    }
