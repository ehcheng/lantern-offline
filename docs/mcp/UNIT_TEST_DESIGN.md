# Unit test design — mcp_server.py (2026-09-19)

Complements `test_mcp.py` (e2e over HTTP + real 256MB db). Unit layer:
import `mcp_server` as a module, call functions directly, tiny in-memory
fixture db + temp fixture library. NO HTTP server, NO real db, NO network
→ runs sandboxed in <5 s. File: `server/test_unit.py`, stdlib
`unittest`, `python3 -m unittest` discoverable, nonzero exit on failure.

## Fixture (setUpClass, tempfile.mkdtemp)

Mini library dir: `_app/config.json` (homeRegion Redwood City 37.485,
-122.236), `_app/index/shelves.json` (3 shelves: medical
historical:false, HISTORICAL historical:true path docs/HISTORICAL,
survivor_library historical:true), `docs/HISTORICAL/README-WARNING.txt`
("HISTORICAL WARNING TEXT"), one real file `docs/medical/x.html`
("<h1>Wound Care</h1><p>irrigate &amp; dress</p>"), a symlinked
top-level dir (symlink `docs` variant — see T2.5), an outside-root file
`/tmp.../outside.txt`. Fixture db (contract schema): pages rows for
docs/medical/a.pdf pages 1-3, docs/HISTORICAL/old.pdf page 1,
docs/survivor_library/s.pdf page 1; titles rows; guard_drugs
('ibuprofen','aspirin'); stations (KALI 48.3042,-114.2636 + FAR
0.0,0.0); normals (KALI months 1 tmean 24.6 / 7 tmean 66.2); callsigns
('KG6DUG','TEST NAME','SAN FRANCISCO','CA'). Init module State against
fixture paths; kiwix URL pointed at a dead port (127.0.0.1:1) for
degrade tests.

## Cases

T1 dose_guard: trips on 'ibuprofen', 'IBUPROFEN pain', 'dose of x',
'500 mg', 'dosage', 'milligrams'; does NOT trip on 'water dosing'?? —
NO: 'dosing' IS a keyword, must trip; does NOT trip on 'aspirations',
'mgso4' (token must equal 'mg', not contain), 'wound care',
'ibuprofenlike' (exact token match only).

T2 safe_library_path: accepts 'docs/medical/x.html' (returns realpath
+ normalized rel); rejects '../etc/passwd', '/etc/passwd',
'docs/../../etc/passwd', '%2e%2e/etc', '%252e%252e' double-encoded,
'' empty, 'docs/medical/../../../outside.txt'. T2.5 symlink anchor:
top-level fixture entry that is a SYMLINK to a dir elsewhere in tmp —
member file accepted (the e2e-found bug), file reached by escaping
THROUGH the symlink target's parent rejected.

T3 strip_html: tags stripped, entities decoded (&amp;), script/style
content dropped, whitespace collapsed.

T4 fts_match_expr: quotes/specials neutralized — inputs 'a"b', 'a AND
b OR c', 'col:val', '(paren' must produce expr that FTS5 accepts
(execute against fixture db, no exception) and multi-term input still
matches a row containing all terms.

T5 haversine: RWC→KALI ≈ 1365 km ±5% (design v1 said 1740 — spec math
error caught by implementing agent, function was right); zero distance
= 0; antipodal > 19,900 km.

T6 tool_sun_times: fixed date 2026-03-20 (equinox) RWC: daylength
12.1±0.3 h, sunrise/sunset UTC values sane (sunrise_utc ≈ 14:0x);
2026-06-21 daylength > 2026-12-21 daylength; explicit lat/lon override
honored; polar edge: lat 89.9 on 2026-06-21 → 24 h or clean
midnight-sun handling, NO exception.

T7 tool_climate_normals: (48.3,-114.26) picks KALI not FAR; jan tmean
24.6 exact from fixture; month out of range (0, 13) → ToolError/isError
not crash.

T8 tool_read_document: pdf page 2 returns page-2 body only; pages=2
from page 1 returns 1+2; page 99 → clean error mentioning range;
docs/HISTORICAL/old.pdf → response STARTS with warning text;
docs/survivor_library/s.pdf → warning too; docs/medical/x.html →
stripped text, no tags; missing path → error not crash.

T9 tool_search_library: 'wound' → hit with title+path+shelf; guarded
query 'ibuprofen' → every hit snippet None/absent + notice present;
shelf filter excludes other shelves; limit respected; kiwix dead port
→ no exception, results still returned (degrade).

T10 tool_callsign_lookup: 'kg6dug' case-insensitive hit; 'XX0XXX' →
not-found error shape, not crash.

T11 rpc_dispatch: initialize echoes known protocolVersion, unknown
version → server default '2025-03-26', instructions non-empty;
tools/list = 6 tools, every inputSchema has type object; tools/call
unknown tool → isError true; unknown method → error -32601; ping →
result {}; notifications/initialized → None (no response).

T12 is_historical/shelf_of: driven by fixture shelves.json flags —
docs/HISTORICAL/x true, docs/survivor_library/x true, docs/medical/x
false; shelf_of maps docs/medical/a.pdf → medical shelf path.

## Rules for the implementing agent

- Read mcp_server.py signatures first; if a case's target function has
  a different shape than assumed here, adapt the CALL, never weaken the
  ASSERTION. If behavior differs from this design (e.g. dose_guard
  misses 'mgso4' exclusion), that is a FINDING: report it, do not
  silently change the expectation — mark the test @expectedFailure with
  a FINDING comment and list it in the summary.
- No network, no screen, no sandbox escape needed. Keep output quiet
  (unittest default), full run log → server/logs/unit.log.
- Module import must not start the HTTP server (main() guard exists).
