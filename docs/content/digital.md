# Digital (non-book) resources — offline survival box

Research date: 2026-09-14. Sizes verified against live sources where noted; estimates flagged.
Legend: **[free]** = free direct download (URL given) · **[build]** = needs local build/scripting · **[paid]** = costs money.

## 1. Offline maps

### Raw OSM data (Geofabrik) — [free]

- Planet PBF: **88 GB** (2026-09-01) — https://planet.openstreetmap.org / https://download.geofabrik.de/
- North America: **18 GB** — https://download.geofabrik.de/north-america.html
- United States: **11.3 GB** (US South 3.8 GB, US West 3.1 GB, US Northeast 1.7 GB) — https://download.geofabrik.de/north-america/us.html
- Raw PBF is input data, not directly viewable — pair with one of the serving options below.

### Phone-app map files — [free]

- **Organic Maps**: entire USA ≈ **8.3 GB**; world overview map 39 MB; countries typically 100–800 MB. Apps download in-app, but the .mwm files can be pulled from Organic Maps' CDN and sideloaded/served on LAN for phones to copy. https://organicmaps.app/
- **OsmAnd**: entire US ≈ **16 GB** (.obf files); most states <1 GB; roads-only variants smaller. Files downloadable via app or https://download.osmand.net/ ; free app caps downloads (OsmAnd+ paid removes cap, F-Droid version is free/unlimited).
- Recommendation: pre-stage both .mwm and .obf sets on the box so any phone OS can grab its native format.

### Browser-served tiles (the LAN-friendly option)

- **Protomaps PMTiles planet** — [free]: full planet vector tiles z0–15 ≈ **120 GB**, daily builds at https://build.protomaps.com/ (e.g. `2026xxxx.pmtiles`). US-only extract: low tens of GB via `pmtiles extract`. Serve with any static HTTP server + MapLibre GL JS in the browser — zero tile-server process needed. Docs: https://docs.protomaps.com/basemaps/downloads
- **tileserver-gl + MBTiles** — [build]: classic stack; generate MBTiles from Geofabrik PBF with **Planetiler** (planet build ~1–2 days on beefy machine, or US in hours) or download prebuilt from OpenMapTiles (**[paid]** for current planet MBTiles; free samples only). Planetiler: https://github.com/onthegomap/planetiler
- Verdict: PMTiles + MapLibre is the lazy correct answer for browser maps over LAN; skip tileserver-gl unless you need server-side raster rendering for dumb clients.

### US topo (USGS) — [free]

- **US Topo GeoPDF full set**: ~65,240 current quads, **~2.8 TB total**, median 40.6 MB/quad — exceeds a 1 TB-ish budget; download per-state via The National Map Downloader batch/CSV dump instead. https://www.usgs.gov/faqs/can-i-get-a-bulk-order-usgs-topographic-maps-pdf-format-a-state-or-entire-country
- Practical alternative: state-level GeoPDF sets (a state ≈ 20–80 GB), or contour/hillshade layers baked into your PMTiles basemap. Historical quads via topoView (individual downloads only).

## 2. Offline web apps over LAN

- **Kiwix-serve** — [free]: single binary serves all ZIMs with built-in **full-text search across the whole library** (Xapian index inside each ZIM). This is the backbone app. https://kiwix.org/en/applications/
- **Offline LLM (llama.cpp / Ollama)** — [free, build to configure]: feasible. Mac Mini (M-series): 7B–14B Q4 GGUF at comfortable speeds; Pi 5 (8/16 GB): 1B–3B models (Llama 3.2 3B ≈ 2 GB, Qwen2.5 3B, Phi-3-mini) at roughly 4–10 tok/s — usable for Q&A, slow for long output (estimate from community benchmarks, not re-verified). Serve llama.cpp's built-in web UI (`llama-server`) over LAN. Budget 5–20 GB for a few models. https://github.com/ggml-org/llama.cpp
- **Offline translation** — [free]: **LibreTranslate** (web API/UI, self-host) on top of **Argos Translate** models, ~**100 MB per language pair**, fully offline after model download; 4–8 GB RAM for 5–10 pairs. https://github.com/LibreTranslate/LibreTranslate
- **Text-to-speech** — [free]: **Piper** (rhasspy/piper) — fast on Pi, voices ~20–100 MB each, has HTTP server mode. https://github.com/OHF-Voice/piper1-gpl
- **Calculators / small tools** — [free/build]: any static PWA works over LAN. Good candidates: SunCalc (solar position, MIT, static HTML), open-source ballistic calculators (e.g. GNU Exterior Ballistics, py-ballisticcalc — wrap in simple page, [build]), unit converters, medical dosage (see below). These are tiny (<50 MB total); collect as a static /tools directory.
- **Medical dosage** — [paid]: no good FOSS offline dosing web app exists; commercial ones (UpToDate, Micromedex) are paid subscriptions. Do NOT hand-build dosing tables (red-team finding: highest-lethality item — transcription errors kill). Buy a current licensed reference instead (e.g. Tarascon Pharmacopoeia; Harriet Lane Handbook for pediatric dosing) and treat wikipedia_en_medicine ZIM as background reading only, never a dosing source.

## 3. Datasets

- **USDA PLANTS checklist** — [free]: complete checklist CSV ≈ **7 MB** (names/families only, no images). https://plants.usda.gov/downloads
- **Edible/poisonous plants with images** — [build/mixed]: no single free image dataset. Options: Wikipedia "List of edible/poisonous plants" articles (in the Wikipedia ZIM already), USDA/Wikimedia Commons image scrape [build], or paid field-guide PDFs/apps ([paid], covered in books track). FEMA/army FM 21-76 survival manual (public domain) includes plant plates — [free] on archive.org.
- **Pill identification** — [free]: NLM **C3PI** pill-image dataset (RxImage API dead since 2021-12, but data archived on NLM Data Discovery: https://datadiscovery.nlm.nih.gov/Drugs-and-Chemicals/Computational-Photography-Project-for-Pill-Identif/5jdf-gdqh). Text-based ID (imprint/color/shape): **DailyMed SPL full releases** (split multi-part zips) https://dailymed.nlm.nih.gov/dailymed/spl-resources-all-drug-labels.cfm — tens of GB with label images; [build] a small imprint-search page over the SPL index.
- **Weather climatology** — [free]: NOAA **1991–2020 U.S. Climate Normals** (station CSVs, a few GB) — https://www.ncei.noaa.gov/products/land-based-station/us-climate-normals ; bulk via NCEI FTP/HTTPS.
- **Celestial/navigation almanac** — [free/build]: JPL ephemeris **DE440s ≈ 32 MB / DE440 ≈ 114 MB** + Python **Skyfield** computes positions offline indefinitely; **SFalmanac/Pyalmanac** generate Nautical-Almanac-style PDF pages [build]. https://rhodesmill.org/skyfield/
- **Ham radio** — [free]: ARRL band plan PDF (https://www.arrl.org/band-plan); **RepeaterBook** CHIRP CSV exports per state/region (https://www.repeaterbook.com/repeaters/downloads/CHIRP/) — export while online, tiny files; RepeaterBook mobile app caches full directory offline. FCC ULS weekly database dumps (callsigns/licenses, ~1 GB) https://www.fcc.gov/uls/transactions/daily-weekly.

## 4. Media

- **TED ZIMs** — [free]: `ted_mul_all_2026-05.zim` **82 GB**; topic subsets: science 14 GB, technology 16 GB. Marginal survival value — take science subset at most.
- **Kolibri (Learning Equality)** — [free]: Khan Academy full English channel ~30–40 GB with videos (estimate); serves over LAN with its own web app. https://learningequality.org/kolibri/
- **Instructional video via yt-dlp** — [build]: highest survival value per GB is curated YouTube channels (first aid: e.g. Prolonged Field Care/SkinnyMedic; bushcraft; gardening; homestead repair). At 720p ≈ 0.7–1.5 GB/hr; a 200-hour curated library ≈ 150–300 GB. Legality: personal archival gray zone; needs-build (yt-dlp + simple static index or Jellyfin).
- **Internet Archive collections** — [free]: e.g. FEMA/CERT training videos, old Army training films (public domain). Sizes vary; cherry-pick.
- **Podcasts/audio** — [free/build]: audio is cheap (~30 MB/hr at 64 kbps Opus). Grab full back-catalogs of survival/medical podcasts via RSS + script [build]. Librivox public-domain audiobooks [free] direct download.

## 5. Kiwix ZIM catalog (verified on lb.download.kiwix.org, 2026-09)

All **[free]**, base URL `https://download.kiwix.org/zim/<project>/`:

| ZIM | Latest file | Size |
|---|---|---|
| Wikipedia EN full + images | `wikipedia_en_all_maxi_2026-08.zim` | **119 GB** |
| Wikipedia EN no images | `wikipedia_en_all_nopic_2026-06.zim` | 49 GB |
| Wikipedia EN mini (intros) | `wikipedia_en_all_mini_2026-06.zim` | 12 GB |
| Wikipedia EN medicine (WikiMed) | `wikipedia_en_medicine_maxi_2026-04.zim` | 2.1 GB |
| WikiMed nopic / mini | `..._nopic_2026-04` / `..._mini_2026-04` | 822 MB / 155 MB |
| Simple English Wikipedia | `wikipedia_en-simple_all_maxi_2026-06.zim` | 3.3 GB |
| Wikibooks EN | `wikibooks_en_all_maxi_2026-04.zim` | 5.8 GB (nopic 3.3 GB) |
| Wikiversity EN | `wikiversity_en_all_maxi_2026-05.zim` | 2.3 GB (nopic 1.5 GB) |
| iFixit EN | `ifixit_en_all_2025-12.zim` | 3.3 GB |
| Project Gutenberg EN | `gutenberg_en_all_2025-11.zim` | **206 GB** |
| Appropedia | `appropedia_en_all_maxi_2026-02.zim` | 555 MB |
| Energypedia | `energypedia_en_all_maxi_2026-06.zim` | 763 MB |
| Post-disaster collection | `zimgit-post-disaster_en_2024-05.zim` | 615 MB |
| Medicine collection (zimgit) | `zimgit-medicine_en_2024-08.zim` | 67 MB |
| Knots | `zimgit-knots_en_2024-08.zim` | 27 MB |
| Water purification | `zimgit-water_en_2024-08.zim` | 20 MB |
| Food preparation | `zimgit-food-preparation_en_2025-04.zim` | 93 MB |
| TruePrepper site archive | `trueprepper.com_en_all_2026-05.zim` | 1.3 GB |
| TED all talks | `ted_mul_all_2026-05.zim` | 82 GB |

- **wikiHow**: `/zim/wikihow/` now returns 404 — Kiwix no longer distributes fresh wikiHow ZIMs (moderate confidence). Last known builds (~2023, EN maxi ≈ 50 GB) circulate on archive.org mirrors — [free but stale]; verify before relying on it.
- Gutenberg at 206 GB is the budget-eater; the books track may prefer a curated subset instead.

### Suggested core bundle (~200 GB before maps/media)

Wikipedia maxi 119 GB + WikiMed 2 GB + Wikibooks 5.8 GB + Wikiversity 2.3 GB + iFixit 3.3 GB + Appropedia/Energypedia/zimgit set ~2.2 GB + Simple EN 3.3 GB ≈ **138 GB**, leaving room for PMTiles US extract, Organic Maps/OsmAnd files, LLM models, Piper voices, and a curated video library within 1 TB.

## Sources

- https://download.geofabrik.de/ · https://docs.protomaps.com/basemaps/downloads · https://build.protomaps.com/
- https://www.usgs.gov/faqs/can-i-get-a-bulk-order-usgs-topographic-maps-pdf-format-a-state-or-entire-country
- https://lb.download.kiwix.org/zim/ (wikipedia, other, wikibooks, wikiversity, ifixit, gutenberg, ted directories)
- https://github.com/LibreTranslate/LibreTranslate · https://github.com/argosopentech/argos-translate
- https://plants.usda.gov/downloads · https://dailymed.nlm.nih.gov/dailymed/spl-resources-all-drug-labels.cfm
- https://www.nlm.nih.gov/pubs/techbull/so21/so21_rximage_api_old.html · https://datadiscovery.nlm.nih.gov/Drugs-and-Chemicals/Computational-Photography-Project-for-Pill-Identif/5jdf-gdqh
- https://www.repeaterbook.com/repeaters/downloads/CHIRP/ · https://www.arrl.org/band-plan
- https://www.howtogeek.com/osmand-maps-offline-maps-put-google-maps-to-shame/ (OsmAnd/Organic sizes)
