#!/usr/bin/env python3
"""Phase 1: copy the 2012 CD3WD PDFs out of the mounted ISOs into
library/docs/cd3wd/2012/<category>/. Skips _pexp (Cambridge past exam papers,
the owner decision 6). Idempotent: skips files already present with the same size.
Usage: python3 fetch/cd3wd_extract.py <mount_root_glob> """
import glob, os, shutil, sys, re, csv

CATS = {  # filename prefix -> folder (the owner names these; see CD3WD_PLAN.md)
 '_ag':'agriculture','_wa':'water','_co':'construction','_mc':'health',
 '_at':'appropriate_technology','_ms':'small_business','_ac':'small_business',
 '_acca':'accounting','_me':'metalwork','_engy':'energy','_wi':'wind_power',
 '_sl':'solar','_ed':'education','_ma':'manufacturing','_wo':'woodwork',
 '_ind':'industry','_mh':'micro_hydro','_tr':'transport','_el':'electricity',
 '_elct':'electricity','_elctr':'electricity','_bg':'biogas','_sa':'sanitation',
 '_it':'computing','_ec':'environment','_st':'stoves','_em':'emergency',
 '_au':'auto_mechanics','_cm':'communication','_curr':'school_curriculum',
 '_ref':'reference','_econ':'economics','_geog':'geography','_hist':'history',
 '_ppl':'reference','_in':'appropriate_technology','_eg':'energy','_sc':'reference',
 '_mng':'mining','_devcoop':'development','_rlgn':'reference','_mktg':'small_business',
 '_maths':'school_curriculum','_ltrcy':'education','_irri':'water','_fraud':'small_business',
 '_engg':'engineering','_dwg':'engineering','_ck':'cooking','_chess':'recreation','_art':'recreation',
}
SKIP = ('_pexp',)
dst_root = 'library/docs/cd3wd/2012'
rows = []; n = 0; skipped = 0
for src in sorted(glob.glob(sys.argv[1] + '/**/*.pdf', recursive=True)):
    name = os.path.basename(src)
    m = re.match(r'^(_[a-z]+)_', name)
    pre = m.group(1) if m else ''
    if pre in SKIP or '_pexp_' in src: skipped += 1; continue
    if pre.startswith('_cd3wd') or name.startswith('__ReadMe') or pre == '_Cd3wd': cat = 'about_cd3wd'
    elif pre in CATS: cat = CATS[pre]
    elif '_cnx_' in name or '_wikibks_' in name or 'chess' in name.lower(): cat = 'college_textbooks'
    else: cat = 'other'
    d = os.path.join(dst_root, cat); os.makedirs(d, exist_ok=True)
    dst = os.path.join(d, name)
    if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src): continue
    shutil.copy2(src, dst); n += 1
    rows.append((src.split('/')[-2] if '/' in src else '', cat, name))
print(f'copied {n}, skipped {skipped} pexp')
with open('logs/audit/cd3wd_extract.csv', 'a') as f: csv.writer(f).writerows(rows)
