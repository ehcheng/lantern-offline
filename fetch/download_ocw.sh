#!/usr/bin/env bash
# download_ocw.sh — MIT OpenCourseWare course package downloader
# Idempotent, resumable. Skips existing files. Logs to logs/ocw.log
# Launch: screen -dmS ocw bash /path/to/download_ocw.sh
# Manual run: bash download_ocw.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEST="${PROJECT_DIR}/library/docs/mit_ocw"
LOG="${PROJECT_DIR}/logs/ocw.log"

mkdir -p "${DEST}" "${PROJECT_DIR}/logs"
exec >> "${LOG}" 2>&1
echo ""
echo "=== OCW download started $(date) ==="

# ponytail: sequential downloads, not parallel — 3-4 concurrent saturates the link per AGENTS.md
download_zip() {
  local url="$1"
  local dir="$2"
  local filename
  filename="$(basename "${url}")"
  local out="${dir}/${filename}"
  mkdir -p "${dir}"
  if [[ -f "${out}" ]]; then
    echo "[SKIP] ${filename} already exists"
    return
  fi
  echo "[DOWN] ${url}"
  curl -fL --retry 3 --retry-delay 5 -o "${out}.tmp" "${url}" && mv "${out}.tmp" "${out}"
  local mb
  mb=$(du -m "${out}" | awk '{print $1}')
  echo "[DONE] ${filename} (${mb}MB)"
}

download_video_dir() {
  # Download all mp4s from an archive.org collection into a videos/ subdir
  local collection_id="$1"
  local dir="$2"
  local vdir="${dir}/videos"
  mkdir -p "${vdir}"
  echo "[VIDEO] Fetching file list for ${collection_id}"
  local files
  files=$(curl -s "https://archive.org/metadata/${collection_id}" | \
    python3 -c "
import json,sys
d=json.load(sys.stdin)
for f in d.get('files',[]):
    n=f.get('name','')
    if n.endswith('.mp4') or n.endswith('.MP4'):
        print(n)
")
  local count=0
  while IFS= read -r fname; do
    [[ -z "${fname}" ]] && continue
    local url="https://archive.org/download/${collection_id}/${fname}"
    local out="${vdir}/$(basename "${fname}")"
    if [[ -f "${out}" ]]; then
      echo "[SKIP] $(basename "${fname}")"
      continue
    fi
    echo "[DOWN] $(basename "${fname}")"
    curl -fL --retry 3 --retry-delay 10 -o "${out}.tmp" "${url}" && mv "${out}.tmp" "${out}"
    count=$((count+1))
  done <<< "${files}"
  echo "[VIDEO DONE] ${count} new files for ${collection_id}"
}

# ─── MATH ────────────────────────────────────────────────────────────────────
download_zip \
  "https://ocw.mit.edu/courses/18-03-differential-equations-spring-2010/18.03-spring-2010.zip" \
  "${DEST}/18.03_differential_equations"

download_zip \
  "https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/18.06-spring-2010.zip" \
  "${DEST}/18.06_linear_algebra"

# 18.06 lecture videos (Strang) — archive.org MIT18.06S05_MP4 (~5GB)
download_video_dir "MIT18.06S05_MP4" "${DEST}/18.06_linear_algebra"

download_zip \
  "https://ocw.mit.edu/courses/18-05-introduction-to-probability-and-statistics-spring-2022/18.05-spring-2022.zip" \
  "${DEST}/18.05_probability_statistics"

download_zip \
  "https://ocw.mit.edu/courses/18-650-statistics-for-applications-fall-2016/18.650-fall-2016.zip" \
  "${DEST}/18.650_statistics_applications"

# ─── PHYSICS ─────────────────────────────────────────────────────────────────
# 8.01SC (Lewin era TEAL format) — zip includes embedded media, ~192MB
download_zip \
  "https://ocw.mit.edu/courses/8-01sc-classical-mechanics-fall-2016/8.01sc-fall-2016.zip" \
  "${DEST}/8.01sc_classical_mechanics"

# 8.01 lecture videos — MIT8.01F16 archive.org (~6GB)
download_video_dir "MIT8.01F16" "${DEST}/8.01sc_classical_mechanics"

download_zip \
  "https://ocw.mit.edu/courses/8-02-physics-ii-electricity-and-magnetism-spring-2007/8.02-spring-2007.zip" \
  "${DEST}/8.02_electricity_magnetism"
# NOTE: 8.02 videos skipped (budget; 4GB archive MIT8.02S02) — add: download_video_dir MIT8.02S02

download_zip \
  "https://ocw.mit.edu/courses/8-04-quantum-physics-i-spring-2016/8.04-spring-2016.zip" \
  "${DEST}/8.04_quantum_physics"

download_zip \
  "https://ocw.mit.edu/courses/8-044-statistical-physics-i-spring-2013/8.044-spring-2013.zip" \
  "${DEST}/8.044_statistical_physics"

# ─── CS/EE ───────────────────────────────────────────────────────────────────
download_zip \
  "https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/6.0001-fall-2016.zip" \
  "${DEST}/6.0001_intro_cs_python"
# NOTE: 6.0001 videos skipped (budget; 1.4GB archive MIT6.0001F16) — add download_video_dir MIT6.0001F16

download_zip \
  "https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/6.006-spring-2020.zip" \
  "${DEST}/6.006_algorithms"
# NOTE: 6.006 videos skipped (budget; 5GB archive MIT6.006F11) — add download_video_dir MIT6.006F11

download_zip \
  "https://ocw.mit.edu/courses/6-002-circuits-and-electronics-spring-2007/6.002-spring-2007.zip" \
  "${DEST}/6.002_circuits_electronics"

download_zip \
  "https://ocw.mit.edu/courses/6-041sc-probabilistic-systems-analysis-and-applied-probability-fall-2013/6.041sc-fall-2013.zip" \
  "${DEST}/6.041sc_probabilistic_systems"

download_zip \
  "https://ocw.mit.edu/courses/6-867-machine-learning-fall-2006/6.867-fall-2006.zip" \
  "${DEST}/6.867_machine_learning"

# ─── CHEMISTRY ───────────────────────────────────────────────────────────────
download_zip \
  "https://ocw.mit.edu/courses/5-111sc-principles-of-chemical-science-fall-2014/5.111sc-fall-2014.zip" \
  "${DEST}/5.111sc_chemical_science"

download_zip \
  "https://ocw.mit.edu/courses/3-091sc-introduction-to-solid-state-chemistry-fall-2010/3.091sc-fall-2010.zip" \
  "${DEST}/3.091sc_solid_state_chemistry"

# ─── BIOLOGY ─────────────────────────────────────────────────────────────────
download_zip \
  "https://ocw.mit.edu/courses/7-016-introductory-biology-fall-2018/7.016-fall-2018.zip" \
  "${DEST}/7.016_introductory_biology"

download_zip \
  "https://ocw.mit.edu/courses/7-03-genetics-fall-2004/7.03-fall-2004.zip" \
  "${DEST}/7.03_genetics"

# ─── ENGINEERING ─────────────────────────────────────────────────────────────
# SUBSTITUTION: 2.003J Dynamics & Vibration (target) → 404 on OCW.
# Using 2.003 Modeling, Dynamics & Control I (Spring 2005) — nearest available with zip.
download_zip \
  "https://ocw.mit.edu/courses/2-003-modeling-dynamics-and-control-i-spring-2005/2.003-spring-2005.zip" \
  "${DEST}/2.003_dynamics_control"

# SUBSTITUTION: 2.005 Thermal-Fluids Engineering (target) → 404 on OCW.
# Using 5.60 Thermodynamics & Kinetics (Spring 2008) — covers thermo fundamentals with zip.
download_zip \
  "https://ocw.mit.edu/courses/5-60-thermodynamics-kinetics-spring-2008/5.60-spring-2008.zip" \
  "${DEST}/5.60_thermodynamics_kinetics"

# 16.001 Unified Engineering → no zip available on OCW. Skipped (noted in README).

# ─── ECON / OTHER ────────────────────────────────────────────────────────────
# SUBSTITUTION: 14.01 Microeconomics Fall 2018 → 404. Using 14.01SC (Fall 2011, Scholar edition).
download_zip \
  "https://ocw.mit.edu/courses/14-01sc-principles-of-microeconomics-fall-2011/14.01sc-fall-2011.zip" \
  "${DEST}/14.01sc_microeconomics"

download_zip \
  "https://ocw.mit.edu/courses/14-02-principles-of-macroeconomics-spring-2023/14.02-Spring-2023.zip" \
  "${DEST}/14.02_macroeconomics"

download_zip \
  "https://ocw.mit.edu/courses/9-00sc-introduction-to-psychology-fall-2011/9.00sc-fall-2011.zip" \
  "${DEST}/9.00sc_psychology"

download_zip \
  "https://ocw.mit.edu/courses/18-085-computational-science-and-engineering-i-fall-2008/18.085-fall-2008.zip" \
  "${DEST}/18.085_computational_science"

echo ""
echo "=== OCW download complete $(date) ==="

# Print disk usage summary
du -sh "${DEST}" 2>/dev/null && echo "Done."
