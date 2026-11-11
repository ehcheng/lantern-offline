#!/bin/bash
# After the first gen_doc_meta --only docs/cd3wd run: drop stem-only entries (text-less before
# OCR) for the two new shelves, then regenerate them and the school textbooks. Serial (one Ollama).
set -euo pipefail
cd "$(dirname "$0")/.."
python3 - <<'PY'
import json
P='data/docs.curated.json'; d=json.load(open(P))
gone=[k for k,v in d.items() if v.get('src')=='stem' and (k.startswith('docs/cd3wd/2012/') or k.startswith('docs/school_textbooks/'))]
for k in gone: del d[k]
json.dump(d,open(P,'w'),indent=1,ensure_ascii=False,sort_keys=True); print('dropped stem entries:',len(gone))
PY
python3 build/gen_doc_meta.py --only docs/cd3wd
python3 build/gen_doc_meta.py --only docs/school_textbooks
python3 - <<'PY'
import json, random
d=json.load(open('data/docs.curated.json'))
keys=[k for k in d if k.startswith('docs/cd3wd/2012/')]
random.seed(20260930); s=random.sample(keys,50)
with open('logs/audit/cd3wd_meta_sample.md','w') as f:
    f.write('# CD3WD 2012 metadata sample (50 random of %d), for the owner\n\nGenerated %s. Filename, then LLM title and one-liner.\n\n' % (len(keys), '2026-09-30'))
    for k in sorted(s):
        f.write('- `%s`  \n  **%s**  \n  %s\n' % (k.split('/',3)[3], d[k].get('t',''), d[k].get('s','')))
print('sample written')
PY
echo FOLLOWUP_DONE
