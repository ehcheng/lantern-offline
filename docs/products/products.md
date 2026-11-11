# Offline Knowledge Box Products & Serving Stack — Research Findings

Date: 2026-09-14. Sources cited inline. Sizes marked "~" are approximate or vary by ZIM release date.

---

## 1. Commercial Products

### Prepper Disk (prepperdisk.com)

- **Price:** $199 (256GB) – $279 (Premium, 512GB). Add-ons: Faraday Defense bag, 10-hr battery. Software-only option for existing Raspberry Pi owners.
- **Hardware:** Raspberry Pi 4B, 2GB RAM, 512GB SD card, aluminum alloy case, passive cooling, 3.5"×2.75"×1", 1-yr warranty. Boots ~30s, creates its own Wi-Fi hotspot; any browser connects.
- **Stack:** Creator stated on HN it bundles "Kiwix, IIAB, Rachel, and a custom web interface." Content stored as ZIM files.
- **Bundled content (from product pages):**
  - English Wikipedia, full text, 6M+ articles with images
  - Project Gutenberg — 60,000 eBooks
  - WikiHow — 90,000+ how-to guides
  - iFixit repair guides
  - Stack Exchange Q&A (outdoor/sustainability topics)
  - TED Talks (curated farming/weather videos)
  - Medical wikis — "50,000+ articles from the National Library of Medicine" (likely MedlinePlus + WikiMed/MDWiki ZIMs)
  - Ready.gov / FEMA disaster planning resources
  - Military survival manuals, hunting/foraging guides
  - Licensed exclusives: Ky Furneaux field guides, original eBooks (livestock, woodland survival, emergency comms)
  - RepeaterBook ham repeater directory (US/Canada), Morse code decoder, emergency phrase translator (200+ phrases, 6 languages)
  - World street maps (North America, Europe, Oceania), all 63 US National Park maps
  - USB file hosting (add your own files)
- **Criticisms (HN thread news.ycombinator.com/item?id=43790409):**
  - ~$199–279 for ~$100 of commodity Pi hardware + mostly free ZIMs
  - SD card data-retention risk when unpowered for years
  - No global map coverage (NA/EU/Oceania only)
  - Overengineered vs. a phone running Kiwix or physical books
  - AI (in later versions) hallucination risk for survival advice

### Iron Ark (ironark.io)

- **Models:** Core (2TB, text-only local AI), Field (4TB, GPU AI, 70+ TOPS), Sentinel (8TB, multimodal AI, 200+ TOPS, global maps). Expandable to 48–96TB.
- **Price:** Undisclosed; $30 reservation. Positioned premium (likely $1k+).
- **Content:** 40+ references — offline Wikipedia, U.S. Army Survival Manual, medical handbooks, nautical charts, seed-saving guides, engineering references; regional topo + street maps (global only on Sentinel).
- **Stack:** Browser-based local web interface, LAN-only, local LLM. Faraday-compatible hardware.
- **Criticism:** vaporware-ish (reservation model), pricing opacity, regional-only maps on lower tiers.

### The Ark / Survival AI (gettheark.com) + OffGrid: AI apps

- Handheld offline "survival AI" device; library covers first aid, nuclear response, fire, water purification, shelter, US Army Survival Manual, EMP. Marketed heavily on AI Q&A rather than browsable corpus. Also exists as phone apps (MWM "Survival AI - The Ark", OffGrid: AI on iOS).
- **Criticism:** small curated library vs. full Wikipedia-class corpus; hallucination risk; unclear provenance of content.
- **Note:** "Ark by Sotera" could not be confirmed as a real product — searches surface only Iron Ark, gettheark.com, and the Ark torrent (below). Treat as possibly misremembered name.

### ARCADIA (arcadiasurvival.com)

- Fanless x86 mini-PC "survival knowledge appliance": encyclopedias, offline maps, medical references, language tools, private local AI; hundreds of GB preloaded. Pricing not captured; same category as Personal Codex.

### SurvivalNet (thesurvivalnet.com)

- **Price:** $89 digital download (~700GB image) or $499 hardware kit (Pi 5, 8GB RAM, 1TB microSD, PSU, Faraday pouch, + 64GB USB with 3,500+ survival eBooks).
- **Stack:** Pi-based offline hotspot, web UI, Ollama AI chat (Llama 3.2, Gemma 2, DeepSeek R1).
- **Content (detailed, ~700GB total):**
  - Wiki resources 124.97GB — Wikipedia (102GB, 6.86M articles), Wiktionary, Wikibooks
  - Technology 83.23GB — Stack Overflow, Super User, programming docs
  - Project Gutenberg 75.2GB — 131,795 eBooks
  - Survivor Library 232GB — 15,144 historical PDFs (1800s–1900s trades/technology)
  - OpenStreetMap 52GB — interactive, 14 zoom levels
  - Health/medical 13.49GB — MDWiki, emergency medicine
  - LibreTexts OER 14.55GB
  - Video collections 15.76GB — 778 prepping/survival videos
  - Bonus USB: 37.87GB manuals (firearms, farming, herbalism, engineering, wilderness)

### Doom Box (Lanstruck) — $699

- Raspberry Pi 5, offline knowledge + local AI. Criticized (personal-codex.com comparison): premium is "software configuration," Pi-class AI inference is very slow (a few tokens/s).

### R.E.A.D.I. — $499

- Pi-based offline knowledge server with basic AI; same Pi hardware constraints as Doom Box/Prepper Disk.

### Personal Codex (personal-codex.com)

- **Tiers:** Essential $499 (Intel iGPU, 5–20 tok/s), Standard $1,495 (Ryzen 7 + Radeon 780M/890M, 30–55 tok/s), Power $2,899.
- **Hardware:** x86 mini PCs — differentiator is usable local AI speed.
- **Content:** Full Wikipedia w/ images, OpenStreetMap, Khan Academy, Ollama-served LLMs.
- **Criticism:** price; 4–6 week lead time.

### RACHEL / World Possible (rachel.worldpossible.org, store.worldpossible.org)

- **Audience:** education in unconnected regions (53+ countries), not preppers.
- **Hardware:** RACHEL-Plus (Intel CAP: content access point with built-in Wi-Fi AP + battery, 500GB HDD) ~$500; RACHEL 5 / RACHEL-Plus 4.0 at $500; also free DIY on Raspberry Pi.
- **Content (modular, via OER2Go library):** Wikipedia (Kiwix ZIMs), Khan Academy (KA Lite/Kolibri), PhET simulations, Project Gutenberg, CK-12, medical modules (Hesperian "Where There Is No Doctor" family), multiple languages, teacher-customizable.
- **Stack:** RACHEL content shell over nginx/Apache + Kiwix-serve + Kolibri; downloadable modules from oer2go.org.
- **Criticism:** education-oriented (weak on maps/survival), HDD-based older units, content freshness depends on module updates.

### Internet-in-a-Box (IIAB) — open source (internet-in-a-box.org, github.com/iiab/iiab)

- **Price:** free software; BYO Pi 4/5 (~$60–150 total). Prefab disk images available.
- **Content:** none by default — Admin Console downloads content packs: any Kiwix ZIM (Wikipedia in 100+ languages, WikiMed…), OpenStreetMap vector tiles + satellite imagery per region or whole world, OER2Go/RACHEL modules, Kolibri channels (Khan Academy etc.).
- **Stack (Ansible-installed on Raspberry Pi OS/Ubuntu/Debian):** nginx front end reverse-proxying: kiwix-serve, Kolibri, osm-vector-maps (http://box/maps), Calibre/calibre-web, Nextcloud, Moodle, WordPress, MediaWiki, Sugarizer, Lokole (offline email), Node-RED, Munin, usb_lib (auto-mount USB content); drag-and-drop Admin Console home page; optional captive portal.
- **Criticism:** install/config complexity vs. turnkey products; multi-GB content downloads left to the user; Pi performance limits with many concurrent users.

### Kiwix itself (kiwix.org) — the substrate almost everyone uses

- Free readers: Android, iOS, Windows/macOS/Linux, browser extension/PWA (kiwix-js), plus **kiwix-serve** LAN server. Kiwix Hotspot tool builds Pi hotspot images.
- ~1,000+ ZIMs in library.kiwix.org catalog. Criticism: BYO content — nothing preloaded; discovery/vetting burden is exactly what commercial boxes monetize.

### Offline Wikipedia devices (historical/adjacent)

- **WikiReader** (Openmoko, 2009): $99 pocket device, text-only Wikipedia on microSD; discontinued — the ancestor of this category.
- **Internet Archive offline projects** (blog.archive.org 2019): IA content served offline via IIAB partnership.
- **XOWA**: desktop offline Wikipedia app, alternative to Kiwix; development largely stalled.
- **PrepperNet:** appears to be a prepper community/network organization, not a knowledge box product; no bundled-content device found under that name. Nearest match is SurvivalNet (above).

### The Ark torrent (DIY, mentioned on HN)

- ~238GB community-assembled SHTF collection (manuals, medical, farming, trades PDFs); free, quality/curation uneven, provenance/legality mixed. Overlaps heavily with the Survivor Library and archive.org "SURVIVAL FILES" collections and github.com/alx-xlx/awesome-survival link list.

---

## 2. Serving Software Stack Landscape

### ZIM serving

- **kiwix-serve** (kiwix-tools, C++): single static binary, serves any set of ZIMs over HTTP with full-text search, library page, mobile-friendly. The de facto standard; used by Prepper Disk, IIAB, RACHEL, SurvivalNet.
- **kiwix-js / PWA:** in-browser ZIM reader; works from a file share with zero server.
- **IIAB:** Ansible roles + nginx reverse proxy + Admin Console (see above). Best "everything integrated" option: ZIMs + maps + LMS + file sharing + captive portal in one image.
- **RACHEL software:** simpler PHP content shell + modules; easiest for nontechnical deployment, less flexible.

### Offline maps over LAN

- **IIAB osm-vector-maps** (github.com/iiab/maps): OSM vector tiles + optional satellite photos, regional or planet, browser-based at http://box/maps.
- **tileserver-gl + MBTiles/PMTiles:** static vector tiles; planet vector build needs ~130GB (tiles+fonts+styles); Europe extract ~30–50GB.
- **Protomaps PMTiles:** single-file planet (~120GB vector); serve with any HTTP server supporting range requests — no tile server process needed. **UNVT Portable** demonstrates PMTiles from a Pi microSD (FOSS4G 2025 talk). Best fit for low-power boxes.
- **Organic Maps / CoMaps:** phone apps with per-region MWM downloads — per-device offline nav (routing included, which browser tile servers lack), not a LAN server. Complementary: preload .mwm files on the box for clients to sideload.
- **MapTiler Server on Raspberry Pi:** commercial turnkey alternative.

### Self-hosted wiki/readers usable over LAN Wi-Fi on mobile browsers

- kiwix-serve (read-only ZIMs) — lightest.
- **Kolibri** (Learning Equality): structured courses, video (Khan Academy channels), progress tracking; heavier (Python/Django).
- **Calibre-Web:** ebook library (EPUB/PDF) with in-browser reader — the standard for the "3,500 survival PDFs" problem.
- MediaWiki / DokuWiki / Wiki.js: for locally-authored content; MediaWiki is what IIAB ships for community editing.
- **Ollama + Open WebUI:** the emerging local-AI layer (SurvivalNet, Personal Codex, Iron Ark). Pi-class hardware = 1–5 tok/s; usable AI needs x86 iGPU or better.

---

## 3. Consolidated Content Inventory Across Products

All ZIMs from https://library.kiwix.org / https://download.kiwix.org/zim/ unless noted. Sizes are current-era (2025–26) and drift per release.

| Resource | Size | Source | Bundled by |
|---|---|---|---|
| Wikipedia EN all maxi (w/ images) | ~110 GiB (2025-07 release 110.8 GiB) | download.kiwix.org/zim/wikipedia/ | Prepper Disk, SurvivalNet, Personal Codex, Iron Ark, IIAB/RACHEL (optional) |
| Wikipedia EN all nopic | ~55 GB | same | DIY builds |
| Wikipedia EN mini | ~13 GB | same | phone/low-storage builds |
| Wiktionary EN maxi | ~7 GB | zim/wiktionary/ | SurvivalNet, IIAB |
| Wikibooks / Wikisource / Wikivoyage / Wikiquote EN | ~0.5–5 GB each | kiwix zim dirs | SurvivalNet, IIAB |
| WikiHow EN maxi | ~50 GB (nopic ~3 GB) | zim/zimit or zim/wikihow | Prepper Disk |
| iFixit EN | ~3.2–3.4 GB | download.kiwix.org/zim/ifixit/ | Prepper Disk |
| Project Gutenberg EN all | ~65–75 GB (SurvivalNet reports 75.2 GB / 131,795 books; Prepper Disk ships a 60k-book subset) | zim/gutenberg/ | Prepper Disk, SurvivalNet, RACHEL |
| Stack Exchange (per-site ZIMs; Stack Overflow largest) | ~100 MB–75 GB per site | zim/stack_exchange/ (sotoki) | SurvivalNet (83 GB tech bundle), Prepper Disk (outdoor/sustainability subset) |
| WikiMed / MDWiki medical encyclopedia | ~2 GB (75,000+ articles) | zim/other/ + dedicated apps | Prepper Disk ("medical wikis"), SurvivalNet |
| WikEM emergency medicine | ~1 GB | kiwix library | SurvivalNet-class bundles |
| MedlinePlus (NLM) | ~few GB | zim/other/ | Prepper Disk ("50,000+ NLM articles") |
| Khan Academy (Kolibri channels or ZIM videos) | ~30–60 GB per language | learningequality.org / kiwix | RACHEL, IIAB, Personal Codex |
| LibreTexts (per-discipline ZIMs) | 14.55 GB (SurvivalNet full OER set); individual libraries 0.2–5 GB | zim/libretexts/ | SurvivalNet, IIAB (optional) |
| PhET simulations | ~100 MB | zim/phet/ | RACHEL, IIAB |
| TED Talks (topic collections) | 1–20 GB per topic | zim/ted/ | Prepper Disk (farming/weather), IIAB |
| CK-12, African Storybook, Hesperian health guides | 0.1–2 GB | oer2go.org modules | RACHEL |
| Survivor Library (historical trades PDFs) | 232 GB / 15,144 PDFs | survivorlibrary.com | SurvivalNet; The Ark torrent overlaps |
| The Ark torrent (SHTF collection) | ~238 GB | community torrent (HN-cited) | DIY |
| Military manuals (US Army FM 21-76 etc.), FEMA/Ready.gov PDFs | <5 GB | public domain (fema.gov, army pubs) | Prepper Disk, Iron Ark, The Ark device |
| Ky Furneaux field guides + Prepper Disk original eBooks | small | licensed, exclusive | Prepper Disk only |
| RepeaterBook US/CA repeater DB | small | repeaterbook.com export | Prepper Disk |
| OpenStreetMap vector tiles | region ~1–50 GB; planet ~52 GB (SurvivalNet raster/14-zoom) to ~120 GB (Protomaps full vector planet) | protomaps.com builds, IIAB maps | SurvivalNet, IIAB, Personal Codex, Prepper Disk (NA/EU/Oceania) |
| Satellite imagery regions | 1–50+ GB per region | IIAB maps catalog | IIAB |
| US National Park maps (63 parks) | small | NPS public domain | Prepper Disk |
| Nautical charts (NOAA) | ~10–20 GB US full set | charts.noaa.gov | Iron Ark |
| Zimgit post-disaster / water / medicine collections | 0.3–1 GB each | kiwix library ("prepper" datasets, HN-recommended) | DIY |
| freeCodeCamp / DevDocs / ArchWiki ZIMs | 0.1–3 GB | kiwix library | tech-oriented builds |
| Survival eBook packs (herbalism, firearms, farming) | ~38 GB (SurvivalNet USB) | archive.org SURVIVAL FILES, awesome-survival list | SurvivalNet, torrents |
| Local LLM weights (Llama 3.2 3B, Gemma 2, DeepSeek R1 distill) | 2–9 GB per model | ollama.com | SurvivalNet, Personal Codex, Iron Ark, Doom Box |

### Cross-product gap analysis (what critics say is missing)

- **Global maps with routing:** almost nobody ships worldwide maps + turn-by-turn; browser tile servers don't route. Organic Maps MWMs sideloaded is the workaround.
- **Data longevity:** SD cards unpowered for years lose data; only Iron Ark markets SSD/expansion seriously.
- **Content freshness/updates:** one-time snapshots; few offer update subscriptions.
- **AI trust:** Pi-class boxes ship 3B-class models — slow and hallucination-prone for life-safety advice.
- **Curation vs. bulk:** Survivor Library/torrents = bulk unvetted PDFs; commercial boxes = curated but thin exclusives; nobody does verified, skill-organized survival curriculum.
- **Multi-language:** prepper products are English-only; only RACHEL/IIAB/Kiwix cover other languages.

---

## Key source URLs

- https://www.prepperdisk.com/ · /pages/how-does-it-work · /pages/faq
- https://news.ycombinator.com/item?id=43790409 (Prepper Disk HN thread)
- https://personal-codex.com/prepper-disk-alternative/ (competitor comparison: Doom Box, R.E.A.D.I., NOMAD, Codex)
- https://ironark.io/ · https://www.gettheark.com/ · https://arcadiasurvival.com/
- https://thesurvivalnet.com/ (most detailed public content manifest)
- https://internet-in-a-box.org/ · https://github.com/iiab/iiab · https://wiki.iiab.io/go/FAQ · https://github.com/iiab/maps
- https://rachel.worldpossible.org/ · https://store.worldpossible.org/ · https://oer2go.org
- https://kiwix.org · https://library.kiwix.org · https://download.kiwix.org/zim/ (mirrors: mirrorservice.org, ftp.fau.de)
- https://archive.org/details/wikipedia-en-all-maxi-2025-07-26 (110.8 GiB)
- https://github.com/alx-xlx/awesome-survival · https://archive.org/details/SURVIVALFILESDOWNLOADS · https://www.survivorlibrary.com
- https://talks.osgeo.org/foss4g-2025/talk/TCZTK7/ (PMTiles on Pi) · https://www.maptiler.com/server/maps-on-raspberry-pi/ · https://protomaps.com
- https://readthemanual.co.uk/project-nomad-self-hosted-internet-in-a-box/ (DIY NOMAD)
- https://ostechnix.com/best-kiwix-zim-files/ · https://gearjunkie.com/news/prepper-disk-brings-online-knowledge-off-grid
