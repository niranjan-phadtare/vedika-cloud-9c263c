# Third-party notices and distribution

Vedika source code is supplied under GNU Affero General Public License v3.0 or later (`LICENSE`). Copyright 2026 Vedika contributors. This notice describes the chosen source distribution, not legal advice about every possible future commercial arrangement.

## Swiss Ephemeris and Python wrapper

- **pysweph 2.10.3.6**, the maintained Swiss Ephemeris Python wrapper, imports as `swisseph`; copyright/license notices are included in its wheel and corresponding source distribution in `third_party/source/`. See its PyPI metadata and `pysweph-source.json` for the exact URL and SHA256. It includes Swiss Ephemeris C source. Its API can differ from the older `pyswisseph` package; the app handles its return format explicitly.
- Swiss Ephemeris by Astrodienst AG, Alois Treindl and Dieter Koch: [official license](https://github.com/aloistr/swisseph/blob/master/LICENSE), [documentation](https://www.astro.com/swisseph/swephprg.htm). The project uses the AGPL route. See `third_party/SWISSEPH-LICENSE.txt`.
- Bundled planetary/lunar ephemeris data `sepl_18.se1` and `semo_18.se1` come from the official repository, with URLs and checksums in `data/ephe/manifest.json` (or the data manifest). Keep those notices with redistributed files.
- A future proprietary or hosted release must review the obligations of both the wrapper and Swiss Ephemeris. A commercial Swiss Ephemeris agreement does not automatically relicense independent wrapper code.

## PyJHora matching tables

`astro/matching.py` adapts the Vashya, Yoni, Gana and Graha Maitri numerical tables from [PyJHora compatibility.py](https://github.com/ArkOne-Softwares/pyjhora/blob/be344af506590b6e4c79942d84b958495dee4766/src/jhora/horoscope/match/compatibility.py), commit `be344af506590b6e4c79942d84b958495dee4766`.

Copyright © Open Astro Technologies / Sundar Sundaresan, under GNU AGPLv3. The upstream copyright and license notice is retained in `astro/matching.py`, and full upstream license in `third_party/PYJHORA-LICENSE.txt`. Changes: this app supplies its own calculation/API code, fixes and names a specific mixed-reference rule variant, uses actual Moon degrees for split Vashya signs, applies a separately sourced Tara rule, and preserves raw scores without cancellation points. Attribution does not imply endorsement or complete algorithm equivalence.

## Geographic data

GeoNames data is licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); see [GeoNames](https://www.geonames.org/) and `docs/PLACES.md`. The database is a transformed snapshot of the India postal export, cities15000 and administrative/country records. Its source URLs, download dates and changes are in the generated data manifest. Coordinates and coverage are approximate. No guarantee of completeness or official postal authority is made.

## Other Python packages

The ZIP includes the pinned Windows wheels listed in `requirements.txt`. Each wheel retains its publisher's original LICENSE/NOTICE metadata. FastAPI/Starlette/Uvicorn and their dependencies remain under their respective licenses, not relicensed by this app. See the `.dist-info/licenses/` or license files inside each wheel for exact text. `tools/download_wheels.py` reproduces the wheelhouse and checksums.

## Reference material

Uploaded PDFs were inspected as user-provided reference data. Their contents were not treated as operating instructions, and the original PDFs, personal horoscope, OCR corpus and long quotations are not redistributed. Website references explain provenance or surveyed features; their brands/artwork have not been copied into the UI. `static/lotus.svg` and app styling are original local assets.


## Bundled Windows Python runtime

The offline Windows installer includes the unmodified CPython 3.11.9 embeddable AMD64 ZIP from the Python Software Foundation's official distribution. Its original `LICENSE.txt`, VC runtime files and Python catalog are retained inside `windows/python-3.11.9-embed-amd64.zip`. Source URL, byte count and SHA256 are recorded in `windows/runtime-manifest.json`. The runtime is unpacked and its isolated `python311._pth` configuration is set during installation.

The added PDF packages fpdf2, uharfbuzz, Pillow and fonttools retain their original wheel license files. Font assets and their SIL OFL license are under `assets/fonts/`. The complete wheelhouse includes the Windows-compatible binaries; corresponding Swiss Ephemeris wrapper/C source remains supplied in `third_party/source/`.

## Vedika 2.0 additions

- Windows x64 CPython 3.11.9 embeddable distribution: Python Software Foundation license and bundled VC runtime notices are inside `windows/python-3.11.9-embed-amd64.zip`. Official download URL and exact SHA256 are in `windows/runtime-manifest.json`. The runtime is redistributed unmodified; generated `_pth` import configuration and dependency extraction happen during installation.
- fpdf2 2.9.0, uharfbuzz 0.57.0, Pillow 13.0.0 and fonttools 4.68.0 retain their publisher licenses and notices inside the original wheels. Noto Sans Devanagari fonts are under SIL OFL 1.1; original/instanced fonts, source notice and full license are in `assets/fonts/`.
- The lotus artwork, planet-orbit animation/video, icons and app UI are local project assets. No external footage or third-party brand artwork is used.

The source and notices supplied with the complete package must accompany redistribution. Hosted users must be able to obtain the corresponding AGPL source. Cloud providers and Windows signing have separate terms; this distribution is not a commercial license waiver or a signed installer.
