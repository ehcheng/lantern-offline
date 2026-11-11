#!/bin/bash
# Second pass after the accented-Latin fix in gen_doc_meta: redo stem-only cd3wd entries, refresh sample.
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
sed -n '/^python3 - <<.PY.$/,$p' fetch/cd3wd_meta_followup.sh | sed -n '2,$p' | sed '/^PY$/,$!b' > /dev/null
python3 - <<'PY'
import json, random
d=json.load(open('data/docs.curated.json'))
keys=[k for k in d if k.startswith('docs/cd3wd/2012/')]
random.seed(20260930); s=random.sample(keys,50)
with open('logs/audit/cd3wd_meta_sample.md','w') as f:
    f.write('# CD3WD 2012 metadata sample (50 random of %d), for the owner\n\nGenerated 2026-09-30. Filename, then LLM title and one-liner; src=stem means the title is a tidied filename (no usable prose).\n\n' % len(keys))
    for k in sorted(s):
        f.write('- `%s`  \n  **%s** (%s)  \n  %s\n' % (k.split('/',3)[3], d[k].get('t',''), d[k].get('src',''), d[k].get('s','')))
print('sample written')
PY
echo FOLLOWUP2_DONE
