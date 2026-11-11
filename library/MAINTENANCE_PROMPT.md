# MAINTENANCE_PROMPT.md — Quarterly Library Maintenance

**How to use:** Copy everything below the horizontal rule and paste it into an AI coding agent on a laptop that is either ssh'd into the library box or on the same network. The agent reads this file, runs all automated checks, and tells you exactly what it found and what you need to do physically.

Do this once a quarter while grid power is available. Budget about two hours, most of which is unattended.

---

## PASTE THIS INTO YOUR AI AGENT

You are running the quarterly maintenance cycle for an offline library box (Raspberry Pi 5). Seven services start on boot: `nginx` (the library pages and the pagefind search), `kiwix` (kiwix-serve, the encyclopedias, port 8080), `kolibri` (lessons, port 8081), `lantern-embed` (the meaning-based search model, port 8091, box only), `lantern-mcp` (search for AI assistants, port 8090, reached at /mcp and /semantic), `lantern-voice` (speech to text, port 8092, reached at /stt) and `lantern-discs` (mounts the CD3WD disc images at /discs/). The box IP is 10.10.10.10 and its hostname is library.lan. You are either ssh'd into the box or on the same Wi-Fi network as it.

Work through the following steps in order. After each step report what you found. When a step fails, tell the human operator what went wrong and what to do — do not silently skip failures.

---

### STEP 1 — Verify all seven services are healthy

Run these checks. Expected outputs are shown.

**1a. nginx (static library + captive portal)**

```
curl -sf --max-time 10 http://library.lan/ | grep -c '<title>'
```

Expected: `1` (any non-zero). If curl times out or returns an error, nginx is down.

```
curl -sf --max-time 10 http://library.lan/triage.html | grep -c 'triage'
```

Expected: `1` or more.

**1b. Kiwix-serve (ZIM encyclopedias)**

```
curl -sf --max-time 10 http://library.lan:8080/catalog/v2/entries?count=1 | grep -c '<entry>'
```

Expected: `1` or more. If this fails, kiwix-serve is not running or has no ZIMs loaded.

**1c. Kolibri (educational channel server)**

```
curl -sf --max-time 15 http://library.lan:8081/api/public/v1/channels | grep -c '"id"'
```

Expected: `1` or more. Kolibri is slow to start — if this fails, wait 60 seconds and retry once before declaring it down.

**1d. Pagefind search index**

```
curl -sf --max-time 10 http://library.lan/search.html | grep -c 'pagefind'
```

Expected: `1` or more. If this fails, the search page is broken; note it but continue.

**1e. MCP server (lantern-mcp, port 8090 proxied at /mcp)**

```
curl -sf --max-time 10 -X POST http://library.lan/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"maintenance-check","version":"1.0"}}}' \
  | python3 -m json.tool
```

Expected: a JSON response containing `"result"` with `"protocolVersion"` and `"serverInfo"`. If you get a connection refused or a non-JSON body, the MCP server is down.

**1f. lantern-embed (meaning-based search, behind /semantic)**

```
curl -sf --max-time 30 'http://library.lan/semantic?q=boil+water&limit=3' | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))'
```

Expected: `1` or more. `0` means the embedding service is down (keyword search still works). If you are ssh'd into the box, `curl -s http://127.0.0.1:8091/health` should print `{"status":"ok"}`; port 8091 is closed to the Wi-Fi.

**1g. lantern-voice (speech to text, behind /stt)**

```
curl -s --max-time 10 -X POST -F x=1 http://library.lan/stt
```

Expected: `{"error": "multipart field 'file' required"}`. That reply comes from the voice service itself, so it is running; it was sent no recording on purpose. A `502 Bad Gateway` page means it is down.

**1h. lantern-discs (CD3WD disc images at /discs/)**

```
curl -sf --max-time 10 http://library.lan/discs/1001_cd3wd/ | grep -c 'href='
```

Expected: more than `1`. A count of exactly `1` (only the `../` link) means the disc is not mounted. On the box, `mount | grep -c ' /srv/discs/'` should equal `ls /srv/discs | wc -l` (26 discs).

**1i. Smoke-test one ZIM article**

Take the first encyclopedia in the Kiwix catalog, open its main page, and confirm the body length is greater than 500 bytes. Kiwix serves on port 8080; nginx has no `/kiwix/` path.

```
B=$(curl -sf --max-time 10 'http://library.lan:8080/catalog/v2/entries?count=1' | grep -o 'href="/content/[^"]*"' | cut -d'"' -f2)
echo "$B"
curl -sfL --max-time 15 "http://library.lan:8080$B" | wc -c
```

`echo` should print a path like `/content/<book name>`. If it prints nothing, the catalog check in 1b failed too.

**Report after Step 1:** List each service as OK or FAILED with the exact error you saw.

**If any service is FAILED:**

- Check the units on the box: `systemctl is-active nginx kiwix kolibri lantern-embed lantern-mcp lantern-voice lantern-discs` should print `active` seven times. For the one that is not, `systemctl status <name>` (the encyclopedia unit is `kiwix`, not kiwix-serve).
- If a service is stopped: `sudo systemctl start <name>` then recheck.
- If it won't start, capture `journalctl -u <name> -n 50 --no-pager` and show the last 20 lines to the operator.
- Tell the operator: "Service X is down. Here is the error. Try rebooting the box (cut power, wait 10 s, restore, wait 3 min) and then run this maintenance prompt again. If it still fails after reboot, note it in the paper log and schedule a repair session."

---

### STEP 2 — Run the full manifest verify (overnight-safe)

This step hashes every file in the library and compares against the stored manifest. It takes 1.5 to 2 hours on the Pi for the full library (about 1.3 TB; sha256sum hashes about 220 MB a second there) and prints nothing until it ends. Run it with `nohup` in the background so it survives the ssh session closing. (`screen` is not on the box; `nohup` always is.)

**2a. Start the verify in the background:**

```bash
sudo -v   # type the password now, so the background job does not stop to ask for it
D=$(date +%F); echo "$D"   # note this date: Step 2c reads the files named with it
sudo nohup sh -c "cd /data && sha256sum -c --quiet library/MANIFEST.sha256 > /home/lantern/verify_$D.log 2>&1; echo \"finished, exit \$?\" > /home/lantern/verify_$D.done" > /dev/null 2>&1 &
```

The prompt comes back at once; the check keeps running after you close ssh. `pgrep -a sha256sum` shows it while it runs.

**2b. Tell the operator:**

> "HAND TO HUMAN: The manifest verify is running in the background on the Pi. It will run for about 2 hours, so leave it overnight. Come back tomorrow morning and run Step 2c."

**2c. (Next morning) Check the result.** Set `D` to the date 2a printed (a new ssh session does not keep it). The first line lists the files newest first, with their dates, if the date was lost:

```bash
ls -t /home/lantern/verify_*
D=2026-10-27                        # the date 2a printed
cat /home/lantern/verify_$D.done    # "finished, exit 0" = done, every file matched
tail -30 /home/lantern/verify_$D.log  # empty when all OK; one line per bad file otherwise
```

If there is no `verify_$D.done` yet, the check is still going (`pgrep -a sha256sum` shows it): wait and look again later. If there is no `verify_$D.done` and `pgrep` shows nothing, the run stopped (power cut, reboot): start 2a again. A `.done` file with an older date is from an earlier quarter and says nothing about this run.

**Expected output (all OK):** an empty log. `sha256sum -c --quiet` prints nothing when every file matches; `wc -l` on the log should print `0`.

**Expected output (failures):**

```
library/_app/text/docs/...: FAILED
library/zim/...: FAILED open or read
(one line per bad file; the log is EMPTY when everything is OK)
```

**If there are failures:**

- Fewer than 5 corrupt or missing files: these are likely individual bit-rot events. Note each file path. Check if the cold backup SSD (Samsung T5, label LANTERN_BAK) has a clean copy by running the same script against the SSD after Step 3 physical tasks. If the SSD copy is clean, rsync the specific files back from it.
- More than 5 failures or failures in core system files (nginx config, pagefind index, RUNBOOK.md, triage.html): this may indicate drive degradation. Tell the operator: "The NVMe drive may be failing. Do a full rsync restore from the cold SSD as described in RUNBOOK Part 3 rebuild procedure, and consider replacing the NVMe."
- Any failure in `library/MANIFEST.sha256` itself: the manifest is corrupted. Restore it from the cold SSD first, then re-run the verify.

---

### STEP 3 — Physical tasks (hand to human)

You cannot perform these steps. Present them to the operator clearly.

---

> **HAND TO HUMAN — Physical Maintenance Steps**
>
> The automated checks are done (or running). Now do these physical steps. Check each one off in your paper notebook.
>
> **A. Cold SSD backup sync (Samsung T5, label LANTERN_BAK)**
>
> 1. Take out the silver Samsung T5 SSD (kept with the spare microSD card).
> 2. Plug it into the library box via USB.
> 3. Tell the agent: "SSD is plugged in — run the backup sync."
>
> The agent will then run:
>
> ```bash
> sudo mkdir -p /mnt/bak
> mountpoint -q /mnt/bak || sudo mount -L LANTERN_BAK /mnt/bak
> mountpoint -q /mnt/bak && echo SSD mounted || echo "STOP: SSD not mounted"
> mountpoint -q /mnt/bak && sudo rsync -aH --delete --info=progress2 /data/library/ /mnt/bak/library/
> mountpoint -q /mnt/bak && (cd /mnt/bak && sudo sha256sum -c --quiet library/MANIFEST.sha256) && echo backup OK
> sudo umount /mnt/bak
> ```
>
> If the third line prints "STOP: SSD not mounted", the agent stops there and tells you: the copy would otherwise fill the Pi's own small system disk. Check the SSD's cable and port, unplug and replug it, and tell the agent to try again. The copy and check lines only run when the SSD is mounted.
>
> The sync copies only what changed, usually a few minutes. The `sha256sum -c` line then checks every file on the SSD against the seal, which takes 1.5 to 2 hours. You will see "backup OK", or a list of the files that failed.
>
> 4. Unplug the T5 and put it back with the spare microSD card. When the session is over, all of the electronics (the Pi with its drive, the router, the T5, the recovery cards and the power banks) go back in the Faraday box, not only the T5.
>
> **B. T5 power-on verify (quarterly)**
>
> This is already covered by step A above — plugging in and running the full check IS the power-on verify. If the drive fails to mount or is unreadable, tell the agent and it will walk you through diagnosis.
>
> **C. Boot-test one microSD clone (yearly — skip if not a yearly cycle)**
>
> Once a year, test the fallback on purpose (RUNBOOK Part 2, steps 3a and 3b): power off, unclip the NVMe ribbon, plug the T5 into a blue USB port, power on, wait 3 minutes. The Pi starts from the microSD in the slot and serves the library from the T5. Tell the agent to run the Step 1 checks (Kolibri is expected to be down in this mode). Power off, reattach the ribbon, unplug the T5, power on, wait 3 minutes, confirm normal operation.
>
> **D. Battery top-up (per RUNBOOK Part 4 chemistry rules)**
>
> - USB battery banks (Li-ion): top up to 50–60% (2–3 LEDs on a 4-LED indicator) every time the T5 is plugged in for step A, and at least every 6 months. They are stored in the Faraday box with the rest of the electronics. Replace any bank that noticeably holds less charge than before.
> - LiFePO4 large battery (if installed): top-charge, measure resting voltage after 1 hour off charger (healthy = ~13.2–13.3 V). Log in paper notebook.
>
> **E. Spare router power-on (yearly — skip if not a yearly cycle)**
>
> This build has no spare router. Once a year, confirm the replacement checklist in RUNBOOK Part 3 still matches the router's admin page (LAN 10.10.10.1, fixed lease for the Pi, wildcard DNS).
>
> **F. Log the cycle**
>
> In the paper notebook kept with the box, write:
> - Date
> - Manifest result (ALL OK / N failures)
> - Services status (all OK / list failures)
> - SSD sync: done
> - Battery status: topped up
> - Any notes on failures or unusual findings

---

### STEP 4 — Content refresh (do after physical steps)

**4a. ZIM refresh check**

Check whether newer ZIM files are available. You cannot download them from here if offline, but note what versions are currently installed:

```bash
ls -lh library/zim/*.zim 2>/dev/null || ls -lh /data/library/zim/*.zim 2>/dev/null
```

Note the filenames (they include the date, e.g., `wikipedia_en_medicine_2024-05.zim`). If grid access is available, check https://download.kiwix.org/zim/ for newer versions. If a newer version is available, tell the operator: "ZIM [name] has a newer version [date]. Download it next time you have fast internet and replace the old file, then regenerate the pagefind index."

**4b. System updates**

If the box has internet access:

```bash
sudo apt update && sudo apt upgrade -y
```

If you are offline (normal maintenance mode), skip this. Note in the log: "apt upgrade skipped — offline."

**4c. After any content change**

Do NOT regenerate `MANIFEST.sha256` on the box. The manifest is the seal: it is produced on the build machine with the generated pages, and `REFRESH.md` describes a reseal. If you restored individual files from the backup SSD, re-run Step 2 on just those files:

```bash
cd /data && grep -F 'library/<path you restored>' library/MANIFEST.sha256 | sudo sha256sum -c --quiet
```

An empty result means the restored file matches the seal.

The microSD cards hold the boot image, not the library, so a content change needs no card rewrite. The cards are rewritten only at an image release (RUNBOOK Part 3).

---

### STEP 5 — Final report

When all steps are done, give the operator a summary in this format:

```
=== QUARTERLY MAINTENANCE REPORT — [DATE] ===

Services:
  nginx          : OK / FAILED
  kiwix          : OK / FAILED
  kolibri        : OK / FAILED
  pagefind       : OK / FAILED
  lantern-embed  : OK / FAILED
  lantern-mcp    : OK / FAILED
  lantern-voice  : OK / FAILED
  lantern-discs  : OK / FAILED

Manifest verify:
  Checked   : N files
  OK        : N
  CORRUPT   : N
  MISSING   : N
  Result    : ALL OK / FAILURES (see log path)

Physical steps completed (operator confirms):
  [ ] SSD backup sync
  [ ] Battery top-up
  [ ] Spare router verify (yearly)
  [ ] microSD boot test (yearly)
  [ ] Paper log entry

Content changes this session:
  [list any files changed, restored, or updated]

Next scheduled maintenance: [date + 3 months]

Outstanding issues requiring follow-up:
  [list any unresolved failures or recommendations]
```

---

END OF AGENT PROMPT

---

## Notes for the operator

Run this prompt quarterly, ideally on the same day each quarter so it becomes a habit. The automated steps (Steps 1–2, 4) take a few minutes to start and then run unattended. The physical steps (Step 3) take about 30 minutes of hands-on time, plus 1.5 to 2 hours of waiting while the SSD copy is checked. The manifest verify runs overnight.

If you are training a second operator, have them run this full prompt with you present once before they do it alone. The physical steps are the ones most likely to need explanation — the agent narrates each one.

If something fails and you cannot resolve it: note it in the paper log, do not skip the other steps, and refer to RUNBOOK Part 2 for hardware diagnosis.
