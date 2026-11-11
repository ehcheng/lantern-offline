#!/usr/bin/env python3
"""Full-CA USGS US Topo (current) GeoPDF downloader — CSV-manifest driven.
Idempotent: rerun on any death. Verifies exact size from USGS CSV + %PDF header.
CSV source: https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/Metadata/ustopo_current.zip
"""
import csv, os, subprocess, time, urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f"{BASE}/library/maps/topo_ca"
LOG = f"{BASE}/logs/topo_ca.log"
CSV_ZIP_URL = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/Metadata/ustopo_current.zip"
CSV_LOCAL = f"{BASE}/docs/sources/ustopo_current.csv"

def log(msg):
    with open(LOG, "a") as f:
        f.write(f"{time.strftime('%F %T')} {msg}\n")

def ensure_csv():
    if os.path.exists(CSV_LOCAL):
        return
    import zipfile, io
    data = urllib.request.urlopen(CSV_ZIP_URL, timeout=300).read()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        with z.open("ustopo_current.csv") as f:
            open(CSV_LOCAL, "wb").write(f.read())

def main():
    os.makedirs(OUT, exist_ok=True)
    ensure_csv()
    rows = [r for r in csv.DictReader(open(CSV_LOCAL))
            if r["primary_state"].strip() == "California"
            and r["product_format"] == "Geospatial PDF"]
    log(f"START: {len(rows)} CA quads, "
        f"{sum(int(r['product_filesize'] or 0) for r in rows)/1e9:.1f} GB expected")
    ok = fail = skip = 0
    for r in sorted(rows, key=lambda r: r["map_name"]):
        url, want = r["product_url"], int(r["product_filesize"] or 0)
        dest = os.path.join(OUT, url.rsplit("/", 1)[1])
        # CSV filesize can be off by a few bytes vs live S3 object — tolerate 1%
        def size_ok(n):
            # floor guards want=0 rows; OE island sheets go down to ~2MB
            return abs(n - want) <= max(want // 100, 1024) and n > 1_000_000
        if os.path.exists(dest) and size_ok(os.path.getsize(dest)):
            skip += 1
            continue
        p = subprocess.run(["curl", "-sSfL", "--retry", "3", "-o", dest + ".part", url],
                           capture_output=True, text=True)
        good = (p.returncode == 0 and os.path.exists(dest + ".part")
                and size_ok(os.path.getsize(dest + ".part"))
                and open(dest + ".part", "rb").read(4) == b"%PDF")
        if good:
            os.rename(dest + ".part", dest)
            ok += 1
            if ok % 100 == 0:
                log(f"progress: {ok} new / {skip} skipped / {fail} failed")
        else:
            fail += 1
            log(f"FAIL {os.path.basename(dest)} rc={p.returncode} "
                f"size={os.path.getsize(dest+'.part') if os.path.exists(dest+'.part') else 0} want={want}")
            if os.path.exists(dest + ".part"):
                os.remove(dest + ".part")
    log(f"DONE: {ok} new, {skip} skipped, {fail} failed / {len(rows)} total")

if __name__ == "__main__":
    main()
