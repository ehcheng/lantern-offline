# Organic Maps (.mwm) Download Research

**Research date:** 2026-09-14

---

## 1. Data Version

The `dataVersion` is an integer embedded in `data/countries.json` under key `v`.

- **OM master (`countries.json`):** `260714` (pinned to last tagged release)
- **OM CDN latest available:** `260826` (verified 200 OK on cdn-us1)
- **CoMaps mapgen latest:** `260826` (same version, separate build)

Source of truth for "what's on the CDN right now":
- Organic Maps: query `https://meta.omaps.app/maps` → returns list of CDN base URLs
- CoMaps: query `https://cdn-us-1.comaps.app/servers` → returns list of CDN base URLs

**Recommended version:** `260826` — confirmed present on both OM and CoMaps CDNs.

To programmatically fetch the current version:

```bash
# Returns integer version from countries.json master branch
curl -sf "https://raw.githubusercontent.com/organicmaps/organicmaps/master/data/countries.json" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['v'])"
# Returns: 260714 (OM master pinned version)

# CoMaps mapgen directory listing shows all available versions:
# https://mapgen-fi-1.comaps.app/maps/
```

---

## 2. CDN URL Pattern

```
https://<cdn-host>/maps/<dataVersion>/<region-id>.mwm
```

Example (verified 200, 32 MB):
```
https://cdn-us1.organicmaps.app/maps/260714/US_Delaware.mwm
```

### Organic Maps CDN hosts (from `private.h`)

```
https://cdn-nl1.organicmaps.app/
https://cdn-uk1.organicmaps.app/
https://cdn.organicmaps.app/
https://cdn-us1.organicmaps.app/   ← US-located, fastest for US downloads
```

Metaserver (returns JSON array of CDN URLs based on requester location):
```
https://meta.omaps.app/maps
```

### CoMaps CDN hosts (from `private.h` in comaps/comaps)

```
https://comaps.firewall-gateway.de/      ← Germany
https://cdn-us-2.comaps.tech/            ← US (404 on tested regions — may be partial mirror)
https://cdn-fi-1.comaps.app/             ← Finland
https://comaps.openstreetmap.fr/         ← France
https://comaps-it1.unfoxo.it/            ← Italy
https://comaps-cdn.s3-website.cloud.ru/  ← Russia
https://mapgen-fi-1.comaps.app/          ← Finland mapgen (primary build server, open directory)
```

Metaserver: `https://cdn-us-1.comaps.app/servers` → returns JSON array

**CoMaps is a viable fallback.** `mapgen-fi-1.comaps.app` has open directory listing and confirmed Delaware at 260826.

---

## 3. US Region Naming

Regions are NOT by state — they're sub-state metro/geographic areas. Format: `US_<State>_<Area>`.

No spaces in the URL matter: regions with spaces in the `id` field use literal spaces in the URL (URL-encoded as `%20`). Example: `US_California_LA North` → `US_California_LA%20North.mwm`.

**States that are a single file (no subdivision):**

| Region ID | Size |
|-----------|------|
| US_Alaska | 327.6 MB |
| US_Connecticut | 179.1 MB |
| US_Delaware | 30.9 MB |
| US_Guam | 5.0 MB |
| US_Hawaii | 32.4 MB |
| US_Maine | 114.8 MB |
| US_Nevada | 146.2 MB |
| US_New Hampshire | 77.3 MB |
| US_Puerto Rico | 75.2 MB |
| US_Rhode Island | 45.2 MB |
| US_South Dakota | 87.3 MB |
| US_Vermont | 56.3 MB |
| US_West Virginia | 132.7 MB |
| US_Wyoming | 109.0 MB |

**States with multiple sub-regions** (select examples):

- California: 10 files (LA, San Diego, Sacramento subregions, etc.)
- Texas: 11 files
- Florida: 5 files
- New York: 4 files

**World files:**

| ID | Size |
|----|------|
| World | 61.0 MB |
| WorldCoasts | 8.0 MB |

---

## 4. Complete US Leaf-Node Region List (163 total)

All downloadable leaf nodes from `data/countries.json` v260714:

```
US_Alabama_Birmingham          # 93.9 MB
US_Alabama_Montgomery          # 133.0 MB
US_Alaska                      # 327.6 MB
US_Arizona_Flagstaff           # 95.3 MB
US_Arizona_Phoenix             # 186.1 MB
US_Arizona_Tucson              # 76.4 MB
US_Arkansas_North              # 97.0 MB
US_Arkansas_South              # 63.5 MB
US_California_Bakersfield_Bakersfield  # 52.8 MB
US_California_Bakersfield_Lancaster    # 71.4 MB
US_California_Chico            # 57.8 MB
US_California_LA               # 294.8 MB
US_California_LA North         # 90.4 MB
US_California_Redding          # 69.9 MB
US_California_Sacramento_Fresno       # 66.3 MB
US_California_Sacramento_Sacramento   # 75.5 MB
US_California_Sacramento_Stockton     # 77.6 MB
US_California_San Diego        # 130.3 MB
US_California_Santa_Clara_Palo Alto   # 223.3 MB
US_California_Santa_Clara_Santa Cruz  # 40.0 MB
US_Colorado_Aspen              # 98.3 MB
US_Colorado_Denver             # 196.2 MB
US_Colorado_South              # 86.1 MB
US_Connecticut                 # 179.1 MB
US_Delaware                    # 30.9 MB
US_Florida_Gainesville         # 147.9 MB
US_Florida_Jacksonville        # 211.0 MB
US_Florida_Miami               # 205.2 MB
US_Florida_Orlando             # 96.3 MB
US_Florida_Tampa               # 199.7 MB
US_Georgia_Atlanta             # 158.9 MB
US_Georgia_Macon               # 85.6 MB
US_Georgia_North               # 63.1 MB
US_Georgia_South               # 91.7 MB
US_Guam                        # 5.0 MB
US_Hawaii                      # 32.4 MB
US_Idaho_North                 # 66.7 MB
US_Idaho_South                 # 82.4 MB
US_Illinois_Chickago           # 126.7 MB
US_Illinois_Elgin              # 87.1 MB
US_Illinois_Rockford           # 51.0 MB
US_Illinois_South              # 88.5 MB
US_Illinois_Springfield        # 105.9 MB
US_Indiana_Evansville          # 63.6 MB
US_Indiana_Indianapolis        # 97.1 MB
US_Indiana_North               # 129.1 MB
US_Iowa_Des Moines             # 69.2 MB
US_Iowa_Waterloo               # 67.5 MB
US_Iowa_West                   # 66.9 MB
US_Kansas_East                 # 81.7 MB
US_Kansas_West                 # 38.9 MB
US_Kansas_Wichita              # 66.3 MB
US_Kentucky_East               # 79.0 MB
US_Kentucky_Louisville         # 47.3 MB
US_Kentucky_West               # 63.2 MB
US_Louisiana_Central           # 88.8 MB
US_Louisiana_New Orleans       # 98.0 MB
US_Maine                       # 114.8 MB
US_Maryland_Baltimore          # 135.4 MB
US_Maryland_and_DC             # 117.4 MB
US_Massachusetts_Boston        # 91.9 MB
US_Massachusetts_Central       # 46.7 MB
US_Massachusetts_Plymouth      # 42.6 MB
US_Massachusetts_Southeastern  # 21.1 MB
US_Massachusetts_West          # 41.4 MB
US_Michigan_Detroit            # 140.9 MB
US_Michigan_Grand Rapids       # 111.4 MB
US_Michigan_Lansing            # 114.5 MB
US_Michigan_North              # 48.1 MB
US_Minnesota_Minneapolis       # 103.3 MB
US_Minnesota_North             # 87.2 MB
US_Minnesota_Rochester         # 74.5 MB
US_Minnesota_Saint Cloud       # 71.2 MB
US_Mississippi_Gulfport        # 35.4 MB
US_Mississippi_North           # 99.7 MB
US_Missouri_East               # 33.4 MB
US_Missouri_Kansas             # 81.9 MB
US_Missouri_Springfield        # 67.7 MB
US_Missouri_St Louis           # 101.9 MB
US_Montana_East                # 66.7 MB
US_Montana_West                # 66.6 MB
US_Nebraska_East               # 70.4 MB
US_Nebraska_West               # 69.6 MB
US_Nevada                      # 146.2 MB
US_New Hampshire               # 77.3 MB
US_New Jersey_North            # 97.9 MB
US_New Jersey_South            # 109.2 MB
US_New Mexico_Albuquerque      # 89.3 MB
US_New Mexico_Roswell          # 72.9 MB
US_New York_East               # 127.3 MB
US_New York_New York           # 117.9 MB
US_New York_North              # 125.9 MB
US_New York_West               # 205.3 MB
US_North Carolina_Asheville    # 70.3 MB
US_North Carolina_Charlotte    # 115.2 MB
US_North Carolina_Greensboro   # 89.2 MB
US_North Carolina_Raleigh      # 105.7 MB
US_North Carolina_Wilmington   # 66.6 MB
US_North Carolina_Wilson       # 66.1 MB
US_North Dakota_Bismarck       # 38.9 MB
US_North Dakota_East           # 54.0 MB
US_North Dakota_Minot          # 33.4 MB
US_Ohio_Cincinnati             # 125.6 MB
US_Ohio_Cleveland              # 147.0 MB
US_Ohio_Columbus               # 100.9 MB
US_Ohio_Toledo                 # 66.9 MB
US_Oklahoma_East               # 33.2 MB
US_Oklahoma_Oklahoma           # 65.3 MB
US_Oklahoma_Tulsa              # 73.9 MB
US_Oklahoma_West               # 30.5 MB
US_Oregon_Eugene               # 84.6 MB
US_Oregon_Portland             # 118.7 MB
US_Oregon_West                 # 69.9 MB
US_Pennsylvania_Central        # 122.0 MB
US_Pennsylvania_Pittsburgh     # 114.8 MB
US_Pennsylvania_Reading        # 115.7 MB
US_Pennsylvania_Scranton       # 100.2 MB
US_Puerto Rico                 # 75.2 MB
US_Rhode Island                # 45.2 MB
US_South Carolina_Charleston   # 57.9 MB
US_South Carolina_Columbia     # 102.9 MB
US_South Carolina_Florence     # 65.4 MB
US_South Dakota                # 87.3 MB
US_Tennessee_East              # 140.8 MB
US_Tennessee_West              # 141.3 MB
US_Texas_Amarillo              # 43.9 MB
US_Texas_Austin                # 109.7 MB
US_Texas_Dallas                # 198.8 MB
US_Texas_Houston               # 146.5 MB
US_Texas_Lubbock               # 46.0 MB
US_Texas_San Antonio           # 93.8 MB
US_Texas_Southwest             # 46.8 MB
US_Texas_Tyler                 # 95.0 MB
US_Texas_Victoria              # 40.1 MB
US_Texas_Wako                  # 63.0 MB
US_Texas_West                  # 76.0 MB
US_United States Minor Outlying Islands  # 1.5 MB
US_Utah_North                  # 134.0 MB
US_Utah_South                  # 63.1 MB
US_Vermont                     # 56.3 MB
US_Virginia_Alexandria         # 102.5 MB
US_Virginia_Lynchburg          # 101.9 MB
US_Virginia_Norfolk            # 92.4 MB
US_Virginia_Richmond           # 70.8 MB
US_Virginia_Roanoke            # 68.7 MB
US_Washington_Coast            # 183.8 MB
US_Washington_Seattle          # 108.3 MB
US_Washington_Yakima           # 116.0 MB
US_West Virginia               # 132.7 MB
US_Wisconsin_Eau Claire        # 60.9 MB
US_Wisconsin_Madison           # 67.6 MB
US_Wisconsin_Milwaukee         # 136.0 MB
US_Wisconsin_North             # 58.9 MB
US_Wyoming                     # 109.0 MB
World                          # 61.0 MB
WorldCoasts                    # 8.0 MB
```

Total ~163 US leaf files + World + WorldCoasts. Estimated total: ~13–14 GB.

---

## 5. Test Download Verification

```bash
curl -L -C - -o library/maps/organicmaps/US_Delaware.mwm \
  "https://cdn-us1.organicmaps.app/maps/260714/US_Delaware.mwm"
# Result: 200 OK, 31 MB downloaded in ~1 second on local network
```

Log saved to: `logs/organicmaps_research.log`

---

## 6. Key Source Files

| File | Content |
|------|---------|
| `private.h` (OM) | CDN base URLs, metaserver URL |
| `data/countries.json` | Region tree with `v` (dataVersion), sizes, hashes |
| `https://meta.omaps.app/maps` | Live CDN list (geo-routed) |
| `https://cdn-us-1.comaps.app/servers` | CoMaps live CDN list |
| `https://mapgen-fi-1.comaps.app/maps/` | CoMaps open directory, all versions |

---

## 7. Caveats

- Region IDs with spaces use literal spaces in the filename (URL-encode as `%20` in curl).
- Parent nodes (e.g., `US_Arkansas`, `US_Georgia`) have `s: 0` and no direct file — download sub-regions only.
- The `v` in `countries.json` on master (260714) lags behind the CDN's latest (260826). The CDN accepts both.
- CoMaps CDN (`cdn-us-2.comaps.tech`) returned 404 for tested regions — use `mapgen-fi-1.comaps.app` or `cdn-fi-1.comaps.app` as fallback.
- No authentication required. No rate limit discovered during testing.
