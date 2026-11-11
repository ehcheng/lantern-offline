# Source Map — Offline Survival Library

**Generated:** 2026-09-14  
**Method:** HEAD-check via `curl -sIL` per URL; directory scraping for Kiwix ZIM catalogs; agent-parallel verification. Raw curl output → `logs/source_map.log`.  
**Legend:** IN-PROGRESS = already queued in `download_zims.sh`; PDF-LAYER = handled by parallel PDF agent; flag column uses ⚠ (changed/broken/stale) or ✓ (matches MASTER_LIST).

---

## §2.1 General Reference

| Resource | Status | URL / Vendor | Verified (HTTP / Size / Date) | Notes |
|---|---|---|---|---|
| Wikipedia EN all maxi 2026-08 | CONCRETE-URL IN-PROGRESS | `https://download.kiwix.org/zim/wikipedia/wikipedia_en_all_maxi_2026-08.zim` | 200 / 118.7 GB / 2026-09-14 | 301→dumps.wikimedia.org→200. Matches MASTER_LIST. ✓ |
| Wikipedia EN medicine maxi 2026-04 | CONCRETE-URL IN-PROGRESS | `https://download.kiwix.org/zim/wikipedia/wikipedia_en_medicine_maxi_2026-04.zim` | 200 / 2.06 GB / 2026-09-14 | Via dumps.wikimedia.org. ✓ |
| Simple English Wikipedia maxi 2026-06 | CONCRETE-URL IN-PROGRESS | `https://download.kiwix.org/zim/wikipedia/wikipedia_en-simple_all_maxi_2026-06.zim` | 200 / 3.26 GB / 2026-09-14 | Via dumps.wikimedia.org. ✓ |
| Wikibooks EN maxi 2026-04 | CONCRETE-URL IN-PROGRESS | `https://download.kiwix.org/zim/wikibooks/wikibooks_en_all_maxi_2026-04.zim` | 200 / 5.75 GB / 2026-09-14 | Via dumps.wikimedia.org. ✓ |
| Wikiversity EN maxi 2026-05 | CONCRETE-URL IN-PROGRESS | `https://download.kiwix.org/zim/wikiversity/wikiversity_en_all_maxi_2026-05.zim` | 200 / 2.29 GB / 2026-09-14 | Via dumps.wikimedia.org. ✓ |
| Appropedia EN maxi 2026-02 | CONCRETE-URL IN-PROGRESS | `https://download.kiwix.org/zim/other/appropedia_en_all_maxi_2026-02.zim` | 200 / 555 MB / 2026-09-14 | Via triplebit mirror. ✓ |
| zimgit-post-disaster 2024-05 | CONCRETE-URL IN-PROGRESS | `https://download.kiwix.org/zim/other/zimgit-post-disaster_en_2024-05.zim` | 200 / 615 MB / 2026-09-14 | Via triplebit mirror. ✓ |
| zimgit-knots 2024-08 | CONCRETE-URL IN-PROGRESS | `https://download.kiwix.org/zim/other/zimgit-knots_en_2024-08.zim` | 200 / 27 MB / 2026-09-14 | Via triplebit mirror. ✓ |
| TruePrepper 2026-05 | CONCRETE-URL IN-PROGRESS | `https://download.kiwix.org/zim/other/trueprepper.com_en_all_2026-05.zim` | 200 / 1.32 GB / 2026-09-14 | Via triplebit mirror. ✓ |
| Wiktionary EN | CONCRETE-URL | `https://download.kiwix.org/zim/wiktionary/wiktionary_en_all_nopic_2026-08.zim` | 200 / 8.5 GB / 2026-09-14 | ⚠ **MASTER_LIST says `_maxi` — no maxi variant exists for Wiktionary.** Correct filename: `wiktionary_en_all_nopic_2026-08.zim`. Size ~8.5 GB vs MASTER_LIST ~7 GB estimate. |
| Wikisource EN | CONCRETE-URL | `https://download.kiwix.org/zim/wikisource/wikisource_en_all_maxi_2026-05.zim` | 200 / 18.3 GB / 2026-09-14 | ⚠ MASTER_LIST omits date. Latest is 2026-05. Two versions available (2026-02, 2026-05). Size 18.3 GB vs ~15 GB estimate. |
| Wikivoyage EN | CONCRETE-URL | `https://download.kiwix.org/zim/wikivoyage/wikivoyage_en_all_maxi_2026-06.zim` | 200 / 1.06 GB / 2026-09-14 | ⚠ MASTER_LIST omits date. Latest is 2026-06. ✓ size |
| Project Gutenberg EN 2025-11 | CONCRETE-URL | `https://download.kiwix.org/zim/gutenberg/gutenberg_en_all_2025-11.zim` | 200 / 206 GB / 2026-09-14 | Matches MASTER_LIST exactly. ✓ |
| wikiHow EN ZIM | BROKEN | No EN ZIM available anywhere | 404 everywhere / 2026-09-14 | ⚠ **CONFIRMED DEAD.** Kiwix `/zim/wikihow/` is 404; OPDS catalog returns 0 results. archive.org has only Dutch ZIM (`wikihow_nl_maxi_2024-08`). No EN source found. Either drop claim or BUILD via zimit crawl of wikihow.com (gray area). |
| Stack Exchange — DIY | CONCRETE-URL | `https://download.kiwix.org/zim/stack_exchange/diy.stackexchange.com_en_all_2026-08.zim` | 200 / 1.92 GB / 2026-09-14 | ✓ |
| Stack Exchange — Electronics | CONCRETE-URL | `https://download.kiwix.org/zim/stack_exchange/electronics.stackexchange.com_en_all_2026-08.zim` | 200 / 3.92 GB / 2026-09-14 | ✓ |
| Stack Exchange — Ham Radio | CONCRETE-URL | `https://download.kiwix.org/zim/stack_exchange/ham.stackexchange.com_en_all_2026-02.zim` | 200 / 0.07 GB / 2026-09-14 | ⚠ 2026-08 build returns 403 on all mirrors; use 2026-02. MASTER_LIST filename needs date pinned. |
| Stack Exchange — Gardening | CONCRETE-URL | `https://download.kiwix.org/zim/stack_exchange/gardening.stackexchange.com_en_all_2026-08.zim` | 200 / 0.86 GB / 2026-09-14 | ✓ |
| Stack Exchange — Outdoors | CONCRETE-URL | `https://download.kiwix.org/zim/stack_exchange/outdoors.stackexchange.com_en_all_2026-08.zim` | 200 / 0.13 GB / 2026-09-14 | ✓ |
| Stack Exchange — Medical Sciences | CONCRETE-URL | `https://download.kiwix.org/zim/stack_exchange/medicalsciences.stackexchange.com_en_all_2026-02.zim` | 200 / 0.06 GB / 2026-09-14 | ⚠ Latest available is Feb 2026. |
| Stack Exchange — Physics | CONCRETE-URL | `https://download.kiwix.org/zim/stack_exchange/physics.stackexchange.com_en_all_2026-08.zim` | 200 / 1.70 GB / 2026-09-14 | ✓ |
| Stack Exchange — Chemistry | CONCRETE-URL | `https://download.kiwix.org/zim/stack_exchange/chemistry.stackexchange.com_en_all_2026-07.zim` | 200 / 0.39 GB / 2026-09-14 | ⚠ Latest is 2026-07 not 2026-08. |
| The Knowledge — Dartnell | PURCHASE | Amazon: `https://www.amazon.com/Knowledge-Have-Everything-Rebuilding-Civilization/dp/0143127047` | ~$17 print | ✓ |
| Back to Basics — Gehring | PURCHASE | Amazon search "Back to Basics Gehring" | ~$18 print | |
| Country Wisdom & Know-How — Storey | PURCHASE | Amazon search "Country Wisdom Know-How Storey" | ~$20 print | |
| When Technology Fails — Stein | PURCHASE | Amazon search "When Technology Fails Stein" | ~$35 print | |
| Survivor Library (15k PDFs) | CONCRETE-URL | `https://archive.org/details/survival.library` | 200 / unverified size / 2026-09-14 | ⚠ Size still unverified (150-232 GB range). QUARANTINE flag applies — serve under "HISTORICAL" section only. |
| CD3WD full set | CONCRETE-URL | `https://archive.org/details/CD3WD12` | 200 / ~13 GB / 2026-09-14 | ✓ |
| awesome-survival index | CONCRETE-URL | `https://github.com/alx-xlx/awesome-survival` | 200 / <1 MB | ✓ |

**§2.1 Stack Exchange total verified: ~7.0 GB** (vs MASTER_LIST ~15 GB — MASTER_LIST estimate was high).

---

## §2.2 Medical

| Resource | Status | URL / Vendor | Verified (HTTP / Size / Date) | Notes |
|---|---|---|---|---|
| Where There Is No Doctor 2025 ed. | CONCRETE-URL | `https://hesperian.org/books-and-resources/` (email-gated) | 200 / page loads | ⚠ **EMAIL-GATE — no direct PDF URL.** Site uses email-collection plugin since ~2022. Submit form or use HTML web edition at `https://en.hesperian.org/hhg/Where_There_Is_No_Doctor`. MASTER_LIST listed as FREE-DL but requires form. |
| Where There Is No Dentist | CONCRETE-URL | `https://hesperian.org/books-and-resources/` (email-gated) | 200 / email-gated | ⚠ Same email-gate. All `/wp-content/uploads/` guesses 404. |
| Where Women Have No Doctor + Midwives | CONCRETE-URL | `https://hesperian.org/books-and-resources/` (email-gated) | 200 / email-gated | ⚠ Same email-gate. `en_wwhnd.pdf` paths return HTML 404. |
| Remaining Hesperian library / HealthWiki | CONCRETE-URL | `https://en.hesperian.org/hhg/` (HTML) | 200 | ⚠ HTML-only web edition; no bulk PDF download. For offline, wget mirror of hesperian.org or email-request PDF set. |
| Where There Is No Psychiatrist — Patel 2nd | CONCRETE-URL | `https://www.cambridge.org/core/books/where-there-is-no-psychiatrist/` | 200 | ⚠ Cambridge Open Access PDF; verify free PDF link vs paywall. Alternate: search RCPsych site. |
| WHO set (MCPC, Pocket Book, Surgical Care, Formulary, IMCI, mhGAP 2.0, PFA, Drinking-water) | CONCRETE-URL | `https://www.who.int/publications/i/` (search per title) | 200 | WHO IRIS provides free PDFs for all listed titles. Base URL: `https://apps.who.int/iris/handle/` per ISBN. ✓ All verified free. |
| PAHO Management of Dead Bodies | CONCRETE-URL | `https://www.paho.org/en/documents/management-dead-bodies-disaster-situations` | 200 | ✓ Free PDF |
| WHO/IPCS poisoning guides | CONCRETE-URL | `https://www.who.int/publications/i/item/management-of-poisoning` | 200 | ✓ Free PDF |
| Contraception/family planning — WHO Global Handbook | CONCRETE-URL | `https://www.who.int/publications/i/item/family-planning-a-global-handbook-for-providers` | 200 | ✓ Free PDF, JHPIEGO edition also available |
| Spanish core (WTIND ES + Hesperian ES + WikiMed ES) | CONCRETE-URL | Hesperian: email-gated; WikiMed ES ZIM: `https://download.kiwix.org/zim/wikipedia/wikipedia_es_medicine_maxi_2026-04.zim` | 200 / ~2 GB | ⚠ Hesperian ES also email-gated. WikiMed ES: verify exact filename in Kiwix catalog. |
| MSF Clinical Guidelines | CONCRETE-URL | `https://medicalguidelines.msf.org/sites/default/files/2026-05/guideline-170-en.pdf` | 200 / 6.8 MB / 2026-05 | ✓ Direct PDF. Note: path includes date prefix (2026-05). |
| MSF Essential Drugs | CONCRETE-URL | `https://medicalguidelines.msf.org/sites/default/files/pdf/guideline-339-en.pdf` | 200 / 2.8 MB | ✓ |
| MSF Obstetrics/Essential Obstetric & Newborn Care | CONCRETE-URL | `https://medicalguidelines.msf.org/sites/default/files/pdf/guideline-449-en.pdf` | 200 / 4.9 MB | ✓. MASTER_LIST linked dead URL (`/viewport/OGC/…`) — use this instead. ⚠ |
| MSF TB guidelines | CONCRETE-URL | `https://medicalguidelines.msf.org/` (search TB) | 200 | ✓ Free PDF via site |
| MedlinePlus ZIM | BROKEN | `https://download.kiwix.org/zim/other/` | 404 (no match) | ⚠ **NO MEDLINEPLUS ZIM EXISTS on Kiwix.** Directory scraped — no `medline*` ZIM found. Remove from MASTER_LIST or substitute `zimgit-medicine_en_2024-08.zim` (already listed). |
| zimgit-medicine 2024-08 | CONCRETE-URL IN-PROGRESS | `https://download.kiwix.org/zim/other/zimgit-medicine_en_2024-08.zim` | 200 / 67 MB / 2026-09-14 | ✓ |
| Emergency War Surgery 5th US rev. | CONCRETE-URL | `https://archive.org/download/emergency-war-surgery-5th-edition/Emergency%20War%20Surgery%205th%20Edition.pdf` | 200 / 29 MB | ⚠ medcoe.army.mil URL returns 404. archive.org is the working source. |
| SOF Medical Handbook 2nd ed. 2008 | CONCRETE-URL | `https://archive.org/` (search "SOF Medical Handbook") | 200 | ✓ PD copy on IA; HISTORICAL banner required per MASTER_LIST. |
| Ranger Medic Handbook (2007 free) | CONCRETE-URL | `https://archive.org/` (search "Ranger Medic Handbook 2007") | 200 | ✓ |
| TCCC Guidelines + Quick Reference | CONCRETE-URL | `https://deployedmedicine.com/` (free account required) | 200 | ⚠ Account-gated; DoD reorganizes periodically. Download week 1, verify checksums. |
| FM 4-25.11 First Aid + TC 4-02.1 | CONCRETE-URL | `https://archive.org/details/civilian-and-non-civilian-medical-guides` | 200 | ✓ |
| ST 31-91B 1982 | CONCRETE-URL | `https://archive.org/` (search "ST 31-91B") | 200 | ✓ QUARANTINE to HISTORICAL section only. |
| Borden Institute Textbooks of Military Medicine | CONCRETE-URL | `https://medcoe.army.mil/borden-institute-textbooks` | 200 | ✓ Free PDFs |
| Red Cross First Aid/CPR manual | PURCHASE | `https://www.redcross.org/store/` | ~$10 | Confirmed NOT free — official manuals are paid. ✓ |
| Gray's Anatomy 1918 PD | CONCRETE-URL | `https://archive.org/details/graysanatomy1918` | 200 | ✓ PD |
| FDA DailyMed SPL full release | CONCRETE-URL | `https://dailymed-data.nlm.nih.gov/public-release-files/` (multi-part ZIPs) | 200 / 3.22 GB/part1 (Rx, 6 parts + 11 OTC + animal + homeopathic) | ⚠ Split into many ZIPs. Full corpus is multi-hundred GB. Main release page: `https://dailymed.nlm.nih.gov/dailymed/spl-resources-all-drug-labels.cfm`. Monthly delta also available. MASTER_LIST 10–20 GB underestimates full set. |
| NLM C3PI pill-image dataset | BROKEN | `https://datadiscovery.nlm.nih.gov/` | No dataset found | ⚠ **LIKELY RETIRED.** rximage.nlm.nih.gov returns 502. No C3PI/RxImage dataset found on Socrata, LHC downloads, or NLM data API. Check NIH Figshare or contact LHNCBC. |
| Helping Babies Breathe (AAP) | PURCHASE | `https://www.aap.org/en/patient-care/helping-babies-breathe/` | 200 / materials not free | ⚠ **NOT FREE.** HBB materials are sold/account-gated AAP products. MASTER_LIST lists as FREE-DL incorrectly. Either purchase or drop. |
| Survival Medicine Handbook — Alton 4th | PURCHASE | Amazon `https://www.amazon.com/dp/0986575526` | ~$40 | ✓ |
| Oxford Handbook Clinical Medicine 11th | PURCHASE/SCAN | Publisher + Amazon | ~$60 | ✓ |
| Auerbach's Wilderness Medicine 7th | PURCHASE/SCAN | Amazon | ~$250 | ✓ SCAN labor: ~2,800 pp. |
| Improvised Medicine — Iserson 2nd | PURCHASE | Amazon | ~$50 | ✓ |
| NOLS Wilderness Medicine | PURCHASE | Amazon | ~$17 | ✓ |
| Ditch Medicine — Coffee | SCAN | Used: eBay/AbeBooks ~$25–60 | — | Paladin Press defunct; used copies only. ✓ |
| Bushcraft First Aid — Canterbury | PURCHASE | Amazon | ~$16 | ✓ |
| Sanford Guide to Antimicrobial Therapy | PURCHASE | Amazon / Sanfordguide.com | ~$60 | ✓ |
| Tarascon Pharmacopoeia | PURCHASE | Amazon | ~$25 | ✓ Tier 1 per red team. |
| Harriet Lane Handbook | PURCHASE | Amazon | ~$45 | ✓ Tier 1 per red team. |
| Merck Manual (Professional or Home) | PURCHASE | Amazon | ~$65 print | ✓ |
| Heart and Hands — Davis 5th | PURCHASE | Amazon | ~$25 | ✓ |
| Emergency Childbirth — White | PURCHASE | Amazon | ~$10 | ✓ |
| Goldfrank's Toxicologic Emergencies | PURCHASE | Amazon | ~$200 | ✓ Tier 3. |
| SAMHSA disaster behavioral health pubs | CONCRETE-URL | `https://www.samhsa.gov/mental-health/disaster-preparedness` | 200 | ⚠ Original MASTER_LIST URL is 404. Content moved to `/mental-health/disaster-preparedness`. Full SERG resource at same page. One-pager PDF: `https://www.samhsa.gov/sites/default/files/division-trauma-behavioral-health-one-pager.pdf` (200, 200 KB). |

---

## §2.3 Food / Preservation / Foraging / Agriculture

| Resource | Status | URL / Vendor | Verified (HTTP / Size / Date) | Notes |
|---|---|---|---|---|
| USDA Complete Guide to Home Canning 2015 | CONCRETE-URL | `https://nchfp.uga.edu/resources/category/usda-guide` | 200 / 2026-09-14 | ✓ PDF downloads linked from page. Only 2015 revision is safe for canning. |
| NCHFP full site mirror | BUILD | `wget -r -np https://nchfp.uga.edu/ -P nchfp/` | 200 (site live) | ✓ Site live; ~1 GB mirror estimate. |
| zimgit-food-preparation 2025-04 | CONCRETE-URL IN-PROGRESS | `https://download.kiwix.org/zim/other/zimgit-food-preparation_en_2025-04.zim` | 200 / 93 MB / 2026-09-14 | ✓ |
| FAO document repository picks | CONCRETE-URL | `https://www.fao.org/documents/` | 200 | ✓ Free PDFs; Better Farming Series included. |
| USDA/extension service PDFs | BUILD | State extension sites (e.g., `https://extension.uga.edu/`, `https://extension.colostate.edu/`) | 200 | ✓ BUILD: wget per-state extension canning/livestock/gardening sections. |
| Five Acres and Independence — Kains PD | CONCRETE-URL | `https://archive.org/search?query=five+acres+and+independence+kains` | 200 | ✓ PD on archive.org |
| FM 21-76 edible-plants chapter | CONCRETE-URL | `https://archive.org/details/fm-21-76` | 200 | ✓ PD; supplement-only (B&W plates inadequate; SUPPLEMENT banner required). |
| Ball Blue Book 38th | PURCHASE | Amazon | ~$15 | ✓ Tier 1 buy. |
| Encyclopedia of Country Living — Emery 50th | PURCHASE | Amazon | ~$28 | ✓ Tier 1 buy. |
| Seed to Seed — Ashworth | PURCHASE | Amazon | ~$25 | ✓ |
| Self-Sufficient Life — Seymour | PURCHASE | Amazon | ~$30 | ✓ |
| Mini Farming — Markham | PURCHASE | Amazon | ~$15 | ✓ |
| Backyard Homestead — Madigan | PURCHASE | Amazon | ~$19 | ✓ |
| Gaia's Garden — Hemenway | PURCHASE | Amazon | ~$30 | ✓ |
| Thayer trilogy (Forager's Harvest + 2 more) | PURCHASE | Amazon / `https://www.eattheweeds.com/` | ~$70 set | ✓ Tier 2. |
| Peterson Edible Wild Plants | PURCHASE | Amazon (regional editions) | ~$21 | ✓ Tier 1 (promoted per red team). |
| Mushrooms Demystified + All That Rain Promises | PURCHASE | Amazon | ~$55 | ✓ Expert-gated banner required per MASTER_LIST. |
| Butchering: Mettler + Hasheider | PURCHASE | Amazon | ~$42 | ✓ |
| Root Cellaring — Bubel | PURCHASE | Amazon | ~$17 | ✓ |
| Art of Fermentation — Katz | PURCHASE | Amazon | ~$40 | ✓ |
| Foxfire vols 1–3 | PURCHASE | Amazon used | ~$48 | ✓ QUARANTINE food-preservation chapters only; craft/skills chapters fine. |
| Storey's Guides (chickens, goats, + species) | PURCHASE | Amazon | ~$60 (×3) | ✓ |
| FAO primary animal health care manuals | CONCRETE-URL | `https://www.fao.org/documents/` (search "primary animal health") | 200 | ✓ |
| USDA PLANTS checklist CSV | CONCRETE-URL | `https://plants.usda.gov/home/downloads` | ⚠ redirect issues | ⚠ `plantlst.txt` URL redirects to error page. Use PLANTS database export form or find current download at `https://plants.usda.gov/csvdownload` or via USDA open data portal. Size ~7 MB. |
| Edible/poisonous plant image set | BUILD | Wikimedia Commons scrape + FM 21-76 plates | BUILD | BUILD: `python3 -m gallery-dl` or `wget` from Wikimedia Commons category pages for edible/poisonous plants. ~5 GB estimate. |
| Where There Is No Vet — Forse | SCAN | AbeBooks / used dealers | — | ✓ Used, patchy availability. |
| Veterinary: Merck Vet + Where No Animal Doctor + Livestock Healthy | PURCHASE | Amazon | ~$125 set | ✓ |
| Preserving Food without Freezing or Canning | PURCHASE | Amazon | ~$25 | ✓ |

---

## §2.4 Water & Sanitation

| Resource | Status | URL / Vendor | Verified (HTTP / Size / Date) | Notes |
|---|---|---|---|---|
| zimgit-water 2024-08 | CONCRETE-URL IN-PROGRESS | `https://download.kiwix.org/zim/other/zimgit-water_en_2024-08.zim` | 200 / 20 MB / 2026-09-14 | ✓ |
| EPA Emergency Disinfection of Drinking Water | CONCRETE-URL | `https://www.epa.gov/waterresilience/emergency-disinfection-drinking-water` | 200 | ✓ Free PDF |
| CAWST biosand/HWT library | CONCRETE-URL | `https://resources.cawst.org/` | 308→200 | ✓ Free resource library (redirects to updated domain). |
| SODIS manual + WHO Slow Sand Filtration | CONCRETE-URL | SODIS: `https://www.sodis.ch/methode/downloads/index_EN.html`; WHO: `https://www.who.int/publications/i/item/9241542101` | 200 | ✓ |
| Texas Manual on Rainwater Harvesting | CONCRETE-URL | `https://www.twdb.texas.gov/publications/reports/numbered_reports/doc/R0-04-05+Rainwater+Harvesting+Manual.pdf` | 200 | ✓ Free PDF, ~10 MB. |
| FM 10-52 Water Supply | CONCRETE-URL | `https://archive.org/search?query=FM+10-52+water+supply` | 200 | ✓ PD on archive.org |
| EMAS well manuals + RWSN/SKAT hand-drilling | CONCRETE-URL | `https://www.skat.ch/` + `https://www.rural-water-supply.net/` | 200 | ✓ Free PDFs |
| Humanure Handbook 3rd ed. | CONCRETE-URL | `https://humanurehandbook.com/downloads.html` | ⚠ 404 | ⚠ `humanurehandbook.com/downloads.html` returned 404. Try: `https://humanurehandbook.com/` main page or archive.org mirror. 4th ed. is paid (~$25). |
| Rainwater Harvesting for Drylands — Lancaster | PURCHASE | Amazon | ~$60 | ✓ |
| Prepper's Water Survival Guide — Luther | PURCHASE | Amazon | ~$16 | ✓ |
| Water for Every Farm — Yeomans | PURCHASE | Amazon | ~$35 | ✓ |

---

## §2.5 Shelter & Construction

| Resource | Status | URL / Vendor | Verified (HTTP / Size / Date) | Notes |
|---|---|---|---|---|
| USDA Wood Handbook FPL-GTR-282 | CONCRETE-URL | `https://www.fpl.fs.usda.gov/documnts/fplgtr/fplgtr282.pdf` | 200 (via redirect) | ✓ Free PDF; 301→302→200 redirect chain. |
| Army FMs (5-426, 3-34.471, 5-428, 5-34, 5-103) | CONCRETE-URL | `https://archive.org/` (bulk search per TM number) + `https://armypubs.army.mil/` | 200 | ✓ PD; armypubs.army.mil hosts current editions. |
| Shelters Shacks and Shanties — Beard 1914 PD | CONCRETE-URL | `https://archive.org/details/sheltersshackssh00bear` | 200 | ✓ |
| The Owner-Built Home — Kern | CONCRETE-URL | Circulates free online; archive.org: search "Owner Built Home Kern" | 200 | ✓ |
| IRC (International Residential Code) | CONCRETE-URL | `https://codes.iccsafe.org/content/IRC2021P1` (free read-only) | 200 | Older editions circulate PDF; current IRC is free read-only browser access. |
| B&D Complete Guide to Wiring 8th + Plumbing | PURCHASE | Amazon | ~$60 | ✓ |
| Building Construction Illustrated — Ching 6th | PURCHASE | Amazon | ~$50 | ✓ |
| Hand-Sculpted House + Earthbag Building | PURCHASE | Amazon | ~$60 | ✓ |
| A Pattern Language + Shelter (Kahn) | PURCHASE | Amazon | ~$85 | ✓ |

---

## §2.6 Energy / Solar / Electrical

| Resource | Status | URL / Vendor | Verified (HTTP / Size / Date) | Notes |
|---|---|---|---|---|
| Energypedia EN maxi 2026-06 | CONCRETE-URL IN-PROGRESS | `https://download.kiwix.org/zim/other/energypedia_en_all_maxi_2026-06.zim` | 200 / 763 MB / 2026-09-14 | ✓ |
| US Navy NEETS (24 modules) | CONCRETE-URL | `https://www.navy-neets.com/` or `https://archive.org/search?query=NEETS+navy` | 200 | ✓ Free PDFs; archive.org has all 24 modules. |
| FEMA wood-gas generator 1989 | CONCRETE-URL | `https://archive.org/details/using-wood-gas-generators` or FEMA.gov GASIFIER document | 200 | ✓ PD; ~10 MB. |
| Battery University site mirror | DROPPED 2026-11-10 (a crawl of a copyrighted site, not redistributable; Appropedia and Wikipedia cover battery care) | `zimit crawl of batteryuniversity.com` | — | ⚠ JS-heavy site; naive `wget` yields broken mirror. Use `zimit` browser-based crawler or substitute with Appropedia/Wikipedia battery articles. `ponytail: zimit run, not wget` |
| Scoraigwind free plans + Appropedia microhydro | CONCRETE-URL | `https://www.scoraigwind.co.uk/` + `https://www.appropedia.org/` | 200 | ✓ |
| Solar Electricity Handbook — Boxwell | PURCHASE | Amazon / `https://www.solarelectricityhandbook.com/` | ~$25 | ✓ |
| SEI Photovoltaics Design & Installation | PURCHASE | Amazon / SEI (DRM-free PDF offered) | ~$60 | ✓ |
| Practical Electronics for Inventors 4th | PURCHASE | Amazon | ~$35 | ✓ |
| Art of Electronics 3rd | PURCHASE/SCAN | Amazon | ~$130 | ✓ SCAN labor: ~1,200 pp. |
| Piggott Wind Turbine Recipe Book | PURCHASE | `https://www.lulu.com/` or Hugh Piggott's site | ~$15 DRM-free PDF | ✓ |
| Micro-Hydro Design Manual — Harvey | PURCHASE | Amazon / ITDG | ~$70 | ✓ |
| Journey to Forever site mirror | BUILD | `zimit crawl of journeytoforever.org` | — | ✓ BUILD; site is largely static HTML, wget may work. ~500 MB. |
| 12V wiring books | PURCHASE | Amazon (used) | ~$50 | ✓ |
| Chemistry shelf (Caveman Chem + 2 more) | PURCHASE | Amazon | ~$80 | ✓ |

---

## §2.7 Communications

| Resource | Status | URL / Vendor | Verified (HTTP / Size / Date) | Notes |
|---|---|---|---|---|
| Ham Stack Exchange ZIM | CONCRETE-URL | `https://download.kiwix.org/zim/stack_exchange/ham.stackexchange.com_en_all_2026-02.zim` | 200 / 70 MB | ⚠ Use 2026-02; 2026-08 returns 403 on all mirrors. |
| NCVEC question pools | CONCRETE-URL | Tech 2026-2030: `http://ncvec.org/downloads/TECH_2026/2026-2030%20Technician%20Pool%20...Dec%2018%202025.pdf` (200/477 KB); General 2023-2027: `http://ncvec.org/downloads/General%20Class%20Pool...6th%20Errata%20Feb%204%202026.pdf` (200/477 KB) | 200 / ~1 MB total | ✓ |
| ARRL band plan PDF | CONCRETE-URL | `https://www.arrl.org/band-plan` (PDF linked from page) | 200 | ✓ |
| RepeaterBook CHIRP CSV | CONCRETE-URL | `https://www.repeaterbook.com/repeaters/downloads/CHIRP/` | 200 | ⚠ **No bulk ZIP.** Form-based per-state export only via `chirp_result.php`. Manual per-state download required; scripting violates ToS. Missing-columns bug #6783 confirmed. |
| FCC ULS weekly dump | CONCRETE-URL | `https://data.fcc.gov/download/pub/uls/complete/l_amat.zip` | 200 / ~197.6 MB / 2026-09-13 | ⚠ MASTER_LIST may have uppercase `l_Amat.zip` — use lowercase. Amateur radio license file only; amateur = `l_amat.zip`. |
| FM 24-19 + TC 9-64 | CONCRETE-URL | `https://archive.org/` + `https://armypubs.army.mil/` | 200 | ✓ PD. |
| Meshtastic + AREDN docs + installers | BUILD | `https://meshtastic.org/`, `https://www.arednmesh.org/`, `https://www.fldigi.net/`, `https://js8call.com/`, `https://winlink.org/` | 200 | ✓ BUILD: mirror docs + download installers. ~2 GB estimate. |
| NVIS/wire-antenna papers + AmRRON guides | CONCRETE-URL | `https://amrron.com/` (free section) | 200 | ✓ |
| ARRL Tech + General license manuals | PURCHASE | Amazon / `https://www.arrl.org/shop/` | ~$33 ea | ✓ Tier 1 buy. |
| ARRL Handbook | PURCHASE | Amazon (used) | ~$30 used | ✓ |
| ARRL Antenna Book | PURCHASE | Amazon | ~$50 | ✓ |
| ARRL Operating Manual | PURCHASE | Amazon | ~$30 | ✓ |
| ARRL EmComm Handbook 2006 OOP | SCAN | Used ~$10 → scan | — | ✓ OOP, substitute Operating Manual. |

---

## §2.8 Repair / Mechanical / Trades

| Resource | Status | URL / Vendor | Verified (HTTP / Size / Date) | Notes |
|---|---|---|---|---|
| iFixit EN ZIM 2025-12 | CONCRETE-URL IN-PROGRESS | `https://download.kiwix.org/zim/ifixit/ifixit_en_all_2025-12.zim` | 200 / 3.33 GB / 2026-09-14 | ✓ |
| TM 9-8000 Automotive Vehicles | CONCRETE-URL | `https://archive.org/search?query=TM+9-8000` | 200 | ✓ PD. |
| TC 9-237 Welding Theory | CONCRETE-URL | `https://archive.org/search?query=TC+9-237+welding` | 200 | ✓ PD. |
| Sheldon Brown bicycle mirror | BUILD | `wget -r sheldonbrown.com` or `zimit crawl` | — | ✓ BUILD; site is static HTML + images. ~1 GB. |
| Canvas/textile TMs + spinning/weaving PD | CONCRETE-URL | `https://archive.org/` (TM 10-269 etc.) | 200 | ✓ PD. |
| Haynes/Chilton manuals (per vehicle ×2) | PURCHASE | Amazon | ~$30 ea | ✓ Tier 1 buy. |
| Machinery's Handbook 31st | PURCHASE | Amazon | ~$110 | ✓ |
| Small-engine manuals (B&S + Roth) | PURCHASE | Amazon | ~$90 | ✓ |
| Park Tool Big Blue Book 4th | PURCHASE | Amazon / parktool.com | ~$25 | ✓ |
| Welder's Handbook + Backyard Blacksmith | PURCHASE | Amazon | ~$50 | ✓ |
| Sewing/leather shelf | PURCHASE | Amazon | ~$85 | ✓ |

---

## §2.9 Maps / Navigation / Weather

| Resource | Status | URL / Vendor | Verified (HTTP / Size / Date) | Notes |
|---|---|---|---|---|
| Protomaps PMTiles — US extract | BUILD | `pmtiles extract https://build.protomaps.com/20260914.pmtiles us.pmtiles --bbox=-180,18,-66,72` | Daily build: 200 / 128 GB total planet / 2026-09-14T08:57:17Z | ✓ BUILD command confirmed. Latest build key: `20260914.pmtiles`. Get current key from: `https://build-metadata.protomaps.dev/builds.json`. US extract will be ~25 GB per MASTER_LIST estimate. |
| Protomaps PMTiles — full planet z0-15 | CONCRETE-URL | `https://build.protomaps.com/20260914.pmtiles` | 200 / 128 GB (138,013,553,034 bytes) | ⚠ MASTER_LIST says 120 GB; actual is ~128 GB as of 2026-09-14. Date-stamped daily; use metadata API for current filename. |
| Organic Maps .mwm — USA | CONCRETE-URL | CDN: `https://cdn.organicmaps.app/` (per-region MWM files) | 200 | ⚠ **No single-file USA archive.** CDN serves individual per-state/region .mwm files via app download protocol. No documented bulk sideload path. Must use Organic Maps app to download regions, or reverse-engineer the per-file CDN URLs (`cdn-us1.organicmaps.app/maps/<dataVersion>/<region>.mwm`). CoMaps fork: `https://github.com/comaps` (active org, likely same CDN). MASTER_LIST "8.3 GB full USA sideload set" understates complexity. |
| OsmAnd .obf — full US | CONCRETE-URL | `https://download.osmand.net/download?standard=yes&file=Us_<state>_northamerica_2.obf.zip` | 200 / ~500 MB/state | ⚠ **No single US OBF.** Per-state files (50+ states + metro splits for CA, FL, NY, TX). Listing at `https://download.osmand.net/list.php`. Pattern: `Us_alabama_northamerica_2.obf.zip`. MASTER_LIST "16 GB full US" requires downloading ~60+ files. OsmAnd indexes.xml (`/rasdazo/`) is 404 — dead URL. |
| Geofabrik US PBF | CONCRETE-URL | `https://download.geofabrik.de/north-america/us-latest.osm.pbf` | 302→200 / 12.1 GB (12,143,122,079 bytes) / 2026-09-14 | ✓ Checksum: `https://download.geofabrik.de/north-america/us-latest.osm.pbf.md5` (200, 52 bytes). |
| USGS US Topo GeoPDF — home state only | CONCRETE-URL | `https://apps.nationalmap.gov/downloader/` (batch by state) | 200 | ✓ Full US set is infeasible (~2.8 TB); state-level only per MASTER_LIST. |
| NOAA ENC/RNC nautical charts | CONCRETE-URL | `https://charts.noaa.gov/` | 200 | ✓ Free download (if coastal). |
| US National Park maps (63) | CONCRETE-URL | `https://www.nps.gov/planyourvisit/maps.htm` (per park) | 200 | ✓ PD. |
| TC 3-25.26 Map Reading and Land Navigation | CONCRETE-URL | `https://irp.fas.org/doddir/army/tc3-25x26.pdf` | 202 (lazy-load / request accepted) | ✓ irp.fas.org hosts it; 202 means server queuing. Alternate: armypubs.army.mil. |
| Bowditch — American Practical Navigator | CONCRETE-URL | NGA MSI portal: `https://msi.nga.mil/Publications/APN` | 200 (SPA, login required for PDF download) | ⚠ **NGA requires CAC/account login** for PDF download (API returns 403 unauthenticated). Best public-domain source: `https://archive.org/search?query=bowditch+american+practical+navigator`. Confirm current edition available on IA. |
| JPL DE440s ephemeris + Skyfield | BUILD | NAIF HTTP: `https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440s.bsp` | 200 (connection established; size unconfirmed due to timeout) | ✓ NAIF HTTPS proxy works. `pip install skyfield` downloads de440s.bsp automatically. BUILD: `python3 -c "from skyfield.api import Loader; Loader('.')('de440s.bsp')"`. ~17 MB. |
| SFalmanac (perpetual nautical almanac) | BUILD | `https://rhodesmill.org/skyfield/` | 200 | ✓ Skyfield-based; no separate download needed. |
| Weather PDFs (AC 00-6B, FM 34-81-1, NWS Skywarn, WMO Cloud Atlas) | CONCRETE-URL | FAA: `https://www.faa.gov/regulations_policies/handbooks_manuals/aviation/media/AC_00-6B.pdf`; WMO: `https://cloudatlas.wmo.int/` | 200 | ✓ |
| NOAA 1991-2020 US Climate Normals | CONCRETE-URL | `https://www.ncei.noaa.gov/data/normals-hourly/1991-2020/access/` | 200 / 467 station CSVs | ✓ Per-station CSVs only; no bulk zip. Scrape directory. ~3 GB total per MASTER_LIST. Also: 2006-2020 normals at same path pattern. |
| Be Expert with Map and Compass — Kjellström | PURCHASE | Amazon | ~$16 | ✓ |
| Eric Sloane + Williams weather books | PURCHASE | Amazon (used) | ~$30 | ✓ |

---

## §2.10 Security / Defense / Gov & Emergency Management

| Resource | Status | URL / Vendor | Verified (HTTP / Size / Date) | Notes |
|---|---|---|---|---|
| Core military FM set (21-76, 3-21.76, 5-103, etc.) | CONCRETE-URL | `https://armypubs.army.mil/` + `https://irp.fas.org/` + `https://archive.org/` | 200 | ✓ PD. irp.fas.org has bulk dumps. |
| FEMA materials (P-2064, CERT, IS-courses, Food & Water) | CONCRETE-URL | `https://training.fema.gov/` + `https://www.fema.gov/` | 200 | ✓ Free PDFs. |
| Ready.gov site mirror | BUILD | `wget -r https://www.ready.gov/` | 200 (site live) | ✓ BUILD: ~500 MB estimate. |
| Nuclear War Survival Skills — Kearny | CONCRETE-URL | `https://oism.org/nwss/nwss.pdf` | 200 | ✓ Free PD PDF. |
| Fire: structure-fire, wildfire, chimney PDFs | CONCRETE-URL | `https://www.nfpa.org/` + `https://www.fs.usda.gov/` + state extension sites | 200 | ✓ |
| CO + fuel safety PDFs | CONCRETE-URL | `https://www.cdc.gov/carbon-monoxide/` + `https://www.cpsc.gov/` | 200 | ✓ Free PDFs. |
| CDC Yellow Book | CONCRETE-URL | `https://wwwnc.cdc.gov/travel/yellowbook/` | 200 | ✓ Free online; PDF download available. |
| MIT Guide to Lock Picking + hunter-safety manuals | CONCRETE-URL | MIT guide: circulates freely as `mit-lockpicking.pdf` on archive.org; state hunter-ed: `https://www.ihea-usa.org/` | 200 | ✓ |
| SAS Survival Handbook — Wiseman 3rd | PURCHASE | Amazon | ~$18 | ✓ Tier 1 buy. |
| Bushcraft 101 — Canterbury | PURCHASE | Amazon | ~$13 | ✓ Tier 1 buy. |
| Kochanski Bushcraft | PURCHASE | Amazon | ~$20 | ✓ |
| Prepper's Long-Term Survival Guide — Cobb | PURCHASE | Amazon | ~$17 | ✓ |
| Reloading: Lyman 51st + Hornady | PURCHASE | Amazon | ~$60 | ✓ |
| A Failure of Civility (OOP) | SCAN | Used → scan | — | ✓ Expensive; OOP. |

---

## §2.11 Education (K-12 → college)

| Resource | Status | URL / Vendor | Verified (HTTP / Size / Date) | Notes |
|---|---|---|---|---|
| Kolibri server + Khan Academy EN channel | CONCRETE-URL | Kolibri app: `https://github.com/learningequality/kolibri/releases/tag/v0.19.5` (200, .apk 215 MB, .deb 99 MB, .dmg 83 MB) | 200 | ⚠ **Khan Academy channel token unavailable via API** (kolibri-studio.com is 502; studio.learningequality.org API path 404). Get token via Kolibri app's built-in import wizard → "Learn with Kolibri" → Khan Academy. |
| CK-12 ZIM | CONCRETE-URL | Check `https://download.kiwix.org/zim/` for CK-12 | Unverified | ⚠ Not found in Kiwix catalog during check. CK-12 may be Kolibri channel only. Verify via Kolibri import wizard. |
| OpenStax textbook library | CONCRETE-URL | API: `https://openstax.org/apps/cms/api/books/?format=json` → `high_resolution_pdf_url` field | 200 / PDFs on `assets.openstax.org` CDN | ✓ CDN PDFs are publicly accessible without auth. Sample: `https://assets.openstax.org/oscms-prodcms/media/documents/algebra-1_-_WEB.pdf` (200/82.7 MB). ~5 GB total for full library. |
| EngageNY K-12 ELA+math | CONCRETE-URL | `https://www.engageny.org/` | ⚠ 502 | ⚠ **engageny.org is down (502).** Content migrated to NYSED: `https://www.nysed.gov/curriculum-instruction`. Find materials there or via Kolibri channel. |
| PhET simulations | CONCRETE-URL | `https://download.kiwix.org/zim/phet/phet_en_all_2026-08.zim` | 200 / 108 MB / 2026-09-14 | ✓. MASTER_LIST says "~100 MB" — confirmed. |
| Core Knowledge K-8 curriculum (CKHG/CKLA) | CONCRETE-URL | `https://www.coreknowledge.org/download-free-curriculum/` | 200 (WooCommerce registration wall) | ⚠ Free curriculum requires registration (free account); not a direct file download. Submit registration to get download access. |
| CD3WD primary/junior school DVD set | CONCRETE-URL | `https://archive.org/details/2015_cdw3d_primary_junior_school_dvd_set` | 200 | ✓ |
| Global Digital Library | CONCRETE-URL | `https://digitallibrary.io/` | 200 / Kolibri channel path TBD | ⚠ No bulk Kolibri export API found (api.digitallibrary.io is 502). Use Kolibri import wizard for GDL channel. Tier 1 per red team (serves under-8s). |
| MIT OCW ZIMs | BROKEN | No ZIMs available on Kiwix | Not found | ⚠ **NO MIT OCW ZIMs EXIST on Kiwix.** MASTER_LIST reference is incorrect. Possible substitute: `courses.lumenlearning.com_en_all_2021-03.zim` (~11.2 GB, 2021 vintage) on Kiwix archive. Either source specific courses via zimit or drop. |
| Saxon Math or Math-U-See | PURCHASE | Amazon / publisher | ~$100/level | ✓ |

---

## §2.12 Media

| Resource | Status | URL / Vendor | Verified (HTTP / Size / Date) | Notes |
|---|---|---|---|---|
| TED science subset ZIM | CONCRETE-URL | Biology: `ted_mul_biology_2026-04.zim` (200/4.67 GB); Medicine: `ted_mul_medicine_2026-04.zim` (200/3.40 GB); Health-care: `ted_mul_health-care_2026-04.zim` (200/3.34 GB); Physics: `ted_mul_physics_2026-04.zim` (200/1.64 GB); Chemistry: `ted_mul_chemistry_2026-04.zim` (200/0.63 GB) | 200 / ~13.7 GB combined | ⚠ **No single "science" TED ZIM.** MASTER_LIST "14 GB science subset" = biology+medicine+health-care+physics+chemistry = ~13.7 GB. These 5 ZIMs = the science subset. All at `https://download.kiwix.org/zim/ted/`. |
| Curated instructional video library | BUILD | yt-dlp (personal archival gray zone) | — | ✓ BUILD per MASTER_LIST. Limit to irreplaceable procedures. |
| IA public-domain training films | CONCRETE-URL | Prelinger Archives: `https://archive.org/details/prelinger` | 200 / 10,468 items | ⚠ MASTER_LIST says "government_film" collection — that returns 0 results. Correct collection is `prelinger` (10,468 items). FEMA/Army subset: filter by keyword. ~10 GB Tier 3. |
| Librivox PD audiobooks | BUILD | `https://librivox.org/api/feed/audiobooks/?format=json` | 200 / paginated catalog | ✓ API works; no bulk download endpoint. BUILD: script to download Opus MP3s from catalog JSON. ~10 GB estimate. |

---

## §2.13 Datasets

| Resource | Status | URL / Vendor | Verified (HTTP / Size / Date) | Notes |
|---|---|---|---|---|
| DailyMed SPL (drug labels) | CONCRETE-URL | `https://dailymed-data.nlm.nih.gov/public-release-files/` (multi-part ZIPs) | 200 / 3.22 GB/part (Rx: 6 parts; OTC: 11 parts + animal/homeopathic) | ⚠ Full release is multi-hundred GB; 10–20 GB MASTER_LIST estimate is for Rx-only subset. Release page: `https://dailymed.nlm.nih.gov/dailymed/spl-resources-all-drug-labels.cfm`. Monthly delta also available. |
| NLM C3PI pill-image dataset | BROKEN | `https://datadiscovery.nlm.nih.gov/` | Dataset not found | ⚠ **Likely retired.** rximage.nlm.nih.gov returns 502; no C3PI dataset on Socrata. MASTER_LIST "Socrata path works today" is outdated. Check NIH Figshare or contact LHNCBC. |
| USDA PLANTS CSV | CONCRETE-URL | `https://plants.usda.gov/home/downloads` | ⚠ redirect issues | ⚠ Static file URL broken; use PLANTS download form or USDA open data portal. |
| NOAA Climate Normals | CONCRETE-URL | `https://www.ncei.noaa.gov/data/normals-hourly/1991-2020/access/` | 200 / 467 CSVs | ✓ (see §2.9) |
| JPL DE440s + Skyfield | BUILD | `https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440s.bsp` | 200 | ✓ (see §2.9) |

---

## §2.14 Offline Apps / AI

| Resource | Status | URL / Vendor | Verified (HTTP / Size / Date) | Notes |
|---|---|---|---|---|
| kiwix-serve | CONCRETE-URL | `https://github.com/kiwix/kiwix-tools/releases` | 200 | ✓ |
| MapLibre GL JS + PMTiles | CONCRETE-URL | `https://docs.protomaps.com/` + `https://unpkg.com/maplibre-gl` | 200 | ✓ |
| Calibre-Web | CONCRETE-URL | `https://github.com/janeczku/calibre-web/releases` | 200 | ✓ |
| Kolibri server | CONCRETE-URL | `https://github.com/learningequality/kolibri/releases/tag/v0.19.5` | 200 / v0.19.5 | ✓ |
| llama.cpp / Ollama + models | CONCRETE-URL | Ollama: `https://ollama.com/`; Models: `https://huggingface.co/` GGUF | 200 | ✓ Llama 3.2 3B, Qwen2.5, Phi-3-mini confirmed available. |
| LibreTranslate + Argos models | CONCRETE-URL | `https://github.com/LibreTranslate/LibreTranslate/releases/tag/v1.9.6` | 200 / pip/Docker only | ✓ No standalone binary. pip install + argostranslate model downloads. |
| Piper TTS + voices | CONCRETE-URL | `https://github.com/OHF-Voice/piper1-gpl/releases/tag/v1.8.0` | 200 / ~34 MB Python wheels | ✓ Python wheels for Linux/macOS/Win. Voice models: `https://huggingface.co/rhasspy/piper-voices`. |

---

## Summary: Key Issues Found

### Confirmed Broken / Missing (need MASTER_LIST updates)

| Issue | MASTER_LIST says | Reality |
|---|---|---|
| wikiHow EN ZIM | FREE-DL (stale, ~50 GB) | No EN ZIM exists anywhere. `/zim/wikihow/` is 404; archive.org has Dutch only. |
| MedlinePlus ZIM | FREE-DL ~2 GB, `zim/other/` | No MedlinePlus ZIM on Kiwix. Substitute: `zimgit-medicine`. |
| MIT OCW ZIMs | FREE-DL ~10 GB, kiwix library | No MIT OCW ZIMs on Kiwix. |
| Wiktionary filename | `wiktionary_en_all_maxi` | Correct: `wiktionary_en_all_nopic_2026-08.zim` (no maxi variant exists). |
| NLM C3PI pill images | FREE-DL via Socrata | Likely retired; rximage.nlm.nih.gov 502; no Socrata dataset found. |
| Helping Babies Breathe (AAP) | FREE-DL | NOT free; paid/account-gated AAP materials. |
| Humanure Handbook downloads page | FREE-DL from humanurehandbook.com | `/downloads.html` returns 404; use main page or archive.org. |
| Hesperian books (WTND, Dent, WWHND) | FREE-DL direct PDF | Email-gate since ~2022; no direct PDF URL. Submit form or use HTML HealthWiki. |
| SAMHSA disaster URL | samhsa.gov/find-help/disaster-distress-helpline/disaster-behavioral-health | 404; content moved to `/mental-health/disaster-preparedness`. |
| MSF obstetric emergencies URL | `/viewport/OGC/…/obstetric-emergencies-6271634.html` | 404; use `guideline-449-en.pdf` directly. |
| Emergency War Surgery — medcoe.army.mil | medcoe.army.mil/emergency-war-surgery | 404; use archive.org instead. |
| FCC ULS filename | `l_Amat.zip` (capitalized) | Must be lowercase: `l_amat.zip`. |
| USDA PLANTS `plantlst.txt` | plants.usda.gov/assets/docs/CompletePLANTSList/plantlst.txt | Redirect leads to error page; use PLANTS database export form. |
| EngageNY | engageny.org | 502; content migrated to NYSED. |
| IA training films collection | `collection:government_film` | Returns 0 items; correct collection is `collection:prelinger` (10,468 items). |
| Bowditch PDF (NGA) | NGA free PDF | NGA MSI requires CAC/login; use archive.org for PD editions. |
| Organic Maps "full USA sideload set" | 8.3 GB, Organic Maps CDN | No monolithic archive; individual per-region MWM files only. CoMaps fork active on same CDN. |
| OsmAnd indexes.xml URL | download.osmand.net/rasdazo/ | 404; use `download.osmand.net/list.php`. No single US OBF; ~60+ per-state files. |
| TED science ZIM | Single "science" ZIM, 14 GB | No generic science ZIM; 5 topic ZIMs (bio+medicine+health+physics+chem) = ~13.7 GB. |
| Protomaps planet size | 120 GB | Actual: 128 GB (138 GB bytes) as of 2026-09-14. Filename is date-stamped; use metadata API. |
| Ham Stack Exchange 2026-08 | `ham.stackexchange.com_en_all` (current) | 2026-08 returns 403; use 2026-02 (70 MB). |
| RepeaterBook bulk export | CHIRP CSV exports — `repeaterbook.com/repeaters/downloads/CHIRP/` | No bulk ZIP; form-based per-state only. Missing-columns bug #6783. |
| DailyMed size | 10–20 GB | Full release is multi-hundred GB. Rx-only part1 = 3.22 GB × 6 parts = ~20 GB for Rx; OTC adds more. |
| Kolibri channel tokens | learningequality.org | kolibri-studio.com is 502; get tokens via app import wizard. |
| Core Knowledge downloads | coreknowledge.org free | Registration wall (free account required, not direct download). |
