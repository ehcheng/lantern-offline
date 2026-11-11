#!/bin/bash
# Reseal on dev, then every dev-side gate. Pushing to the Pi is a separate step (deploy/push_seal.sh, then
# deploy/pi_mcp_deploy.sh when the MCP server or nginx conf changed).
#   screen -dmS r47 env T=r47 bash build/reseal_dev.sh          seal only: b5_reseal + acceptance (content stage unchanged)
#   screen -dmS r47 env T=r47 FULL=1 bash build/reseal_dev.sh   full: build_triage + r19_run (content regen, mcp index,
#                                                               embeddings, frontend, seal, t3/t4/t8) first
# Sandbox off. Log: logs/<T>_chain.log, ends with <T>_DEV_DONE.
cd "$(dirname "$0")/.."; L=logs; mkdir -p $L; T=${T:?T=tag}; log=$L/${T}_chain.log
if [ -n "${FULL:-}" ]; then
  echo "== build_triage $(date)" >> $log; python3 build/build_triage.py >> $log 2>&1 || { echo "$T FAIL build_triage" >> $log; exit 1; }
  echo "== r19_run $(date)" >> $log; T=$T bash build/r19_run.sh >> $log 2>&1 || { echo "$T FAIL r19_run" >> $log; exit 1; }
  # the 4 Spanish library notes: titles.json rows link to their rendered pages
  for n in energy/cargar_el_telefono_con_la_bateria_del_carro military_manuals/encender_fuego_con_lena_mojada \
           homesteading_extension/cultivos_de_cosecha_rapida food_preservation/conservar_carne_con_sal; do
    [ -s library/docs/$n.html ] && echo "note ok $n" >> $log || echo "$T FAIL note page missing docs/$n.html" >> $log; done
else
  echo "== seal_chain $T $(date)" >> $log; bash build/seal_chain.sh $T >> $log 2>&1
  echo "== t3 $(date)" >> $log; python3 tests/t3_reach.py > $L/t3_$T.log 2>&1; echo "t3 rc=$?" >> $log
  echo "== t4 dev $(date)" >> $log; python3 tests/t4_coverage.py > $L/t4_dev_$T.log 2>&1; echo "t4 rc=$?" >> $log
fi
grep -q CHAIN_DONE $log || { echo "$T FAIL seal not CHAIN_DONE" >> $log; exit 1; }
echo "== t5 dev $(date)" >> $log; python3 tests/t5_render.py 8 > $L/t5_dev_$T.log 2>&1; echo "t5 dev rc=$?" >> $log
echo "== c4_dev $(date)" >> $log; bash tests/c4_dev.sh > $L/c4_dev_$T.log 2>&1; echo "c4_dev rc=$?" >> $log
echo "== t8_mirror_entry $(date)" >> $log; python3 tests/t8_mirror_entry.py > $L/t8_mirror_entry_$T.log 2>&1; echo "t8_mirror_entry rc=$?" >> $log
echo "== narrow text (L7 #218) $(date)" >> $log; T=$T bash build/narrow_gate.sh >> $log 2>&1; rc=$?; [ $rc = 0 ] || echo "$T FAIL narrow text check" >> $log
echo "== report $(date)" >> $log; python3 tests/report.py >> $log 2>&1; grep -E "^\| t|Not green" tests/REPORT.md >> $log
echo "${T}_DEV_DONE $(date)" >> $log
