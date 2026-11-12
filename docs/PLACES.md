# Birthplace data and ephemerides

## Offline place coverage

The included read-only SQLite database was built on 11 November 2026 from the official [GeoNames download service](https://download.geonames.org/):

- **155,570 India postal locality records** from [`IN.zip`](https://download.geonames.org/export/zip/IN.zip), searchable by PIN, locality, district and state.
- **34,214 worldwide city records** from [`cities15000.zip`](https://download.geonames.org/export/dump/cities15000.zip). This dataset covers cities with more than 15,000 people and administrative capitals, rather than every village worldwide.
- Official GeoNames administrative division and country tables supply state, district and country names. These are provider labels; political and administrative boundaries can change.
- India postal results use the IANA zone `Asia/Kolkata`; worldwide city records carry the IANA timezone supplied by GeoNames. The calculation engine uses the timezone database for the actual historical birth date. The India postal table is geographic data, not evidence of an individual’s precise birth position. For historical records, particularly colonial India before national timekeeping was uniform, verify the recorded clock standard separately: an IANA zone’s database history cannot establish whether a birth record used Bombay, Madras, another local mean time, or national civil time.
- Alternate city names, including available Hindi/Marathi names, are indexed. Unicode locality-name coverage depends on GeoNames. India postal names are generally English. Search the English spelling or use manual coordinates when a local-language name is absent.
- A PIN frequently identifies several localities. The app returns distinct named results for explicit selection. It never assumes one birthplace from a PIN alone. The result list is bounded at 30 items by default (up to 50 through the helper); refine the query when needed.
- Coordinates are approximate locality/city centroids. They are not a geocoded maternity hospital address or guarantee of geographic precision. Confirm the city, district, state, country, coordinates, and timezone. For missing places enter confirmed latitude, longitude, and IANA timezone manually.
- Search is local and never transmits birth details to a geocoding provider. No geocoder account, API key, or Internet connection is needed for normal use.

**Attribution:** Contains information from [GeoNames](https://www.geonames.org/), licensed under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/). Data is provided without a completeness or accuracy warranty. GeoNames’ source and checksum manifest is in `data/places.manifest.json`.

To update the place database, with Internet access:

```console
python tools/build_places.py --download
```

This intentionally updates only the gazetteer; saved profile coordinates are not silently changed. Keep your own database backup before updating.

## Swiss Ephemeris data

Included astronomical files are downloaded from the official [Swiss Ephemeris repository](https://github.com/aloistr/swisseph/tree/master/ephe):

- [`sepl_18.se1`](https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/sepl_18.se1): planetary positions for the 1800–2399 file period.
- [`semo_18.se1`](https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/semo_18.se1): lunar positions for the same file period.

The app deliberately restricts accepted dates to its documented tested range. The engine checks returned ephemeris flags and refuses silent Moshier fallback. Swiss Ephemeris is dual licensed; see the app’s top-level license and dependency notices before redistribution or commercial publication. These data files do not provide astrology interpretation or establish the predictive validity of astrology.
