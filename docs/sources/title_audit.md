# PDF Title Audit

Audit date: 2026-09-16. Method: `pdftotext -f 1 -l 3` + `pdfinfo`. Excludes `survivor_library` and `cd3wd` bulk dumps.

Verdicts: **OK** = title matches filename expectation | **WRONG** = content is clearly a different document | **SCAN** = no extractable text (image-only PDF) | **SUSPECT** = content partially matches but has discrepancy worth noting

---

## energy/

| Filename | Detected Title | Pages | Verdict |
|---|---|---|---|
| fema_wood_gas_generator.pdf | Construction of a Simplified Wood Gas Generator for Fueling Internal Combustion Engines in a Petroleum Emergency | 66 | OK |
| neets/neets_module_01.pdf | NEETS Module 1 — Introduction to Matter, Energy, and Direct Current (NAVEDTRA 14173) | 283 | OK |
| neets/neets_module_02.pdf | NEETS Module 2 — Introduction to Alternating Current and Transformers (NAVEDTRA 14174) | 250 | OK |
| neets/neets_module_03.pdf | NEETS Module 3 — Introduction to Circuit Protection, Control, and Measurement (NAVEDTRA 14175) | 214 | OK |
| neets/neets_module_04.pdf | NEETS Module 4 — Introduction to Electrical Conductors, Wiring Techniques, and Schematic Reading (NAVEDTRA 14176) | 152 | OK |
| neets/neets_module_05.pdf | NEETS Module 5 — Introduction to Generators and Motors (NAVEDTRA 14177) | 120 | OK |
| neets/neets_module_06.pdf | NEETS Module 6 — Introduction to Electronic Emission, Tubes, and Power Supplies (NAVEDTRA 14178) | 204 | OK |
| neets/neets_module_07.pdf | NEETS Module 7 — Introduction to Solid-State Devices and Power Supplies (NAVEDTRA 14179) | 287 | OK |
| neets/neets_module_08.pdf | NEETS Module 8 — Introduction to Amplifiers (NAVEDTRA 14180) | 186 | OK |
| neets/neets_module_09.pdf | NEETS Module 9 — Introduction to Wave-Generation and Wave-Shaping (NAVEDTRA 14181) | 275 | OK |
| neets/neets_module_10.pdf | NEETS Module 10 — Introduction to Wave Propagation, Transmission Lines, and Antennas (NAVEDTRA 14182) | 276 | OK |
| neets/neets_module_11.pdf | NEETS Module 11 — Microwave Principles (NAVEDTRA 14183) | 192 | OK |
| neets/neets_module_12.pdf | NEETS Module 12 — Modulation (NAVEDTRA 14184) | 230 | OK |
| neets/neets_module_13.pdf | NEETS Module 13 — Introduction to Number Systems and Logic (NAVEDTRA 14185) | 218 | OK |
| neets/neets_module_14.pdf | NEETS Module 14 — Introduction to Microelectronics (NAVEDTRA 14186) | 175 | OK |
| neets/neets_module_15.pdf | NEETS Module 15 — Principles of Synchros, Servos, and Gyros (NAVEDTRA 14187) | 196 | OK |
| neets/neets_module_16.pdf | NEETS Module 16 — Introduction to Test Equipment (NAVEDTRA 14188) | 272 | OK |
| neets/neets_module_17.pdf | NEETS Module 17 — Radio-Frequency Communications Principles (NAVEDTRA 14189) | 201 | OK |
| neets/neets_module_18.pdf | NEETS Module 18 — Radar Principles (NAVEDTRA 14190) | 204 | OK |
| neets/neets_module_19.pdf | NEETS Module 19 — The Technician's Handbook (NAVEDTRA 14191) | 156 | OK |
| neets/neets_module_20.pdf | NEETS Module 20 — Master Glossary (NAVEDTRA 14192) | 95 | OK |
| neets/neets_module_21.pdf | NEETS Module 21 — Test Methods and Practices (NAVEDTRA 14193) | 216 | OK |
| neets/neets_module_22.pdf | NEETS Module 22 — Introduction to Digital Computers (NAVEDTRA 14194) | 172 | OK |
| neets/neets_module_23.pdf | NEETS Module 23 — Magnetic Recording (NAVEDTRA 14195) | 164 | OK |
| neets/neets_module_24.pdf | NEETS Module 24 — Introduction to Fiber Optics (NAVEDTRA 14196) | 238 | OK |

---

## fire_safety/

| Filename | Detected Title | Pages | Verdict |
|---|---|---|---|
| nfpa_firewise_noncombustible_zone.pdf | Wildfire Research Fact Sheet: Immediate (Noncombustible) Zone | 1 | OK |
| nfpa_wildfire_hiz_checklist.pdf | Reducing Wildfire Risks in the Home Ignition Zone | 7 | OK |
| usfs_home_ignition_guide.pdf | (Cephalosporium Wilt of Elm — 1968 plant disease article) | 2 | **WRONG** — content is a 1968 botany/plant disease paper, not a home ignition guide |

---

## food_preservation/

| Filename | Detected Title | Pages | Verdict |
|---|---|---|---|
| usda_canning_guide_01.pdf | Complete Guide to Home Canning, Guide 1: Principles of Home Canning | 40 | OK |
| usda_complete_guide_home_canning_2015.pdf | Complete Guide to Home Canning, Revised 2015 (Agriculture Information Bulletin No. 539) | 193 | OK |

---

## HISTORICAL/

| Filename | Detected Title | Pages | Verdict |
|---|---|---|---|
| sof_medical_handbook.pdf | Special Operations Forces Medical Handbook | 723 | OK |
| st_31-91b_special_forces_medical_1982.pdf | (no extractable text) | 210 | **SCAN** — image-only; 1982 era scan, acceptable |

---

## medical/ (main)

| Filename | Detected Title | Pages | Verdict |
|---|---|---|---|
| army_combat_medic_handbook.pdf | First Aid in Armed Conflicts and Other Situations of Violence (ICRC) | 286 | **WRONG** — is an ICRC publication, not a US Army combat medic handbook |
| emergency_war_surgery.pdf | Emergency War Surgery — Third United States Revision, 2004 | 489 | OK |
| fm_4-25.11_first_aid.pdf | First Aid (FM 4-25.11 / NTRP 4-02.1.1 / AFMAN 44-163(I) / MCRP 3-02G) | 227 | OK |
| hesperian_where_there_is_no_dentist.pdf | Where There Is No Dentist | 240 | OK |
| ranger_medic_handbook_2007.pdf | Ranger Medic Handbook 2007 | 154 | OK |
| tc_4-02.1_medical_evacuation.pdf | Theater Hospitalization (ATP 4-02.10) | 166 | **WRONG** — filename implies TC 4-02.1 Medical Evacuation; content is ATP 4-02.10 Theater Hospitalization |
| who_drinking_water_quality_4th_ed.pdf | Guidelines for Drinking-water Quality, Fourth Edition (WHO, 2011) | 564 | OK |
| who_family_planning_global_handbook.pdf | Family Planning: A Global Handbook for Providers, 2018 Edition | 460 | OK |
| who_imci_chart_booklet.pdf | IMCI Distance Learning Course — Introduction Module | 42 | SUSPECT — text layer identifies this as the introductory module, not the chart booklet; charts may be image-embedded |
| who_mhgap_intervention_guide_v2.pdf | mhGAP Intervention Guide Version 2.0 (WHO, 2016) | 174 | OK |
| who_pocket_book_hospital_care_children.pdf | Pocket Book of Hospital Care for Children (WHO) | 438 | OK |
| who_psychological_first_aid.pdf | Psychological First Aid: Guide for Field Workers (WHO, 2011) | 64 | OK |
| who_surgical_care_district_hospital.pdf | Surgical Care at the District Hospital (WHO, 2003) | 514 | OK |

---

## medical/hesperian_where_there_is_no_doctor/

| Filename | Detected Title | Pages | Verdict |
|---|---|---|---|
| Child_growth_chart_nwtnd.pdf | WHO Child Growth Standards 2006 (Growth Curve) | 2 | OK |
| en_cgeh_2012_15.pdf | Sustainable Farming (Ch. 15, Community Guide to Environmental Health) | 40 | **WRONG** — is from Hesperian's CGEH book, not NWTND; different Hesperian title misfiled here |
| en_dvc_2018_32.pdf | Mental Slowness — Down Syndrome, Hypothyroidism (Ch. 32, Disabled Village Children) | 6 | **WRONG** — is from Hesperian's DVC book, not NWTND; different Hesperian title misfiled here |
| en_nwtnd_2011_27d.pdf | Newborn Babies and Breastfeeding | 29 | OK |
| en_nwtnd_2011_28d.pdf | Caring for Children | 63 | OK |
| en_nwtnd_2011_31e.pdf | Good Food Makes Good Health | 42 | OK |
| en_nwtnd_2014_03g.pdf | First Aid | 89 | OK |
| en_nwtnd_2014_24b.pdf | Women's Menstrual Cycles | 8 | OK |
| en_nwtnd_2014_26d.pdf | Pregnancy and Birth | 39 | OK |
| en_nwtnd_2015_25b.pdf | Family Planning | 24 | OK |
| en_nwtnd_2016_20a.pdf | Cancer | 25 | OK |
| en_nwtnd_2016_21a.pdf | Diabetes | 40 | OK |
| en_nwtnd_2017_9_eyechart_landscape.pdf | (Visual eye chart — "Distance") | 1 | OK — single-page visual chart, minimal text expected |
| en_nwtnd_2017_9.pdf | Problems with the Eyes and Seeing | 36 | OK |
| en_nwtnd_2018_14.pdf | Heart Disease and High Blood Pressure | 35 | OK |
| en_nwtnd_2019_16b.pdf | Sexually Transmitted Infections | 43 | OK |
| en_nwtnd_2019_22a.pdf | Malaria, Dengue, and Other Illnesses from Mosquitoes | 44 | OK |
| en_nwtnd_2019_30a.pdf | Vaccines Prevent Illness | 17 | OK |
| NWTND_Development_Charts.pdf | Child Development Charts (Appendix A from Ch. 28) | 8 | OK |

---

## medical/msf/

| Filename | Detected Title | Pages | Verdict |
|---|---|---|---|
| msf_clinical_guidelines.pdf | Clinical Guidelines — Diagnosis and Treatment Manual (MSF, Dec 2024 ed.) | 409 | OK |
| msf_essential_drugs.pdf | Essential Drugs — Practical Guide (MSF, Jan 2026 ed.) | 663 | OK |
| msf_obstetrics_newborn.pdf | Essential Obstetric and Newborn Care (MSF, 2019 ed.) | 279 | OK |

---

## medical/tccc/

| Filename | Detected Title | Pages | Verdict |
|---|---|---|---|
| Airway_Management_in_Trauma.pdf | Airway Management in Trauma (JTS CPG) | 32 | OK |
| Burn_Care.pdf | Burn Care (JTS CPG) | 47 | OK |
| CPG_Index.pdf | JTS Clinical Practice Guidelines Index | 4 | OK |
| Damage_Control_Resuscitation.pdf | Damage Control Resuscitation (JTS CPG) | 24 | OK |
| DD_Form_1380_TCCC_Card_Instructions.pdf | Instructions: DD Form 1380, TCCC Card | 3 | OK |
| DD_Form_1380_TCCC_Card.pdf | Tactical Combat Casualty Care (TCCC) Card — DD Form 1380 | 2 | OK |
| Documentation_Requirements_Combat_Casualty_Care.pdf | Documentation Requirements for Combat Casualty Care (CPG ID: 11) | 8 | OK |
| En_Route_Care_Patient_Packaging.pdf | En Route Care (ERC) Patient Packaging (JTS CPG) | 16 | OK |
| Extremity_Compartment_Syndrome_Fasciotomy.pdf | Acute Extremity Compartment Syndrome and the Role of Fasciotomy | 22 | OK |
| High_Bilateral_Amputations_Blast_Injury.pdf | High Bilateral Amputations and Dismounted Complex Blast Injury (JTS CPG) | 20 | OK |
| Hypothermia_Prevention_Treatment.pdf | Hypothermia: Prevention and Treatment (JTS CPG) | 20 | OK |
| Prehospital_Blood_Transfusion.pdf | Prehospital Blood Transfusion (JTS CPG) | 24 | OK |
| Prolonged_Casualty_Care_Guidelines.pdf | Prolonged Casualty Care Guidelines (CPG ID: 91) | 75 | OK |
| TBI_Traumatic_Brain_Injury_PFC.pdf | Traumatic Brain Injury Management in Prolonged Field Care (JTS CPG) | 23 | OK |
| TCCC_Guidelines_2024-01-25.pdf | Tactical Combat Casualty Care (TCCC) Guidelines — 25 January 2024 | 17 | OK |
| Vascular_Injury.pdf | Vascular Injury (JTS CPG) | 41 | OK |
| War_Wounds_Debridement_and_Irrigation.pdf | War Wounds: Debridement and Irrigation (CPG ID: 31) | 14 | OK |
| Wartime_Thoracic_Injury.pdf | Wartime Thoracic Injury (CPG ID: 74) | 31 | OK |
| Wound_Management_PFC.pdf | Acute Traumatic Wound Management in Prolonged Field Care (CPG ID: 62) | 25 | OK |

---

## military_manuals/

| Filename | Detected Title | Pages | Verdict |
|---|---|---|---|
| fm_21-76_survival.pdf | US Army Survival Manual (FM 21-76) | 277 | OK |
| fm_5-103_survivability.pdf | Survivability (FM 5-103) | 257 | OK — image cover, title confirmed from preface text |
| tc_3-21.76_ranger_handbook.pdf | Ranger Handbook (TC 3-21.76) | 370 | OK |
| tc_9-237_welding.pdf | Welding Theory and Application (TM 9-237) | 299 | SUSPECT — filename prefix "tc_" but document is TM (Technical Manual); content correct |
| tm_9-8000_automotive_vehicles.pdf | Principles of Automotive Vehicles (TM 9-8000) | 780 | OK |

---

## navigation/

| Filename | Detected Title | Pages | Verdict |
|---|---|---|---|
| tc_3-25.26_map_reading_land_nav.pdf | Map Reading and Land Navigation (TC 3-25.26) | 126 | OK |

---

## nuclear/

| Filename | Detected Title | Pages | Verdict |
|---|---|---|---|
| nuclear_war_survival_skills_kearny.pdf | Nuclear War Survival Skills — Cresson H. Kearny | 317 | OK — no text-layer title page; title confirmed from body |

---

## shelter/

| Filename | Detected Title | Pages | Verdict |
|---|---|---|---|
| fm_3-34.471_plumbing.pdf | Plumbing, Pipe Fitting, and Sewerage (FM 3-34.471) | 276 | OK |
| fm_5-34_engineer_field_data.pdf | Engineer Field Data (FM 5-34) | 577 | SUSPECT — Google Books scan; OCR text fragmented/reversed throughout; readable but degraded |
| fm_5-426_carpentry.pdf | Carpentry (FM 5-426) | 223 | OK — moderate OCR artifacts but readable |
| fm_5-428_concrete_masonry.pdf | Concrete and Masonry (FM 5-428) | 323 | OK |
| usda_wood_handbook.pdf | Wood Handbook — Wood as an Engineering Material (USDA FPL-GTR-190, Centennial Ed. 2010) | 509 | OK |

---

## water/

| Filename | Detected Title | Pages | Verdict |
|---|---|---|---|
| cawst_biosand_filter_manual.pdf | Biosand Filter Construction Manual (CAWST, Aug 2012) | 190 | OK |
| fm_10-52_water_supply.pdf | Water Supply in the Field (FM 10-52) | 90 | OK — no title on first pages, inferred from FM number and content |
| sodis_manual.pdf | Solar Water Disinfection — A Guide for the Application of SODIS (SANDEC/EAWAG, 2002) | 88 | OK |
| texas_rainwater_harvesting_manual.pdf | The Texas Manual on Rainwater Harvesting (Texas Water Development Board, 3rd Ed.) | 88 | OK |

---

## Summary

- **Total audited:** 109
- **OK:** 96
- **WRONG (content mismatch):** 6
  - `fire_safety/usfs_home_ignition_guide.pdf` — Cephalosporium Wilt of Elm botany paper
  - `medical/army_combat_medic_handbook.pdf` — ICRC "First Aid in Armed Conflicts", not US Army handbook
  - `medical/tc_4-02.1_medical_evacuation.pdf` — ATP 4-02.10 Theater Hospitalization, not TC 4-02.1 Medical Evacuation
  - `medical/hesperian_where_there_is_no_doctor/en_cgeh_2012_15.pdf` — Hesperian CGEH "Sustainable Farming", misfiled in NWTND folder
  - `medical/hesperian_where_there_is_no_doctor/en_dvc_2018_32.pdf` — Hesperian DVC "Mental Slowness/Down Syndrome", misfiled in NWTND folder
- **SCAN (no extractable text):** 1
  - `HISTORICAL/st_31-91b_special_forces_medical_1982.pdf` — 1982 scan, acceptable
- **SUSPECT (minor discrepancy, review recommended):** 3
  - `medical/who_imci_chart_booklet.pdf` — text layer is introductory module, not chart booklet proper
  - `military_manuals/tc_9-237_welding.pdf` — filename prefix "tc_" but document designation is TM
  - `shelter/fm_5-34_engineer_field_data.pdf` — Google Books scan with fragmented/reversed OCR text
