# MCP Server Plan — Lantern Library (v2, post adversarial vetting 2026-09-19)

Goal: any MCP-speaking client on the LIBRARY WiFi (future phone with local
model) can search the library, read documents as paginated plain text, and
run structured dataset lookups — with the Part 5 content-safety rules
enforced SERVER-SIDE (the visiting model's prompt cannot be trusted).

## Decisions

- **Stdlib-only Python, no pip.** Matches the image doctrine ("hand-rolled
  for image reproducibility, NO IIAB"). MCP surface implemented directly:
  JSON-RPC 2.0 over Streamable HTTP (POST /mcp, application/json responses —
  spec-legal without SSE). Methods: `initialize`, `notifications/initialized`,
  `ping`, `tools/list`, `tools/call`. No sessions state needed (stateless
  server; echo an `Mcp-Session-Id` for client comfort).
- **Search backend = SQLite FTS5** (bundled in Python), built at library
  build time from existing artifacts — NOT a new content pipeline:
  - `_app/text/**/*.html` — the 631 pdftotext-extracted PDFs, per-page
    (`<h2 id="pN">` structure) → FTS rows (path, title, shelf, page, body).
  - `_app/index/titles.json` — all ~9.7k titles → title-search FTS table.
  - mirrors (hesperian/nchfp/ready_gov, EN html) → FTS rows, tag-stripped.
- **ZIM fulltext = proxy kiwix-serve** (`http://127.0.0.1:8080/search?pattern=`)
  when reachable (2 s timeout); merged into search results, degraded
  silently on dev Mac where kiwix-serve is absent. `read_document` accepts
  kiwix paths (`zim/<book>/<path>`) and returns tag-stripped article text.
- **Port 8090** on the Pi; nginx `location /mcp` proxy + `/.well-known/mcp.json`
  + `/llms.txt` for discovery. systemd unit `lantern-mcp.service` (5th service).

## Tools (6)

1. `search_library(query, shelf?, limit=10)` — FTS5 (pages + titles) +
   kiwix merge. Each hit: title, path, page, snippet, shelf, open-URL.
2. `read_document(path, page?=1, pages?=3)` — paginated plain text.
   PDF → serve from the pre-extracted text wrappers (only whitelisted PDFs
   readable; others return "no text layer / not extracted, open <url>").
   HTML/MD → tag-stripped. ZIM → kiwix content proxy, tag-stripped.
3. `list_shelves()` — shelves.json verbatim (curated order, counts, descs).
4. `sun_times(lat?, lon?, date?)` — NOAA solar calc, pure python (~40 lines),
   defaults from `_app/config.json` homeRegion. Sunrise/set/noon/daylength.
5. `climate_normals(lat?, lon?, month, day?)` — nearest station (station
   table built from CSV first-rows), aggregate hourly-normals CSV to
   temp min/mean/max, wind, cloud stats for that month(/day).
6. `callsign_lookup(callsign)` — FCC l_amat EN.dat → sqlite table
   (callsign, name, city, state). Identify who you hear on ham bands.

## Server-side guardrails (the design constraint)

- **Dose-guard**: DRUGS list + dose-keyword regex parsed AT BUILD TIME out of
  `search.html` (single source of truth, no drift). Matching queries in
  `search_library`: body snippets suppressed, titles/links kept, dosing-card
  notice injected (same doctrine as G3, exact same trigger logic).
  `read_document` is NOT dose-gated (deliberate: G3 gates search surface,
  not the books themselves — links "still open the full books").
- **HISTORICAL**: any result/document under `docs/HISTORICAL/` gets the
  README-WARNING.txt text prepended verbatim in the tool response.
- **initialize response `instructions` field**: content-safety preamble
  (doses = printed card only; no plant-ID inference — lookalike warnings
  verbatim; canning = USDA/NCHFP only; "AI must verify against primary
  sources" banner rule from tools/README.md).
- No plant-ID tool. No drug_label tool v1 (dailymed = 19 GB raw SPL zips;
  extraction deferred, and dosing policy makes it low-value — Phase 2 note).
- Read-only server; no write tools; no auth (network is open by design);
  bind 0.0.0.0 on Pi (LAN-only network), :8090.

## Files

| File | What |
|---|---|
| `server/build_mcp_index.py` | builds `library/_app/mcp/mcp.db` (FTS5 pages+titles, guard list, climate stations, fcc callsigns) |
| `server/mcp_server.py` | stdlib ThreadingHTTPServer, JSON-RPC/MCP, 6 tools |
| `server/test_mcp.py` | end-to-end test suite (below) |
| `library/.well-known/mcp.json` | discovery doc (endpoint URL, name, tool summary) |
| `library/llms.txt` | machine-readable library map + MCP pointer |
| `image/stage-lantern/00-lantern/files/lantern-mcp.service` | systemd unit |
| `image/.../nginx-lantern.conf` | + `location /mcp` proxy, `.well-known` |
| `image/.../01-run.sh` | install server + unit, enable service |

`mcp.db` lives in `_app/` (generated, like pagefind bundle): added to
MANIFEST.sha256 via the standard refresh + set-compare. `.well-known/mcp.json`
+ `llms.txt` are content → manifest too.

## Test plan (`test_mcp.py`, stdlib urllib, server on :8090)

1. MCP handshake: initialize → capabilities.tools, instructions non-empty;
   tools/list returns exactly 6 tools with valid JSON schemas.
2. Search positive: "pickled beets" → nchfp hit with page number;
   "thermophilic compost" → g2 sanitation doc (matches acceptance fixtures).
3. **Dose NEG probe** (mirrors acceptance_run hardening): "ibuprofen dose"
   → notice present, zero body snippets, NO `\d+ *mg` anywhere in response.
4. HISTORICAL probe: search hitting HISTORICAL doc → warning text present.
5. read_document: known wrapper PDF page text matches pdftotext output;
   page beyond EOF → clean error; non-extracted PDF → fallback message.
6. sun_times: Redwood City 2026-09-19 sunrise within [05:30, 07:30] PT,
   daylength ~12.2 h ±15 min (equinox sanity).
7. climate_normals: KALISPELL station lat/lon → returns that station,
   January mean below July mean.
8. callsign_lookup: known callsign from EN.dat sample row.
9. Protocol errors: unknown method → -32601; malformed JSON → -32700;
   unknown tool → tool error, not crash.
10. Concurrency smoke: 8 parallel searches, all 200, < 2 s each.

Dev run: server in screen (`mcp8090`), tests via no-sandbox (localhost
gotcha). Kiwix merge path tested only for graceful-absence on Mac; on-Pi
kiwix proxy verified at next C4 image simulator run (add to acceptance).

## v2 AMENDMENTS (adversarial vetting outcomes — BINDING)

P0 (all must ship):

1. `read_document` path canonicalization: realpath-resolve, containment
   check under library root AFTER symlink resolution, reject `..`,
   absolute paths, `%2e%2e`. Traversal probes in test 9.
2. Historical gating source of truth = `shelves.json` `historical: true`
   flags (covers BOTH `docs/HISTORICAL` and `docs/survivor_library`),
   NEVER a hardcoded path.
3. Guard-list build FAILS HARD if <100 drug names parsed from search.html;
   dose-keyword regex must match search.html:156 semantics
   (`dose|doses|dosage|dosages|dosing|mg|milligram|milligrams` token match).
   Note: G3 list edits in search.html require index rebuild to propagate.
4. Dose-guard decision made ONCE per query, applies to ALL result sources
   including kiwix-merged snippets (kiwix results = titles+links only when
   guard trips).

P1: kiwix proxy pinned to configured host, paths restricted to `/search`
and `/content/...` only; ready_gov indexed EN ONLY; add 2 on-Pi checks to
C4 acceptance (kiwix-merged search hit; /mcp via nginx answers initialize).

P2: echo client's protocolVersion when recognized; GET /mcp → 405; answer
application/json even when client Accepts text/event-stream (spec MAY).

Design rationale (do not relitigate): `read_document` is NOT dose-gated —
matches shipped G3 decision, "links still open the full books"; G3 gates
the search surface only.

Precompute doctrine: library is FIXED after freeze — precompute
everything possible at build time. Climate: monthly aggregates
precomputed into db (no runtime CSV scans). Reuse `_app/text/mirrors/`
wrappers if present rather than re-stripping raw mirror HTML.

Build order: `build_mcp_index.py` runs AFTER build_frontend/gen_text
(consumes `_app/text`, `_app/index/*.json`, `search.html`).

## DB CONTRACT (agents build/consume independently — do not deviate)

Path: `library/_app/mcp/mcp.db` (SQLite, gitignored, manifested).

```sql
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
  -- keys: built_at, pages_count, titles_count, guard_count, schema_version=1
CREATE VIRTUAL TABLE pages USING fts5(
  body, title, path UNINDEXED, shelf UNINDEXED, page UNINDEXED,
  tokenize='porter unicode61');           -- page = INT-as-text, 0 if n/a
CREATE VIRTUAL TABLE titles USING fts5(
  title, path UNINDEXED, shelf UNINDEXED, tokenize='porter unicode61');
CREATE TABLE guard_drugs(name TEXT PRIMARY KEY);
CREATE TABLE stations(id TEXT PRIMARY KEY, name TEXT, lat REAL, lon REAL);
CREATE TABLE normals(station TEXT, month INT, tmin REAL, tmean REAL,
  tmax REAL, wind_avg REAL, PRIMARY KEY(station, month));  -- °F, mph
CREATE TABLE callsigns(callsign TEXT PRIMARY KEY, name TEXT, city TEXT,
  state TEXT);
```

`path` always relative to library root, URL-decoded, no leading slash.

## SERVER CONTRACT

`server/mcp_server.py`, stdlib only, Python 3.11+ compatible
(Pi OS ships 3.11; dev Mac 3.14). Args:
`--library PATH --port 8090 --kiwix http://127.0.0.1:8080 --db PATH`
(db default `<library>/_app/mcp/mcp.db`). Threading HTTP server,
POST /mcp JSON-RPC 2.0: initialize, notifications/initialized (202),
ping, tools/list, tools/call. Stateless. Tool errors = result with
`isError: true`, protocol errors = JSON-RPC error codes.
Server reads at startup: shelves.json (historical flags + shelf order),
config.json (homeRegion). Historical warning text loaded from
`docs/HISTORICAL/README-WARNING.txt`.

## Out of scope v1 (explicit)

- drug_label/dailymed extraction (Phase 2; dosing stays on printed card).
- Plant identification inference.
- MCP resources/prompts capabilities, SSE streaming, sessions, auth.
- Triage as bespoke tool — triage.html readable via read_document; the
  interactive tree stays a human UI.
- Landing-page HTML changes (generated; llms.txt + .well-known suffice).
