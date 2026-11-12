# VR-3 five-section report catalogue

`astro/reports.py` exposes `build_report(section, profile, as_of=None, horizon_months=24, person_b=None, relationship_status='considering')`. It performs no database, filesystem or network writes. Dates and chart calculations use the shared IR-1/PM-1 selected-local-noon context. `as_of=None` means today's civil date in the profile's selected IANA timezone, not a hardcoded year or the host's timezone.

Every report has localized English/Hindi/Marathi titles, significance text, calculation evidence and limits. Source titles and raw technical evidence may remain English in the audit. The exact section keys are `personal`, `love`, `career`, `health` and `compatibility`.

## Personal Kundali

The D1/D9 chart, all nine grahas, ascendant, Moon star/pada and dasha data remain available. The planetary table independently marks own sign, exaltation sign and debilitation sign for the seven classical planets. Mercury in Virgo can meet both own and exaltation conditions. Nodes are explicitly unscored because their sign-dignity conventions vary. These labels are not full Shadbala, exact exaltation strength, combustion, affliction or a final strong/weak rank.

An overall reflection shows actual Lagna and Moon signs plus broad traditional element themes. These are not a validated personality assessment or evidence of personal character. Existing Manglik and eight yoga geometry checks retain their individual significance, qualifications, current-period participants and geometric transit contacts.

**KS-BASE-1** is a disclosed Kalsarpa base-geometry screen: all seven classical grahas must lie in either of the two 180° halves bounded by mean Rahu and its opposite Ketu. Exact node endpoints are included in both halves, with `1e-7°` tolerance solely for floating-point agreement. The ascendant and outer planets are excluded. One planet outside the common half means this base screen is absent. No partial forms, named Kalsarpa/Kalamrita distinctions, cancellation, severity, compulsory remedy or outcome is inferred. The conventional node-axis description is illustrated by [this practitioner PDF](https://www.kalsarpa.com/download/kalsarpa.pdf); this app's inclusive endpoints and both-half convention are explicit application choices. Do not describe this as a universally accepted complete classical rule.

## Love & Marriage

PM-1 natal fifth/seventh/family-house connections, seventh-lord/Venus context, gender-neutral timing samples, direction symbolism and adult guard are retained. The meeting-medium section maps the actual seventh lord's natal house to openly declared broad introduction themes (for example the tenth to professional/public contexts). This is an application-level symbolic association, not knowledge of a real person, online platform or location.

A first meeting date cannot be established. `meeting_windows` is an explicit copy of the existing PM-1 review month groups, never a separate first-contact prediction. No claim is made that the first meeting lies in the future. The report does not identify partner gender, location, direction, physical features, character or relationship outcome as fact. For a profile under 18 at the selected date, partner/style/meeting/timing interpretations are withheld.

## Career

IR-1 government/public service, technology, business, education/advisory and creative-service association sections remain. A separate private-employment/job section applies the same eight-condition application matrix with Saturn/Mercury/Sun, sixth-house service and tenth-house work references. Education/advisory is explicitly labelled consultancy, education and advisory; consultancy can be salaried or independent. These work modes overlap and do not establish a single best sector.

The monthly graph retains visible equal-condition counts and current MD/AD. Its extremes concern only the selected rules within the searched horizon, with full ties retained. They do not predict actual job, income, promotion, unemployment, examination success, business profit or career highs/lows. Education, real skills, opportunity and circumstances remain necessary for actual choices.

## Health

The health report deliberately has **no monthly health-risk graph**, forecast, disease label, organ assignment, lifespan or fertility score. Its only chart-specific reference is actual Lagna/sixth-house/lord geometry, explicitly treated as traditional routine/service symbolism. Wellbeing suggestions are general reflection prompts for everyone, not individual treatment. Real symptoms and medical decisions require qualified healthcare assessment; the report does not advise delaying care, changing medication or buying a planetary remedy.

## Compatibility Checker

Raw AK-1 eight-koota points and the 18/36 threshold are retained without cancellation adjustments. Person A and B occupy the historical directional groom/bride table positions regardless of entered gender labels. Full-point rules form a traditional-positive discussion list; incomplete rules form an individual-review list. Neither list measures real-world relationship quality. Nadi/Bhakoot zeroes and each person's Manglik/Kalsarpa base screens are shown separately. A count of displayed flags is not severity or risk.

`relationship_status` is `considering` or `married`. It changes discussion wording only: chart positions, raw guna points and monthly conditions are identical. The one-line review states the raw total, threshold result and displayed flag count; it makes no marriage recommendation. Separation/divorce is explicitly **not determinable** from the chart/score, and no yes/no forecast is generated.

Joint month groups require both people separately to pass the PM-1 combination (Venus/seventh-lord MD or AD, plus Jupiter in 2/5/7/9/11 from natal Moon) at that month's sample. Saturn 12/1/2 screens are separate pressure counts. Each person uses local noon in their own selected timezone: intersected month labels are calendar bins, not simultaneous event moments, exact transition intervals or wedding muhurtas. No listed group means no match in these limited filters, not impossibility of marriage. Both profiles must be at least 18 at the selected date for joint timing.

## Verification

`tests/test_reports_v3.py` checks all five report schemas/languages, input immutability and isolation, actual selected dates, eight-koota sum, relationship-status invariance, joint timing conditions, minor guards, dignity boundary cases and degree-based nodal wraparound/endpoints. Generic existing engine/IR-1/PM-1 tests remain applicable. Medical validity, prediction accuracy and actual Windows execution are not established by these software tests.
