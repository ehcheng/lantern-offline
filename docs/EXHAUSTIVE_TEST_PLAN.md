# Exhaustive content test — plan (2026-09-28, before the next reseal)

Goal: every file in the library is proven present, valid, served, reachable
from a page, findable by search, and renderable, before we seal and build
LOCK 1.0.1. Deterministic checks do the work and write a per-file verdict.
Low-cost agents only babysit runs, triage failures, and sample-review the
few things that need eyes. Nothing streams into the TUI.

Inventory under test (MANIFEST 269,052 lines): kolibri_data 111,991,
_app 80,633 (text wrappers, pagefind, indexes), maps 33,053, mirrors 31,512,
docs 8,959, audio 1,565, tools 779, datasets 475, zim 38, video 20, root 30.
By type: vtt 54k, html 37k, jpg/png/gif/webp 45k, pdf 19.5k, txt 15.7k,
mp4 11.5k, ENC .000 7.3k, perseus 7.3k, h5p 6.7k, zip 4.5k, mp3 1.6k,
kap 1.5k, bsb 660, pbf 1k, csv 467, plus 26 iso (served via /discs/),
2 pmtiles, 156 mwm, gguf/onnx/apk/dmg/exe/pkg/appimage.

## Ground rules

- Every check emits one CSV row: `tier,check,path,status,detail`
  (status PASS/FAIL/SKIP) into `tests/results/<tier>.csv`.
  Runs are idempotent and resumable: a runner skips paths already PASS.
- `tests/report.py` folds the CSVs into
  `tests/REPORT.md`: totals per tier, every FAIL with its
  detail, and the pre-declared known failures netted out.
- Logs go to `tests/logs/`; runners are launched with
  `screen -dmS ex_<tier> bash <script>` (no-sandbox), never in the
  foreground. Progress is read with `grep -c PASS results/<tier>.csv`.
- Concurrency (AGENTS.md): CLI fan-out with `xargs -P 16` on the M2 Ultra;
  Pi HTTP crawl with 16 keep-alive connections; at most 6 babysitter agents
  (haiku) alive at once in an interactive session, 12 under tmux. Each agent
  owns one tier, writes findings to a file, returns one paragraph.
- Pre-declared known failures (must appear in results, must not block):
  22 PDFs that fail text extraction (`grep 'FAIL extract' logs/b5_reseal_r6.log`),
  6 scans with no text after OCR (`cache/ocr/spotcheck.md`), and the
  removed `Refrigeration_*` paths that pagefind/mcp.db/embeddings still list
  until the reseal rebuilds them.

## Tiers

### T0 Integrity (Pi and dev tree)
- `sha256sum -c --quiet MANIFEST.sha256` on the Pi (`vb.sh` pattern, ~2 h,
  detached) and on the dev tree (`shasum` via xargs -P 16).
- Disk-vs-manifest set diff both sides (the b5_reseal gate, run standalone):
  0 missing, 0 extra, with the kolibri runtime exclusions.
- Zero-byte files, dangling symlinks, files with `.Conflict`/`_` sync
  suffixes or `._*`/`.DS_Store` names anywhere in the tree: expect none.
- SSD backup: same sha256 pass after the reseal rsync (already scripted).

### T1 Format validity (dev tree, one tool per type, all deterministic)
| Type | Check | Tool |
|---|---|---|
| pdf (19.5k) | opens, page count > 0, no structural error; for docs/ also text chars on first 3 pages > 0 unless on the known-no-text list | `pdfinfo`, `qpdf --check`, `pdftotext -l 3` |
| jpg/png/gif/webp/jpeg (45k) | decodes fully | Python PIL `Image.open().verify()` then `.load()` |
| mp4 (11.5k), mp3 (1.6k) | probe ok, duration > 0, mp4 is h264+aac (phone browsers) | `ffprobe -v error -show_streams` |
| vtt (54k) | parses, cue count > 0, timestamps monotonic | Python `webvtt` or a 30-line parser |
| html/htm (38k) | parses, no empty body, every relative href/src resolves on disk | `crawl_check.py` extended |
| txt/md/csv | utf-8 decodes; csv parses with a stable column count | Python |
| zip (4.5k), h5p (6.7k), perseus (7.3k) | archive integrity | `unzip -tq` / `zipfile.testzip()` |
| kolibri sqlite (channel DBs) | `PRAGMA integrity_check` = ok | `sqlite3` |
| zim (38) | header magic 5a494d04; kiwix catalog lists it; 25 random articles per book fetch 200 from :8080 | `xxd`, `kiwix-serve` on the dev box |
| iso (26) | mounts read-only, file count > 0 (Pi: already mounted under /srv/discs, count via /discs/ autoindex) | `hdiutil attach -readonly` on Mac / `mount -o loop` on Pi |
| ENC .000 (7.3k) | ISO 8211 leader present (bytes 0-5 digits, "3LE1" at 6) | Python |
| kap/bsb (2.1k) | text header starts `!` or `VER/`, has `BSB/NA=` | Python |
| mwm (156) | Organic Maps magic; size > 1 MB | Python |
| pmtiles (2) | header magic `PMTiles`, tile (0,0,0) decodes | `pmtiles` js or Python |
| pbf | gzip/protobuf opens | Python |
| gguf, onnx, apk, dmg, exe, pkg, appimage | magic bytes match type; sha256 matches the folder's SHA256SUMS | `file`, `shasum` |
| pagefind fragments (_app/pagefind*) | index loads and answers a query | Playwright on search.html (T5) |

Runner: `tests/t1_format.sh` groups paths by extension from
MANIFEST and fans each group through `xargs -P 16` into a per-type checker
(`checks/<ext>.py|sh`) that prints one CSV row per path.

### T2 Serving (Pi, over HTTP)
- HEAD every manifest path on the Pi with 16 keep-alive connections
  (`tests/t2_serve.py`, asyncio): status 200 and
  Content-Length == manifest size. About 269k requests, ~10 min on LAN.
- MIME spot rules on every file of these types: .apk is
  `application/vnd.android.package-archive`, .md is text/plain, .pdf is
  application/pdf, .mp4 answers a Range request with 206, .pmtiles 206.
- /discs/: every mounted disc lists, and 20 random files per disc fetch 200.
- Kiwix: catalog lists all 38 books; 25 random `/content/` fetches per book.
- Kolibri: channels API lists every channel; 50 random content nodes fetch.
- MCP: tools/list, and read_document on 200 random docs paths returns text
  within 2 s each (regression guard for the loc fix).

### T3 Reachability (dev tree)
- Every manifest path under docs/, audio/, video/, maps/, tools/, mirrors/
  entry pages is linked from some generated page (shelf row, plants, audio,
  video, map, tools) or is inside a folder that is linked as a folder.
  Build the set of hrefs from all root pages + `_app/shelf/*.html` +
  `_app/*.html`, resolve, compare to the manifest set. Report unreachable.
- `verify_frontend.py` (already: every href resolves, historical routes via
  the interstitial) = 0 problems.
- Every `.md` has its rendered `.html` sibling and vice versa.
- Every shelf group has a one-line description (gen_shelves WARNING = none).
- Uniformity rule (2026-10-03: "everything in plain page and MCP should be
  accessible from the Lantern site"). `reach_direct`: folder-only reach is a
  FAIL for docs/ PDFs, every datasets/ file (climate_normals station CSVs
  excepted: one described folder row) and every tools/*/README.md; maps and
  mirrors inner files and bulk sets (>200 rows) stay folder-reach. `v1_parity`:
  every index_v1.html link target is linked by a Lantern page, or is a folder
  some Lantern link points into. `mcp_parity`: every mcp.db titles path has a
  Lantern row (direct for docs/ PDFs and datasets/, reachable otherwise).
  Generated pages are read from the dev tree, not the sealed manifest.

### T4 Search coverage (dev DB and indexes)
- Every docs/ PDF path appears in `mcp.db` loc table (page 1) and in the
  pagefind index (by URL); every docs/mirrors HTML page too. Report misses.
- Embeddings: every docs/ path has at least one vector (per-doc for
  historical, per-page otherwise).
- Known-item retrieval: `cache/eval/gen_known_items.py` sample of 500
  pages; expect the source doc in the top 3 for >= 90% (current gold 35/35).
- Title search: every shelf title returns itself at rank 1.
- Semantic cold start after `lantern-mcp` restart < 2 s (T2 on the Pi).

### T5 Rendering (Playwright, dev server :8765, light/dark, 390 and 1200 px)
- Every root page and every `_app/shelf/*.html` and `_app/*.html`: 0
  console errors (LAN LLM probes excluded), breadcrumb present, header
  search present, tab bar on mobile, no horizontal overflow.
- reader.html on 3 random PDFs per shelf: pdf.js draws page 1, page jump
  `&p=N` lands, text layer selectable.
- plants.html: all 62 species render 5 photos each (img naturalWidth > 0).
- audio.html / video.html: every item listed; first item of each group
  starts playback (media `readyState` >= 2).
- map.html: planet tile draws; nautical section links resolve.
- search.html: 20 queries in both modes return rows; historical divider.
- chat.html: mocked-LLM e2e (`pw_chat_e2e.py`) passes.
- Screenshots only on failure, into `tests/shots/`.

### T6 Box behaviour (Pi)
- `live_test.sh` 54/54. c4 sim green on the current image.
- Service restart matrix: restart each of nginx, kiwix, kolibri, lantern-mcp,
  lantern-embed, lantern-voice, lantern-discs; each comes back active and its
  T2 spot check passes within 60 s.
- Power pull: unplug, replug, boot, gate within 3 min; /discs/ mounted;
  journal has no failed units.
- SSD degraded boot is NOT in this plan; it belongs to the reflash rehearsal.

### T7 Judgment sampling (agents, after T1-T5 are green)
- 2% random sample of docs/ PDFs (about 200): an agent reads page 1-3 text
  via read_document and marks garbled/blank/wrong-language. Writes
  `tests/t7_text_quality.md`.
- 30 random shelf groups: description matches the folder's contents.
- 30 random search queries drawn from RUNBOOK/SKILLS topics: top-3 titles
  make sense. Findings, not scores.

### T8 Plain version (index_v1.html, triage_v1.html; dev tree, file://, and the Pi)

The no-script pages that must work from a bare drive in any browser. Before
T8 the only coverage was `plain_test.py` (all links exist, a 5-link browser
sample) inside acceptance and live_test. `t8_plain.py <check>` runs one check
per invocation so one agent can own each, in parallel:

- `static`: no `<script>`, no external asset, charset + viewport, size budget,
  every `#anchor` has its id, ids unique, an h1.
- `links`: every relative href exists on disk and folders are folders;
  `--base http://10.10.10.10/` repeats it as HEAD 200 with `Host: library.lan`.
- `coverage`: every `gen_index.SHELVES` key and every second-level content
  folder in the manifest is linked from index_v1 (itself, an ancestor, or a
  child). This is the check that catches shelves added after the plain page
  was written (8 were missing on 2026-10-03). kolibri_data is SKIP.
- `parity`: every triage_v1 section's text survives into triage.html, every
  anchor and link too (build_triage lifts sections verbatim); index_v1 keeps
  its size line, triage, VERSION.json and runbook links.
- `browser [--shard i/N]`: real Chrome, JavaScript disabled, 390 px: both
  pages plus EVERY link open with no error page, no console error, no
  request leaving file:// (Chrome's own PDF viewer extension is allowed);
  pages have no horizontal overflow and still show an h1 without JS.

Exit: 0 FAIL in all five. Untestable: Safari cannot list folders from a
drive (documented on the page), and the Kiwix app path.

## Orchestration

1. `tests/run_all.sh <tier>` launches one tier in a screen,
   logging to `logs/<tier>.log`, results to `results/<tier>.csv`.
2. Order: T0 on the Pi first (detached, 2 h) while T1 runs on the Mac
   (~40 min with -P 16; the 119 GB Wikipedia zim is catalog+sample only, a
   full `zimcheck` is an optional overnight job). T2, T3, T4 follow; T5 last
   among the deterministic tiers (Playwright, 8 workers, ~30 min with the
   sampling above). T6 needs the box quiet: run after T2.
3. Babysitters: one haiku agent per running tier, prompt = "watch
   logs/<tier>.log and results/<tier>.csv, do not run the checks yourself,
   report stalls (no new rows for 10 min), crashes, and the FAIL count;
   write `tests/notes_<tier>.md`; return one paragraph".
   Max 6 alive. T7 agents start only when T1-T5 report 0 unexplained FAILs.
4. `report.py` runs at the end of every tier; REPORT.md is the artifact.
5. Fix loop: each FAIL becomes a line in the fix list
   (path, tier, cause, fix, commit). Re-run only the failing tier.

## Exit criteria (then merge, reseal, LOCK 1.0.1)

- Every tier's results file is newer than the seal in VERSION.json (report.py marks older ones STALE) and
  T1/T2 show 0 in the "unchecked" column: a tier that never looked at a path proves nothing about it.
  A green REPORT.md with a STALE tag or an unchecked count is NOT green (red team 2026-10-03).
- T0, T2, T3, T6, T8: 0 FAIL.
- T1: 0 FAIL outside the pre-declared lists; those lists unchanged or shrunk.
- T4: 100% of docs/ and mirrors/ paths indexed; known-item >= 90%.
- T5: 0 console errors, 0 render failures.
- T7: findings triaged; anything that is a content error fixed or listed
  as accepted in REPORT.md.

## Build order for the scripts (about a day of work, ponytail)

1. `results` schema + `report.py` (30 lines).
2. `t1_format.sh` + per-type checkers (most are 10-line scripts around an
   existing tool; the image toolset already has pdfinfo, ffprobe, sqlite3).
3. `t2_serve.py` (asyncio HEAD crawler, 60 lines).
4. `t3_reach.py` (href set vs manifest set, 60 lines).
5. `t4_coverage.py` (sqlite + pagefind URL list, 60 lines).
6. `t5_render.py` (Playwright, reuse `pw_chat_e2e.py` and the R5 shoot
   script patterns).
7. `t6_box.sh` (systemctl loop + live_test).
8. Agent prompt template in `tests/BABYSIT_PROMPT.md`.
