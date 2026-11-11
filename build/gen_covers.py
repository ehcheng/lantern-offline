#!/usr/bin/env python3
"""A6 covers: first PDF page -> _app/covers/<sha8(librel_path)>.jpg (400px wide).
Manifest-driven (sealed 09-17), idempotent (skips existing), rerun-on-death.
Launch: screen -dmS covers bash -c 'python3 build/gen_covers.py'
After completion: rerun gen_shelves.py so doc rows pick up the <img>s."""
import hashlib, os, subprocess, sys, time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = f"{BASE}/library"
OUT = f"{LIB}/_app/covers"
LOG = f"{BASE}/logs/covers.log"

def log(m):
    with open(LOG, "a") as f:
        f.write(f"{time.strftime('%F %T')} {m}\n")

def sha8(p):  # MUST match gen_shelves.sha8
    return hashlib.sha256(p.encode()).hexdigest()[:8]

os.makedirs(OUT, exist_ok=True)
pdfs = []
with open(f"{LIB}/MANIFEST.sha256") as f:
    for line in f:
        p = line.split(None, 1)[1].strip()
        if (p.lower().endswith(".pdf") and p.startswith("library/")
                and not p.startswith("library/kolibri_data/")):
            pdfs.append(p[len("library/"):])

done = fail = skip = 0
log(f"START: {len(pdfs)} pdfs in manifest")
for i, rel in enumerate(pdfs):
    dst = f"{OUT}/{sha8(rel)}.jpg"
    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        skip += 1
        continue
    src = f"{LIB}/{rel}"
    if not os.path.exists(src):
        log(f"MISSING {rel}")
        fail += 1
        continue
    try:
        r = subprocess.run(
            ["pdftoppm", "-f", "1", "-l", "1", "-jpeg", "-jpegopt", "quality=70",
             "-scale-to-x", "400", "-scale-to-y", "-1", "-singlefile", src, dst[:-4]],
            capture_output=True, timeout=120)
        err = r.stderr.decode()[:120] if r.returncode != 0 else ""
    except subprocess.TimeoutExpired:
        err = "timeout 120s"
    if not err and os.path.exists(dst) and os.path.getsize(dst):
        try:
            from PIL import Image
            Image.open(dst).verify()   # two covers sealed as unreadable JPEGs (T1 2026-10-04); a bad cover is no cover
        except Exception as e:
            err = "unreadable jpeg: %s" % str(e)[:60]
    if err or not os.path.exists(dst) or os.path.getsize(dst) == 0:
        if os.path.exists(dst): os.unlink(dst)   # a timeout leaves a 0-byte jpg that would seal and ship
        log(f"FAIL {rel}: {err}")
        fail += 1
    else:
        done += 1
    if (i + 1) % 500 == 0:
        log(f"progress {i+1}/{len(pdfs)} (new={done} skip={skip} fail={fail})")
log(f"ALL DONE: new={done} skipped-existing={skip} fail={fail}")
