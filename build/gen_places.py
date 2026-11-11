#!/usr/bin/env python3
"""places.js (BUILD_PLAN A5): region-name list + phone-map downloads,
straight from the maps/organicmaps + maps/osmand file listings. v1 = names
only, no geocoding (explicit descope). Shipped as a .js global (like plants.js)
because fetch() of a .json is blocked on file:// and map.html lists the files
in drive mode too (red team 10-09 a3 B1, FIXES #155)."""
import json, os, re

LIB = os.path.join(os.path.dirname(__file__), '..', 'library')
OUT = os.environ.get('PLACES_OUT') or os.path.join(LIB, '_app', 'index', 'places.js')  # PLACES_OUT: a dry run

# round 9 a3 W2 (#256): Organic Maps names its files after its own region tree, with upstream typos and a repeated
# parent ("US_Illinois_Chickago", "US_California_Sacramento_Sacramento"). The file names stay; the list shows the place.
# The Bay Area file's own strings name Redwood City, Golden Gate Park and Lake Merritt (redteam_20261026_a3.md W2).
DISPLAY = {"US_Illinois_Chickago": "US Illinois Chicago",
           "US_Texas_Wako": "US Texas Waco",
           "US_California_Santa_Clara_Palo Alto": "US California Bay Area (San Francisco, Oakland, Palo Alto)",
           "US_California_Bakersfield_Bakersfield": "US California Bakersfield",
           "US_California_Bakersfield_Lancaster": "US California Lancaster",
           "US_California_Sacramento_Fresno": "US California Fresno",
           "US_California_Sacramento_Sacramento": "US California Sacramento",
           "US_California_Sacramento_Stockton": "US California Stockton",
           "US_California_LA": "US California Los Angeles",
           "US_California_LA North": "US California Los Angeles North",
           "US_Oklahoma_Oklahoma": "US Oklahoma Oklahoma City",
           "US_Missouri_Kansas": "US Missouri Kansas City",
           "US_New York_New York": "US New York New York City",
           # round 10 a3 W2 (#275): the file's own strings name Santa Cruz 813 times, Monterey 1,279, Salinas 269,
           # Gilroy 192, Hollister 81 and Santa Clara 35 (858 in the Bay Area file)
           "US_California_Santa_Clara_Santa Cruz": "US California Santa Cruz and Monterey (Salinas, Gilroy, Hollister)",
           # round 10 a3 N3: the country once, and the OsmAnd row named as the shelf names it ("of", not "Of")
           "US_United States Minor Outlying Islands": "US Minor Outlying Islands",
           "Us_district-of-columbia_northamerica_2": "US District of Columbia"}

def mb(n):
    """round 9 a3 N5: the shelf's rule (gen_shelves.human_size): one decimal under 10 MB, whole numbers above."""
    x = n / 1e6
    assert x < 999.5, "a region file of 1 GB or more: gen_shelves would print GB"  # ponytail: no GB branch, none is that big
    return f"{x:.1f}" if x < 9.95 else f"{x:.0f}"

def rows(sub, ext):
    d = os.path.join(LIB, 'maps', sub)
    out = []
    if not os.path.isdir(d):
        return out
    for f in sorted(os.listdir(d)):
        if not f.endswith(ext):
            continue
        name = DISPLAY.get(f[:-len(ext)]) or re.sub(r'\.[a-z0-9.]+$', '', f).replace('_', ' ').strip()
        if sub == 'osmand' and f[:-len(ext)] not in DISPLAY:  # RT3 a3 N10: "Us_california_san-diego_northamerica_2" -> "US California San Diego"
            name = re.sub(r'^Us\b', 'US', re.sub(r' northamerica \d+$', '', name).replace('-', ' ').title())
        out.append({
            'name': name,
            'file': 'maps/%s/%s' % (sub, f),
            # #188 (RT3 a3 W3): decimal MB, what a phone's file manager and Organic Maps show (was MiB labelled MB)
            'mb': mb(os.path.getsize(os.path.join(d, f))),
        })
    return sorted(out, key=lambda r: r['name'].lower())  # a display name can move a row (Bay Area)

if __name__ == '__main__':  # gen_shelves can import DISPLAY and mb() for the maps shelf rows
    om, oa = (os.path.join(LIB, 'maps', s) for s in ('organicmaps', 'osmand'))
    if os.path.isdir(om) and os.path.isdir(oa):  # a build without the map apps' files has nothing to check
        assert DISPLAY.keys() <= {f[:-4] for f in os.listdir(om)} | {f[:-8] for f in os.listdir(oa)}, 'DISPLAY names a missing file'
    places = {
        'organicmaps': rows('organicmaps', '.mwm'),
        'osmand': rows('osmand', '.obf.zip'),
    }
    with open(OUT, 'w') as fh:
        fh.write('window.LANTERN_PLACES=')
        json.dump(places, fh, separators=(',', ':'))
        fh.write(';\n')
    print('places.js: %d organicmaps, %d osmand, %d bytes' %
          (len(places['organicmaps']), len(places['osmand']), os.path.getsize(OUT)))
