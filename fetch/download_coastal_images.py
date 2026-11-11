#!/usr/bin/env python3
"""
Download coastal species identification images from Wikimedia Commons.
Cloned from download_plant_images.py v4 — same resume logic, same backoff.
Prefers ID-feature shots (shell shape, siphon, frond structure).
"""

import os
import sys
import signal
import time
import json
import re
import urllib.request
import urllib.parse
import urllib.error

# Ignore SIGPIPE so broken pipes (e.g. screen detach) don't kill the process
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/library/docs/coastal_id"
LOG_FILE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/logs/coastal_images.log"
API_BASE = "https://commons.wikimedia.org/w/api.php"
API_DELAY = 1.5
DL_DELAY  = 3.0

# (slug, scientific_name, common_search_term)
SPECIES = [
    ("california_mussel",       "Mytilus californianus",        "california mussel"),
    ("bay_mussel",              "Mytilus trossulus",            "bay mussel"),
    ("pacific_oyster",          "Magallana gigas",              "pacific oyster"),
    ("manila_clam",             "Ruditapes philippinarum",      "manila clam"),
    ("gaper_clam",              "Tresus nuttallii",             "gaper clam"),
    ("razor_clam_pacific",      "Siliqua patula",               "pacific razor clam"),
    ("littleneck_clam_native",  "Leukoma staminea",             "native littleneck clam"),
    ("dungeness_crab",          "Metacarcinus magister",        "dungeness crab"),
    ("red_rock_crab",           "Cancer productus",             "red rock crab"),
    ("purple_shore_crab",       "Hemigrapsus nudus",            "purple shore crab"),
    ("gooseneck_barnacle",      "Pollicipes polymerus",         "gooseneck barnacle"),
    ("purple_sea_urchin",       "Strongylocentrotus purpuratus","purple sea urchin"),
    ("red_abalone",             "Haliotis rufescens",           "red abalone"),
    ("black_turban_snail",      "Tegula funebralis",            "black turban snail"),
    ("moon_snail_lewisii",      "Neverita lewisii",             "Lewis moon snail"),
    ("bull_kelp",               "Nereocystis luetkeana",        "bull kelp"),
    ("giant_kelp",              "Macrocystis pyrifera",         "giant kelp"),
    ("nori_porphyra",           "Porphyra umbilicalis",         "nori porphyra seaweed"),
    ("sea_lettuce_ulva",        "Ulva lactuca",                 "sea lettuce ulva"),
    ("kombu_laminaria",         "Laminaria digitata",           "kombu kelp"),
    ("alaria_marginata",        "Alaria marginata",             "alaria winged kelp"),
    ("dulse_palmaria",          "Palmaria palmata",             "dulse seaweed"),
    ("sea_palm_postelsia",      "Postelsia palmaeformis",       "sea palm postelsia"),
    ("monkeyface_prickleback",  "Cebidichthys violaceus",       "monkeyface prickleback"),
]

UA = "CoastalIDBot/1.0 (offline survival reference; educational use)"

def log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(msg + "\n")
    try:
        print(msg, flush=True)
    except (BrokenPipeError, OSError):
        pass

def api_call(params, backoff=60):
    params["format"] = "json"
    url = API_BASE + "?" + urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = backoff * (attempt + 1)
                log(f"  [API-429] sleeping {wait}s")
                time.sleep(wait)
            else:
                raise
    return {}

def search(query, limit=15):
    data = api_call({"action": "query", "list": "search",
                     "srsearch": query, "srnamespace": "6", "srlimit": str(limit)})
    time.sleep(API_DELAY)
    return [r["title"].replace("File:", "") for r in data.get("query", {}).get("search", [])]

def get_infos(filenames):
    result = {}
    for chunk_start in range(0, len(filenames), 10):
        chunk = filenames[chunk_start:chunk_start+10]
        titles = "|".join(f"File:{fn}" for fn in chunk)
        data = api_call({
            "action": "query", "titles": titles,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|mime|size|thumburl",
            "iiurlwidth": "1600",
        })
        time.sleep(API_DELAY)
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            title = page.get("title", "").replace("File:", "")
            ii = page.get("imageinfo", [])
            if ii:
                result[title] = ii[0]
    return result

def download(url, dest, backoff=60):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            with open(dest, "wb") as f:
                f.write(data)
            return len(data)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = backoff * (attempt + 1)
                log(f"  [DL-429] sleeping {wait}s")
                time.sleep(wait)
            elif e.code in (400, 404):
                return None
            else:
                raise
        except Exception as e:
            if attempt < 2:
                time.sleep(10)
            else:
                raise
    return None

def count_images(folder):
    if not os.path.isdir(folder):
        return 0
    return sum(1 for f in os.listdir(folder)
               if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')))

def process(slug, sci, common):
    folder = os.path.join(BASE_DIR, slug)
    os.makedirs(folder, exist_ok=True)

    n = count_images(folder)
    if n >= 5:
        log(f"  [DONE] {slug}: {n} images already")
        return n, 0

    log(f"\n[{slug}] {sci}")

    # Search scientific name first, fallback to common name
    fnames = search(sci, 20)
    if len(fnames) < 3:
        fnames2 = search(common, 10)
        seen = set(fnames)
        for f in fnames2:
            if f not in seen:
                fnames.append(f)
                seen.add(f)

    if not fnames:
        log(f"  [0 results]")
        return n, 0

    infos = get_infos(fnames)

    credits = []
    total_bytes = 0
    idx = n + 1

    for fname in fnames:
        if n >= 5:
            break
        info = infos.get(fname)
        if not info:
            continue

        mime = info.get("mime", "")
        if "svg" in mime:
            continue

        fn_lower = fname.lower()
        if fn_lower.endswith((".svg", ".tif", ".tiff")):
            continue

        # Skip obvious aquarium/tank shots by filename keyword
        skip_words = ["aquarium", "tank", "captive", "zoo"]
        if any(w in fn_lower for w in skip_words):
            log(f"  [SKIP-aquarium] {fname[:65]}")
            continue

        use_url = info.get("thumburl") or info.get("url")
        if not use_url:
            continue

        thumb_path = use_url.split("?")[0].split("/")[-1]
        if "." in thumb_path:
            ext = "." + thumb_path.rsplit(".", 1)[-1].lower()
        else:
            ext = ".jpg"
        if ext in (".tif", ".tiff", ".svg"):
            continue
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            ext = ".jpg"

        meta = info.get("extmetadata", {})
        artist = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "Unknown")).strip()[:200]
        lic = meta.get("LicenseShortName", {}).get("value", "Unknown")
        commons_url = f"https://commons.wikimedia.org/wiki/File:{urllib.parse.quote(fname)}"

        dest_name = f"{slug}_{idx:02d}{ext}"
        dest_path = os.path.join(folder, dest_name)

        log(f"  [{idx}] {fname[:65]}")
        try:
            nbytes = download(use_url, dest_path)
            time.sleep(DL_DELAY)
        except Exception as e:
            log(f"      [ERR] {e}")
            if os.path.exists(dest_path):
                os.remove(dest_path)
            time.sleep(API_DELAY)
            continue

        if nbytes is None:
            if os.path.exists(dest_path):
                os.remove(dest_path)
            log(f"      [SKIP] 400/404")
            continue

        total_bytes += nbytes
        n += 1
        idx += 1
        credits.append(f"{dest_name} | {artist} | {lic} | {commons_url}")
        log(f"      {dest_name} ({nbytes//1024} KB)")

    # Append (not overwrite) credits so resume doesn't wipe prior entries
    credits_path = os.path.join(folder, "CREDITS.txt")
    if credits:
        existing = ""
        if os.path.exists(credits_path):
            with open(credits_path) as f:
                existing = f.read()
        header = f"# {slug} — {sci}\n# filename | author | license | commons_url\n"
        with open(credits_path, "w") as f:
            if existing:
                f.write(existing)
            else:
                f.write(header)
            for line in credits:
                if line not in existing:
                    f.write(line + "\n")

    log(f"  => {n} images")
    return n, total_bytes


def main():
    import subprocess
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    ts = subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"]).decode().strip()
    log(f"=== download_coastal_images.py {ts} ===")

    total_imgs = 0
    total_bytes = 0
    with_imgs = 0

    for i, (slug, sci, common) in enumerate(SPECIES):
        log(f"\n--- [{i+1}/{len(SPECIES)}] {slug} ---")
        try:
            n, b = process(slug, sci, common)
            if n > 0:
                with_imgs += 1
            total_imgs += n
            total_bytes += b
        except Exception as e:
            log(f"  [FATAL] {e}")

    ts2 = subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"]).decode().strip()
    log(f"\n=== SUMMARY ===")
    log(f"Completed: {ts2}")
    log(f"Species attempted: {len(SPECIES)}")
    log(f"Species with images: {with_imgs}")
    log(f"Total images: {total_imgs}")
    log(f"New bytes: {total_bytes/1024/1024:.1f} MB")
    log(f"Directory: library/docs/coastal_id/")

if __name__ == "__main__":
    main()
