#!/usr/bin/env python3
"""L7 (round 6 fix wave, #218 class 7): b2's narrow-text measure (copied from b2_narrow.py), with its own outputs, plus the
page width (b2_render_all's docW) and a render check. Phone 390x844, is_mobile, dpr 2, file://, nothing leaves the box.
For each article text node of 40+ characters: its line boxes (Range.getClientRects). Per run recorded:
[median px, lines, words, text, in table.lantern-fit, in .lantern-zoom, in table, chars per line, culprit chain,
widest line in em of the run's own font size, CSS zoom taken out (a drawing's captions shrink with the drawing),
inside an absolutely placed caption].
b2 grades:  F1 = a run of median <= 15 px, 10+ lines, inside table.lantern-fit (one letter per line);
            sq = a run of median < 45 px, 6+ lines (words broken mid-word); wide = docW > 400.
Render check (#218): FAIL = a run of 4+ lines whose widest line is under 3 em (about 6 characters a line), except a
caption placed absolutely on a drawing (Hesperian fixes its box width in px at every screen size, desktop included).
Sliver check (round 9 #248, b2_narrow9's per-line metric): every article text node of 12+ characters is split into lines
character by character; its interior lines (not the first or last, which are short by nature) give the median characters per
line, and a line break between two letters of one word is a mid-word break. FAIL = such a run with a median of 3 or fewer
characters a line and a mid-word break, placed drawing labels included since round 10 (b2 W5, b5 F-M1-3; the old median-width
measure passed the 1-2 letter breech-birth columns, F1=0). Recorded per run in "sl": [median chars a line, lines, mid-word breaks, text, in table, caption];
sl6 counts b2's sliver rule (median 6 or fewer with a mid-word break, outside captions) for the log.
Usage: fix_l7_narrow.py OUT.jsonl HHG_DIR [--list FILE] [--check] [--css FILE]
  HHG_DIR: the .../es.hesperian.org/hhg (or en) folder to walk; --list: page names (relative to HHG_DIR), one per line.
  --css FILE: probe only, a style added at DOMContentLoaded (before the page's load-time script) to try a rule.
Off-screen check (round 10 #262, b2 B3 dental instrument lists at -25 to -51 px, b5 W8): every text line box and every leaf element
with text, placed drawing labels included, that starts left of 0 or ends past the screen (1 px rounding) outside a box that really
scrolls sideways (text left of a scroll box's start still counts: it cannot scroll there). FAIL = any such run ("off_fail"; one
"  OFF page: ..." line per page, t = text line, e = element box).
  --check: exit 1 when any page fails the render, sliver or off-screen check or throws a script error. Prints one summary line."""
import json, os, sys, urllib.parse
from playwright.sync_api import sync_playwright

JS = '''() => { const root = document.getElementById('mw-content-text'); const docW = document.documentElement.scrollWidth;
  if (!root) return {strips: 0, words: 0, ex: [], docW};
  const chain = e => { const o = []; for (let k = 0; e && k < 4; k++, e = e.parentElement) o.push(e.tagName.toLowerCase() + (e.className ? '.' + String(e.className).trim().replace(/\\s+/g, '.') : '') + ':' + Math.round(e.getBoundingClientRect().width)); return o.join('<'); };
  const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT); let n, strips = 0, words = 0; const ex = [];
  while ((n = w.nextNode())) { const t = n.textContent.trim(); if (t.length < 40) continue;
    if (n.parentElement.closest('#sidetoc, #bct, #bookinfosidebar, #toc')) continue;
    const r = document.createRange(); r.selectNodeContents(n); const rs = [...r.getClientRects()].filter(x => x.width > 0);
    if (rs.length < 4) continue; const ws = rs.map(x => x.width).sort((a, b) => a - b); const med = ws[ws.length >> 1];
    const cpl = t.length / rs.length; let z = 1; for (let a = n.parentElement; a; a = a.parentElement) z *= parseFloat(getComputedStyle(a).zoom) || 1;
    const em = ws[ws.length - 1] / z / (parseFloat(getComputedStyle(n.parentElement).fontSize) || 16);
    if (med < 70 || em < 3) { strips++; words += t.split(/\\s+/).length; ex.push([Math.round(med), rs.length, t.split(/\\s+/).length, t.slice(0, 60), !!n.parentElement.closest('table.lantern-fit'), !!n.parentElement.closest('.lantern-zoom'), !!n.parentElement.closest('table'), Math.round(cpl * 10) / 10, chain(n.parentElement), Math.round(em * 100) / 100, !!n.parentElement.closest('[style*="position: absolute"],[style*="position:absolute"]')]); } }
  const sl = []; const w2 = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  while ((n = w2.nextNode())) { const t = n.textContent; if (t.trim().length < 12) continue; const pe = n.parentElement;
    if (pe.closest('#sidetoc, #bct, #bookinfosidebar, #toc, script, style') || getComputedStyle(pe).display === 'none') continue;
    const r = document.createRange(); r.selectNodeContents(n); const rs = [...r.getClientRects()].filter(x => x.width > 0);
    if (rs.length < 3 || !rs.slice(1, -1).some(x => x.width < 90)) continue;
    const lines = []; let cur = null, mid = 0, prev = '';
    for (let i = 0; i < t.length; i++) { const ch = t[i]; if (/\\s/.test(ch)) { prev = ' '; continue; }
      r.setStart(n, i); r.setEnd(n, i + 1); const b = r.getBoundingClientRect(); if (!b.width && !b.height) continue;
      const top = Math.round(b.top);
      if (cur === null || Math.abs(top - cur.top) > 3) { if (cur && /\\p{L}/u.test(prev) && /\\p{L}/u.test(ch)) mid++; cur = {top, n: 0}; lines.push(cur); }
      cur.n++; prev = ch; }
    if (lines.length < 3) continue;
    const c = lines.slice(1, -1).map(x => x.n).sort((a, b) => a - b); const med = c[c.length >> 1];
    if (med <= 6 && mid) sl.push([med, lines.length, mid, t.trim().slice(0, 60), !!pe.closest('table'),
      getComputedStyle(pe).position === 'absolute' || !!pe.closest('[style*="position: absolute"],[style*="position:absolute"]')]); }
  // round 10 #262 (b2 B3, b5 W8): text a phone cannot reach. Every text line box (b2_offscreen's measure) and every leaf
  // element with text (b5_labels_all's: placed drawing labels included) that starts left of 0 or ends right of the screen
  // (1 px of rounding), unless a box that really scrolls sideways holds it; a scroll box cannot scroll to negative overflow,
  // so text left of that box's own start (or of the screen) still counts.
  const VW = document.documentElement.clientWidth, offx = []; let offn = 0;
  const lost = (pe, L, R) => { for (let a = pe; a && a !== document.body && a !== document.documentElement; a = a.parentElement) {
      const ox = getComputedStyle(a).overflowX; if (ox === 'visible') continue;
      if (ox === 'auto' || ox === 'scroll') { if (a.scrollWidth > a.clientWidth + 2) return L < Math.max(a.getBoundingClientRect().left, 0) - 1; continue; }
      break; }
    return L < -1 || R > VW + 1; };
  const seen = new Set(); const w3 = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while ((n = w3.nextNode())) { const t = n.textContent.trim(); if (t.length < 2) continue; const pe = n.parentElement;
    if (pe.closest('script, style, noscript')) continue; const cs = getComputedStyle(pe);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const r = document.createRange(); r.selectNodeContents(n); const rs = [...r.getClientRects()].filter(x => x.width > 0 && x.height > 0);
    const bad = rs.filter(x => lost(pe, x.left, x.right)); if (!bad.length) continue;
    seen.add(pe); offn++; if (offx.length < 8) offx.push([t.slice(0, 50), Math.round(Math.min(...bad.map(x => x.left))), Math.round(Math.max(...bad.map(x => x.right))), 't']); }
  for (const e of document.querySelectorAll('body *')) { if (e.children.length || seen.has(e) || !(e.innerText || '').trim()) continue;
    const b = e.getBoundingClientRect(); if (!b.width || !b.height) continue; const cs = getComputedStyle(e);
    if (cs.visibility === 'hidden' || cs.display === 'none' || !lost(e, b.left, b.right)) continue;
    offn++; if (offx.length < 8) offx.push([e.innerText.trim().slice(0, 50), Math.round(b.left), Math.round(b.right), 'e']); }
  return {strips, words, ex, docW, sl, offx, offn}; }'''


def grade(r):
    ex = r.get('ex', [])
    return {'F1': any(e[0] <= 15 and e[1] >= 10 and e[4] for e in ex), 'sq': any(e[0] < 45 and e[1] >= 6 for e in ex),
            'fail': any(e[1] >= 4 and e[9] < 3 and not e[10] for e in ex), 'wide': r.get('docW', 0) > 400,
            'sliver': any(e[0] <= 3 for e in r.get('sl', [])),   # round 10 b2 W5 / b5 F-M1-3: placed labels count too
            'sl6': any(not e[5] for e in r.get('sl', [])),
            'off': r.get('offn', 0) > 0}


def main():
    a = sys.argv[1:]
    out_path, hhg = a[0], a[1]
    pages = [l.rstrip('\n') for l in open(a[a.index('--list') + 1], encoding='utf-8') if l.strip()] if '--list' in a else \
        sorted(os.path.relpath(os.path.join(dp, f), hhg) for dp, _, fs in os.walk(hhg) for f in fs if f.endswith('.html'))
    tot = {'F1': 0, 'sq': 0, 'fail': 0, 'wide': 0, 'sliver': 0, 'sl6': 0, 'off': 0, 'error': 0}; bad = []
    with open(out_path, 'w', encoding='utf-8') as out, sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, device_scale_factor=2)
        ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(('file:', 'data:')) else r.abort())
        if '--css' in a:
            css = json.dumps(open(a[a.index('--css') + 1], encoding='utf-8').read())
            ctx.add_init_script('document.addEventListener("DOMContentLoaded",function(){var s=document.createElement("style");s.textContent=%s;document.head.appendChild(s)})' % css)
        pg = ctx.new_page(); perr = []
        pg.on('pageerror', lambda e: perr.append(str(e)[:120]))   # a broken lantern-phone-js leaves every fix undone
        for f in pages:
            perr.clear()
            try:
                pg.goto('file://' + urllib.parse.quote(os.path.join(hhg, f)), wait_until='load', timeout=45000)
                pg.wait_for_timeout(100)
                r = pg.evaluate(JS)
            except Exception as e:  # noqa
                r = {'error': str(e)[:120], 'strips': 0, 'words': 0, 'ex': [], 'docW': 0}
                tot['error'] += 1
            if perr and 'error' not in r:
                r['error'] = 'pageerror: ' + perr[0]; tot['error'] += 1
            r['page'] = f; r.update(grade(r))
            for k in ('F1', 'sq', 'fail', 'wide', 'sliver', 'sl6', 'off'):
                tot[k] += r[k]
            if r['sliver'] or r['off']:
                bad.append(r)
            out.write(json.dumps(r, ensure_ascii=False) + '\n'); out.flush()
        b.close()
    print('fix_l7_narrow %s: pages=%d F1=%d sq45=%d check_fail=%d sliver3_fail=%d sliver6=%d off_fail=%d wide400=%d errors=%d'
          % (hhg, len(pages), tot['F1'], tot['sq'], tot['fail'], tot['sliver'], tot['sl6'], tot['off'], tot['wide'], tot['error']))
    for r in (x for x in bad if x['off']):
        print('  OFF %s: %d runs: %s' % (r['page'], r['offn'], ' | '.join('%s %d..%d px: %s' % (e[3], e[1], e[2], e[0]) for e in r['offx'][:4])))
    for r in (x for x in bad if x['sliver']):
        print('  SLIVER %s: %s' % (r['page'], ' | '.join('%d chars/line x %d lines, %d mid-word: %s' % tuple(e[:4]) for e in r['sl'] if e[0] <= 3)))
    if '--check' in a and (tot['fail'] or tot['sliver'] or tot['off'] or tot['error']):
        sys.exit(1)


if __name__ == '__main__':
    main()
