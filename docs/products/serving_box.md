# Serving Box Architecture — Offline Knowledge Server

**Research date:** 2026-09-14
**Goal:** Battery-powered box serving Kiwix/Kolibri/maps/files over its own wifi to phones/tablets, running months-to-years with no grid and no internet.

---

## 1. Hardware comparison

| Metric | Raspberry Pi 5 (8/16GB) | Intel N100 mini-PC (Beelink S12 Pro class) | Mac Mini M4 |
|---|---|---|---|
| Idle draw (measured) | ~2.7–3.0 W headless; ~2.75 W with NVMe HAT idle | 6–8 W headless (some units 12–14 W with bad BIOS/OS config) | 3–4 W (Apple spec 4 W; Notebookcheck 2.6 W) |
| Load draw | 8–10 W (full CPU + NVMe) | 15–25 W | 30–65 W peak (irrelevant for this workload) |
| Realistic serving avg (light duty cycle) | ~4 W | ~9 W | ~6 W |
| Power input | **5V DC USB-C (27W PD)** — direct from battery via buck converter | **12V DC barrel** — direct from LiFePO4 (often 12–19V tolerant; check unit) | **AC only** — requires inverter |
| RAM | 8–16 GB | 16 GB (upgradeable) | 16 GB min |
| Storage | NVMe via M.2 HAT (PCIe x1 Gen2/3) | Full M.2 2280 NVMe + 2.5" SATA bay in many units | Internal (expensive) + USB/TB external |
| Onboard wifi as AP | Yes, but weak (1 antenna, ~2.4/5 GHz, ~15–30 clients realistic ceiling lower) | Usually Intel AX card — mediocre AP support | Poor; macOS Internet Sharing is flaky, not headless-friendly |
| OS longevity offline | Raspberry Pi OS / Debian — fully offline-maintainable | Debian — same | macOS wants Apple servers for reinstall/activation edge cases |
| Ecosystem for this exact job | **Excellent** — IIAB and Kiwix Hotspot ship Pi images | Good — generic Debian, run IIAB installer | None; DIY everything |
| Price (unit only) | $80 (8GB) / $120 (16GB) | ~$140–170 | $599 ($499 on sale) |

### Verdict

- **Winner: Raspberry Pi 5** for the pure serving-box role. Lowest wattage of any option that takes clean DC input, and the *entire ecosystem* (Internet-in-a-Box, Kiwix Hotspot imager) targets it. Known-good recipes matter enormously for a box you'll rely on when you can't google problems.
- **N100 mini-PC** is the right pick if you also want this box to do heavier duty (local LLM inference at small scale, video transcoding, Kolibri with many concurrent students, ZFS). ~2× the idle watts of a Pi but 3–4× the CPU, real SATA+NVMe dual-drive, and still native 12V DC.
- **Mac Mini M4** loses despite superb idle efficiency: **AC-only power is disqualifying for battery/solar**. A cheap 300W inverter burns 5–10 W at idle — more than the Mac itself — roughly halving runtime vs. DC-native options. Add macOS's poor headless/AP story and dependence on Apple servers for recovery, and it's the wrong tool. Only pick it if it's a dual-use machine you already own and you buy a low-idle pure-sine inverter (Victron Phoenix 250VA, ~$115, ~2.6 W self-draw).

### Battery runtime math (12.8V 100Ah LiFePO4, 1280 Wh, ~$140–180 street 2026)

Usable ≈ 1280 Wh × 0.9 DoD × 0.87 conversion efficiency ≈ **~1000 Wh delivered**.

| Build | Avg draw (server + AP) | Runtime on one 100Ah LiFePO4 |
|---|---|---|
| Pi 5 + NVMe + GL.iNet travel router | ~4.5–6 W | **7–9 days** continuous; 3–4 weeks at 8h/day |
| N100 + NVMe + travel router | ~10–12 W | **3.5–4 days** continuous |
| Mac Mini M4 via inverter + router | ~12–16 W | ~2.5–3.5 days continuous |

**Duty-cycling is the big lever:** a cron/physical-switch schedule (server on 6–10 h/day) turns the Pi build into a month per charge. Wake-on-demand is overengineering; a $10 12V timer switch or just a toggle works. LiFePO4 self-discharge (~2–3%/month) and 3000–6000 cycle life make it the correct chemistry; do not use lead-acid (half usable capacity, 1/10 the cycles) or Li-ion power banks (calendar aging, fire risk in storage).

### Solar pairing

- **Pi build:** 100 W panel + Victron SmartSolar 75/10 MPPT (~$70) + the 100Ah battery = indefinite runtime. Even 2 sun-hours/day (200 Wh) covers 24/7 Pi operation (~110–140 Wh/day) with margin.
- **N100 build:** same battery, 200 W panel + 75/15 MPPT for winter margin (needs ~250–290 Wh/day).
- Wire loads from the battery via a fused 12V distribution block; Pi gets a quality 12V→5V/5A USB-C buck (Pololu D36V50F5 or a USB-C PD trigger + buck rated 25W+ — undersized converters are the #1 cause of Pi 5 brownouts). N100 runs straight off battery only if its input range covers 10–14.6V; otherwise a 12V→12V regulated converter or 12V→19V boost.
- Alternative "appliance" route: EcoFlow River-class power station (~$200–300) — integrated MPPT/BMS/USB-C PD, less to build, but proprietary electronics are a single point of failure over years. Bare LiFePO4 + Victron is more repairable. Tradeoff noted; recommend the bare battery.

---

## 2. Wifi AP: hostapd vs. travel router in front

**Recommendation: dedicated travel router (GL.iNet) in front, Pi's onboard wifi disabled or kept as backup.**

| | hostapd on Pi onboard wifi | GL.iNet travel router (Beryl AX GL-MT3000, ~$90; Opal GL-SFT1200, ~$35–40) |
|---|---|---|
| Range/clients | Poor antenna, single chain; degrades past ~10–15 active clients | Real antennas, WiFi 6 (Beryl AX), comfortably 30+ clients |
| Failure isolation | AP bug takes down access to the server you'd use to debug it | Router dies → swap any spare router; server untouched |
| Power | 0 extra W | +2–3 W (Beryl AX ~2.5 W typical), USB-C 5V powered — same battery rail |
| Setup | hostapd + dnsmasq config by hand (IIAB automates it) | OpenWrt GUI; set static leases, point DNS at server |
| Spares strategy | Spare Pi needed | Any consumer router works in a pinch |

hostapd-on-Pi is acceptable for the budget build (and IIAB configures it for you), but for the reference build the $90 router buys range, client capacity, and failure isolation. Buy **two Opals ($40 ea) as cold spares** regardless — routers are the most likely lightning/ESD casualty.

Topology: `[phones] ⇄ wifi ⇄ [GL.iNet router: DHCP+DNS] ⇄ ethernet ⇄ [Pi/N100 server, static IP]`.

---

## 3. Storage

### Sizing (2026 ZIM/content reality)

| Content | Size |
|---|---|
| Wikipedia EN all maxi (with images) | ~110 GB |
| Wiktionary, Wikibooks, Wikivoyage, Wikihow, iFixit, StackExchange full set | ~150–250 GB |
| Project Gutenberg, medical (WikiMed, Medicine StackExch, Hesperian PDFs), military/survival manuals | ~100 GB |
| Kolibri channels (Khan Academy full EN + selected) | ~100–250 GB |
| OpenStreetMap planet mbtiles/pmtiles (vector, whole planet) | ~80–120 GB; one continent ~10–40 GB |
| Video (curated how-to library) | open-ended; budget 500 GB+ |
| **Practical total** | **1–2 TB comfortable; 4 TB = never think about it** |

### Recommendation

- **Primary: 4 TB NVMe** (WD Black SN770 / Crucial P3 Plus class, ~$200–250). NVMe over SATA/USB for reliability (no cable/bridge chipset) and idle power (~0.3 W ASPM).
- **Boot:** on the same NVMe (Pi 5 boots NVMe natively via HAT). Keep a flashed microSD clone of the boot partition taped inside the case as a recovery path.
- **Cold backup: 2nd identical 4 TB SSD**, updated via `rsync` before grid-down, then **unplugged and stored in a closed metal box (a Faraday cage) with all of the other electronics**: the server, the router, the recovery cards and the power banks go in it too, not only the backup SSD. Charge the power banks whenever the SSD is powered up, and at least every 6 months. SSDs retain data unpowered for years but **power it up and re-verify checksums every 6–12 months** — flash charge does leak. Add a `sha256sum` manifest at copy time.
- Third copy of the *irreplaceable* subset (your curated docs, not re-downloadable ZIMs) on a 512 GB microSD in the go-bag.
- Filesystem: plain ext4. ZFS on a survival box is complexity you can't repair offline. `ponytail:` ext4 + rsync + checksums; upgrade to ZFS mirror only if you go N100 with dual drives and want bitrot self-healing.

---

## 4. OS choice

- **Pi:** **Raspberry Pi OS Lite (64-bit, Bookworm-based)** — it's what IIAB/Kiwix images target; largest offline-fixable knowledge base. Debian stable also fine.
- **N100:** **Debian stable**, minimal netinstall.
- Rules for a years-offline box: pin the release (no `dist-upgrade` after freeze), disable unattended-upgrades post-freeze, **create a full local apt mirror of installed+likely packages** (`apt-mirror` or just `apt-get download` the dep tree into a local repo dir), set `Storage=persistent` journald with size cap, mount with `noatime`, install `log2ram` or tmpfs `/var/log` if booting SD, and **disable NTP panic**: install a **DS3231 RTC module** ($5, I²C) on the Pi — without a valid clock, HTTPS certs and file timestamps go sideways. Serve everything over plain HTTP (no cert expiry time-bombs).

---

## 5. Software stack

**Base recipe: Internet-in-a-Box (IIAB) 8.3** — it *is* this product: one installer that configures nginx, hostapd/RaspAP, dnsmasq, captive-portal redirect, Kiwix-serve, Kolibri, OSM vector maps, admin console, content download manager. Actively maintained (8.3, 2026; Kiwix 3.8.2, Kolibri 0.19.4). Install: 1-line installer from download.iiab.io onto Pi OS Lite, or flash their ready image via Raspberry Pi Imager (github.com/iiab/iiab/releases → Assets). The `MENU` question during install builds the unified landing page.

Layered view (whether via IIAB or hand-rolled):

| Layer | Tool | Notes |
|---|---|---|
| Reverse proxy / landing | **nginx** + one static `index.html` | Single port-80 front door; links to every service. Hand-written HTML — no SPA, must render on a 2015 phone browser. |
| Encyclopedic content | **Kiwix-serve** (`kiwix-serve --library library.xml *.zim`) | Built-in **Xapian full-text search across all ZIMs** — this is your global search; don't build another. |
| Structured learning | **Kolibri** | Khan Academy, PhET sims, per-user progress. Python; ~300 MB RAM. Skip on the budget build if RAM-tight. |
| Maps | IIAB's OSM vector map pack, or **tileserver-gl-light / mbtileserver** with a pmtiles/mbtiles extract + MapLibre GL JS page | Vector tiles: whole-planet fits in ~100 GB. Pre-render a raster fallback of your home region for ancient devices. |
| File dump (PDFs, videos, docs) | **Caddy `file_server browse`** or nginx `autoindex on` | Do not install Nextcloud/Jellyfin-class software; directory listing + HTML5 `<video>` works everywhere. `ponytail:` autoindex; add a static index generator script only if the tree gets unnavigable. |
| Search across the file dump | `recoll` CLI or a pre-built static index (e.g. **Pagefind** run over extracted text at build time) | Kiwix covers ZIMs; Pagefind's static JS index covers your own docs with zero running daemon. |
| Admin | IIAB admin console + SSH over ethernet | No cloud dashboards. |

DNS/discovery glue: dnsmasq answers all DNS with the box's IP (see §6).

**Alternative known-good recipes**
- **Kiwix Hotspot / Imager Service** (get.kiwix.org → Hotspots): web-based image builder — pick ZIMs, download a ready Pi SD/SSD image, done. Simpler than IIAB (no Kolibri/admin console). The old desktop `kiwix-hotspot` app is archived; use the online Imager Service (Hotspot Imager 3.0). Good budget-build path.
- **IIAB on x86:** same 1-line installer on Debian for the N100.
- Others exist (RACHEL, Otter/LibraryBox descendants) but IIAB and Kiwix Imager are the two actively maintained mainstreams — stick to them.

---

## 6. Discovery ("captive-portal-style")

Goal: user joins wifi, content appears with zero typed URLs.

1. **Wildcard DNS:** dnsmasq `address=/#/10.10.10.1` — every hostname resolves to the box. Any typed URL lands on the landing page.
2. **Captive-portal detection triggers:** answer the OS probe URLs (`captive.apple.com`, `connectivitycheck.gstatic.com/generate_204`, `www.msftconnecttest.com/connecttest.txt`) with a redirect to the landing page → **iOS/Android auto-pop the "sign in to network" sheet showing your library**. IIAB ships this ("captive portal" install option); on GL.iNet/OpenWrt front-router, `opkg` nodogsplash or simple nginx rules on the server do it. Caveat: some Android builds mark the network "no internet" and nag — IIAB's implementation handles the common cases; test on your actual devices *before* grid-down.
3. **Memorable name:** SSID `LIBRARY` (open, no password — WPA2 adds nothing against a neighbor you'll be sharing with anyway, and open + captive-pop is smoother; add WPA2 only if you must ration battery/clients), plus `http://library.lan` and mDNS `library.local` for Apple devices.
4. **Physical fallback:** QR-code sticker (wifi-join QR + URL QR) laminated on the box lid.

---

## 7. Maintenance & update procedure (while grid is up)

Run this loop **quarterly**, ~2 hours:

1. **Content refresh:** download updated ZIMs (`kiwix-manage` + rsync from download.kiwix.org — ZIMs are versioned monthly), Kolibri channel updates, new OSM extract yearly.
2. **OS packages:** `apt update && apt upgrade` *within the pinned stable release only*; refresh the local apt mirror afterward.
3. **Verify serving:** join the wifi with a phone, confirm captive-pop, search Kiwix, open a map tile, play one video. A 5-minute manual smoke test beats monitoring infrastructure you can't act on anyway.
4. **Backup sync:** plug in cold SSD → `rsync -a --delete --checksum-choice=xxh3` → regenerate sha256 manifest → spot-verify 5 random files → unplug, back in the Faraday box with the rest of the electronics.
5. **Battery care:** LiFePO4 stored at 50–60% SoC if the box is in standby mode; top-charge and log resting voltage quarterly. Exercise the solar charge path once a year.
6. **Image the boot drive:** after any config change, `dd`/rpi-clone the boot SSD to the spare microSD.
7. **Freeze protocol (grid-down imminent):** final content sync, final backup sync, `apt-mark hold` everything, print this document + the network config + IPs and tape it inside the lid.

Log each cycle in a paper notebook kept with the box.

---

## 8. Recommended reference build (Pi 5, ~$700 all-in)

| Part | Price |
|---|---|
| Raspberry Pi 5, 16 GB | $120 |
| Raspberry Pi M.2 HAT+ (or Pimoroni NVMe Base) | $15 |
| 4 TB NVMe SSD (WD SN770 class) ×2 (primary + cold backup) | $440 |
| Active cooler (official) | $6 |
| Case fitting HAT (Argon NEO 5 M.2 or similar) | $20 |
| DS3231 RTC module | $5 |
| GL.iNet Beryl AX (GL-MT3000) router | $90 |
| GL.iNet Opal (GL-SFT1200) cold-spare router ×1 | $40 |
| 12V→5V 5A USB-C buck converter (quality, 25 W+) ×2 | $30 |
| 64 GB microSD (boot recovery clone) ×2 | $16 |
| Fused 12V distribution block + wiring | $25 |
| **Subtotal, serving box** | **~$807** |
| 12.8V 100Ah LiFePO4 battery (LiTime class) | $170 |
| Victron SmartSolar 75/10 MPPT | $70 |
| 100 W solar panel | $80 |
| **Total with power system** | **~$1,130** |

Software: Pi OS Lite 64-bit + IIAB 8.3 (full install: Kiwix, Kolibri, OSM maps, captive portal, admin console), Beryl AX as AP/DHCP/DNS in front, wildcard DNS + captive-pop, ext4, quarterly maintenance loop. Runs 24/7 forever on the 100 W panel; ~8 days on battery alone.

## 9. Budget Pi build (~$220 all-in, no dedicated power system)

| Part | Price |
|---|---|
| Raspberry Pi 5, 8 GB (or Pi 4 4GB, $55, if found cheaper — IIAB supports it) | $80 |
| M.2 HAT + 2 TB NVMe | $15 + $110 |
| Active cooler + basic case | $16 |
| **Total** | **~$221** |

Uses **onboard wifi via IIAB's hostapd setup** (no router), boots/serves from the 2 TB NVMe, powered by whatever USB-C PD source is around (any 27 W PD power bank ≈ 15–20 h; car 12V + buck; existing solar generator). Backup = a $60 2 TB external SSD synced quarterly instead of a second NVMe. Software path of least resistance: **Kiwix Imager Service ready-made image** if Kiwix-only, or IIAB 1-liner for the full stack. Skips: Kolibri (RAM/battery), spare router, RTC (accept clock drift, re-set by hand). Add each when the gap bites.

---

## Key risks / tradeoffs flagged

- **Mac Mini's AC-only input is the deal-breaker**, not its efficiency — inverter idle loss dominates. Confidence: high.
- Pi 5 brownouts under cheap 5V converters are the most common field failure — buy the good buck converter twice.
- Captive-portal behavior varies by Android vendor build; test on the household's actual devices before you need it.
- ZIM sizes grow ~10%/yr; 4 TB primary gives ~a decade of headroom.
- All-eggs-one-SSD is the real long-tail risk; the cold spare + quarterly checksum verify is the mitigation, not RAID.

## Sources

- [Apple: Mac mini power consumption](https://support.apple.com/en-us/103253) · [Notebookcheck M4 review](https://www.notebookcheck.net/Apple-Mac-Mini-M4-review-Smaller-faster-and-louder.918832.0.html) · [Jeff Geerling M4 efficiency](https://www.jeffgeerling.com/blog/2024/m4-mac-minis-efficiency-incredible/) · [ServeTheHome M4](https://www.servethehome.com/the-apple-mac-mini-m4-sets-the-mini-computer-standard/3/)
- [raspberry.tips Pi power tests 2026](https://raspberry.tips/en/raspberrypi-tutorials/raspberry-pi-power-consumption-update-2026-all-models-compared) · [Pimoroni forum Pi5+NVMe measurements](https://forums.pimoroni.com/t/pi-5-power-consumption/23959/8)
- [N100 idle/load measurements](https://bishalkshah.com.np/blog/low-power-homelab-n100-mini-pc) · [minilabhq N100 power](https://minilabhq.com/posts/n100-mini-pc-power-consumption/) · [CNX Beelink EQ12 review](https://www.cnx-software.com/2023/05/16/beelink-eq12-review-intel-processor-n100-mini-pc-windows-11-truenas-pfsense-ubuntu/)
- [IIAB 8.3 release notes](https://github.com/iiab/iiab/wiki/IIAB-8.3-Release-Notes) · [IIAB Pi images](https://github.com/iiab/iiab/wiki/Raspberry-Pi-Images-~-Summary) · [internet-in-a-box.org](https://internet-in-a-box.org/)
- [Kiwix Imager Service](https://get.kiwix.org/en/solutions/hotspots/imager-service/) · [Hotspot Imager 3.0](https://kiwix.org/en/hotspot-imager-3-0-is-out/) · [DIY Pi Kiwix hotspot writeup](https://sven-seeberg.de/wp/?p=1241)
- [LiTime 12V 100Ah LiFePO4](https://www.litime.com/products/litime-12v-100ah-lithium-lifepo4-battery) · [GrenerPower 100Ah pricing](https://grenerpower.com/products/grenerpower-12v-100ah-lifepo4-lithium-battery)
