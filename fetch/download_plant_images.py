#!/usr/bin/env python3
"""
Download plant identification images from Wikimedia Commons.
v4: Uses exact thumburl from API (thumb.wikimedia.org, natural size).
    Longer delays, proper 429 backoff. Resume-capable.
"""

import os
import time
import json
import re
import urllib.request
import urllib.parse
import urllib.error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/library/docs/plant_id"
API_BASE = "https://commons.wikimedia.org/w/api.php"
API_DELAY = 1.5       # seconds between API calls
DL_DELAY = 3.0        # seconds between downloads (more conservative)

SPECIES = [
    ("cattail",                  "Typha latifolia",              "cattail"),
    ("dandelion",                "Taraxacum officinale",         "dandelion"),
    ("common_purslane",          "Portulaca oleracea",           "common purslane"),
    ("lambsquarters",            "Chenopodium album",            "lambsquarters"),
    ("stinging_nettle",          "Urtica dioica",                "stinging nettle"),
    ("wood_sorrel",              "Oxalis acetosella",            "wood sorrel"),
    ("chickweed",                "Stellaria media",              "chickweed"),
    ("cleavers",                 "Galium aparine",               "cleavers"),
    ("plantain_broadleaf",       "Plantago major",               "broadleaf plantain"),
    ("ground_elder",             "Aegopodium podagraria",        "ground elder"),
    ("wild_garlic",              "Allium ursinum",               "wild garlic"),
    ("ramps",                    "Allium tricoccum",             "ramps"),
    ("wild_carrot",              "Daucus carota",                "wild carrot"),
    ("elderberry",               "Sambucus nigra",               "elderberry"),
    ("blackberry",               "Rubus fruticosus",             "blackberry"),
    ("wild_strawberry",          "Fragaria vesca",               "wild strawberry"),
    ("hawthorn",                 "Crataegus monogyna",           "hawthorn"),
    ("rose_hips",                "Rosa canina",                  "rose hips"),
    ("acorn_white_oak",          "Quercus alba",                 "white oak"),
    ("acorn_red_oak",            "Quercus rubra",                "red oak"),
    ("black_walnut",             "Juglans nigra",                "black walnut"),
    ("hickory_nut",              "Carya ovata",                  "shagbark hickory"),
    ("pawpaw",                   "Asimina triloba",              "pawpaw"),
    ("persimmon",                "Diospyros virginiana",         "persimmon"),
    ("serviceberry",             "Amelanchier alnifolia",        "serviceberry"),
    ("mulberry",                 "Morus rubra",                  "red mulberry"),
    ("jerusalem_artichoke",      "Helianthus tuberosus",         "Jerusalem artichoke"),
    ("cattail_pollen",           "Typha",                        "cattail pollen"),
    ("watercress",               "Nasturtium officinale",        "watercress"),
    ("miners_lettuce",           "Claytonia perfoliata",         "miner's lettuce"),
    ("water_hemlock",            "Cicuta maculata",              "water hemlock"),
    ("poison_hemlock",           "Conium maculatum",             "poison hemlock"),
    ("death_camas",              "Anticlea elegans",             "death camas"),
    ("false_hellebore",          "Veratrum viride",              "false hellebore"),
    ("deadly_nightshade",        "Atropa belladonna",            "deadly nightshade"),
    ("bittersweet_nightshade",   "Solanum dulcamara",            "bittersweet nightshade"),
    ("pokeweed",                 "Phytolacca americana",         "pokeweed"),
    ("jimsonweed",               "Datura stramonium",            "jimsonweed"),
    ("monkshood",                "Aconitum napellus",            "monkshood"),
    ("lily_of_the_valley",       "Convallaria majalis",          "lily of the valley"),
    ("foxglove",                 "Digitalis purpurea",           "foxglove"),
    ("white_snakeroot",          "Ageratina altissima",          "white snakeroot"),
    ("giant_hogweed",            "Heracleum mantegazzianum",     "giant hogweed"),
    ("wild_parsnip",             "Pastinaca sativa",             "wild parsnip"),
    ("angels_trumpet",           "Brugmansia",                   "angel's trumpet"),
    ("hen_of_the_woods",         "Grifola frondosa",             "hen of the woods"),
    ("chicken_of_the_woods",     "Laetiporus sulphureus",        "chicken of the woods"),
    ("chanterelle",              "Cantharellus cibarius",        "chanterelle"),
    ("jack_o_lantern",           "Omphalotus olearius",          "jack-o-lantern mushroom"),
    ("morel",                    "Morchella esculenta",          "morel"),
    ("false_morel",              "Gyromitra esculenta",          "false morel"),
    ("puffball_giant",           "Calvatia gigantea",            "giant puffball"),
    ("amanita_death_cap",        "Amanita phalloides",           "death cap"),
    ("amanita_destroying_angel", "Amanita bisporigera",          "destroying angel"),
    ("fly_agaric",               "Amanita muscaria",             "fly agaric"),
    ("field_garlic",             "Allium vineale",               "field garlic"),
    ("garlic_mustard",           "Alliaria petiolata",           "garlic mustard"),
    ("wild_ginger",              "Asarum canadense",             "wild ginger"),
    ("mayapple",                 "Podophyllum peltatum",         "mayapple"),
    ("black_elderberry_flowers", "Sambucus nigra",               "elderberry flowers"),
    ("red_elderberry",           "Sambucus racemosa",            "red elderberry"),
    ("cow_parsnip",              "Heracleum maximum",            "cow parsnip"),
]

UA = "PlantIDBot/4.0 (offline survival reference; educational use)"

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
                print(f"  [API-429] sleeping {wait}s", flush=True)
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
    """Batch imageinfo, returns dict fname->info"""
    result = {}
    for chunk_start in range(0, len(filenames), 10):
        chunk = filenames[chunk_start:chunk_start+10]
        titles = "|".join(f"File:{fn}" for fn in chunk)
        data = api_call({
            "action": "query", "titles": titles,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|mime|size|thumburl",
            "iiurlwidth": "1600",  # large enough to get a real thumb; API clips to natural width
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
                print(f"  [DL-429] sleeping {wait}s", flush=True)
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
               if f.lower().endswith(('.jpg','.jpeg','.png','.webp')))

def process(slug, sci, common):
    folder = os.path.join(BASE_DIR, slug)
    os.makedirs(folder, exist_ok=True)

    n = count_images(folder)
    if n >= 5:
        print(f"  [DONE] {slug}: {n} images already", flush=True)
        return n, 0

    print(f"\n[{slug}] {sci}", flush=True)

    fnames = search(sci, 20)
    if len(fnames) < 3:
        fnames2 = search(common, 10)
        seen = set(fnames)
        for f in fnames2:
            if f not in seen:
                fnames.append(f)
                seen.add(f)

    if not fnames:
        print(f"  [0 results]", flush=True)
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

        # Use thumburl (exact URL from API, already at natural/clamped width)
        # Falls back to full url only if no thumburl
        use_url = info.get("thumburl") or info.get("url")
        if not use_url:
            continue

        # Derive extension from thumburl or filename
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

        print(f"  [{idx}] {fname[:65]}", flush=True)
        try:
            nbytes = download(use_url, dest_path)
            time.sleep(DL_DELAY)
        except Exception as e:
            print(f"      [ERR] {e}", flush=True)
            if os.path.exists(dest_path):
                os.remove(dest_path)
            time.sleep(API_DELAY)
            continue

        if nbytes is None:
            if os.path.exists(dest_path):
                os.remove(dest_path)
            print(f"      [SKIP] 400/404", flush=True)
            continue

        total_bytes += nbytes
        n += 1
        idx += 1
        credits.append(f"{dest_name} | {artist} | {lic} | {commons_url}")
        print(f"      {dest_name} ({nbytes//1024} KB)", flush=True)

    if credits:
        with open(os.path.join(folder, "CREDITS.txt"), "w") as f:
            f.write(f"# {slug} — {sci}\n# filename | author | license | commons_url\n")
            for line in credits:
                f.write(line + "\n")

    print(f"  => {n} images", flush=True)
    return n, total_bytes


def main():
    import subprocess
    ts = subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"]).decode().strip()
    print(f"=== plant_images_v4.py {ts} ===", flush=True)

    total_imgs = 0
    total_bytes = 0
    with_imgs = 0

    for i, (slug, sci, common) in enumerate(SPECIES):
        print(f"\n--- [{i+1}/{len(SPECIES)}] {slug} ---", flush=True)
        try:
            n, b = process(slug, sci, common)
            if n > 0:
                with_imgs += 1
            total_imgs += n
            total_bytes += b
        except Exception as e:
            print(f"  [FATAL] {e}", flush=True)

    ts2 = subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"]).decode().strip()
    print(f"\n=== TASK 2 SUMMARY ===", flush=True)
    print(f"Completed: {ts2}", flush=True)
    print(f"Species attempted: {len(SPECIES)}", flush=True)
    print(f"Species with images: {with_imgs}", flush=True)
    print(f"Total images: {total_imgs}", flush=True)
    print(f"New bytes: {total_bytes/1024/1024:.1f} MB", flush=True)
    print(f"Directory: library/docs/plant_id/", flush=True)

if __name__ == "__main__":
    main()
