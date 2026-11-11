#!/usr/bin/env python3
"""End-to-end tests for the Lantern Library MCP server (stdlib only).

Run:  python3 server/test_mcp.py [--url http://127.0.0.1:8090/mcp]
Server must already be running against the real library/ + mcp.db.
Implements MCP_PLAN.md test plan 1-10 + v2 amendments (traversal probes,
kiwix graceful degrade + code-inspection of guard branch, historical
warnings for BOTH docs/HISTORICAL and docs/survivor_library).
"""
import argparse
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

URL = "http://127.0.0.1:8090/mcp"
SERVER_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "mcp_server.py")
_id = [0]
RESULTS = []  # (name, ok, detail)


def post(payload, raw=None):
    """POST JSON-RPC; returns (http_status, parsed_body). Never raises."""
    data = raw if raw is not None else json.dumps(payload).encode()
    req = urllib.request.Request(URL, data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
            status = r.status
    except urllib.error.HTTPError as e:
        body = e.read()
        status = e.code
    try:
        return status, json.loads(body) if body else None
    except ValueError:
        return status, body.decode("utf-8", "replace")


def get(url):
    """GET; returns (http_status, parsed_json). Never raises."""
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def rpc(method, params=None):
    _id[0] += 1
    return post({"jsonrpc": "2.0", "id": _id[0], "method": method,
                 "params": params or {}})


def call_tool(name, arguments):
    """Returns (isError, parsed_tool_output_or_text, full_response_dict)."""
    status, resp = rpc("tools/call", {"name": name, "arguments": arguments})
    assert status == 200, "HTTP %s for tools/call %s" % (status, name)
    res = resp["result"]
    text = res["content"][0]["text"]
    if res.get("isError"):
        return True, text, resp
    return False, json.loads(text), resp


def check(name, fn):
    try:
        fn()
        RESULTS.append((name, True, ""))
        print("PASS  %s" % name)
    except AssertionError as e:
        RESULTS.append((name, False, str(e)))
        print("FAIL  %s -- %s" % (name, e))
    except Exception as e:
        RESULTS.append((name, False, "%s: %s" % (type(e).__name__, e)))
        print("FAIL  %s -- %s: %s" % (name, type(e).__name__, e))


# ------------------------------------------------------------------ tests

def t01_handshake():
    status, resp = rpc("initialize", {
        "protocolVersion": "2025-03-26",
        "capabilities": {}, "clientInfo": {"name": "test", "version": "0"}})
    assert status == 200, "initialize HTTP %s" % status
    r = resp["result"]
    assert "tools" in r["capabilities"], "no tools capability"
    assert r.get("instructions", "").strip(), "instructions empty"
    assert "dose" in r["instructions"].lower(), "instructions missing dose rule"
    assert r["protocolVersion"] == "2025-03-26", "protocolVersion not echoed"
    # notification -> 202, no body
    st, body = post({"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert st == 202, "notification HTTP %s (want 202)" % st
    status, resp = rpc("tools/list")
    tools = resp["result"]["tools"]
    names = sorted(t["name"] for t in tools)
    assert names == sorted(["search_library", "read_document", "list_shelves",
                            "sun_times", "climate_normals",
                            "callsign_lookup"]), "tools: %s" % names
    assert len(tools) == 6, "expected exactly 6 tools, got %d" % len(tools)
    for t in tools:
        s = t["inputSchema"]
        assert s.get("type") == "object", "%s schema not object" % t["name"]
        assert isinstance(s.get("properties"), dict), \
            "%s schema has no properties" % t["name"]


def t02_search_positive():
    err, out, _ = call_tool("search_library", {"query": "pickled beets"})
    assert not err, out
    hits = out["hits"]
    good = [h for h in hits
            if ("nchfp" in h["path"] or "usda_complete_guide" in h["path"])
            and h.get("page")]
    assert good, "no USDA/nchfp hit with page for 'pickled beets': %s" % \
        [h["path"] for h in hits]

    err, out, _ = call_tool("search_library",
                            {"query": "thermophilic compost"})
    assert not err, out
    hits = out["hits"]
    good = [h for h in hits if "eawag" in h["path"]
            or h["path"].startswith("docs/sanitation/")]
    assert good, "no EAWAG/sanitation hit for 'thermophilic compost': %s" % \
        [h["path"] for h in hits]


def t03_dose_guard_negative():
    err, out, resp = call_tool("search_library", {"query": "ibuprofen dose"})
    assert not err, out
    assert out.get("dose_guard") is True, "dose_guard flag missing"
    assert "printed drug guide" in out.get("notice", ""), \
        "dose notice missing"
    assert out["hits"], "guarded search returned no hits at all"
    for h in out["hits"]:
        assert h.get("snippet") in (None, ""), \
            "snippet leaked on guarded query: %r" % h["snippet"]
    # NO dose text anywhere in the serialized wire response
    wire = json.dumps(resp, ensure_ascii=False)
    m = re.search(r"\d+\s*mg\b", wire, re.I)
    assert m is None, "dose-looking text in response: %r" % m.group(0)


def t04_historical_warning():
    # BOTH historical shelves (shelves.json historical:true), title-index hits
    for query, prefix in [("sof medical handbook", "docs/HISTORICAL/"),
                          ("bookkeeping accounting 1922",
                           "docs/survivor_library/")]:
        err, out, _ = call_tool("search_library", {"query": query})
        assert not err, out
        hist = [h for h in out["hits"] if h["path"].startswith(prefix)]
        assert hist, "no %s hit for %r: %s" % (
            prefix, query, [h["path"] for h in out["hits"]])
        for h in hist:
            assert h.get("historical") is True, "hit not flagged: %s" % h
            assert h.get("warning", "").strip(), "hit missing warning text"
        assert out.get("historical_warning", "").strip(), \
            "top-level historical_warning missing for %r" % query


def t05_read_document():
    pdf = "docs/food_preservation/usda_complete_guide_home_canning_2015.pdf"
    err, out, _ = call_tool("read_document",
                            {"path": pdf, "page": 10, "pages": 1})
    assert not err, out
    assert out["text"].strip(), "empty text for known wrapper PDF page"
    assert "Fish in quart jars" in out["text"], \
        "page 10 text mismatch: %r" % out["text"][:120]
    # page beyond EOF -> clean tool error
    err, msg, _ = call_tool("read_document", {"path": pdf, "page": 99999})
    assert err, "page 99999 did not error"
    assert "beyond end" in msg, "unclear EOF error: %r" % msg
    # non-extracted PDF -> fallback message with open-URL
    err, msg, _ = call_tool("read_document", {
        "path": "docs/survivor_library/SurvivalLibrary/library/Accounting/"
                "20th_century_bookkeeping_and_accounting_1922.pdf"})
    assert err, "non-extracted PDF did not return fallback error"
    assert "no text layer" in msg, "fallback message wrong: %r" % msg


def t13_read_document_dose_guard():
    # who_mhgap p.50 carries 10 dose figures in mcp.db (checked 2026-10-03); the page must come back redacted
    dose = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|µg|ug|g|ml|mL|iu|units?)\b", re.I)
    err, out, _ = call_tool("read_document", {
        "path": "docs/medical/who_mhgap_intervention_guide_v2.pdf", "page": 50, "pages": 1})
    assert not err, out
    assert out.get("dose_guard") is True, "dose_guard flag missing on a formulary page"
    assert out["text"].startswith("This library's own pages, summaries and search never state drug doses"), out["text"][:120]
    assert not dose.search(out["text"]), "dose figure survived: %r" % dose.search(out["text"]).group(0)
    assert "[dose removed; printed guide]" in out["text"]
    # a canning page keeps its gram/millilitre quantities (no drug language)
    err, out, _ = call_tool("read_document", {
        "path": "docs/food_preservation/usda_complete_guide_home_canning_2015.pdf", "page": 10, "pages": 1})
    assert not err, out
    assert not out.get("dose_guard"), "canning page tripped the dose guard"


def t14_search_class_keyword_guard():
    # acceptance 2026-10-03: a drug CLASS word ("medicine", "antibiotic", "painkiller") trips the guard like a drug name
    dose = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|µg|ug|g|ml|mL|iu|units?)\b", re.I)
    for q in ("fever medicine for a child", "antibiotic for tooth infection"):
        err, out, _ = call_tool("search_library", {"query": q, "limit": 8})
        assert not err, out
        assert out.get("dose_guard") is True, "class keyword did not trip the guard: %r" % q
        for h in out.get("results", out.get("hits", [])):
            assert not (h.get("snippet") or h.get("excerpt")), "snippet served on a guarded query: %r" % h
    # an unguarded query never carries a dose figure in a snippet either (scrub_dose). 2026-10-09 (F1): ORS and
    # water-treatment amounts ("of sugar", "de sal", "per litre") are not doses and stay in snippets.
    dose = re.compile(dose.pattern + r"(?!\s*(?:(?:level|rasas?)\s+)?(?:of|de)\s+(?:salt|sugar|water|sal|az[uú]car|agua)"
                      r"|\s*(?:per|por|/)\s*(?:litre|liter|litro|l\b))", re.I)
    err, out, _ = call_tool("search_library", {"query": "rehydration drink recipe", "limit": 8})
    assert not err, out
    for h in out.get("results", out.get("hits", [])):
        assert not dose.search(h.get("snippet") or ""), "dose figure in snippet: %r" % h.get("snippet")



ES_DOSE_PAGES = [  # red team 2026-10-09 b2 F2 / a7a / a7b: Spanish Hesperian pages that returned full regimens
    "New_Where_There_Is_No_Doctor:Medicinas_para_las_lombrices_(parásitos):_La_salud_de_los_niños.html",
    "New_Where_There_Is_No_Doctor:Medicinas_para_el_dolor:Primeros_auxilios.html",
    "New_Where_There_Is_No_Doctor:Los_antibióticos_combaten_las_infecciones:_Los_recién_nacidos_y_el_amamantamiento.html",
    "Where_Women_Have_No_Doctor:Complicaciones_de_las_infecciones_sexuales.html",
    "Helping_Children_Who_Are_Deaf:Infecciones_de_los_oídos.html",
]


def t16_spanish_dose_pages():
    # 2026-10-09 (#146): Spanish units, counts and frequencies; every one of these pages trips the guard and keeps no
    # dose figure (whole ranges go, not just the upper bound)
    leak = re.compile(r"\d+(?:[.,]\d+)*\s*(?:mg|g|gramos?|unidades|pastillas?|tabletas?|c[aá]psulas?|cucharaditas?|ml)\b"
                      r"(?!\s*(?:(?:rasas?)\s+)?de\s+(?:sal|az[uú]car|agua))|\d+\s+veces\s+al\s+d[ií]a|cada\s+\d+\s*(?:a\s+\d+\s+)?horas"
                      r"|\b\d+\s+(?:a|to)\s+\[dose removed", re.I)
    for name in ES_DOSE_PAGES:
        rel = "mirrors/hesperian/es.hesperian.org/hhg/" + name
        err, out, _ = call_tool("read_document", {"path": rel, "page": 1, "pages": 3})
        assert not err, (name, out)
        assert out.get("dose_guard") is True, "dose_guard flag missing: %s" % name
        m = leak.search(out["text"])
        assert m is None, "Spanish dose text survived on %s: %r" % (name, out["text"][max(0, m.start() - 60):m.end() + 40])
    err, out, _ = call_tool("search_library", {"query": "dosis de amoxicilina para niños", "limit": 8})
    assert not err, out
    assert out.get("dose_guard") is True, "Spanish dose query did not trip the guard"

def t06_sun_times():
    # FIXED date per plan; config default location (Redwood City)
    err, out, _ = call_tool("sun_times", {"date": "2026-09-19"})
    assert not err, out
    assert abs(out["lat"] - 37.485) < 0.01, "default lat wrong: %s" % out
    sr = out["sunrise"]["local"]
    h, m = int(sr[:2]), int(sr[3:])
    mins = h * 60 + m
    assert 5 * 60 + 30 <= mins <= 7 * 60 + 30, \
        "sunrise %s outside [05:30, 07:30] local" % sr
    assert abs(out["daylength_hours"] - 12.2) <= 0.25, \
        "daylength %.2f h not 12.2 +/- 0.25" % out["daylength_hours"]


def t07_climate_normals():
    err, jan, _ = call_tool("climate_normals",
                            {"lat": 48.3, "lon": -114.26, "month": 1})
    assert not err, jan
    assert jan["station"]["id"] == "USC00244558", \
        "wrong station: %s" % jan["station"]
    err, jul, _ = call_tool("climate_normals",
                            {"lat": 48.3, "lon": -114.26, "month": 7})
    assert not err, jul
    assert jan["tmean_f"] < jul["tmean_f"], \
        "Jan tmean %s not < Jul tmean %s" % (jan["tmean_f"], jul["tmean_f"])


def t08_callsign():
    err, out, _ = call_tool("callsign_lookup", {"callsign": "KG6DUG"})
    assert not err, out
    assert out["callsign"] == "KG6DUG"
    assert out.get("name", "").strip(), "no licensee name"
    assert out.get("state"), "no state"


def t09_protocol_errors():
    status, resp = rpc("no/such/method")
    assert resp["error"]["code"] == -32601, "unknown method: %s" % resp
    status, resp = post(None, raw=b"{this is not json")
    assert resp["error"]["code"] == -32700, "bad JSON: %s" % resp
    status, resp = rpc("tools/call", {"name": "no_such_tool", "arguments": {}})
    assert status == 200, "unknown tool crashed: HTTP %s" % status
    assert resp["result"]["isError"] is True, "unknown tool not isError"


def t10_traversal():
    probes = [
        "../../etc/passwd",
        "/etc/passwd",
        "%2e%2e/%2e%2e/etc/passwd",
        "%252e%252e/%252e%252e/etc/passwd",  # double-encoded
        "docs/../../etc/passwd",
    ]
    for p in probes:
        err, msg, resp = call_tool("read_document", {"path": p})
        assert err, "traversal probe accepted: %r -> %s" % (p, msg)
        wire = json.dumps(resp)
        assert "root:" not in wire, "passwd content leaked for %r" % p


def t11_kiwix_degrade_and_guard_branch():
    # kiwix-serve absent on this Mac: searches must still succeed (silent
    # degrade, no error, no zim/ hits) -- t02/t03 already ran fine; assert
    # explicitly that no zim results appear and no error surfaces.
    err, out, _ = call_tool("search_library", {"query": "solar"})
    assert not err, out
    assert not any(h["path"].startswith("zim/") for h in out["hits"]), \
        "zim hits present though kiwix-serve is absent on this host"
    # Code-inspection note (kiwix unreachable here, so the merged-snippet
    # suppression can't fire live): assert the guard branch in kiwix_search
    # suppresses snippets when the single per-query dose decision tripped.
    with open(SERVER_SRC, encoding="utf-8") as f:
        src = f.read()
    ks = src[src.index("def kiwix_search"):src.index("def tool_read_document")]
    assert "guarded" in ks and "None if guarded else" in ks, \
        "kiwix_search lacks dose-guard snippet suppression branch"
    assert "guarded = dose_guard(query)" in src, \
        "dose decision not made once per query"


def t12_concurrency():
    queries = ["water", "canning", "compost", "antenna",
               "solar", "shelter", "first aid", "radio"]
    errs, times = [], []
    lock = threading.Lock()

    def worker(q):
        t0 = time.monotonic()
        try:
            err, out, _ = call_tool("search_library", {"query": q, "limit": 5})
            ok = not err
        except Exception as e:
            ok, out = False, str(e)
        dt = time.monotonic() - t0
        with lock:
            times.append(dt)
            if not ok:
                errs.append((q, out))

    threads = [threading.Thread(target=worker, args=(q,)) for q in queries]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errs, "parallel search failures: %s" % errs
    slow = [t for t in times if t >= 2.0]
    assert not slow, "searches >= 2 s: %s" % ["%.2f" % t for t in slow]


def t15_rerank():
    # E1b: GET /rerank next to /semantic; same server, same embed service.
    base = URL.rsplit("/", 1)[0]
    status, out = get(base + "/rerank?q=safe+drinking+water&paths=")
    assert status == 400, "missing paths should 400, got %s" % status
    err, res, _ = call_tool("search_library", {"query": "water purification"})
    assert not err, res
    paths = [h["path"] for h in res["hits"][:3]]
    assert paths, "no hits to rerank"
    status, out = get(base + "/rerank?q=safe+drinking+water&paths=" +
                      urllib.parse.quote("|".join(paths + ["docs/nope.pdf"]), safe=""))
    assert status == 200, "HTTP %s" % status
    assert out == [] or [r["path"] for r in out] == paths + ["docs/nope.pdf"], out
    if out:  # [] only when the embed service is down (silent degrade)
        assert out[-1]["score"] is None, out[-1]
        assert all(-1 <= r["score"] <= 1 for r in out[:-1] if r["score"] is not None), out


def main():
    global URL
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=URL)
    URL = ap.parse_args().url

    check("01 MCP handshake + tools/list schemas", t01_handshake)
    check("02 search positive fixtures", t02_search_positive)
    check("03 dose-guard NEG probe (ibuprofen dose)", t03_dose_guard_negative)
    check("04 historical warning (HISTORICAL + survivor_library)",
          t04_historical_warning)
    check("05 read_document (PDF page / EOF / non-extracted)",
          t05_read_document)
    check("06 sun_times Redwood City 2026-09-19", t06_sun_times)
    check("07 climate_normals Kalispell", t07_climate_normals)
    check("08 callsign_lookup KG6DUG", t08_callsign)
    check("09 protocol errors (-32601 / -32700 / unknown tool)",
          t09_protocol_errors)
    check("10 traversal probes rejected", t10_traversal)
    check("11 kiwix graceful degrade + guard-branch inspection",
          t11_kiwix_degrade_and_guard_branch)
    check("12 concurrency: 8 parallel searches < 2 s", t12_concurrency)
    check("13 read_document dose guard (formulary redacted, canning untouched)",
          t13_read_document_dose_guard)
    check("14 search guard on drug-class words; snippets never carry dose figures",
          t14_search_class_keyword_guard)
    check("15 /rerank max-cosine per path, input order, null for unknown",
          t15_rerank)
    check("16 Spanish medicine pages redacted whole, Spanish dose query guarded",
          t16_spanish_dose_pages)

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = len(RESULTS) - passed
    print("\n%d passed, %d failed, %d total" % (passed, failed, len(RESULTS)))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
