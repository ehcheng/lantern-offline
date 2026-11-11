#!/usr/bin/env python3
"""Drive mode (file://, no plants.html): write the edible/deadly verdict next to the photos.
Per species folder: README.txt (verdict, note, lookalike) and a `# VERDICT:` line 2 in CREDITS.txt.
Per group folder (docs/plant_id, docs/coastal_id): README.txt index, deadly first.
Source of truth: data/plants.curated.json / coastal.curated.json. Rerunnable; FIXES #154 (a7a F3).
--check: write nothing, list every file whose content would change, exit 1 if any (red team 10-16 K7, #208)."""
import json, os, sys

CHECK = "--check" in sys.argv
STALE = []


def put(path, text):
    old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
    if old == text:
        return
    if CHECK:
        STALE.append(path)
    else:
        open(path, "w", encoding="utf-8").write(text)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = f"{BASE}/library"
CUR = f"{BASE}/data"
GROUPS = (("plants.curated.json", "docs/plant_id", "Plant and mushroom ID"),
          ("coastal.curated.json", "docs/coastal_id", "Coastal species ID"))
DANGER = ("danger", "regulated")
# Spanish key for every label on the drive lists (a2 W2: the 5 shellfish labels were missing)
LABEL_ES = (("DEADLY", "mortal"), ("POISONOUS", "venenoso"), ("BURNS SKIN", "quema la piel"),
            ("REGULATED", "prohibido tomarlo: no los coma"), ("EDIBLE", "comestible"),
            ("EDIBLE COOKED", "comestible cocido"),
            ("NOV–APR ONLY, NO ADVISORY", "comestible cocido solo del 1 de noviembre al 30 de abril y solo si no hay "
             "aviso sanitario"),
            ("ONLY IF NO ADVISORY", "comestible cocido solo si no hay aviso sanitario"),
            # a2 W1 (rt6): "permiso" read as a permit a fishing licence satisfies; the label means a health all-clear
            ("ONLY WITH OFFICIAL ALL-CLEAR", "comestible cocido solo si las autoridades de salud dicen que es seguro"))


def name(slug):
    return slug.replace("_", " ").capitalize()


def main():
    n = 0
    for cur, folder, title in GROUPS:
        if not os.path.isdir(f"{LIB}/{folder}"):   # photos not fetched: nothing to label
            continue
        data = {k: v for k, v in json.load(open(f"{CUR}/{cur}")).items() if not k.startswith("_")}
        rows, labels = [], []
        for slug, m in sorted(data.items(), key=lambda kv: (kv[1]["kind"] not in DANGER, kv[0])):
            d = f"{LIB}/{folder}/{slug}"
            if not os.path.isdir(d):
                print(f"WARN no folder: {slug}", file=sys.stderr)
                continue
            # optional curated 'verdict' says the condition plainly (shellfish: cooking does not remove toxins; FIXES #196)
            verdict = f"{m['label']} — {'DO NOT EAT' if m['kind'] in DANGER else m.get('verdict') or 'edible as described'}"
            look = f"\nDo not confuse with: {name(m['lookalike'])} (folder ../{m['lookalike']}/)" if m.get("lookalike") else ""
            put(f"{d}/README.txt",
                f"{name(slug)}\n{verdict}\n\n{m['note']}{look}\n\n"
                f"Photo credits: CREDITS.txt in this folder. Full card with photos side by side: plants.html in the "
                f"library's top folder (opens from the drive too, no server needed).\n")
            cp = f"{d}/CREDITS.txt"
            lines = [ln for ln in open(cp).read().splitlines() if not ln.startswith("# VERDICT:")]
            lines.insert(1, f"# VERDICT: {verdict}. See README.txt here.")
            put(cp, "\n".join(lines) + "\n")
            rows.append(f"{m['label']:13} {name(slug)}  ({slug}/)")
            labels.append(m["label"])
            n += 1
        # a2 page note: the coastal list has no deadly or poisonous entry, so say what really comes first
        first = ("deadly and poisonous ones listed first" if any(m["kind"] == "danger" for m in data.values())
                 else "the ones you may not take (REGULATED) listed first")
        key = "; ".join(f"{en} = {es}" for en, es in LABEL_ES if en in labels)
        put(f"{LIB}/{folder}/README.txt",
            f"{title} — {len(rows)} species, {first}.\n"
            f"Each folder has photos, a README.txt with the verdict and the warning text, and CREDITS.txt.\n"
            f"Never eat a plant, mushroom or shellfish on a photo match alone: read the folder's README.txt.\n"
            f"Español: nunca coma una planta, un hongo o un marisco solo porque se parece a una foto. Los hongos, los "
            f"mariscos y las plantas que se confunden con una planta mortal o venenosa tienen una línea «Español —» en "
            f"el README.txt de su carpeta. En la lista: {key}.\n\n"
            + "\n".join(rows) + "\n")
    print(f"species readme: {n}" + (f"; --check: {len(STALE)} file(s) would change" if CHECK else ""))
    for p in STALE:
        print(f"STALE {p}")
    return 1 if STALE else 0


if __name__ == "__main__":
    sys.exit(main())
