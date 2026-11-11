#!/usr/bin/env python3
"""fema.gov Akamai 403s every curl TLS fingerprint — fetch the 4 G2 items
through real Chrome (page.goto response body). Idempotent, %PDF + floor gated."""
import pathlib, sys
import os
from playwright.sync_api import sync_playwright

LIB = pathlib.Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/library/docs/emergency_mgmt")
ITEMS = [
    ("fema_e74_nonstructural_earthquake_damage_2012.pdf", 60_000_000,
     "https://www.fema.gov/sites/default/files/2020-07/fema_earthquakes_reducing-the-risks-of-nonstructural-earthquake-damage-a-practical-guide-fema-e-74.pdf"),
    ("fema_p530_earthquake_safety_at_home_2020.pdf", 11_000_000,
     "https://www.fema.gov/sites/default/files/2020-08/fema_earthquakes_fema-p-530-earthquake-safety-at-home-march-2020.pdf"),
    ("fema_b526_earthquake_safety_checklist_2023.pdf", 4_000_000,
     "https://www.fema.gov/sites/default/files/documents/fema_b-526-eq-safety-checklist.pdf"),
    ("fema_p312_homeowners_guide_retrofitting_flood_2014.pdf", 50_000_000,
     "https://www.fema.gov/sites/default/files/2020-07/fema_homeowners-guide-to-retrofitting_guide.pdf"),
]

fails = []
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page()
    for name, floor, url in ITEMS:
        out = LIB / name
        if out.exists() and out.stat().st_size >= floor and out.open("rb").read(4) == b"%PDF":
            print("SKIP", name); continue
        try:
            resp = pg.goto(url, timeout=300_000)
            body = resp.body()
        except Exception as e:
            print("FAIL", name, e); fails.append(name); continue
        if body[:4] == b"%PDF" and len(body) >= floor:
            out.write_bytes(body); print("OK  ", name, len(body))
        else:
            print("FAIL", name, "magic/floor", len(body)); fails.append(name)
    b.close()
sys.exit(1 if fails else 0)
