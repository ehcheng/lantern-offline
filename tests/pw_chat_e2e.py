#!/usr/bin/env python3
"""Ask page end to end with a mocked Ollama (seal t5 "chat" row). Round 11 fix F (r40): rewritten from the version that
asserted quoted passages, which the Ask page no longer shows (D4, #278). Same mocked Ollama and same call form:

    python3 tests/pw_chat_e2e.py <shots dir> [BASE]

Asserts: the model request is the pick prompt with numbered PAGES (titles, no passage text); the page quotes nothing (no
.c-pas, no blockquote); the model's pick [2,1] puts the old second title first in "Other matching pages"; nothing the model
writes besides the numbers reaches the page. Optional env: FIX_F_APP (serve this app.js for every _app/app*.js request,
for a dev check before the bundle is rebuilt), FIX_F_MCP (forward /semantic and /mcp to this port).
"""
import json, os, re, sys

from playwright.sync_api import sync_playwright

D = sys.argv[1]
B = (sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8765/").rstrip("/") + "/"
captured = []

with sync_playwright() as p:
    br = p.chromium.launch(args=["--proxy-server=" + os.environ["T5_PROXY"]] if os.environ.get("T5_PROXY") else [])
    ctx = br.new_context(viewport={"width": 390, "height": 844}, color_scheme="dark", device_scale_factor=2)
    if os.environ.get("FIX_F_APP"):
        ctx.route(re.compile(r".*/_app/app(?:\.[0-9a-f]{8})?\.js(?:\?.*)?$"), lambda r: r.fulfill(path=os.environ["FIX_F_APP"], content_type="application/javascript"))
    if os.environ.get("FIX_F_MCP"):
        ctx.route(re.compile(r"^http://127\.0\.0\.1:8765/(?:semantic\?|mcp$)"), lambda r: r.fulfill(response=r.fetch(
            url=r.request.url.replace(":8765/", ":%s/" % os.environ["FIX_F_MCP"]), timeout=90000)))
    pg = ctx.new_page()
    errs = []
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.route("**/fakellm/api/tags", lambda r: r.fulfill(
        status=200, content_type="application/json", body=json.dumps({"models": [{"name": "test-model"}]})))

    def chat(r):
        captured.append(json.loads(r.request.post_data))
        r.fulfill(status=200, content_type="application/json",
                  body=json.dumps({"message": {"content": '{"pick":[2,1]} Boil water for one minute ZZPROSE.'}}))
    pg.route("**/fakellm/api/chat", chat)
    pg.add_init_script("localStorage.setItem('lantern.llm.endpoints', JSON.stringify(['http://127.0.0.1:8765/fakellm']));"
                       " sessionStorage.removeItem('lantern.caps')")
    pg.goto(B + "chat.html")
    pg.goto(B + "chat.html")
    pg.wait_for_selector("#form:not([hidden])", timeout=40000)
    pg.fill("#q", "how do I purify water")
    pg.press("#q", "Enter")
    for _ in range(300):
        if captured: break
        pg.wait_for_timeout(100)
    pg.wait_for_timeout(1500)

    body = captured[-1] if captured else {"messages": [{"content": ""}, {"content": ""}]}
    sysmsg, user = body["messages"][0]["content"], body["messages"][-1]["content"]
    lines = [l for l in user.split("\n") if l.startswith("[")]
    prompt_ok = '"pick"' in sysmsg and "PAGES:" in user and "PASSAGES" not in user and len(body["messages"]) == 2 and len(lines) >= 2
    quotes = pg.eval_on_selector_all(".c-pas, #log blockquote", "els=>els.length")
    titles = pg.evaluate("""() => { const p = [...document.querySelectorAll('#log .c-msg.bot p.l-caption')]
      .filter(x => /^Other matching pages/.test(x.textContent)).pop(); return p ? [...p.querySelectorAll('a')].map(a => a.textContent) : []; }""")
    second = re.sub(r"^\[\d+\] (.*?)(?:, p\.(\d+))?$", lambda m: m.group(1) + (" p." + m.group(2) if m.group(2) else ""), lines[1]) if len(lines) >= 2 else None
    reordered = bool(titles) and second is not None and titles[0].startswith(second)   # pick [2,1]: old [2] shows first
    leaked = "ZZPROSE" in pg.inner_text("body")
    print("pick prompt (PAGES, titles only):", prompt_ok, "| titles in request:", len(lines), "| quotes shown:", quotes)
    print("first titles:", titles[:3])
    print("reordered by pick:", reordered, "| model prose on page:", leaked)
    print("errors:", [e for e in errs if "fakellm" not in e and "ERR_ADDRESS" not in e])
    pg.screenshot(path=f"{D}/mobile_dark_ask_titles.png")
    br.close()
    assert prompt_ok and not quotes and titles and reordered and not leaked, "ASK E2E FAILED"
    print("ASK E2E OK")
