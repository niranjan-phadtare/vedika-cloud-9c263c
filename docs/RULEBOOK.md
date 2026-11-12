# Implemented calculation rulebook

Engine version **VEDA-1**; matchmaking variant **AK-1**. Calculations are deterministic for a fixed input and software/data version. Astrology interpretations are traditional conventions, not scientifically established forecasts or a measured probability of marriage success.

## Required birth data

A full chart requires local birth date and time, confirmed latitude/longitude, and an IANA timezone. Name and gender do not enter the astronomical calculation. Supported birth years are 1900–2100, with future birth timestamps rejected. Latitude must lie strictly between −89° and +89°; longitude between −180° and +180°. Unknown birth times are unsupported rather than replaced by noon.

Timezones use the bundled IANA tzdb through Python `zoneinfo`. A nonexistent clock time during a daylight-saving jump is rejected. A clock time that occurs twice during a backward jump is also rejected; the birth record's correct UTC offset must be confirmed, then the equivalent UTC date/time may be entered with timezone UTC. A place lookup's modern timezone is not historical evidence for the civil time printed in an old record. Particularly for historical Indian births, verify local mean time and regional civil-time conventions.

Approximate birth times remain explicitly marked approximate. No unmeasured confidence interval is invented, and no birth-time rectification is performed.

## Astronomical settings

- Swiss Ephemeris, file-backed planetary and lunar ephemerides. Both `sepl_18.se1` and `semo_18.se1` must exist. Missing files, warnings or a planetary Moshier fallback stop the calculation.
- Sidereal ecliptic positions, Lahiri ayanamsha (`SIDM_LAHIRI`), geocentric positions and apparent/standard Swiss Ephemeris defaults. The Julian day uses UTC Gregorian birth date/time and `calc_ut` applies Swiss Ephemeris UT handling.
- Whole-sign houses from the sidereal ascendant sign.
- Mean lunar north node Rahu. Ketu is precisely 180° opposite mean Rahu.
- D1 and D9 are provided. D9 sign is `floor((sidereal_longitude mod360) ×9 /30) mod12`, equivalent to the conventional movable/fixed/dual sequence. D9 houses use the similarly calculated D9 ascendant sign.
- Planetary retrogression is the sign of longitudinal speed. Names and declared gender are not used to modify positions.

Swiss global settings and calculations run under a shared process lock to prevent concurrent requests from mixing configuration.

## Vimshottari periods

The Moon's sidereal nakshatra selects the opening mahadasha lord. The cycle is Ketu7, Venus20, Sun6, Moon10, Mars7, Rahu18, Jupiter16, Saturn19, Mercury17 years. A year is fixed at **365.25 days** in this build. Other software may use different year-length conventions.

The elapsed fraction of the Moon's nakshatra determines the elapsed fraction of the opening mahadasha. Each mahadasha's nine antardashas begin with its own lord and follow the cycle. An antardasha's untrimmed duration equals `mahadasha_days × antardasha_lord_years /120`. The first displayed MD and AD are clipped at birth, but all subdivisions are calculated from the original untrimmed MD start. The timeline ends 120 fixed years after birth. Full start/end timestamps are retained separately. Current periods are selected using the server's current UTC timestamp.

These dates are outputs of the named mathematical model. They do not establish that a career or marriage event will occur.

## Eight-factor matchmaking: AK-1

Each chart's **sidereal Moon longitude** supplies its sign, nakshatra and pada. Names, numerology and name sounds are unused. Person A uses historical groom-role tables and person B bride-role tables, regardless of gender labels. Direction matters for some tables and must be preserved.

| Factor | Maximum | Exact selected rule |
|---|---:|---|
| Varna | 1 | Water/fire/earth/air → Brahmin/Kshatriya/Vaishya/Shudra using Drik Panchang's mapping. Award1 when A's category is equal to or earlier in this traditional sequence than B's. Historical labels are not identity, caste or human worth. |
| Vashya | 2 | Fixed PyJHora `VasiyaArray`; bride-row/groom-column. Sagittarius0–15° Human,15–30° Quadruped; Capricorn0–15° Quadruped,15–30° Water. Actual longitude is used. |
| Tara | 3 | Inclusive count each direction `(target_nak-source_nak) mod27 +1`; award1.5 per direction if count modulo 9 is not3,5,7. Same-star Tara is3. |
| Yoni | 4 | Fixed PyJHora27-nakshatra→14-animal map and14×14 `YoniArray`. |
| Graha Maitri | 5 | Fixed PyJHora Moon-sign-lord matrix, natural friendship only. |
| Gana | 6 | Fixed PyJHora directional North `gana_array`, bride-row/groom-column. |
| Bhakoot | 7 | 2/12,5/9,6/8 inclusive Moon-sign relationships score0; other relationships7. |
| Nadi | 8 | Fixed27-nakshatra Nadi mapping; equal Nadi0, unequal8. |

Exact arrays live in `astro/matching.py`. The source reference is [PyJHora compatibility.py pinned commit be344af506590b6e4c79942d84b958495dee4766](https://github.com/naturalstupid/PyJHora/blob/be344af506590b6e4c79942d84b958495dee4766/src/jhora/horoscope/match/compatibility.py). Adapted tables retain AGPL-3.0-or-later attribution to Open Astro Technologies and Sundar Sundaresan. [Drik Varna](https://www.drikpanchang.com/tutorials/jyotisha/kundali-match/ashta-kuta/varna-kuta.html), [Drik Vashya](https://www.drikpanchang.com/tutorials/jyotisha/kundali-match/ashta-kuta/vashya-kuta.html) and [Maitreya/Saravali Dina](https://saravali.github.io/astrology/koota_dina.html) supply the explicitly stated Varna mapping, degree split and independently implemented Tara formula. This build corrects a reversed Tara condition and approximate Vashya split in the inspected upstream implementation; it does not claim output parity with upstream.

AK-1 is an openly specified combination of selected North Indian rules, not an industry-wide standard or a claim that all classical authorities agree. No Nadi, Bhakoot or Manglik cancellation points are added. Cancellation traditions, South Indian porutham and other regional systems are not implemented. Scores may therefore differ from other apps even with identical birth data.

The selected **18/36** threshold returns `meets_threshold` or `below_threshold`. This is a yes/no answer to that arithmetic threshold only. Individual Nadi and Bhakoot base-rule flags remain visible even above18. Nadi is not a fertility, health or genetic test, and Yoni/Gana do not measure a person's sexual function or personality.

## Limited dosha and yoga screens

**Manglik/Kuja:** Mars in1,2,4,7,8 or12 from the whole-sign Ascendant, Moon or Venus. All three references and their actual house numbers are returned separately. Overall `present` means at least one reference meets this selected base rule. No severity, cancellation, partner harm or life outcome is inferred. Other traditions may choose fewer houses or references.

Eight yoga base screens are returned with true/false conditions and explicit scope:

1. Gaja Kesari: Jupiter in1/4/7/10 from Moon.
2. Budha Aditya: Sun and Mercury in the same sidereal sign.
3. Chandra Mangala: Moon and Mars in the same sidereal sign.
4. Ruchaka: Mars in own/exaltation sign and a kendra from Ascendant.
5. Bhadra: Mercury in own/exaltation sign and a kendra from Ascendant.
6. Hamsa: Jupiter in own/exaltation sign and a kendra from Ascendant.
7. Malavya: Venus in own/exaltation sign and a kendra from Ascendant.
8. Shasha: Saturn in own/exaltation sign and a kendra from Ascendant.

These are geometric eligibility screens. Combustion, avasthas, shadbala, afflictions, exact exaltation strength, comprehensive aspects, cancellation rules and all other yoga qualifications are not assessed for these labels. `false` means that one named implemented base rule was not met; it never means all yogas/doshas are absent. The uploaded books are reference material and have not been exhaustively encoded.

## Verification scope

Automated checks cover Julian-day/UTC conversion, tropical versus Lahiri sidereal subtraction, node opposition, whole-sign/D9 assignment, DST fold/gap rejection, MD/AD continuity and opening balance, exact Ashtakoota fixtures, 15° Vashya boundaries, matrix orientation and sensitive pinned-source cells. All four adapted full matrices were compared cell-for-cell to the pinned source during implementation.

These checks establish software behavior for the named rules. Independent practitioner review across a larger chart corpus is still required before offering broad professional readings. The implementation does not calculate every past/future event or provide guaranteed marriage/career outcomes.

## WP-1: preliminary wedding-date screening

`astro/timing.py` samples Lahiri geocentric Sun and Moon at **12:00 local civil time** on each requested date. This is not a computed auspicious wedding time. The maximum request is 366 dates, 1900–2100 inclusive. The timezone selects the UTC instant; latitude/longitude are retained as event metadata and are not used by these geocentric filters.

A listed date passes three primary filters at the sample: Moon in the fixed 11 wedding nakshatras, neither Rikta tithi (4/9/14 within either fortnight) nor Amavasya, and a karana other than Vishti/Shakuni/Chatushpada/Naga. The 11 nakshatras are Rohini, Mrigashira, Magha, Uttara Phalguni, Hasta, Swati, Anuradha, Mula, Uttara Ashadha, Uttara Bhadrapada and Revati.

The displayed 0–8 value is simply the number of passed checks, each worth one: these three, weekday (Monday/Wednesday/Thursday/Friday), Tara bala for person A/B, and Chandra bala for person A/B. Tara uses the inclusive natal-to-event nakshatra count modulo 9, passing remainders 0/2/4/6/8. Chandra bala passes Moon-sign distances 1/3/6/7/10/11. A result with 8/8 is not a probability, a compatibility score or an endorsement to marry. Sort order is check count descending, then date ascending; no 'best date' fact is inferred.

Tithi is floor((Moon−Sun modulo 360)/12)+1; karana uses 6° half-tithi segments, the seven repeating movable karanas and the fixed first/last karanas. These are sample classifications, not whole-day classifications or transition times.

[Drik Panchang's marriage-election explanation](https://www.drikpanchang.com/shubh-dates/info/choosing-auspicious-marriage-date.html?lang=en) is a reference for the broad filters and, crucially, the additional conditions that a complete muhurta needs. This implementation does not reproduce its calendar. **Not evaluated**: sunrise boundaries, exact transitions, prohibited solar/lunar months, Adhika/Kshaya masa, Chaturmas, Holashtak, panchanga yoga exclusions, combustion, eclipses, event lagna/D9 or dasha/transit marriage timing. It can list dates that would fail a complete muhurta. Do not book a ceremony from this screen alone.
