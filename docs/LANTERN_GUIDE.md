# Lantern: an offline reference library on a Raspberry Pi

Author and developer: Eric Cheng | http://echeng.com

Lantern is a 1.1 TB survival and reference library that runs on a Raspberry Pi 5, broadcasts its own Wi-Fi network, and serves everything to the phones and laptops in a household. No internet connection is needed and nothing is installed on the client devices. A user joins a network called LIBRARY, types library.lan into a browser, and has Wikipedia, about 12,000 medical and technical PDFs, maps with routing files, Khan Academy, and a symptom triage page.

This document describes what is in the library, how it was assembled, and what it would take to build another one. The operator runbook (how to turn it on, what to do when it does not work) ships inside the library and is summarized in section 4.

## 1. The box

### Hardware

The server, its storage, and a travel router fit in a case the size of a paperback. Estimated parts cost about \$1,600 at September 2026 prices, which were high for memory and storage, but much of this hardware was already owned by the developer.

| Part | Role |
|---|---|
| Raspberry Pi 5, 16 GB | The server. The web stack needs far less memory; Kolibri, the server for Khan Academy and the other school content, is a Django application and uses most of it. An 8GB model would be sufficient if the school content was cut.|
| Samsung 970 EVO Plus 2 TB NVMe on a Pimoroni NVMe Base | Boot disk and library, mounted under the Pi on a ribbon cable. This is effectively optional; the whole thing could run using the recovery/backup setup as primary if desired.|
| Samsung T5 2 TB portable SSD | Cold backup of the whole library plus the boot image. Formatted ext4 so a Pi booted from a card can serve the library from it directly.  |
| Two microSD cards (32 GB and 64 GB) | Recovery boot media: one in the slot, one stored with the SSD. |
| GL.iNet Beryl AX travel router | Broadcasts the LIBRARY network and answers every DNS query with the Pi's address. |
| Two Anker PowerCore III Elite banks (25,600 mAh, about 92 Wh) | Use one while the other charges. Any USB-C PD bank of 20,000 mAh or more works. |
| Active cooler, 60 mm case fan, USB fan controller, Pimoroni case | Cooling. The NVMe runs hot under sustained hashing. |

Power draw is about 5 W for the Pi and 5 W for the router. One bank runs the Pi alone for roughly 15 hours, or both devices for roughly 7 hours; two banks cover a full day. These are calculated from the draw, not measured, and the runbook leaves a blank for the measured figure. A 60 W folding solar panel, stored disconnected, is the planned recharge path if household power electronics are lost.

The Pi 5 asks for 5 V at 5 A over USB-C and the banks supply 3 A. A headless Pi runs on a power limit set in the boot configuration.

### Redundancy

The design goal was a box that survives its owner. If only one person can recover it from a bad disk, the household has no library.

The boot image lives in three places (the NVMe, the card in the slot, the card with the SSD) and the library content in two (the NVMe and the backup SSD). The Pi's bootloader tries the NVMe first, then the card. A card-booted Pi has no library on its own disk, so it looks for the backup SSD by partition label and serves from it read-only. Everything works in that mode except Kolibri, which needs to write. Any Raspberry Pi 5 becomes the library with a card and the SSD plugged in.

Every file has a SHA-256 line in a 48 MB manifest. The quarterly maintenance step hashes every file (about 380,000) against it, which takes about an hour on the Pi. Unpowered SD cards lose data over years; SSD-class storage, a checksummed manifest, and a periodic power-up are the longevity plan.

### Software on the Pi

The Pi runs Raspberry Pi OS Lite (64-bit) from a 3.9 GB image built with pi-gen. Seven services start on boot:

- nginx serves the library as static files and acts as the captive-portal responder. It answers the URLs that iOS, Android, and Windows probe when they join a network, so most phones show a "sign in to network" sheet that is actually the library's front page.
- kiwix-serve 3.7.0 serves the 38 ZIM files (Wikipedia and related collections) on port 8080 with its own full-text search.
- Kolibri 0.19.5 serves Khan Academy, CK-12, OpenStax, EngageNY, and the Global Digital Library.
- A llamafile process runs the nomic embedding model that powers semantic search, so that search can match by meaning (section 3).
- A 1,100-line Python server using only the standard library speaks the Model Context Protocol (MCP) on port 8090. An AI client on the network can search and read the library through it, with the content safety rules enforced on the server rather than in the client's prompt.
- A voice server on port 8092 (reachable at /stt) turns speech from the Ask page's microphone button into text. Browsers offer the microphone only over a secure connection, so phones on the plain http library get no button and type instead.
- A disc mounter mounts the CD3WD disc images read-only, so /discs/ browses them like folders.

On first boot the image caps its own partition at 20 GB, creates a data partition from the rest of the disk, generates fresh ssh keys and a machine ID, and shows a "copy the library" page until content arrives. Every flashed card is therefore a clean clone rather than a copy of one particular box.

Nothing on the image is installed from pip or from Internet-in-a-Box. An early Kolibri installation through piwheels failed in ways that would not be repairable without internet access, and the image has been hand-assembled since. Anything absent at image lock is absent for the life of the box, so the image also carries sqlite3, jq, poppler, ffmpeg, smartmontools, tmux, and the other tools a future maintainer would otherwise need to download.

## 2. Content

The sealed library (October 2026) is 1.1 TB and about 380,000 files. Sizes in this section are binary units (1 GB = 2^30 bytes, as Linux `du -h` reports them). A Mac's Finder counts 1 GB as 10^9 bytes and shows about 7 percent more, for example 138 GB for the planet map file.

| Area | Size | Contents |
|---|---|---|
| Encyclopedias (ZIM) | 399 GB | 38 Kiwix files: full English Wikipedia with images (119 GB), Project Gutenberg (206 GB), Simple English Wikipedia, Wikibooks, Wikiversity, Wikisource, Wikivoyage, Wiktionary, Wikipedia Medicine in English and Spanish, iFixit, Appropedia, Energypedia, Battery University, eight Stack Exchange sites (DIY, electronics, ham radio, gardening, outdoors, medical sciences, physics, chemistry), PhET simulations, five TED science topics, TruePrepper, and the small zimgit collections on water, knots, medicine, post-disaster response, and food preparation |
| Maps | 291 GB | Protomaps planet vector tiles for the browser map (129 GB), USGS topographic quads for California (104 GB), Organic Maps and OsmAnd routing files for the whole US (31 GB), Geofabrik source data, NOAA nautical charts, satellite imagery for California. This is pluggable; other regions could be downloaded at high fidelity if desired, although the library would have to be reverified and sealed.|
| Documents | 267 GB | About 12,000 PDFs organized as 23 shelves (table below) |
| Kolibri | 100 GB | Khan Academy, CK-12, OpenStax, EngageNY, Global Digital Library |
| Video | 47 GB | 1,484 Khan Academy math and science lessons transcoded to H.264 for phones, 430 preschool reading and clock videos, 20 Prelinger Archive films |
| Datasets | 20 GB | FDA DailyMed drug labels (17 GB, deliberately excluded from search; see the safety rules), NOAA 1991 to 2020 climate normals for 467 stations, JPL ephemeris for a perpetual almanac, 1.6 million FCC amateur radio callsigns |
| Audio | 13 GB | 52 LibriVox audiobooks sorted into five age shelves |
| Tools | 11 GB | llamafile with Llama 3.2 3B and Llama 3.1 8B models, Whisper speech-to-text, Piper text-to-speech, Argos offline translation with wheels for four platforms, Android APKs for Organic Maps, OsmAnd and Kiwix, Kiwix Desktop, OpenCPN, video players for older devices |
| Site mirrors | 6.4 GB | Hesperian's health guides, the National Center for Home Food Preservation, Ready.gov, Sheldon Brown's bicycle site, Journey to Forever, Meshtastic and AREDN documentation |
| Generated | 20 GB | Search indexes, extracted text, covers, metadata (section 3) |

### The document shelves

The front page shows 30 shelves. The document shelves, with current PDF counts:

| Shelf | PDFs | Contents |
|---|---|---|
| Medical | 68 | TCCC 2024, MSF clinical guidelines, WHO manuals, the full Hesperian library (Where There Is No Doctor 2025 chapters, Where There Is No Dentist 2025, Where Women Have No Doctor, A Book for Midwives), Emergency War Surgery |
| Homestead and garden | 37 | Extension-service guides for canning, dehydrating, seeds, soils, livestock |
| Sanitation | 36 | Latrines, septic systems after floods, composting waste |
| Energy and power | 27 | The 24-module Navy NEETS electronics course, FEMA wood gas, solar |
| Communications | 18 | Radio, mesh networking, antennas |
| Emergency management | 14 | FEMA planning and response |
| Grain and bread | 9 | Milling, storage, sourdough from scratch |
| Water, shelter, military manuals, security, textiles, death care, coastal foraging, food preservation, fire safety, nuclear, navigation, historical medical | 1 to 7 each | Small shelves with one authoritative document each: the EPA water card, the USDA 2015 canning guide, FM 21-76, Bowditch, Nuclear War Survival Skills |
| Development handbooks (CD3WD) | 6,085 | Aid-agency how-to manuals, 1970 to 2012, extracted from the six 2012 DVD images |
| Survivor Library | 4,825 | Pre-industrial trade scans, 1800s to 1950s, behind a warning page |
| School textbooks | 966 | Siyavula grades 4 to 12, Connexions open textbooks |
| MIT OpenCourseWare | 23 courses | Direct course downloads, since no ZIM exists |
| Plants, mushrooms and the coast | 86 species (62 plants and mushrooms, 24 coastal) | One to six photos each, curated labels, poisonous and deadly lookalikes included on purpose |

Spanish content includes Wikipedia Medicine ES, Wikibooks ES, Vikidia ES, MedlinePlus ES, and the Hesperian Spanish editions. Search defaults to English with a toggle.

### The list

The first step in content selection was a survey of the commercial products (Prepper Disk, SurvivalNet, and others) and the community lists. All of them are Kiwix ZIMs on a Pi. Their snapshots are one-time; Lantern's content can be refreshed. None have routing maps; Lantern has Organic Maps and OsmAnd files for every US state. SurvivalNet ships the dated Survivor Library as primary content; Lantern puts it behind a warning page and puts current sources first.

The second step was gathering a 426-line master list with every resource, its size, its source, and a priority tier. The third was a red-team review of that list, which produced a set of must-fix items. Most of what distinguishes Lantern from the commercial boxes came from that review: the triage page, the historical quarantine, the printed tier, the rule that the library's own pages, summaries and search never state a drug dose (the medical books on the shelf do; the printed drug guide is the dosing reference), and the skills checklist.

After content selection, there was about two weeks of downloading and content additionswith verification rules that tightened each time something slipped through. One example: the Where There Is No Dentist PDF was labelled as the 2025 edition when it was actually the 2010 printing. Every PDF now has its header checked, its size gated, and its printing year read from the copyright page against the master list.

### Digital versus print

The original purchase list ran from \$340 for a core shelf of books to \$3,795 for everything. All of it was deferred until the digital build was complete, and when it was, most of it was unnecessary. The 2015 USDA canning guide is free and is the source the Ball Blue Book derives from. Hesperian gives away the current Where There Is No Doctor. The military manuals are public domain.

What finally went to paper:

- Drug dosing. The library's own pages, summaries and search never state a drug dose, by design; the medical books on the shelf do. A wrong table kills, and neither a 3B-parameter model nor a 1982 Special Forces handbook should be the dosing source in an emergency. The dosing reference is Davis's Drug Guide for Nurses, 20th edition (2026), $40, plus a one-page weight-band card written from it and laminated. Tarascon, the usual recommendation, stopped publishing in 2020 and was skipped
- Foraging. Three regional books (California Foraging, The Bay Area Forager, The Sea Forager's Guide), $71 total. Foraging decisions happen outdoors in glare, and plant photos are never printed at home because grayscale printing removes the color features used for identification.
- A set of paper resources for when nothing electronic works: Where There Is No Doctor (535 pages, double-sided into a six-tab binder with its own table of contents), Where There Is No Dentist, seven NCHFP canning guides, an EPA water card, a triage tree, the runbook, and a network sheet with the Wi-Fi QR code. All black and white; Hesperian's illustrations are line-drawn for mono printing.

Total spent on books: $191. The Survivor Library and the CD3WD set cost nothing, and most of the deferred purchase list turned out to be older editions of material already on disk. Paper covers the few things that have to be right and readable with no power. Disk covers breadth.

### Content safety rules

Five rules appear in the runbook, in the MCP server's handshake, and in the system prompt of the chat page:

1. Doses come from the printed licensed reference only. 
2. The Survivor Library, CD3WD's health category, and the pre-2010 medical shelf are background and technique history, never for food preservation recipes or drug guidance. Every link into them passes through a warning page that cannot be dismissed by tapping outside it.
3. Canning follows the 2015 USDA guide or NCHFP only (botulism is unforgiving).
4. Foraging: no positive, multi-feature identification means do not eat. Mushrooms are never to be eaten on the basis of the library alone; the pages exist to recognize the deadly species, not to clear an edible one.
5. Practice while it is easy. One drilled repetition per core skill (a tourniquet, a pressure-canning run, a ham radio contact) is the point of the skills checklist, although practically it is unlikely many people will actually go through all the practice steps.

The build fails if a generated page links directly into a historical shelf without the interstitial, or if the DailyMed drug labels appear in any search index. These are assertions in the verifier, not guidelines.

### Licensing

Everything on the box is redistributable within a household, and a unit given away needs no changes. A unit that is sold is a different matter, and the library ships a license manifest (`LICENSES.md`, on the front page sidebar under Operator) that says, class by class, what has to be stripped first. The repository's own build scripts and site code carry no open-source license yet; they are copyright of the author.

Software on the Pi and in the browser:

| Component | License |
|---|---|
| Raspberry Pi OS Lite, nginx, sqlite3, poppler, ffmpeg, Tesseract, ocrmypdf | Debian free-software stack: GPL, BSD-2, MIT, Apache 2.0, MPL 2.0 by package; the Pi firmware blobs are under Broadcom's redistribution terms |
| kiwix-serve, Kiwix Desktop, Kiwix for Android | GPL 3.0 |
| Kolibri | MIT |
| llamafile, nomic-embed-text, pdf.js, Pagefind (MIT), MapLibre GL and pmtiles (BSD 3-Clause) | Apache 2.0 unless noted |
| Llama 3.2 3B and Llama 3.1 8B | Llama Community License; the license texts ship beside the models and anything built on them must display "Built with Llama" |
| Whisper, Piper, Argos Translate | MIT |
| Organic Maps, OsmAnd, OpenCPN, VLC (Android and desktop installers) | Apache 2.0, GPL 3.0, GPL 2.0, GPL 2.0 and LGPL |
| Newsreader, Atkinson Hyperlegible, Noto Sans | SIL Open Font License 1.1 |
| The MCP server, the site JavaScript and CSS, the generators | No license file yet (all rights reserved by default) |

Content, by class:

| Class | License | Resale |
|---|---|---|
| Wikipedia and the Wikimedia ZIMs, Appropedia, Energypedia, the Stack Exchange sites | CC BY-SA (3.0 or 4.0); attribution travels inside the ZIM | Allowed with attribution |
| Project Gutenberg | Texts are public domain in the US; the Project Gutenberg name is a trademark and a sold copy must either follow the PG license or remove the mark | Strip before sale |
| iFixit, Khan Academy, EngageNY, MIT OpenCourseWare, TED | CC BY-NC-SA or CC BY-NC-ND | Noncommercial only |
| CK-12 | CK-12 curriculum license, noncommercial | Noncommercial only |
| OpenStax, PhET, Siyavula, most Connexions texts | CC BY | Allowed with attribution |
| Hesperian Health Guides (PDFs and the site mirror) | Hesperian open copyright, noncommercial | Strip before sale |
| WHO, MSF, Sphere, IFRC, IRENA, PAHO and other humanitarian publishers | Mostly CC BY-NC-SA; a few publisher-specific free-use terms | Per item, not yet cleared |
| US government: FEMA, CISA, EPA, USDA and extension services, NOAA, USGS, JPL, FDA, FCC, military manuals, LibriVox and Prelinger (public domain by dedication) | Public domain | Allowed |
| Survivor Library scans | Public domain by age; the collection itself asserts no license | Allowed |
| CD3WD | Collected for free redistribution by the CD3WD project; individual documents keep their source agency's terms | Per item |
| OpenStreetMap data (Protomaps planet, Organic Maps, OsmAnd, Geofabrik) | Open Database License 1.0; attribution required | Allowed with attribution |
| NOAA charts, USGS topo quads, NAIP imagery | Public domain | Allowed |
| DailyMed drug labels | Public domain (and excluded from search by rule) | Allowed |
| ARRL, ITU, UC ANR, Interweave Press and a handful of other single documents | Publisher copyright, free download only | Strip before sale |

The practical rule from the manifest: gifting a unit is clean, selling one is not. A strip script removes the three classes that are definitely restricted (Hesperian, the Gutenberg ZIM, and the named publisher-copyright PDFs) and keeps the Llama notices, but the noncommercial medical documents and the Kolibri channels still need per-item clearance before any sale.

## 3. Metadata: making 380,000 files findable

A Pi serving static files has no search of its own, and Kiwix searches only its own ZIMs. The PDF layer, where the life-critical content lives, was missing from search until the following was built. Everything in this section is precomputed off the box and shipped as files; the Pi does no live indexing.

### Text extraction and OCR

pdftotext runs over every whitelisted PDF and writes HTML wrapper files of 25 pages each, with one heading per page, so a search hit can open the reader at the right page. The wrappers total 5.1 GB.

About 3,100 PDFs were scans with no text layer, mostly the Survivor Library and the CD3WD health manuals. ocrmypdf with Tesseract (English plus Spanish) processed 670,000 pages in place, ten files at a time with two Tesseract threads each, for a total of 259 CPU-hours. 56 CD3WD PDFs remain image-only (drawing sheets, Bengali leaflets) and 2 are unreadable.

### Titles and summaries from a local model

Filenames like `_acca_f4_syllabus2012_eng.pdf` are not titles. For every PDF, the qwen3:32b model (run locally through Ollama) reads the filename and the first clean prose of the book, with cover noise skipped by a clean-token ratio, and returns a title and a one-sentence summary as JSON. This took about 4 seconds per document across 14,553 documents. For the 427 CD3WD PDFs with no usable text, the vision model qwen3-vl:32b reads the first three pages at 80 dpi, with a prompt that asks about the document rather than the picture.

The output is one JSON file of 15,290 entries keyed by path. Only missing keys are generated on a rerun, so hand edits survive, and deleting a key regenerates it. Three entries are hand-written.

The same approach produced one-line descriptions for all 30 shelves and the 340 groups within shelves (every Survivor Library topic folder, every Khan Academy unit, every tools folder). The rule is that everything gets a description, and the shelf generator warns on any group without one. 53 audiobook lines and 119 Survivor Library topic lines were written by hand because the model's were generic.

### Hand-written metadata

Three small files are written and reviewed by people, not generated by a model, because an error in them could hurt someone or break a page.

- The plant and coastal list: 86 species (62 plants and mushrooms, 24 coastal), each with a safety label (EDIBLE, EDIBLE COOKED, POISONOUS, DEADLY, BURNS SKIN or REGULATED), the species it is commonly confused with, and, for
shellfish, a note about biotoxin closures. The plant pages read their labels from this file and nowhere else.
- The emergency-card matcher: the Ask page reads the words of the question (everyday phrases such as "throwing up", "can't breathe", "blood loss", misspellings
included) and names the closest emergency cards; a matching card for a life-threatening emergency (severe bleeding, choking, unconscious or not breathing, a severe allergic reaction, carbon monoxide) is always first. Search and the front page take their card rows from the same matcher, so the three pages agree, and each page follows the closest cards
with the list of all the cards.
- The link table: a list of short names for documents and encyclopedia articles. Any page or summary can refer to a document by its short name, for example `ref:usda_canning`, and
the build replaces the name with the correct file path or Kiwix article. If the named file is missing, the build stops.

### Four search indexes

Search on the box is three layers plus the encyclopedia, each a separate precomputed artifact.

Titles. A 1.9 MB JSON file of every document's title and path, prefix-compressed, loaded once into the browser. Matching is client-side with seven ranking rules (whole-word bonus, historical demotion to 0.5, authoritative-shelf boost to 1.4, one result per audiobook, emergency card rows from the Ask page's matcher). This layer works from a USB stick with no server.

Full text (Pagefind). Three static indexes. One shared index let 1.9 million pages of 1890s word statistics reorder modern results and made every query take 2 to 4 seconds, so the corpus was split. The modern index is 99 MB and covers 8,830 pages across the current shelves and mirrors. The historical index is 2.8 GB and loads only when a query is run against it. A third index of 240 MB holds one 3,000-character record per CD3WD handbook and school textbook, because 800,000 pages of development manuals were pushing both other shelves out of the results.

Meaning (embeddings). Every page of the modern shelves and every document of the historical ones is a 768-dimension nomic-embed-text vector in a 1.26 GB SQLite sidecar: 269,648 vectors. The MCP server loads them with numpy and does a brute-force cosine scan, with a median of 27 ms on the development machine. Results below cosine 0.60 are dropped; that floor was tuned on an 86-query set where 0.65 emptied every Spanish query and 0.55 let junk through. The search page fuses the Pagefind and semantic lists by reciprocal rank, one row per document, and the semantic hit's page wins unless Pagefind found an exact phrase. On a blind-graded evaluation, the fused mode scored doc@8 of 0.69 against 0.58 for either layer alone.

Full-text SQLite (for AI clients). A 10.3 GB FTS5 database with 2,676,013 page rows across 19,174 documents, plus climate normals aggregated by month, the FCC callsign table, and the drug-name guard list. This is what the MCP server queries. Document reads took 24 seconds until a side index on path and page was added; they now take 18 milliseconds.

The encyclopedia layer is Kiwix's own Xapian search, proxied, with its results in the last slot. The Ask page, Search and the MCP server show no text quoted from the documents: they return titles and page links, and the text is read on the page itself.

### Covers and the reader

The first page of every PDF is rendered to a 400-pixel JPEG, 542 MB in total, named by a hash of the path. The reader is pdf.js with a resume position per document in the browser's local storage, so the front page can show "Continue reading" rows with the curated titles.

## 4. The runbook

The runbook is a 20 KB Markdown file that ships inside the library and is printed and taped inside the lid. It exists because of one red-team finding: if the owner is unavailable, the library ends. The response is a document that a non-technical household member can follow while standing at the box.

It has five parts. Parts 1 and 2 (turn it on, find things, turn it off, what to do when it does not work) need no computer skills and are written as "if this, do that, wait 3 minutes." Part 2 is a ladder from "no Wi-Fi network" through "the Pi is dead" to "nothing electronic works, here is the paper shelf." Part 3 is the as-built inventory with prices and modern replacements, how the Pi boots, where every copy lives, and how to rewrite a recovery card or rebuild from nothing. Part 4 is quarterly maintenance. Part 5 is the five content safety rules.

Three decisions shaped the runbook:

- It describes the box as built, not as planned, and every reference to something on the box is both a live link and a printed locator ("on Lantern: front page sidebar, Skills checklist"). The printed copy has to work without the links.
- Every step that can be drilled is on the skills checklist with a blank for a date and initials. The first item is a second household member bringing the box up alone, with no coaching.
- The quarterly and two-year maintenance cycles are written as prompts. The operator opens a file on the box, pastes it into any capable AI agent on a laptop on the same Wi-Fi, and the agent runs the service checks, starts the overnight hash, and says when to plug in the SSD. The two-year version assumes the maintainer has never seen the project and explains what rots (model binaries against kernel updates, ZIM releases, the almanac year, the FCC question pool cycle) before saying what to do. Both can also be done by hand; the steps are listed.

The runbook, the checklist, and the maintenance prompts are versioned content, generated into HTML at build like everything else, and never hand-edited on the box. The footer of the front page shows two numbers, the library seal date and the image version, both read from files on disk, so what is displayed is what is running.

## 5. How the site was built

### The frontend

No framework. 692 lines of ES5 JavaScript, 569 lines of CSS, two themes (dark by default; the file:// fallback forces light), three layout shells by screen width, and a bottom tab bar on phones with the red "Hurt or sick" disc in the center of every page. The landing page is under 100 KB before images and works with JavaScript off, because the shelf grid is written as static HTML at build time. Search, the PDF reader, the map, and chat need JavaScript; everything else degrades to links.

Direct mode matters for recovery. If index.html is opened from the backup SSD on a Linux laptop with no server, the shelves, PDFs, and plant photos work as plain files. The shelves that need the server (encyclopedias, full-text search) render greyed with a NEEDS THE SERVER badge and the path to the file.

### The build pipeline

Everything under the generated folder and every root HTML page is produced by one script, which stops at the first failure:

1. Generate the title index, shelf list, and plant data from the sealed manifest plus the curated JSON. Assert the title file is under its size budget and that no DailyMed path appears.
2. Render covers for any PDF without one.
3. Extract text to wrappers, stage three copies for the three Pagefind indexes, run Pagefind.
4. Generate 30 shelf pages, the static landing grid, and an HTML sibling for every Markdown file.
5. Restyle the triage page from its source, resolving named links.
6. Verify: every link on every generated page resolves on disk, no direct historical hrefs outside the interstitial, no doses, landing page under budget.
7. Hash-suffix the CSS and JS filenames (last, since it touches every page), then verify again.

Sealing is a separate two-pass script: hash all content, run the pipeline above over that manifest, hash the generated output, merge, and gate on a set comparison between disk and manifest. The gate exists because a parallel hashing run once dropped one file out of 269,000 and the loss was not noticed until the verify on the Pi failed. The MCP database and embeddings are then rebuilt against the new wrappers, and a push script syncs only what the manifest diff says changed.

The repository has 285 commits over 14 days and about 10,900 lines of Python, shell, JavaScript, and CSS. The generated output is 20 GB.

### Testing

Two harnesses. Acceptance is 59 deterministic checks (links, known-item queries against fixtures, safety invariants) that run before every seal. The exhaustive test is seven tiers, each a resumable script writing one CSV row per file: hash every file on the Pi against the manifest, open every file with a validator for its type (pdfinfo, PIL, ffprobe, a VTT parser, ZIM and ISO magic bytes), HEAD-request every manifest path from the Pi, crawl every link, confirm every title is in an index, and drive the pages in a headless browser. 269,000 files validate in about 12 minutes on 16 cores. Small models babysit the runs and sample-review the few items that need judgment; they do not grade text quality in bulk, because two passes over the same 200 samples disagreed (77% versus 34% rated acceptable).

### Building another one

Two approaches are possible.

Forking the scripts. They are not packaged as a product. The repository path is a constant, the content is assumed to live in a bulk store reached through symlinks, the metadata pass assumes a local machine capable of running a 32B model, and every shelf is a hardcoded dictionary. 

Someone forking the repository would need to change paths, download ~1.1 TB. With an AI coding agent, adapting the scripts (paths, shelf list, region) is an hour or two of work, most of it the agent's. Downloading 1.1 TB is limited by the source mirrors, not the local connection; the original downloads took about two weeks with verification, and the Kiwix mirrors in particular throttle large files. Regenerating the metadata is compute time, unattended: roughly 17 hours for titles and summaries (15,290 documents at 4 seconds each on a local 32B model), 259 CPU-hours of OCR if the scanned shelves are included, and a few hours each for the three Pagefind indexes, the 2.7 million row full-text database, and the 269,648 embedding vectors. A copy of an existing library on an SSD skips all of that, since the extracted text, indexes, and metadata ship with it.

Treat the repository as a worked example for an AI coding agent. The project already runs this way for maintenance: the quarterly and two-year cycles are prompts, not scripts, and the operating rules for a working session (concurrency limits, what to verify before trusting a download, where to write findings) are in a file at the repository root. A fresh agent session reads that file, the progress log, and the master list, and continues from the first unchecked task. That is how every session of the build after the first proceeded.

A build for a different household would start the same way: give the agent this repository and a description of the region and the people (a coastal town with toddlers and a sailboat produces a different map set, plant list, and triage page), and let it adapt the master list, re-run the downloads under the verification doctrine, regenerate the metadata with whatever local model is available, and produce a new seal. The scripts are the parts of that work that were frozen because they are the same for every build: hashing, Pagefind staging, the safety verifier, the reseal gate. The judgment calls (what goes behind the warning page, which edition is current, what gets printed) are in the progress log and the design notes as decisions with reasons, which is what an agent needs to make the next ones.

Two constraints from the build apply to anyone doing this. An agent's "verified" claim has to be re-checked by a deterministic script; the verification doctrine in the operating rules is a list of the occasions when that was learned. And the limit on parallel agents was never CPU or memory. It was the number of bytes per second written into the terminal. One agent streaming a verbose build output froze the terminal emulator; twenty read-only agents did not. Every long job writes to a log file, and the log is grepped.
