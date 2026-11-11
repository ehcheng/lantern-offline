# Lantern Library — License Manifest

This unit contains third-party content with license obligations. **Household units need no action.** Units that leave the household fall into two classes:

- **GIFTED** (no money changes hands): keep this file and the Llama license
  texts in place. Nothing needs removing.
- **SOLD**: strip the restricted items named below from the copy BEFORE it
  is written to the new unit, then rebuild the frontend so indexes and links
  regenerate without them. The strip script (`strip_restricted.sh <data-root> sold`)
  is kept with the build tools; it is not part of this library.

## Obligations by content class

### AI models — Meta Llama (tools/models/)

Built with Llama.

- `Llama-3.2-3B-Instruct-Q4_K_M.gguf` — Llama 3.2 Community License
  (see `tools/models/LICENSE-llama-3.2.txt`, shipped verbatim)
- `Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf` — Llama 3.1 Community License
  (see `tools/models/LICENSE-llama-3.1.txt`, shipped verbatim)

Redistribution (gift or sale) is permitted provided the license text ships
with the model and derivative works display "Built with Llama". Both
conditions are satisfied by keeping this file and the two LICENSE files.

### Maps: OpenStreetMap, Protomaps, MapLibre

Applies to `maps/` and `map.html`.

- Map data in `maps/` (Organic Maps .mwm, OsmAnd .obf.zip, Geofabrik extracts) and
  the whole-planet PMTiles basemap are made from OpenStreetMap data,
  © OpenStreetMap contributors, Open Database License (ODbL) 1.0. Keep the
  attribution visible wherever the map is shown (map.html does) and, if the
  data is changed and passed on, pass it on under the same license.
- The PMTiles basemap was built with Protomaps (its tile schema and build
  tools, BSD-3-Clause). Protomaps asks for the credit "Protomaps" next to
  "© OpenStreetMap" on the map; map.html shows both.
- `map.html` renders with MapLibre GL JS 6.10.0 (`_app/vendor/maplibre/`),
  pmtiles 4.5.0 (`_app/vendor/pmtiles/`) and the Protomaps basemap style
  5.7.2 (`_app/vendor/basemaps.js`), all BSD-3-Clause. The script files carry
  only a one-line pointer to the license online, so the notice is given here.
  MapLibre GL JS: copyright MapLibre contributors; it contains code from
  mapbox-gl-js v1.13 and earlier, copyright Mapbox. pmtiles and the basemap
  style: copyright Protomaps LLC. The terms, the same for all three, follow.

BSD 3-Clause terms for MapLibre GL JS, pmtiles and the Protomaps basemap style: Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met: (1) Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer. (2) Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution. (3) Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The full license texts are in the same folders as the scripts (see "Site software and fonts" below). The source repository lists the version, download address and license of each one in `sources.json`.

Gift or sale: all three allow redistribution with the attribution kept.

### Site software and fonts (_app/)

The pages are Lantern's own code, under Apache-2.0. They load the third-party parts listed here. The license text for
each part is in the folder named next to it, and every one of these licenses allows giving or selling a copy as long
as the license text stays with it.

- pdf.js 6.3.289 in `_app/vendor/pdfjs/`: Apache-2.0, copyright Mozilla Foundation. License: `LICENSE` in the same folder.
- MapLibre GL JS, pmtiles and the Protomaps basemap style: BSD-3-Clause, terms above. Licenses:
  `_app/vendor/maplibre/LICENSE.txt`, `_app/vendor/pmtiles/LICENSE` and `_app/vendor/basemaps-LICENSE.md`.
- Map labels in `_app/vendor/basemaps-assets/fonts/`: Noto Sans glyphs, SIL Open Font License 1.1. License: `OFL.txt`.
- Map icons in `_app/vendor/basemaps-assets/sprites/`: based on the Mapzen tangrams icons, MIT. License: `LICENSE.md`.
- Page fonts in `_app/fonts/` (Newsreader, Atkinson Hyperlegible, Libre Baskerville): SIL Open Font License 1.1.
  Each family has its own `*-OFL.txt`.
- Search in `_app/pagefind/` and the `pagefind` tool: Pagefind 1.5.2, MIT. License: `_app/vendor/pagefind-LICENSE`.

### Hesperian health guides (mirrors/hesperian/)

Hesperian Health Guides open-copyright terms are **noncommercial**:
reproduction and distribution are allowed for nonprofit purposes only.
GIFTED: OK as-is. SOLD: **must strip** `mirrors/hesperian/` (the strip
script also removes the derived search wrappers under
`_app/text/mirrors/hesperian/`).

### Project Gutenberg (zim/gutenberg_en_all_2025-11.zim)

The texts are public domain in the US, but "Project Gutenberg" is a
registered trademark: selling copies that carry the trademark requires
complying with the PG license (including royalties) or removing the
trademark. Removing it from a ZIM is impractical. GIFTED: OK (free
redistribution is expressly permitted). SOLD: **must strip** the ZIM.

### Public-domain collections — no obligations

LibriVox audiobooks (audio/librivox), Prelinger films (video/prelinger),
NOAA charts, USGS topo/NAIP imagery, US military field manuals: public
domain, no restrictions on gift or sale.

### G2 shelves (docs/sanitation, docs/comms, docs/emergency_mgmt) — added 09-19

Mostly US-government public domain (FEMA, CISA, USGS, CGS, military, GPO,
EPA, NCVEC-declared-PD exam pools) or free humanitarian publications
(WHO/WEDC CC BY-NC-SA, CAWST copy-freely, Eawag/GWC compendia, Sphere
CC BY-NC, Hesperian open copyright NC). Household + GIFTED: all fine with
notices. In the SOLD strip list: ARRL ARES manual (ARRL (c)), ITU Morse
recommendation (ITU (c)), UC ANR wildfire guide (UC Regents, redistribution
restricted), Fire Safe Marin guide (license unstated), Hesperian
environmental-health book (NC). KB6NU study guide is free-distributed by
the author; ECA earthquake booklets are free public-education — both fine
gifted, review if sold. The full provenance notes (candidates, review, gap
fills) are kept with the build tools.

### R6 content (docs/grain_processing, docs/textiles, docs/security, docs/death_care, additions to docs/medical, docs/energy, docs/homesteading_extension) — added 09-19

US-government public domain bulk: FAO (open) and US Extension (USDA/land-grant/state universities): ksu, ndsu, uiuc, uaf, uark, osu, clemson, texas4h, unh, purdue — all US public domain or freely-redistributable extension publications. CISA and DHS files (docs/security): US government public domain. DOJ COPS materials: US government public domain. Neighborhood Watch Manual: US government (LEAA 1986) public domain. PAHO/WHO/ICRC/IFRC dead bodies field manual: CC BY-NC-SA (humanitarian). CDP grief/bereavement toolkit: free public education distribution. WHO AFRO IPC guidance: open WHO publication. IRENA off-grid guidebook (docs/energy): CC BY-NC-SA 4.0, noncommercial. Household + GIFTED: all fine with notices.

CC/nonprofit items to review if SOLD:
- `docs/energy/irena_remote_communities_offgrid_2023.pdf` — CC BY-NC-SA 4.0 (noncommercial)
- `docs/death_care/paho_who_icrc_dead_bodies_field_manual_2016.pdf` — CC BY-NC-SA
- `docs/medical/` IASC, UNHCR, WHO, Sphere MHPSS additions — CC BY-NC-SA variants

Interweave Press (strip on SOLD):
- `docs/textiles/interweave_spinning_beginners.pdf` — © Interweave Press; free PDF but no open redistribution license. Added to strip_restricted.sh sold-list.

Headington Institute (re-check flag):
- `docs/medical/headington_going_the_distance.pdf` — Headington Institute (org wound down 2025). Free use stated; no redistribution restriction found at download. Re-verify status periodically as org is defunct.
- `docs/medical/headington_trauma_critical_incident.pdf` — Same as above.

### ⚠ Not yet cleared for SALE — review before selling any unit

- `docs/medical/` WHO publications are typically CC BY-NC-SA
  (noncommercial); MSF and Hesperian PDFs similar. A SOLD unit likely needs
  these stripped or individually cleared — NOT yet enumerated in the strip
  list. Review docs/medical, docs/water, and the mirrors before any sale.
- Kolibri lesson channels (Khan Academy CC BY-NC-SA, CK-12 custom NC
  license, EngageNY CC BY-NC-SA): noncommercial terms — same review needed.
  The channel files live in Kolibri's own data folder, which the web server does not serve.
- `video/khan_academy/` (Khan Academy videos, CC BY-NC-SA): noncommercial,
  same review needed.
- OpenStax (CC BY) and GDL (mostly CC BY/CC BY-NC mixed) vary per item.

Practical summary: **gifting a unit is clean** (everything above permits
noncommercial redistribution with the shipped notices). **Selling a unit is NOT clean yet** — the strip list covers the three named classes (Hesperian,
Gutenberg trademark, Llama notice compliance), but the NC-licensed medical
docs and Kolibri channels still need per-item clearance or stripping.
