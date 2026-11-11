#!/usr/bin/env python3
"""Full-California aerial imagery → MBTiles, from USGS USGSImageryOnly (NAIP-backed,
public domain). z8–ZMAX over CA bbox. Idempotent: existing tiles skipped; rerun on death.
Viewer: any MBTiles reader (QGIS, OsmAnd, tileserver)."""
import math, os, sqlite3, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = f"{BASE}/library/maps/satellite_ca/satellite_ca_naip.mbtiles"
LOG = f"{BASE}/logs/satellite.log"
SRV = "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile"
W, S, E, N = -124.48, 32.52, -114.13, 42.01  # California bbox
ZMIN, ZMAX = 8, 14  # 09-17: cap v1 at z14 (~10m/px). z15/16 later as
                    # home-region-only bbox top-up (vector layer covers streets)
WORKERS = 8

def log(m):
    with open(LOG, "a") as f:
        f.write(f"{time.strftime('%F %T')} {m}\n")

def tiles_for(z):
    n = 2 ** z
    x0 = int((W + 180) / 360 * n); x1 = int((E + 180) / 360 * n)
    def ty(lat):
        r = math.radians(lat)
        return int((1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * n)
    y0, y1 = ty(N), ty(S)
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            yield x, y

def fetch(z, x, y):
    url = f"{SRV}/{z}/{y}/{x}"
    for attempt in range(2):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                b = r.read()
            return (z, x, y, b) if len(b) > 300 else None  # skip empty/blank tiles
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "FAIL"      # no-coverage (ocean) tile — permanent, don't retry
            time.sleep(2 * (attempt + 1))
        except Exception:
            time.sleep(2 * (attempt + 1))
    return "FAIL"

def main():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    db = sqlite3.connect(DB)
    db.executescript("""
      CREATE TABLE IF NOT EXISTS tiles (zoom_level INT, tile_column INT, tile_row INT,
        tile_data BLOB, PRIMARY KEY(zoom_level,tile_column,tile_row));
      CREATE TABLE IF NOT EXISTS metadata (name TEXT PRIMARY KEY, value TEXT);
      -- permanent-fail tiles (NAIP no-coverage / CDN-poisoned): skipped on
      -- resume so restarts don't re-burn 30min re-attempting dead tiles.
      -- To force a retry sweep: DELETE FROM fails;
      CREATE TABLE IF NOT EXISTS fails (zoom INT, x INT, y INT,
        PRIMARY KEY(zoom,x,y));
      INSERT OR REPLACE INTO metadata VALUES
        ('name','California NAIP (USGSImageryOnly)'),('type','baselayer'),
        ('version','1.1'),('format','jpg'),
        ('bounds','-124.48,32.52,-114.13,42.01'),
        ('description','USGS ImageryOnly tiles (NAIP, public domain), CA bbox, 2026-09');
    """)
    # zoom range derives from the constants — hand-copied values drifted once
    db.execute("INSERT OR REPLACE INTO metadata VALUES ('minzoom',?)", (str(ZMIN),))
    db.execute("INSERT OR REPLACE INTO metadata VALUES ('maxzoom',?)", (str(ZMAX),))
    db.commit()
    fails = 0
    for z in range(ZMIN, ZMAX + 1):
        have = {(x, y) for x, y in db.execute(
            "SELECT tile_column,(1<<?)-1-tile_row FROM tiles WHERE zoom_level=?", (z, z))}
        dead = {(x, y) for x, y in db.execute(
            "SELECT x,y FROM fails WHERE zoom=?", (z,))}
        todo = [(x, y) for x, y in tiles_for(z)
                if (x, y) not in have and (x, y) not in dead]
        log(f"z{z}: {len(todo)} to fetch ({len(have)} stored, {len(dead)} known-dead)")
        batch = []
        # futures + wait(FIRST_COMPLETED, 300s) gap detector: urllib reads on
        # half-closed CDN conns can hang past their timeout (observed: all 8
        # workers CLOSE_WAIT, db stale 30min). A 300s gap with zero completions
        # = wedged; hard-exit, the screen wrapper relaunches, resume skips
        # stored + known-dead tiles. (as_completed's timeout is total-elapsed,
        # not per-gap — wrong tool: it fires mid-download on big levels.)
        ex = ThreadPoolExecutor(WORKERS)
        fut2tile = {ex.submit(fetch, z, x, y): (x, y) for x, y in todo}
        pending = set(fut2tile)
        while pending:
            done, pending = wait(pending, timeout=300, return_when=FIRST_COMPLETED)
            if not done:
                if batch:
                    db.executemany("INSERT OR REPLACE INTO tiles VALUES (?,?,?,?)", batch)
                    db.commit()
                log(f"z{z}: STALLED (no completion in 300s) — exiting for relaunch")
                db.close()
                os._exit(3)
            for fut in done:
                res = fut.result()
                if res == "FAIL":
                    fails += 1
                    fx, fy = fut2tile[fut]
                    db.execute("INSERT OR IGNORE INTO fails VALUES (?,?,?)", (z, fx, fy))
                    continue
                if res is None:
                    continue
                zz, x, y, b = res
                batch.append((zz, x, (1 << zz) - 1 - y, b))
                if len(batch) >= 500:
                    db.executemany("INSERT OR REPLACE INTO tiles VALUES (?,?,?,?)", batch)
                    db.commit()
                    batch.clear()
        ex.shutdown(wait=False)
        if batch:
            db.executemany("INSERT OR REPLACE INTO tiles VALUES (?,?,?,?)", batch)
        db.commit()   # also persists fails-table inserts on tile-less levels
        n = db.execute("SELECT COUNT(*) FROM tiles").fetchone()[0]
        # page_count*page_size ≈ db size; SUM(LENGTH(blob)) was a full scan
        # over tens of GB per zoom level
        sz = (db.execute("PRAGMA page_count").fetchone()[0]
              * db.execute("PRAGMA page_size").fetchone()[0])
        log(f"z{z} done. total tiles={n} size={sz/1e9:.1f}GB fails-so-far={fails}")
    log(f"ALL DONE. fails={fails} (rerun to retry)")

if __name__ == "__main__":
    main()
