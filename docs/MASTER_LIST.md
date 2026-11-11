# MASTER LIST — Offline Survival Library (Canonical Requirements)

Synthesized 2026-09-14 from `docs/products/products.md`, `docs/content/domains.md`, `docs/content/books.md`, `docs/content/digital.md`. One row per resource; where sources disagreed, the verified 2026 size from `digital.md` wins, then `domains.md`, then `products.md`.

Red-team findings (`the private test record`, 2026-09-14) folded in: all 9 MUST-FIX + all SHOULD-FIX items. See §2.15 (safety build items), Tier 0 (§4), quarantine flags inline.

Status legend:  

- **FREE-DL** — legally free direct download
- **BUY** — purchase (print or DRM-free ebook)
- **SCAN** — out of print / DRM-locked; acquire used print and scan
- **BUILD** — requires local scripting/assembly (mirrors, extracts, curation)
- **DONE** — already acquired (nothing yet)

---

## 1. Executive Summary

**Total library size:** ~200–215 GB (Tier 1 core) → ~700–720 GB (Tier 2 full) → ~1.25 TB (Tier 3 worst case). Storage spec: **2 TB minimum / 4 TB reference** (reconciled with serving_box.md; also absorbs GB-vs-GiB ~7% squeeze). A designed **Tier 0 printed core** (§4) survives box/SSD/power/client failure.

**Total cost estimate:**  

- Digital content: **$0** (everything digital is free or public domain; the only paid digital items are optional DRM-free ebooks)
- Purchase layer (print + ebook): **~$340 core / ~$1,180 core+extended / ~$3,795 everything** (see §6)
- Hardware excluded from this document — EXCEPT client devices: 2 cheap Android tablets, stored in the Faraday box with all of the other electronics, preloaded with Kiwix app + WikiMed + Organic Maps (library survives box death; phone fleet degrades to zero over years), plus a 12V charging path. ~$200. Content-access dependency, same class as the SSD.

**Why this beats Prepper Disk ($199–279, 256–512 GB) and SurvivalNet ($89–499, ~700 GB):**  

- **Same substrate, better curation.** Both products are Kiwix ZIMs + Pi. Every ZIM they ship is on this list, free, and in a fresher release (their snapshots are one-time; ours can refresh quarterly).
- **Global maps with routing.** Prepper Disk covers NA/EU/Oceania browser tiles only; neither ships turn-by-turn. This list stages PMTiles for browser + Organic Maps `.mwm` and OsmAnd `.obf` files for sideloaded phone routing — the gap every HN critic named.
- **Vetted vs. bulk.** SurvivalNet's 232 GB Survivor Library is unvetted 1800s scans; this list puts curated, safety-current sources first (2015 USDA canning, Hesperian 2025, current WHO/MSF, Borden Institute) and demotes bulk PDF dumps to Tier 3.
- **Real medical depth.** Products ship "50,000 NLM articles"; this list adds the full Hesperian library, MSF clinical guidelines, Emergency War Surgery, SOF Medical Handbook, DailyMed drug labels, and a purchased austere-medicine shelf (Alton, Auerbach) no commercial box includes.
- **Education, translation, TTS, celestial nav, and datasets** (pill ID, climate normals, ephemeris) — absent from every commercial product surveyed.
- **Longevity plan:** SSD-class storage + checksummed manifest vs. their unpowered-SD-card data-rot risk.

---

## 2–3. Content Inventory (deduplicated, one row per resource)

ZIM base URL: `https://download.kiwix.org/zim/` (mirror: `lb.download.kiwix.org`). Sizes verified 2026-09 where exact.

### 2.1 General Reference (backbone)

| Resource | Source | Size | Status | Tier |
|---|---|---|---|---|
| Wikipedia EN full w/ images | `wikipedia_en_all_maxi_2026-08.zim` | 119 GB | FREE-DL | 1 |
| Wikipedia EN medicine (WikiMed/MDWiki) | `wikipedia_en_medicine_maxi_2026-04.zim` | 2.1 GB | FREE-DL | 1 |
| Simple English Wikipedia | `wikipedia_en-simple_all_maxi_2026-06.zim` | 3.3 GB | FREE-DL | 1 |
| Wikibooks EN | `wikibooks_en_all_maxi_2026-04.zim` | 5.8 GB | FREE-DL | 1 |
| Wikiversity EN | `wikiversity_en_all_maxi_2026-05.zim` | 2.3 GB | FREE-DL | 1 |
| Appropedia (appropriate tech) | `appropedia_en_all_maxi_2026-02.zim` | 555 MB | FREE-DL | 1 |
| zimgit-post-disaster | `zimgit-post-disaster_en_2024-05.zim` | 615 MB | FREE-DL | 1 |
| zimgit-knots | `zimgit-knots_en_2024-08.zim` | 27 MB | FREE-DL | 1 |
| TruePrepper site archive | `trueprepper.com_en_all_2026-05.zim` | 1.3 GB | FREE-DL | 1 |
| Wiktionary EN | `wiktionary_en_all_nopic_2026-08.zim` (no maxi variant exists) | ~7 GB | FREE-DL | 2 |
| Wikisource EN | `wikisource_en_all_maxi` | ~15 GB | FREE-DL | 2 |
| Wikivoyage EN | `wikivoyage_en_all_maxi` | ~1 GB | FREE-DL | 2 |
| Project Gutenberg EN | `gutenberg_en_all_2025-11.zim` | **206 GB** | FREE-DL | 2 |
| ~~wikiHow EN ZIM~~ — CUT: confirmed dead 2026-09-14, no EN version anywhere (not merely stale). Drop wikiHow-parity claim vs Prepper Disk; Appropedia + zimgit + TruePrepper cover the ground | — | — | CUT | — |
| Stack Exchange picks (DIY, electronics, ham, gardening, outdoors, medical sci, physics, chem) | `zim/stack_exchange/` per-site | ~15 GB total | FREE-DL | 2 |
| The Knowledge — Dartnell (framing book) | buy print/ebook, ~$17 | — | BUY | 2 |
| Back to Basics — Gehring | buy print ~$18 | — | BUY | 3 |
| Country Wisdom & Know-How — Storey | buy print ~$20 | — | BUY | 2 |
| When Technology Fails — Stein | buy print ~$35 | — | BUY | 3 |
| Survivor Library (15k historical trade PDFs) [QUARANTINE — serve under "HISTORICAL — never use for food preservation or drug dosing" section] | archive.org/details/survival.library | 150–232 GB (unverified) | FREE-DL | 3 |
| CD3WD full set | archive.org/details/CD3WD12 + 2012 DVD set | ~13 GB | FREE-DL | 3 |
| The Ark torrent (~238 GB) | community torrent | — | SKIP — overlaps Survivor Library, provenance mixed | — |
| awesome-survival index (checklist only) | github.com/alx-xlx/awesome-survival | <1 MB | FREE-DL | 1 |

### 2.2 Medical

| Resource | Source | Size | Status | Tier |
|---|---|---|---|---|
| New Where There Is No Doctor, Advance Chapters (revisions 2015-2023): 17 chapter PDFs in library/docs/medical/hesperian_where_there_is_no_doctor/, per-chapter revision dates in library/BINDER_1_TOC.md (D6, 2026-10-09). NOTE: Hesperian email-gates the full book PDF since ~2022; manual form submission per title | hesperian.org/books-and-resources/ | ~25 MB | FREE-DL (gated) | 1 |
| Where There Is No Dentist | hesperian.org (en_dent_2025 chapter PDFs, merged; 2010 replaced 2026-09-28) | 25 MB | FREE-DL | 1 |
| Where Women Have No Doctor + A Book for Midwives | hesperian.org | ~60 MB | FREE-DL | 1 |
| Full remaining Hesperian library + HealthWiki dumps | languages.hesperian.org | ~500 MB | FREE-DL | 1 |
| Where There Is No Psychiatrist — Patel 2nd ed. | Cambridge/RCPsych free PDF | ~10 MB | FREE-DL | 1 |
| WHO set: MCPC, Pocket Book Hospital Care for Children, Surgical Care at District Hospital, Model Formulary [HISTORICAL — 2008, quarantine per §2.15], IMCI [chart booklet 2014 edition, ISBN 9789241506823, fetched 2026-10-06 from https://iris.who.int/server/api/core/bitstreams/dfe9634a-da9b-46bb-a1eb-1b5faa09ff63/content (IRIS item 10665/104772), 80 pp, 5.3 MB; 2008 printing moved to the private test record, mhGAP 2.0, Psychological First Aid, Drinking-water Quality 4th | who.int/iris | ~500 MB | FREE-DL | 1 |
| PAHO/WHO Management of Dead Bodies After Disasters | paho.org free PDF | ~20 MB | FREE-DL | 1 |
| WHO/IPCS poisoning guides (Management of Poisoning, pesticide/chemical guides) | who.int free | ~100 MB | FREE-DL | 1 |
| Goldfrank's Toxicologic Emergencies (optional depth) | buy ~$200 | — | BUY | 3 |
| Contraception/family planning: WHO Family Planning Global Handbook + Hesperian coverage (LAM, fertility awareness, existing IUD/implant management) | who.int / hesperian.org | ~50 MB | FREE-DL | 1 |
| Spanish core: WTIND ES + Hesperian ES set + WikiMed ES | hesperian.org / kiwix | ~3 GB | FREE-DL | 1 |
| MSF guides: Clinical Guidelines, Essential Drugs, Obstetrics, TB | medicalguidelines.msf.org | ~200 MB | FREE-DL | 1 |
| ~~MedlinePlus ZIM~~ — DOES NOT EXIST on Kiwix (source-map verified 2026-09-14); WikiMed + purchased shelf covers | — | — | CUT | — |
| zimgit-medicine | `zimgit-medicine_en_2024-08.zim` | 67 MB | FREE-DL | 1 |
| Emergency War Surgery (5th US rev.) | medcoe.army.mil / archive.org | ~100 MB | FREE-DL | 1 |
| SOF Medical Handbook 2nd ed. (2008, PD) [HISTORICAL banner — pre-2010 tourniquet doctrine; current TCCC governs] | archive.org; current ed. jsomonline.org [BUY] | ~100 MB | FREE-DL | 1 |
| Ranger Medic Handbook (2007 free; 2025 ed. ~$20) | archive.org / jsomonline.org | ~50 MB | FREE-DL | 1 |
| TCCC Guidelines + Quick Reference | deployedmedicine.com (free account) | ~100 MB | FREE-DL | 1 |
| FM 4-25.11 First Aid, TC 4-02.1, combat-medic materials | archive.org/details/civilian-and-non-civilian-medical-guides, irp.fas.org | ~2 GB | FREE-DL | 1 |
| ST 31-91B (1982) [QUARANTINE — 1982 drug protocols, HISTORICAL section only] | archive.org | ~100 MB | FREE-DL | 3 |
| Borden Institute Textbooks of Military Medicine | medcoe.army.mil | ~2 GB | FREE-DL | 2 |
| Red Cross First Aid/CPR/AED participant manual | Red Cross Store (verified NOT free — official manuals are paid; free copies are IA-lending/old-edition strays) | — | BUY ~$10 (or drop; WTIND+FEMA covers) | 1 |
| Gray's Anatomy 1918 (PD) | bartleby.com/107 / archive.org | ~200 MB | FREE-DL | 3 |
| FDA DailyMed SPL full release (all US drug labels) | dailymed.nlm.nih.gov | 10–20 GB | FREE-DL | 2 |
| The Survival Medicine Handbook — Alton 4th ed. | buy ~$40 | — | BUY | 1 |
| Oxford Handbook of Clinical Medicine 11th | buy ~$60 (DRM) | — | BUY/SCAN | 2 |
| Auerbach's Wilderness Medicine 7th (2 vol) | buy ~$250 | — | BUY/SCAN | 3 |
| Improvised Medicine — Iserson 2nd | buy ~$50 | — | BUY | 3 |
| NOLS Wilderness Medicine — Schimelpfenig | buy ~$17 | — | BUY | 3 |
| Ditch Medicine — Coffee (Paladin defunct) | used ~$25–60, scan | — | SCAN | 3 |
| Bushcraft First Aid — Canterbury | buy ~$16 | — | BUY | 3 |
| Sanford Guide to Antimicrobial Therapy | buy ~$60 | — | BUY | 3 |
| Tarascon Pharmacopoeia (current ed. — THE dosing reference; promoted from Tier 3 per red team) | buy ~$25 | — | BUY | 1 |
| Harriet Lane Handbook (pediatric dosing — replaces the deleted DIY dosing-table BUILD) | buy ~$45 | — | BUY | 1 |
| Merck Manual (print, Professional or Home) | buy ~$65; old eds used/scan | — | BUY | 3 |
| Heart and Hands — Davis 5th (midwifery) | buy ~$25 | — | BUY | 2 |
| Emergency Childbirth — White | buy ~$10 | — | BUY | 2 |
| Ina May's Guide to Childbirth | buy ~$15 | — | BUY | 3 |
| Nelson Essentials of Pediatrics | buy ~$70 | — | BUY | 3 |
| Helping Babies Breathe (AAP) — verified NOT free (account-gated AAP product); buy or rely on WHO Pocket Book + midwifery shelf | aap.org | — | BUY (~$20) | 2 |
| Herbal shelf: Gladstar Medicinal Herbs ($15) + Herbal Recipes ($20), Hutchens ($16), Green Medicine-Maker's ($22), Peterson Medicinal Plants ($21) | buy print | — | BUY | 2 |
| SAMHSA disaster behavioral health pubs | samhsa.gov | ~100 MB | FREE-DL | 2 |
| Mental-health shelf: Feeling Good, Body Keeps the Score, Man's Search for Meaning, Deep Survival | buy ~$60 total | — | BUY | 3 |

### 2.3 Food / Preservation / Foraging / Agriculture

| Resource | Source | Size | Status | Tier |
|---|---|---|---|---|
| USDA Complete Guide to Home Canning (2015 rev. ONLY) | nchfp.uga.edu/resources/category/usda-guide | ~50 MB | FREE-DL | 1 |
| NCHFP full site mirror | wget nchfp.uga.edu | ~1 GB | BUILD | 1 |
| zimgit-food-preparation | `zimgit-food-preparation_en_2025-04.zim` | 93 MB | FREE-DL | 1 |
| FAO document repository picks + Better Farming Series | fao.org/documents (also in CD3WD) | ~2 GB | FREE-DL | 2 |
| USDA/extension service PDFs (canning, livestock, gardening) | state extension sites | ~2 GB | BUILD | 2 |
| Five Acres and Independence — Kains (PD/Dover $12) | archive.org or Dover print | ~50 MB | FREE-DL | 3 |
| FM 21-76 edible-plants chapter + Army Illustrated Guide to Edible Wild Plants [SUPPLEMENT ONLY — B&W plates inadequate for positive ID; water hemlock/wild parsnip lookalike is fatality-grade; UI banner: "no positive multi-feature ID = don't eat"] | archive.org (PD) | ~100 MB | FREE-DL | 3 |
| Ball Blue Book Guide to Preserving 38th ed. | buy ~$15 | — | BUY | 1 |
| Encyclopedia of Country Living — Emery 50th | buy ~$28 | — | BUY | 1 |
| Seed to Seed — Ashworth | buy ~$25 | — | BUY | 2 |
| Self-Sufficient Life — Seymour | buy ~$30 | — | BUY | 2 |
| Mini Farming — Markham | buy ~$15 | — | BUY | 2 |
| Backyard Homestead — Madigan | buy ~$19 | — | BUY | 3 |
| Gaia's Garden — Hemenway | buy ~$30 | — | BUY | 3 |
| Resilient Farm and Homestead — Falk | buy ~$40 | — | BUY | 3 |
| Square Foot Gardening + New Seed-Starters Handbook | buy ~$40 | — | BUY | 3 |
| Thayer trilogy (Forager's Harvest, Nature's Garden, Incredible Wild Edibles) | buy ~$70 | — | BUY | 2 |
| Peterson Edible Wild Plants (region) — PRIMARY foraging reference (promoted; FM 21-76 plates demoted to supplement) | buy ~$21 | — | BUY | 1 |
| Mushrooms Demystified + All That the Rain Promises — Arora [UI: mushrooms expert-gated] | buy ~$55 | — | BUY | 3 |
| Butchering: Mettler ($17) + Hasheider Complete Book ($25) | buy print | — | BUY | 3 |
| Root Cellaring — Bubel | buy ~$17 | — | BUY | 3 |
| Preserving Food without Freezing or Canning | buy ~$25 | — | BUY | 3 |
| Art of Fermentation — Katz | buy ~$40 | — | BUY | 3 |
| Foxfire vols 1–3 [food-preservation chapters QUARANTINE — pre-modern canning is dangerous; craft/skills chapters fine] | buy used ~$48 | — | BUY | 3 |
| Storey's Guides (chickens, goats, + species kept) | buy ~$20/vol (×3) | — | BUY | 2 |
| Beekeeper's Handbook — Sammataro | buy ~$30 | — | BUY | 3 |
| Veterinary: Merck Vet Manual ($65), Where There Is No Animal Doctor ($40), Keeping Livestock Healthy ($20) | buy print | — | BUY | 3 |
| Where There Is No Vet — Forse | used, patchy | — | SCAN | 3 |
| FAO primary animal health care manuals | fao.org | ~200 MB | FREE-DL | 2 |
| USDA PLANTS checklist CSV | plants.usda.gov/downloads | 7 MB | FREE-DL | 1 |
| Edible/poisonous plant image set | Wikimedia Commons scrape + FM 21-76 plates | ~5 GB | BUILD | 3 |

### 2.4 Water & Sanitation

| Resource | Source | Size | Status | Tier |
|---|---|---|---|---|
| zimgit-water | `zimgit-water_en_2024-08.zim` | 20 MB | FREE-DL | 1 |
| EPA Emergency Disinfection of Drinking Water | epa.gov | <10 MB | FREE-DL | 1 |
| CAWST biosand/HWT library | resources.cawst.org | ~500 MB | FREE-DL | 1 |
| SODIS manual + WHO Slow Sand Filtration | sodis.ch, who.int | ~50 MB | FREE-DL | 1 |
| Texas Manual on Rainwater Harvesting | TWDB free PDF | ~10 MB | FREE-DL | 1 |
| FM 10-52 Water Supply | PD, archive.org | ~50 MB | FREE-DL | 1 |
| EMAS well manuals + RWSN/SKAT hand-drilling | free PDFs | ~200 MB | FREE-DL | 2 |
| Humanure Handbook (3rd ed. free; 4th $25) | humanurehandbook.com | ~30 MB | FREE-DL | 1 |
| Rainwater Harvesting for Drylands v1–2 — Lancaster | buy ~$60 | — | BUY | 3 |
| Prepper's Water Survival Guide — Luther | buy ~$16 | — | BUY | 3 |
| Water for Every Farm — Yeomans | buy ~$35 | — | BUY | 3 |

### 2.5 Shelter & Construction

| Resource | Source | Size | Status | Tier |
|---|---|---|---|---|
| USDA Wood Handbook (FPL-GTR-282) | fpl.fs.usda.gov | ~50 MB | FREE-DL | 1 |
| Army: FM 5-426 Carpentry, FM 3-34.471 Plumbing, FM 5-428 Concrete/Masonry, FM 5-34 Engineer Field Data, FM 5-103 Survivability | armypubs / archive.org | ~1 GB | FREE-DL | 1 |
| Shelters, Shacks and Shanties — Beard 1914 (PD) + log/cob classics | archive.org | ~200 MB | FREE-DL | 2 |
| The Owner-Built Home — Kern | circulates free / scan | ~50 MB | FREE-DL | 3 |
| IRC (International Residential Code) | free read-only codes.iccsafe.org; PDF buy; older eds circulate | ~100 MB | FREE-DL/BUY | 3 |
| B&D Complete Guide to Wiring 8th + Plumbing | buy ~$60 | — | BUY | 2 |
| Building Construction Illustrated — Ching 6th | buy ~$50 | — | BUY | 3 |
| Hand-Sculpted House + Earthbag Building | buy ~$60 | — | BUY | 3 |
| A Pattern Language + Shelter (Kahn) | buy ~$85 | — | BUY | 3 |

### 2.6 Energy / Solar / Electrical

| Resource | Source | Size | Status | Tier |
|---|---|---|---|---|
| Energypedia ZIM | `energypedia_en_all_maxi_2026-06.zim` | 763 MB | FREE-DL | 1 |
| US Navy NEETS (24 modules, PD) | free PDFs | ~500 MB | FREE-DL | 1 |
| FEMA wood-gas generator (1989, PD) | free PDF | <10 MB | FREE-DL | 1 |
| Battery University site mirror | batteryuniversity.com | ~500 MB | DROPPED 2026-11-10: a crawl of a copyrighted site, not redistributable | 2 |
| Scoraigwind free plans + Appropedia/CD3WD microhydro | free | ~100 MB | FREE-DL | 2 |
| NFPA 70 (NEC) | free read-only nfpa.org; PDF buy | — | BUY (optional) | 3 |
| Solar Electricity Handbook — Boxwell | buy ~$25 | — | BUY | 2 |
| SEI Photovoltaics: Design & Installation | buy ~$60 (DRM-free PDF offered) | — | BUY | 2 |
| Practical Electronics for Inventors 4th | buy ~$35 | — | BUY | 2 |
| Art of Electronics 3rd | buy ~$130 (DRM) | — | BUY/SCAN | 3 |
| 12V: Wiring 12 Volts for Ample Power + 12-Volt Bible | buy used ~$50 | — | BUY | 3 |
| Piggott Wind Turbine Recipe Book | buy ~$15 DRM-free PDF | — | BUY | 2 |
| Micro-Hydro Design Manual — Harvey | buy ~$70 | — | BUY | 3 |
| Alcohol Can Be a Gas (Blume) + From the Fryer to the Fuel Tank (Tickell) | buy ~$70 | — | BUY | 3 |
| Journey to Forever site mirror (biofuels) | journeytoforever.org | ~500 MB | BUILD | 2 |
| Chemistry: Caveman Chemistry ($30), Home Chemistry Experiments ($30), Soapmaker's Companion ($20) | buy print | — | BUY | 3 |
| CRC Handbook | skip — Wikipedia data pages suffice | — | SKIP | — |

### 2.7 Communications

| Resource | Source | Size | Status | Tier |
|---|---|---|---|---|
| Ham Stack Exchange ZIM | `ham.stackexchange.com_en_all` | ~300 MB | FREE-DL | 1 |
| NCVEC question pools (current) | ncvec.org | <10 MB | FREE-DL | 1 |
| ARRL band plan PDF | arrl.org/band-plan | <5 MB | FREE-DL | 1 |
| RepeaterBook CHIRP CSV exports (state/region) | repeaterbook.com/repeaters/downloads/CHIRP/ | <100 MB | FREE-DL | 1 |
| FCC ULS weekly dump (callsigns) | fcc.gov/uls | ~1 GB | FREE-DL | 2 |
| FM 24-19 Radio Operator's Handbook, TC 9-64 | PD | ~100 MB | FREE-DL | 1 |
| Meshtastic + AREDN docs mirrors; installers (Meshtastic fw, fldigi, JS8Call, Winlink) | project sites | ~2 GB | BUILD | 1 |
| NVIS/wire-antenna papers, AmRRON free guides | free PDFs | ~100 MB | FREE-DL | 2 |
| ARRL Tech + General license manuals (current pool) | buy ~$33 ea | — | BUY | 1 |
| ARRL Handbook (recent used ed. ~$30; new $60–90) | buy | — | BUY | 2 |
| ARRL Antenna Book | buy ~$50 | — | BUY | 3 |
| ARRL Operating Manual | buy ~$30 | — | BUY | 2 |
| ARRL EmComm Handbook (2006, OOP) | used ~$10 → scan, or substitute Operating Manual | — | SCAN | 3 |

### 2.8 Repair / Mechanical / Trades

| Resource | Source | Size | Status | Tier |
|---|---|---|---|---|
| iFixit EN ZIM | `ifixit_en_all_2025-12.zim` | 3.3 GB | FREE-DL | 1 |
| TM 9-8000 Principles of Automotive Vehicles (PD) | archive.org | ~200 MB | FREE-DL | 1 |
| TC 9-237 Welding Theory and Application (PD) | archive.org | ~100 MB | FREE-DL | 1 |
| Practical Blacksmithing (Richardson 1889, PD) + Survivor Library trades shelves | archive.org | in Survivor Lib | FREE-DL | 3 |
| Sheldon Brown bicycle site mirror | sheldonbrown.com | ~1 GB | BUILD | 2 |
| Canvas/textile TMs (TM 10-269 etc., PD) + spinning/weaving PD classics | archive.org | ~500 MB | FREE-DL | 2 |
| Haynes/Chilton manuals (per owned vehicle ×2) | buy ~$30 ea | — | BUY | 1 |
| Machinery's Handbook 31st | buy ~$110 | — | BUY | 3 |
| Small-engine: B&S official manual ($30) + Roth Small Gas Engines ($60) | buy | — | BUY | 2 |
| Auto Repair for Dummies + How Cars Work | buy ~$40 | — | BUY | 3 |
| Welder's Handbook — Finch | buy ~$25 | — | BUY | 3 |
| Backyard Blacksmith — Sims | buy ~$25 | — | BUY | 3 |
| Park Tool Big Blue Book 4th | buy ~$25 | — | BUY | 2 |
| Sewing/leather: RD Guide to Sewing (used $15), DK Sewing Book ($30), Leatherworking Handbook ($25), Tan Your Hide! ($15) | buy | — | BUY | 3 |

### 2.9 Maps / Navigation / Weather

| Resource | Source | Size | Status | Tier |
|---|---|---|---|---|
| Protomaps PMTiles — US extract (`pmtiles extract`) | build.protomaps.com daily planet | ~25 GB | BUILD | 1 |
| Protomaps PMTiles — full planet z0–15 | build.protomaps.com | 120 GB | FREE-DL | 2 |
| Organic Maps .mwm — full USA (sideload set) — no single-file archive; batch ~60 per-state files (scripted loop; CoMaps alternate) | Organic Maps CDN | 8.3 GB | BUILD | 1 |
| OsmAnd .obf — full US — same: batch per-state/region files | download.osmand.net | 16 GB | BUILD | 1 |
| Geofabrik raw PBF — US (source data for rebuilds) | download.geofabrik.de | 11.3 GB | FREE-DL | 2 |
| USGS US Topo GeoPDF — home state(s) only (full set = 2.8 TB, infeasible) | apps.nationalmap.gov batch | 20–80 GB/state | FREE-DL | 3 |
| NOAA ENC/RNC nautical charts (if coastal) | charts.noaa.gov | ~15 GB | FREE-DL | 3 |
| US National Park maps (63) | NPS, PD | <1 GB | FREE-DL | 2 |
| Satellite imagery, home region (IIAB maps catalog) | github.com/iiab/maps | ~20 GB | FREE-DL | 3 |
| TC 3-25.26 Map Reading and Land Navigation (PD) | armypubs | ~50 MB | FREE-DL | 1 |
| Bowditch — American Practical Navigator (PD) | NGA free PDF | ~100 MB | FREE-DL | 1 |
| JPL DE440s ephemeris + Skyfield + SFalmanac (perpetual nautical almanac) | rhodesmill.org/skyfield | ~150 MB | BUILD | 1 |
| Be Expert with Map and Compass — Kjellström | buy ~$16 | — | BUY | 2 |
| Weather: AC 00-6B Aviation Weather (FAA, PD), FM 34-81-1, NWS Skywarn guides, WMO Cloud Atlas mirror | free | ~500 MB | FREE-DL | 1 |
| NOAA 1991–2020 US Climate Normals (station CSVs) | ncei.noaa.gov | ~3 GB | FREE-DL | 2 |
| Home region packet: county road maps, state hunting/fishing regs, regional venomous species + toxic plant one-pagers, human-readable frost/climate summary (raw CSVs unusable by stressed human) | assemble | ~2 GB | BUILD | 1 |
| Eric Sloane's Weather Book + The Weather Book (Williams) | buy used ~$30 | — | BUY | 3 |

### 2.10 Security / Defense / Gov & Emergency Management

| Resource | Source | Size | Status | Tier |
|---|---|---|---|---|
| Core military FM set: FM 21-76 Survival (+ FM 3-05.70/ATP 3-50.21), FM 21-76-1, Ranger Handbook TC 3-21.76, FM 3-21.8, FM 5-103, ATP 3-37.34, cold/jungle/desert manuals | armypubs.army.mil, irp.fas.org, archive.org bulk dumps | ~5 GB | FREE-DL | 1 |
| FEMA: Are You Ready (P-2064), CERT materials, IS-course PDFs, Food & Water in an Emergency | training.fema.gov, fema.gov | ~2 GB | FREE-DL | 1 |
| Ready.gov site mirror | ready.gov | ~500 MB | BUILD | 1 |
| Nuclear War Survival Skills — Kearny (PD, incl. KFM plans) | oism.org/nwss | ~50 MB | FREE-DL | 1 |
| Fire: structure-fire response, wildfire home hardening/ember zones, chimney fires (NFPA/USFS/state extension PDFs) | nfpa.org, fs.usda.gov, extensions | ~200 MB | FREE-DL | 1 |
| CO + fuel safety (improvised indoor heating kills; sits next to wood-gas plan) | CDC/CPSC free PDFs | <10 MB | FREE-DL | 1 |
| CDC Yellow Book | cdc.gov free | ~100 MB | FREE-DL | 2 |
| MIT Guide to Lock Picking + state hunter-safety manuals | free PDFs | ~50 MB | FREE-DL | 2 |
| Manufacturer armorer's manuals (owned platforms) | manufacturer sites | ~100 MB | FREE-DL | 2 |
| SAS Survival Handbook — Wiseman 3rd | buy ~$18 | — | BUY | 1 |
| Bushcraft 101 — Canterbury | buy ~$13 | — | BUY | 1 |
| Kochanski Bushcraft | buy ~$20 | — | BUY | 3 |
| Prepper's Long-Term Survival Guide — Cobb | buy ~$17 | — | BUY | 2 |
| Reloading: Lyman 51st + Hornady | buy ~$60 | — | BUY | 3 |
| NRA guides / Gun Digest Shooter's Guide | buy ~$40 | — | BUY | 3 |
| A Failure of Civility (OOP, expensive) | used → scan | — | SCAN | 3 |

### 2.11 Education (K-12 → college)

| Resource | Source | Size | Status | Tier |
|---|---|---|---|---|
| Kolibri server + Khan Academy EN channel | learningequality.org | 35–50 GB (video) | FREE-DL | 2 |
| CK-12 channel/ZIM | Kolibri / kiwix | ~10 GB | FREE-DL | 2 |
| OpenStax full textbook library | openstax.org PDFs / Kolibri | ~5 GB | FREE-DL | 2 |
| EngageNY K-12 ELA+math (PD) | Kolibri | ~5 GB | FREE-DL | 2 |
| PhET simulations ZIM | `phet_en` | ~100 MB | FREE-DL | 1 |
| Core Knowledge K-8 curriculum (CKHG/CKLA) | coreknowledge.org free downloads | ~5 GB | FREE-DL | 2 |
| CD3WD primary/junior school DVD set | archive.org/details/2015_cdw3d_primary_junior_school_dvd_set | ~10 GB | FREE-DL | 3 |
| Global Digital Library / African Storybook — young-kids slice promoted (nothing else in Tier 1 serves under-8s under stress) | Kolibri | ~2 GB | FREE-DL | 1 |
| MIT OCW (selected courses) — no Kiwix ZIMs exist (verified 2026-09-14); direct course downloads from ocw.mit.edu instead | ocw.mit.edu per-course zips | ~10 GB | BUILD | 3 |
| Saxon Math or Math-U-See (structured math) | buy ~$100/level set | — | BUY | 3 |

### 2.12 Media

| Resource | Source | Size | Status | Tier |
|---|---|---|---|---|
| TED science subset ZIM | `ted` topic ZIMs (full `ted_mul_all` 82 GB — skip) | 14 GB | FREE-DL | 3 |
| Curated instructional video library — CUT to irreplaceable procedures only (suturing, tourniquet, birth); yt-dlp at 200-hr scale is unreliable (2024+ anti-bot throttling/bans) and weeks of labor; buy/print the rest | YouTube channels — personal-archival gray zone | ~50 GB | BUILD | 3 |
| IA public-domain training films (FEMA/CERT, Army) | archive.org | ~10 GB | FREE-DL | 3 |
| Librivox PD audiobooks + podcast back-catalogs (RSS scrape, ~30 MB/hr Opus) | librivox.org + scripts | ~10 GB | BUILD | 3 |

### 2.13 Datasets

| Resource | Source | Size | Status | Tier |
|---|---|---|---|---|
| DailyMed SPL (see §2.2) — also feeds pill-ID imprint search page | dailymed.nlm.nih.gov | (counted in 2.2) | BUILD | 2 |
| NLM C3PI pill-image dataset — RETIRED (Socrata path also dead, verified 2026-09-14); fall back to text-only imprint search from DailyMed | — | — | CUT (DailyMed text fallback) | — |
| USDA PLANTS CSV (see §2.3) | plants.usda.gov | 7 MB | FREE-DL | 1 |
| NOAA Climate Normals (see §2.9) | ncei.noaa.gov | (counted in 2.9) | FREE-DL | 2 |
| JPL DE440s + Skyfield (see §2.9) | rhodesmill.org | (counted in 2.9) | BUILD | 1 |

### 2.14 Offline Apps / AI (serving layer)

| Resource | Source | Size | Status | Tier |
|---|---|---|---|---|
| kiwix-serve (backbone, full-text search) | kiwix.org | <100 MB | FREE-DL | 1 |
| MapLibre GL JS + static HTTP for PMTiles | docs.protomaps.com | <100 MB | FREE-DL | 1 |
| Calibre-Web (PDF/EPUB shelf for purchased/scanned books) | github | <500 MB | FREE-DL | 1 |
| Kolibri server | learningequality.org | (app only) <1 GB | FREE-DL | 2 |
| llama.cpp / Ollama + 2–3 models (Llama 3.2 3B, Qwen2.5, Phi-3-mini; 7–14B if x86) — with life-safety guardrails: banner + primary-source citation on every answer; block/redirect medical-dose, plant-ID, and canning queries to curated sources (a 3B model WILL invent canning times) | ollama.com / HF GGUF | 5–20 GB | FREE-DL | 1 |
| LibreTranslate + Argos models (5–10 language pairs) | github.com/LibreTranslate | ~1 GB | FREE-DL | 1 |
| Piper TTS + voices | github.com/OHF-Voice/piper1-gpl | ~500 MB | FREE-DL | 1 |
| Static /tools: SunCalc, unit converters, ballistic calc (NO DIY dosing table — deleted per red team; dosing = purchased Tarascon/Harriet Lane + printed licensed card only) | assemble | <100 MB | BUILD | 1 |

### 2.15 Build Items — Serving-Layer Safety (red-team MUST-FIX, 2026-09-14)

| Item | What | Status | Tier |
|---|---|---|---|
| Emergency triage landing page | Symptom-first decision tree (bleeding / not breathing / choking / childbirth / burns / poisoning / hypothermia / broken bone) linking directly to the correct page of the correct CURRENT document; wifi captive-portal landing target. <1 day to build; single highest-leverage item | BUILD | 1 |
| HISTORICAL quarantine UI | Survivor Library, Foxfire food chapters, ST 31-91B, SOF 2008, WHO Formulary 2008 served under a separate "HISTORICAL — never use for food preservation or drug dosing" section/banner; triage page links current sources only | BUILD | 1 |
| Pagefind static index over PDF layer | Life-critical medical layer is PDFs — invisible to Kiwix/Xapian search. Required in MASTER_LIST, not just serving_box.md | BUILD | 1 |
| Operator runbook (non-technical) | Laminated quick-start (power on, join `LIBRARY`, open browser, sections) + "won't turn on" flowchart (swap router, swap SSD, phone + Kiwix app on microSD copy); train second household member — owner-dead scenario currently ends the library | BUILD | 0 |
| Printed dosing card | Weight-band emergency-drug card printed from licensed source (Tarascon/Harriet Lane) | BUILD | 0 |
| Skills-practice checklist | One drilled rep per Tier 1 domain before grid-down (ham QSO, pressure-canning run, tourniquet drill); content without practice is dead weight | BUILD | 0 |

---

## 4. Priority Tiers

Tier assignments are in the inventory tables above. Size roll-up:

| Tier | Contents (delta) | Cumulative size |
|---|---|---|
| **Tier 0 — Paper (survives everything)** | Printed: WTIND, WTIN Dentist, USDA canning 2015, emergency triage tree, water-disinfection card, first-aid quick reference, licensed dosing card, operator runbook. Designed paper core, not an accident of the purchase list | shelf, not disk |
| **Tier 1 — Core** | Wikipedia maxi + WikiMed + core ZIMs (~138 GB), full free medical/canning/water/military/FEMA PDF layer + Spanish core (~20 GB), US maps + home-region packet (PMTiles US + .mwm + .obf ≈ 52 GB), LLM/translate/TTS/tools (~15 GB) | **~215–225 GB** |
| **Tier 2 — Full** | + Gutenberg 206 GB, wikiHow ~50 GB (stale), Wiktionary/Wikisource/Wikivoyage ~23 GB, Stack Exchange ~15 GB, PMTiles planet (+95 GB over US extract), education stack ~70–85 GB, DailyMed ~20 GB, misc datasets/mirrors ~25 GB | **~700–720 GB** |
| **Tier 3 — Max** | + Survivor Library up to 232 GB, CD3WD 13+10 GB, TED science 14 GB, curated video ~50 GB (cut from 150 per red team), state topo ~50 GB, NOAA charts 15 GB, satellite region 20 GB, pill images 10 GB, audio 10 GB, OCW 10 GB | **~1.15–1.25 TB worst case** |

Notes:  

- Storage: **2 TB minimum / 4 TB reference** (per serving_box.md). The old "fit 1 TB" gymnastics are deleted — a 1 TB SSD is 931 GiB and Tier 3 never fit it.
- Gutenberg (206 GB) is the Tier 2 budget-eater; a curated subset (BUILD) recovers ~150 GB if ever needed.
- Kiwix mirrors report GiB; budget in GiB where sources do.

## 5. Flagged Risks & Uncertainties

- **wikiHow ZIM discontinued** — Kiwix `/zim/wikihow/` returns 404; only ~2023 builds circulate on archive.org. Verify integrity before relying on it; a Prepper Disk headline feature we can only match with stale data.
- **Survivor Library size discrepancy** — reported 150–200 GB (archive.org mirror) vs. 232 GB (SurvivalNet manifest). Budget 232 GB worst case; content is unvetted 1800s scans — reference redundancy, not primary guidance.
- **Edition safety for canning** — only the 2015 USDA revision and current Ball Blue Book are safe; older recipes (incl. much of Survivor Library / Foxfire food content) are actively dangerous. Same class of risk: ham license manuals must match the current NCVEC question pool; Nautical Almanac is annual (mitigated by Skyfield perpetual generation); drug references age.
- **LLM hallucination on life-safety advice** — 3B-class local models are convenience search, not authority; UI should label AI answers and link primary sources. (This is the top HN criticism of the commercial boxes.)
- **Legality gray zones** — scanning owned DRM-locked books (Oxford Handbook, Art of Electronics) is personal-use gray area; yt-dlp video archiving likewise; archive.org copies of in-copyright books (SAS, The Knowledge) are lending-only, not downloads; circulating PDFs of Gladstar/ARRL/Alton are pirated — excluded.
- **Data longevity** — SD cards lose data unpowered over years; require SSD + periodic power-up + checksummed manifest.
- **Unverified sizes** — Khan Academy channel (30–50 GB), Hesperian full library, site mirrors (NCHFP, Battery University, Journey to Forever) are estimates; verify at download time. "Ark by Sotera" could not be confirmed to exist.
- **USGS full topo infeasible** — complete US Topo GeoPDF set is ~2.8 TB; state-level only.
- **Mirror-immediately list (takedown/retirement-prone — download week 1, verify checksums):** archive.org user collections (civilian-and-non-civilian-medical-guides, survival.library, FM dumps), TCCC via deployedmedicine.com (account-gated, DoD reorganizes), Survivor Library, NLM C3PI (Socrata bulk path works today; NLM retiring legacy datasets), wikiHow ZIM (verify checksum against known-good hash or CUT and stop claiming wikiHow parity).
- **Battery University mirror** — JS-heavy site; naive wget yields broken mirror. Real BUILD: zimit/browser-based crawl, or substitute static Appropedia/Wikipedia articles.
- **Organic Maps CDN continuity** — project forked (CoMaps) after 2025 governance disputes; snapshot BOTH .mwm sets, note CoMaps as alternate source.
- **RepeaterBook** — ToS reserves export rights + rate limits; CHIRP CSV export has missing-columns bug (#6783). Manual per-state exports via website while logged in, validate in CHIRP; don't script it.
- **SCAN labor is project-scale** — Oxford Handbook ~900 pp, Art of Electronics ~1,200 pp, Auerbach ~2,800 pp = 40+ hr flatbed. Either budget sheet-fed scanner + book destruction, or convert to BUY-print-only, no digital copy.
- **Manifest metadata required** — stamp every item with edition/snapshot date + verify-against note: NCVEC pools rotate 4-yr cycles (ARRL manuals expire as exam prep), DailyMed snapshot date on the pill-ID page, almanac year.
- **Accepted-risk omissions (conscious, documented):** legal/land/statutes (low value-per-GB, changes constantly); herbal shelf stays Tier 2 as adjunct with quarantine framing; personal-use DRM scanning; Gray's 1918 (anatomy stable).

## 6. Purchase List (print + ebook)

> **SUPERSEDED 2026-09-17** — after the full 885 GB build, the live amended list is **`library/PURCHASE_LIST.md`**: ~$120 books (Tarascon, Harriet Lane if kids, Peterson Edible Plants regional) + ~$230 hardware/consumables (tablets, toner). The tiers below are historical; most items dropped as covered by acquired content.

Prices approximate street (2025–26). DRM-free PDF available where noted.

**Digital vs physical split (2026-09-14):** ALL physical/print purchases are DEFERRED until after the full digital build is done — do not re-raise. Groups A/B/C below are the deferred physical list.

**Digital-now purchases** (only items with a usable offline digital edition — Kindle/DRM ebooks excluded, they cannot be served from the box):  

| Item | Format | Price |
|---|---|---|
| Piggott, A Wind Turbine Recipe Book | DRM-free PDF, scoraigwind.co.uk | ~$15 |
| Tarascon Pharmacopoeia app (optional interim until deferred print copy) | iOS/Android app, offline after install — lives on phone, NOT servable from box | ~$3–5/mo |

Everything else in A/B/C is print or DRM-locked ebook → physical/deferred. (Low confidence on a few B/C titles possibly having DRM-free publisher PDFs — verify at purchase time.)

**Group A — Core (Tier 1 buys):**  

| Item | Price |
|---|---|
| Encyclopedia of Country Living (Emery, 50th) | $28 |
| SAS Survival Handbook (Wiseman 3rd) | $18 |
| Ball Blue Book 38th | $15 |
| Survival Medicine Handbook (Alton 4th) | $40 |
| ARRL Technician + General license manuals | $66 |
| Bushcraft 101 (Canterbury) | $13 |
| Haynes/Chilton × 2 owned vehicles | $60 |
| Tarascon Pharmacopoeia (promoted — dosing reference) | $25 |
| Harriet Lane Handbook (pediatric dosing) | $45 |
| Peterson Edible Wild Plants, regional (promoted — primary foraging ID) | $21 |
| Red Cross First Aid/CPR manual (reclassified from FREE-DL) | $10 |
| **Subtotal A** | **~$340** |

**Group B — Extended (Tier 2 buys):** The Knowledge $17, Seed to Seed $25, Seymour $30, Mini Farming $15, Country Wisdom $20, Thayer trilogy $70, Peterson Medicinal $21, Gladstar ×2 $35, Hutchens $16, Green $22, Storey's ×3 $60, Prepper's LT Guide $17, ARRL Handbook (used) $30, ARRL Operating Manual $30, Kjellström $16, B&D Wiring+Plumbing $60, Boxwell Solar $25, SEI PV $60, Practical Electronics $35, Piggott (PDF) $15, B&S + Roth small-engine $90, Park Tool BBB $25, Heart and Hands $25, Emergency Childbirth $10, Oxford Handbook $60, Cobb $17 — **Subtotal B ≈ $840** (A+B ≈ $1,180).

**Group C — Specialist/depth (Tier 3 buys):** Auerbach $250, Machinery's Handbook $110, Art of Electronics $130, Improvised Medicine $50, Iserson/NOLS/Ditch(used)/Bushcraft FA ~$60, Sanford $60, Goldfrank's Toxicology $200, Merck $65, Merck Vet $65, No Animal Doctor $40, Livestock Healthy $20, Beekeeper's $30, Nelson Peds $70, mushrooms (Arora ×2) $55, butchering ×2 $42, fermentation/root-cellar/preserving $82, Foxfire 1–3 $48, permaculture (Gaia's, Falk, Backyard Homestead) $89, construction (Ching, Pattern Language, Shelter, cob/earthbag) $195, 12V ×2 $50, microhydro $70, biofuels ×2 $70, chemistry ×3 $80, welding/blacksmith/sewing/leather ~$135, ARRL Antenna $50, reloading ×2 $60, NRA/Gun Digest $40, Kochanski $20, mental-health shelf $60, weather ×2 $30, Lancaster $60, Luther $16, Yeomans $35, When Tech Fails $35, Back to Basics $18, Kains Dover $12, Ina May $15, Saxon Math level $100 — **Subtotal C ≈ $2,615 new; ~$2,050 buying used where flagged.**

**Totals:**  

- Core only (A): **~$340**
- Core + Extended (A+B): **~$1,180**
- Everything (A+B+C): **~$3,795 new / ~$3,150 with used buys** — spread over time; C is optional depth.
- Plus client tablets ×2 (~$200, hardware; see §1).

Scan-needed shortlist (used purchase + scan): Ditch Medicine, ARRL EmComm Handbook (or substitute Operating Manual), Where There Is No Vet, A Failure of Civility, old Merck editions.
