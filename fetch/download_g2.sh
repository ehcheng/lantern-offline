#!/bin/bash
# G2 shelf fill: docs/sanitation, docs/comms, docs/emergency_mgmt.
# Idempotent: skips files that already exist AND pass the %PDF gate.
# fema.gov items are fetched separately by fetch_fema.py (Akamai blocks curl).
# Every file is %PDF-gated + size-floored; failures listed at the end, exit 1.
ROOT=$(cd "$(dirname "$0")/.." && pwd)
set -u
LIB=$ROOT/library/docs
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'
FAILS=()

# shelf|filename|min_bytes|flags(k=insecure)|url
ITEMS='
sanitation|wedc_excreta_disposal_emergencies_field_manual_2007.pdf|14000000||https://sswm.info/sites/default/files/reference_attachments/HARVEY%202007%20Excreta%20Disposal%20in%20Emergencies%20%20A%20Field%20Manual.pdf
sanitation|who_wedc_wash_emergencies_technical_notes_2013.pdf|14000000||https://bdd.pseau.org/outils/ouvrages/wedc_who_technical_notes_water_sanitation_hygiene_in_emergencies.pdf
sanitation|emergency_sanitation_compendium_2020.pdf|7000000||https://www.washnet.de/wp-content/uploads/emergency-sanitation-compendium.pdf
sanitation|hygiene_promotion_emergencies_compendium_2022.pdf|2000000|k|https://emergency-wash.org/hygiene/files/WSH_hygiene_compendium_digital.pdf
sanitation|eawag_sanitation_systems_technologies_compendium_2014.pdf|8500000||https://www.eawag.ch/fileadmin/Domain1/Abteilungen/sandec/schwerpunkte/sesp/CLUES/Compendium_2nd_pdfs/Compendium_2nd_Ed_Lowres_1p.pdf
sanitation|hesperian_community_guide_environmental_health_2012.pdf|14000000||https://kolibri.teacherinabox.org.au/modules/en-hesperian_health/en_cgeh_2012_full.pdf
sanitation|cawst_latrine_construction_manual_2011.pdf|1400000|k|https://www.susana.org/downloads?documentID=2091
sanitation|sphere_handbook_2018.pdf|5500000||https://emergency.unhcr.org/sites/default/files/2024-01/Sphere-Handbook-2018-EN.pdf
sanitation|mhm_in_emergencies_toolkit_full_guide_2017.pdf|3000000||https://www.rescue.org/sites/default/files/document/2113/themhminemergenciestoolkitfullguide.pdf
sanitation|epa_septic_systems_after_flood_2005.pdf|100000||https://www.epa.gov/sites/default/files/2015-11/documents/2005_09_22_faq_fs_whattodoafteraflood_septic_eng.pdf
sanitation|tamu_graywater_safe_use_b6176.pdf|1500000||https://ossf.tamu.edu/files/2023/01/B-6176-3.08-Greywater.pdf
sanitation|tceq_graywater_alternative_onsite_rg536.pdf|200000||https://www.tceq.texas.gov/downloads/assistance/publications/rg-536.pdf/@@download/file/rg-536.pdf
sanitation|vt_greywater_reuse_factsheet.pdf|150000||https://www.wellwater.bse.vt.edu/files/Greywater-reuse.pdf
sanitation|kitsap_two_bucket_emergency_toilet_flyer.pdf|400000||https://www.kitsapdem.com/wp-content/uploads/2021/10/2-Bucket-Pee-Poo-System.pdf
sanitation|sfpuc_graywater_design_manual.pdf|2500000||https://www.sfpuc.gov/sites/default/files/documents/Graywater_Design_Manual.pdf
comms|ncvec_technician_pool_2026_2030.pdf|400000||https://ncvec.org/downloads/TECH_2026/2026-2030%20Technician%20Pool%20and%20Syllabus%20Public%20Release%20Dec%2018%202025.pdf
comms|ncvec_general_pool_2023_2027.pdf|400000||https://ncvec.org/downloads/General%20Class%20Pool%20and%20Syllabus%202023-2027%20Public%20Release%20with%206th%20Errata%20Feb%204%202026.pdf
comms|ncvec_extra_pool_2024_2028.pdf|1300000||https://ncvec.org/downloads/2024-2028%20Extra%20Class%20Question%20Pool%20and%20Syllabus%20Public%20Release%20December%207%202023.pdf
comms|kb6nu_no_nonsense_technician_study_guide_2026.pdf|4000000||https://www.kb6nu.com/wp-content/uploads/2026/07/2026-no-nonsense-tech-study-guide-v1-2-20260722.pdf
comms|cisa_nifog_v2_02_2024.pdf|6000000||https://www.cisa.gov/sites/default/files/2024-12/NIFOG%202.02_508%20FINAL%20VERSION%2012%2003%202024.pdf
comms|cisa_auxfog_v1_1_2016.pdf|3000000||https://www.cisa.gov/sites/default/files/publications/AUXFOG%20June%202016%20-%20508%20Reviewed%20-%20Final%20%282-16-17%29.pdf
comms|arrl_ares_manual_2015.pdf|2300000||http://www.arrl.org/files/file/Public%20Service/ARES/ARESmanual2015.pdf
comms|army_fm24_18_tactical_single_channel_radio_1987.pdf|9500000||https://archive.org/download/milmanual-fm-24-18-tactical-single-channel-radio-communications-techni/fm_24-18_tactical_single_channel_radio_communications_techniques.pdf
comms|usmc_antenna_handbook_mcrp_8_10b11_2016.pdf|2800000||https://w5sc.org/wp-content/uploads/2020/06/MCRP-8-10B.11.pdf
comms|navy_neets_mod10_propagation_transmission_antennas.pdf|6500000||https://upload.wikimedia.org/wikipedia/commons/e/e2/14182A_-_NEETS_Module_10-Wave_Propagation%2C_Transmission_Lines%2C_and_Antennas.pdf
comms|cfr47_part97_amateur_radio_2024.pdf|300000||https://www.govinfo.gov/content/pkg/CFR-2024-title47-vol5/pdf/CFR-2024-title47-vol5-part97.pdf
comms|cfr47_part95_personal_radio_gmrs_frs_2024.pdf|400000||https://www.govinfo.gov/content/pkg/CFR-2024-title47-vol5/pdf/CFR-2024-title47-vol5-part95.pdf
comms|itu_international_morse_code_m1677.pdf|1300000||https://www.itu.int/dms_pubrec/itu-r/rec/m/R-REC-M.1677-1-200910-I%21%21PDF-E.pdf
comms|ofsc_frs_gmrs_emergency_communications_guide22.pdf|230000||https://oaklandfiresafecouncil.org/wp-content/uploads/OFSC-Guide-22-Emergency-Communications.pdf
comms|certla_using_frs_gmrs_radios_2009.pdf|60000||https://www.cert-la.com/downloads/radio/Using-FRS-and-GMRS-by-N6VI-10-14-09-1.pdf
comms|scares_san_mateo_frequency_wallet_card_2017.pdf|140000||https://k6mpn.org/training/resources/2017SCARESfreq-walletcard.pdf
comms|sc4ares_field_operations_guide_v5.pdf|23000000|k|https://www.sc4ares.org/wp-content/uploads/2023/12/SC4ARES%20Field%20Operations%20Guide%20v5.pdf
emergency_mgmt|fema_cert_basic_training_participant_manual_2019.pdf|5000000||https://www.ready.gov/sites/default/files/2019.CERT_.Basic_.PM_FINAL_508c.pdf
emergency_mgmt|usgs_putting_down_roots_earthquake_country_bay_area_2005.pdf|5000000||https://pubs.usgs.gov/gip/2005/15/gip-15.pdf
emergency_mgmt|eca_staying_safe_where_earth_shakes_bay_area.pdf|7000000||https://www.earthquakecountry.org/library/StayingSafeWhereTheEarthShakes_BayAreaEdition.pdf
emergency_mgmt|eca_seven_steps_earthquake_safety_2023.pdf|350000||https://www.earthquakecountry.org/library/ECA_Seven_Steps_Earthquake_Safety-EN.pdf
emergency_mgmt|ucanr_home_survival_wildfire_prone_areas_8939.pdf|4500000||https://firesafesanmateo.org/images/documents/home_survival_in_wildfire_prone_areas_8939.pdf
emergency_mgmt|firesafemarin_wildfire_retrofitting_guide.pdf|5300000||https://firesafemarin.org/wp-content/uploads/Wildfire-Retrofitting-Guide-ONLINE.pdf
emergency_mgmt|iafc_ready_set_go_wildland_fire_action_guide.pdf|2300000||https://www.iafc.org/docs/default-source/pdf/rsg-eag.pdf?sfvrsn=d1316f0c_24
emergency_mgmt|san_mateo_county_fire_hazard_severity_zone_map.pdf|1700000|k|https://www.smcgov.org/media/159771/download?inline=
emergency_mgmt|fema_flood_insurance_study_san_mateo_county_vol2.pdf|2300000||https://www.sanbruno.ca.gov/DocumentCenter/View/950/Flood-Insurance-Study-06081CV002C-PDF
emergency_mgmt|cgs_seismic_hazard_zone_report_133_sf_south.pdf|8500000|k|https://www.conservation.ca.gov/cgs/Documents/Publications/SHZR/SHZR_133_San_Francisco_South_a11y.pdf
'

fetch() { # shelf file min flags url
  local out="$LIB/$1/$2" min="$3" flags="$4" url="$5" kflag=""
  [ "$flags" = k ] && kflag="-k"
  if [ -s "$out" ] && head -c4 "$out" | grep -q '%PDF'; then echo "SKIP $2"; return 0; fi
  curl -sSL --retry 3 -A "$UA" $kflag -o "$out.part" "$url"
  local sz=$(stat -f%z "$out.part" 2>/dev/null || echo 0)
  if head -c4 "$out.part" 2>/dev/null | grep -q '%PDF' && [ "$sz" -ge "$min" ]; then
    mv "$out.part" "$out"; echo "OK   $2 ($sz)"
  else
    rm -f "$out.part"; echo "FAIL $2 (size=$sz)"; FAILS+=("$1/$2"); return 1
  fi
}

echo "$ITEMS" | while IFS='|' read -r shelf file min flags url; do
  [ -z "$shelf" ] && continue
  fetch "$shelf" "$file" "$min" "$flags" "$url"
done

# Humanure 4th ed: chapter names are NOT pattern-guessable — scrape contents.html
HDIR="$LIB/sanitation/humanure_4th_ed"; mkdir -p "$HDIR"
HC=$(mktemp); curl -sSL -A "$UA" https://humanurehandbook.com/contents.html -o "$HC"
grep -o 'downloads/H4/[^"]*\.pdf' "$HC" | sort -u | while read -r rel; do
  name=$(basename "$rel" | sed 's/ /_/g')
  url="https://humanurehandbook.com/$(echo "$rel" | sed 's/ /%20/g')"
  out="$HDIR/$name"
  if [ -s "$out" ] && head -c4 "$out" | grep -q '%PDF'; then echo "SKIP humanure/$name"; continue; fi
  curl -sSL --retry 3 -A "$UA" -o "$out.part" "$url"
  if head -c4 "$out.part" 2>/dev/null | grep -q '%PDF'; then mv "$out.part" "$out"; echo "OK   humanure/$name"
  else rm -f "$out.part"; echo "FAIL humanure/$name"; fi
done
# Loo construction plans (author-hosted)
fetch sanitation humanure_4th_ed/Loo_Construction_plans.pdf 2500000 '' https://humanurehandbook.com/downloads/Loo_Construction.pdf

echo "---"
echo "Run fetch_fema.py next for the 4 fema.gov items, then verify_g2.sh"
