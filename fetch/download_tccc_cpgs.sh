#!/bin/bash
ROOT=$(cd "$(dirname "$0")/.." && pwd)
set -e

DEST="$ROOT/library/docs/medical/tccc"
BASE="https://jts.health.mil"
LOG="$ROOT/logs/tccc.log"

echo "" >> "$LOG"
echo "=== CPG Downloads $(date) ===" >> "$LOG"

download_verify() {
  local fname="$1"
  local path="$2"
  local url="${BASE}${path}"
  local outfile="${DEST}/${fname}"

  /usr/bin/curl -sk --max-time 60 "$url" -o "$outfile"
  local size
  size=$(wc -c < "$outfile" 2>/dev/null || echo 0)
  local header
  header=$(head -c 4 "$outfile" | tr -d '\n')

  if [ "$header" = "%PDF" ] && [ "$size" -gt 10000 ]; then
    echo "DONE ${fname} size=${size}"
    echo "DONE ${fname} size=${size}" >> "$LOG"
  else
    echo "FAIL ${fname} size=${size} header=${header}"
    echo "FAIL ${fname} size=${size}" >> "$LOG"
    rm -f "$outfile"
  fi
}

download_verify "CPG_Index.pdf" "/assets/docs/cpgs/CPG_Index.pdf"
download_verify "Prolonged_Casualty_Care_Guidelines.pdf" "/assets/docs/cpgs/Prolonged_Casualty_Care_Guidelines_21_Dec_2021_ID91.pdf"
download_verify "Prehospital_Blood_Transfusion.pdf" "/assets/docs/cpgs/Prehospital_Blood_Transfusion_30_Oct_2020_ID82.pdf"
download_verify "Airway_Management_in_Trauma.pdf" "/assets/docs/cpgs/Airway_Management_in_Trauma_28_Jan_2026_ID39.pdf"
download_verify "Hypothermia_Prevention_Treatment.pdf" "/assets/docs/cpgs/Hypothermia_Prevention_Treatment_07_Jun_2023_ID23.pdf"
download_verify "Damage_Control_Resuscitation.pdf" "/assets/docs/cpgs/Damage_Control_Resuscitation_12_Jul_2019_ID18.pdf"
download_verify "Wartime_Thoracic_Injury.pdf" "/assets/docs/cpgs/Wartime_Thoracic_Injury_26_Dec_2018_ID74.pdf"
download_verify "War_Wounds_Debridement_and_Irrigation.pdf" "/assets/docs/cpgs/War_Wounds_Debridement_and_Irrigation_27_Sep_2021_ID31.pdf"
download_verify "Burn_Care.pdf" "/assets/docs/cpgs/Burn_Care_CPG_10_June_2025_ID12_v1.3.pdf"
download_verify "Vascular_Injury.pdf" "/assets/docs/cpgs/Vascular_Injury_09_Apr_2025_ID46_v1.2.pdf"
download_verify "En_Route_Care_Patient_Packaging.pdf" "/assets/docs/cpgs/En_Route_Care_Patient_Packaging_21_Aug_2024_ID97_v1.2.pdf"
download_verify "Extremity_Compartment_Syndrome_Fasciotomy.pdf" "/assets/docs/cpgs/Extremity_Compartment_Syndrome_and_Fasciotomy_ID17_21_May_2026.pdf"
download_verify "TBI_Traumatic_Brain_Injury_PFC.pdf" "/assets/docs/cpgs/Traumatic_Brain_Injury_PFC_06_Dec_2017_ID63.pdf"
download_verify "High_Bilateral_Amputations_Blast_Injury.pdf" "/assets/docs/cpgs/High_Bilateral_Amputations_Dismounted_Complex_Blast_Injury_05_Aug_2024_ID22_v1.2.pdf"
download_verify "Wound_Management_PFC.pdf" "/assets/docs/cpgs/Wound_Management_PFC_24_Jul_2017_ID62.pdf"

echo "Done."
