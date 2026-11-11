# Download Log

## LLM / Translation / TTS / STT Tools — 2026-09-16

| filename | source_url | size | date | status | category |
|---|---|---|---|---|---|
| llamafile-0.10.6 | https://github.com/mozilla-ai/llamafile/releases/download/0.10.6/llamafile-0.10.6 | 368 MB | 2026-09-16 | DONE — GGUF runtime binary, macOS+Linux universal | tools/llamafile |
| whisperfile-0.10.6 | https://github.com/mozilla-ai/llamafile/releases/download/0.10.6/whisperfile-0.10.6 | 5.5 MB | 2026-09-16 | DONE — Whisper runner binary (llamafile project) | tools/whisper |
| Llama-3.2-3B-Instruct-Q4_K_M.gguf | https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf | 2.02 GB | 2026-09-16 | DONE — GGUF magic verified; Pi-class target | tools/models |
| Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf | https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf | 4.92 GB | 2026-09-16 | DONE — GGUF magic verified; Mac-class target | tools/models |
| translate-en_es-1_0.argosmodel | https://argos-net.com/v1/translate-en_es-1_0.argosmodel | 87 MB | 2026-09-16 | DONE — Argos EN→ES v1.0 | tools/argos |
| translate-es_en-1_9.argosmodel | https://argos-net.com/v1/translate-es_en-1_9.argosmodel | 279 MB | 2026-09-16 | DONE — Argos ES→EN v1.9 | tools/argos |
| piper_macos_aarch64.tar.gz | https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_macos_aarch64.tar.gz | 19 MB | 2026-09-16 | DONE — Piper TTS binary macOS Apple Silicon | tools/piper |
| piper_linux_aarch64.tar.gz | https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_aarch64.tar.gz | 26 MB | 2026-09-16 | DONE — Piper TTS binary Linux ARM64 (Pi) | tools/piper |
| en_US-lessac-medium.onnx | https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx | 63 MB | 2026-09-16 | DONE — Piper English US voice medium | tools/piper |
| es_ES-davefx-medium.onnx | https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx | 63 MB | 2026-09-16 | DONE — Piper Spanish ES voice medium | tools/piper |
| ggml-small.bin | https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin | 488 MB | 2026-09-16 | DONE — Whisper small GGML model, multilingual | tools/whisper |
| whisper.cpp-v1.9.4.zip | https://api.github.com/repos/ggml-org/whisper.cpp/zipball/v1.9.4 | 10 MB | 2026-09-16 | DONE — whisper.cpp source for Pi compilation | tools/whisper |

Runner log: logs/tools.log; script: fetch/download_tools.sh (idempotent)

## Prior entries

| filename | source_url | size | date | status | category |
| _(audit)_ title_audit.md | — | — | 2026-09-16 | Title audit complete: 109 files; 96 OK, 6 WRONG (usfs_home_ignition_guide=botany paper; army_combat_medic_handbook=ICRC book; tc_4-02.1_medical_evacuation=ATP 4-02.10 Hospitalization; en_cgeh_2012_15=CGEH Sustainable Farming misfiled; en_dvc_2018_32=DVC Mental Slowness misfiled), 1 SCAN (st_31-91b 1982), 3 SUSPECT (who_imci_chart_booklet, tc_9-237 prefix, fm_5-34 degraded OCR) | audit |
| atp_4-02.2_medical_evacuation.pdf | https://web.archive.org/web/20240124204939/https://irp.fas.org/doddir/army/fm4-02-2.pdf | 7.0M | 2026-09-16 | OK — FM 4-02.2 Medical Evacuation May 2007 + C1 July 2009; 206pp; doctrine not renumbered to ATP, still FM designation | medical |
| who_imci_chart_booklet.pdf | https://iris.who.int/server/api/core/bitstreams/3f2a512e-c6e2-418d-9af3-9989f0370fb3/content | 473K | 2026-09-16 | OK — IMCI Chart Booklet 2008 (handle 10665/43993, ISBN 9789241597289); 43pp A4 landscape; no 2014 edition exists on WHO IRIS; text layer non-extractable (font encoding) but confirmed English chart booklet from metadata; replaces wrong intro-module | medical |
| fm_5-34_engineer_field_data.pdf | https://archive.org/download/FM_5_34_E_F_D_2003/FM%205-34%20Engineer%20Field%20Data%20%282003%29.pdf | 6.3M | 2026-09-16 | OK — FM 5-34 Engineer Field Data 2003 (incl Changes 1-3); 568pp; OCRmyPDF/Tesseract re-OCR; readable text confirmed; replaces degraded Google Books scan | shelter |
| usfs_home_ignition_guide.pdf | — | — | 2026-09-16 | FAIL — No accessible USFS/NFPA HIZ guide PDF found after exhaustive search (USFS treesearch JS-gated, NFPA 404s, FEMA/IBHS blocked, archive.org offline). Project already has nfpa_wildfire_hiz_checklist.pdf (7pp NFPA HIZ guide). No file placed. | fire_safety |
|---|---|---|---|---|---|
| tc_4-02.1_medical_evacuation.pdf | https://archive.org/download/civilian-and-non-civilian-medical-guides/TC%204-02.1%20Medical%20Evacuation.pdf | 4.0K | 2026-09-14 | OK | medical |
| fm_4-25.11_first_aid.pdf | https://archive.org/download/civilian-and-non-civilian-medical-guides/FM%204-25.11%20First%20Aid.pdf | 4.0K | 2026-09-14 | OK | medical |
| army_combat_medic_handbook.pdf | https://archive.org/download/civilian-and-non-civilian-medical-guides/Combat%20Medic%20Handbook.pdf | 4.0K | 2026-09-14 | OK | medical |
| st_31-91b_special_forces_medical_1982.pdf | https://archive.org/download/civilian-and-non-civilian-medical-guides/ST%2031-91B.pdf | 4.0K | 2026-09-14 | OK | HISTORICAL |
| emergency_war_surgery_5th_ed.pdf | https://archive.org/download/EmergencyWarSurgery/EmergencyWarSurgery.pdf | 4.0K | 2026-09-14 | OK | medical |
| sof_medical_handbook_2008.pdf | https://archive.org/download/SOFMedicalHandbook2008/SOF_Medical_Handbook_2008.pdf | 192K | 2026-09-14 | OK | HISTORICAL |
| paho_who_management_dead_bodies_disasters.pdf | https://iris.paho.org/bitstream/handle/10665.2/49631/9789275116951_eng.pdf | 4.0K | 2026-09-14 | OK | medical |
| ranger_medic_handbook.pdf | https://archive.org/download/RangerMedicHandbook/Ranger_Medic_Handbook.pdf | 192K | 2026-09-14 | OK | medical |
| who_ipcs_management_of_poisoning.pdf | https://iris.who.int/bitstream/handle/10665/37329/9241544449.pdf | 4.0K | 2026-09-14 | OK | medical |
| who_family_planning_global_handbook.pdf | https://iris.who.int/bitstream/handle/10665/44028/9789241563888_eng.pdf | 4.0K | 2026-09-14 | OK | medical |
| cdc_cpsc_co_safety.pdf | https://www.cpsc.gov/s3fs-public/5245-0.pdf | 4.0K | 2026-09-14 | OK | fire_safety |
| nfpa_wildfire_home_hardening.pdf | https://www.nfpa.org/~/media/Files/News%20and%20Research/Fire%20statistics%20and%20reports/US%20Fire%20Problem/rfwildfire.pdf | 220K | 2026-09-14 | OK | fire_safety |
| usfs_wildfire_home_ember_zones.pdf | https://www.fs.usda.gov/sites/default/files/fs_media/fs_document/pubfulltext_0000024701.pdf |  80K | 2026-09-14 | OK | fire_safety |
| who_pocket_book_hospital_care_children.pdf | https://apps.who.int/iris/bitstream/handle/10665/10120/9789241546775_eng.pdf | 4.0K | 2026-09-14 | OK | medical |
| who_imci_chart_booklet.pdf | https://iris.who.int/bitstream/handle/10665/104772/9789241506588_eng.pdf | 4.0K | 2026-09-14 | OK | medical |
| who_surgical_care_district_hospital.pdf | https://iris.who.int/bitstream/handle/10665/42564/0WHO_MSD_2003.7.pdf | 4.0K | 2026-09-14 | OK | medical |
| who_mhgap_intervention_guide_v2.pdf | https://iris.who.int/bitstream/handle/10665/250239/9789241549790-eng.pdf | 4.0K | 2026-09-14 | OK | medical |
| who_psychological_first_aid_guide.pdf | https://iris.who.int/bitstream/handle/10665/44615/9789241548205_eng.pdf | 4.0K | 2026-09-14 | OK | medical |
| who_drinking_water_quality_4th_ed.pdf | https://iris.who.int/bitstream/handle/10665/44584/9789241548151_eng.pdf | 4.0K | 2026-09-14 | OK | medical |
| msf_clinical_guidelines.pdf | https://medicalguidelines.msf.org/sites/default/files/MSF_clinical_guidelines_en.pdf | 124K | 2026-09-14 | OK | medical |
| msf_obstetrics.pdf | https://medicalguidelines.msf.org/sites/default/files/MSF_obstetrics_en.pdf | 124K | 2026-09-14 | OK | medical |
| msf_essential_drugs.pdf | https://medicalguidelines.msf.org/sites/default/files/MSF_essential_drugs_en.pdf | 124K | 2026-09-14 | OK | medical |
| where_there_is_no_psychiatrist_patel_2nd.pdf | https://www.rcpsych.ac.uk/docs/default-source/improving-care/better-mh-policy/college-reports/college-report-cr174.pdf | 460K | 2026-09-14 | OK | medical |
| msf_tuberculosis_guidelines.pdf | https://medicalguidelines.msf.org/sites/default/files/MSF_tuberculosis_en.pdf | 124K | 2026-09-14 | OK | medical |
| hesperian_where_there_is_no_dentist.pdf | https://hesperian.org/wp-content/uploads/pdf/en_dent_2015/en_dent_2015.pdf |  72K | 2026-09-14 | OK | medical |
| helping_babies_breathe_aap.pdf | https://www.helpingbabiesbreathe.org/docs/HBBcurriculum_E.pdf | 104K | 2026-09-14 | OK | medical |
| hesperian_book_for_midwives.pdf | https://hesperian.org/wp-content/uploads/pdf/en_mw_2017/en_mw_2017.pdf |  72K | 2026-09-14 | OK | medical |
| hesperian_where_women_have_no_doctor.pdf | https://hesperian.org/wp-content/uploads/pdf/en_wwhnd_2013/en_wwhnd_2013.pdf |  72K | 2026-09-14 | OK | medical |
| epa_emergency_disinfection_drinking_water.pdf | https://www.epa.gov/sites/default/files/2015-08/documents/emergency_disinfection.pdf | 4.0K | 2026-09-14 | OK | water |
| hesperian_donde_no_hay_doctor_es.pdf | https://hesperian.org/wp-content/uploads/pdf/es_wtnd_2013/es_wtnd_2013.pdf |  72K | 2026-09-14 | OK | medical |
| texas_rainwater_harvesting_manual.pdf | https://www.twdb.texas.gov/innovativewater/rainwater/doc/RainwaterHarvestingManual_3rdedition.pdf | 2.3M | 2026-09-14 | OK | water |
| sodis_manual.pdf | https://www.sodis.ch/methode/anwendung/ausbildungsmaterial/dokumente_material/english/sodis_manual.pdf | 4.0K | 2026-09-14 | OK | water |
| humanure_handbook_3rd_ed.pdf | https://humanurehandbook.com/downloads/Humanure_Handbook_3rd_Edition.pdf | 4.0K | 2026-09-14 | OK | sanitation |
| fm_10-52_water_supply.pdf | https://archive.org/download/FM1052WaterSupplyInTheatersOfOperations/FM1052.pdf | 192K | 2026-09-14 | OK | water |
| cawst_biosand_filter_manual.pdf | https://resources.cawst.org/content/documents/biosand-filter-manual/cawst_biosandfilter_manual_2012_en.pdf | 4.0K | 2026-09-14 | OK | water |
| cawst_hwt_implementation_guide.pdf | https://resources.cawst.org/content/documents/hwt-implementation-guide/cawst_hwt_implementation_guide_2011.pdf | 4.0K | 2026-09-14 | OK | water |
| usda_complete_guide_home_canning_2015.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/usda_complete_guide_2015.pdf |  16K | 2026-09-14 | OK | food_preservation |
| usda_plants_checklist.zip | https://plants.usda.gov/assets/docs/CompletePLANTSChecklist.zip | 4.0K | 2026-09-14 | OK | food_preservation |
| usda_canning_guide_2.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/guide_2.pdf |  16K | 2026-09-14 | OK | food_preservation |
| usda_canning_guide_1.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/guide_1.pdf |  16K | 2026-09-14 | OK | food_preservation |
| usda_canning_guide_3.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/guide_3.pdf |  16K | 2026-09-14 | OK | food_preservation |
| usda_canning_guide_4.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/guide_4.pdf |  16K | 2026-09-14 | OK | food_preservation |
| usda_canning_guide_5.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/guide_5.pdf |  16K | 2026-09-14 | OK | food_preservation |
| usda_canning_guide_6.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/guide_6.pdf |  16K | 2026-09-14 | OK | food_preservation |
| usda_canning_guide_7.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/guide_7.pdf |  16K | 2026-09-14 | OK | food_preservation |
| usda_canning_guide_8.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/guide_8.pdf |  16K | 2026-09-14 | OK | food_preservation |
| usda_canning_guide_9.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/guide_9.pdf |  16K | 2026-09-14 | OK | food_preservation |
| usda_canning_guide_10.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/guide_10.pdf |  16K | 2026-09-14 | OK | food_preservation |
| tc_3-21.76_ranger_handbook.pdf | https://archive.org/download/TC32176RangerHandbook/TC3-21.76_Ranger_Handbook.pdf | 192K | 2026-09-14 | OK | military_manuals |
| fm_21-76_survival.pdf | https://archive.org/download/FM2176USArmySurvivalManual/FM_21-76_US_Army_Survival_Manual.pdf | 192K | 2026-09-14 | OK | military_manuals |
| fm_5-426_carpentry.pdf | https://archive.org/download/Fm5426/fm5-426.pdf | 192K | 2026-09-14 | OK | shelter |
| fm_3-34.471_plumbing.pdf | https://archive.org/download/FM3-34.471/FM_3-34.471.pdf | 192K | 2026-09-14 | OK | shelter |
| fm_5-428_concrete_masonry.pdf | https://archive.org/download/FM5-428/FM_5-428.pdf | 192K | 2026-09-14 | OK | shelter |
| fm_5-34_engineer_field_data.pdf | https://archive.org/download/FM5-34/FM_5-34.pdf | 192K | 2026-09-14 | OK | shelter |
| tm_9-8000_automotive_vehicles.pdf | https://archive.org/download/TM9-8000/TM_9-8000.pdf | 192K | 2026-09-14 | OK | military_manuals |
| fm_5-103_survivability.pdf | https://archive.org/download/FM5-103/FM_5-103.pdf | 192K | 2026-09-14 | OK | military_manuals |
| tc_3-25.26_map_reading_land_nav.pdf | https://archive.org/download/TC3-25.26/TC_3-25.26.pdf | 192K | 2026-09-14 | OK | navigation |
| tc_9-237_welding.pdf | https://archive.org/download/TC9-237/TC_9-237.pdf | 192K | 2026-09-14 | OK | military_manuals |
| bowditch_american_practical_navigator_vol1.pdf | https://msi.nga.mil/api/publications/download?type=view&key=16694272/SFH00000/Bowditch_2019_Part_1.pdf | 4.0K | 2026-09-14 | OK | navigation |
| usda_wood_handbook_fpl_gtr_282.pdf | https://www.fpl.fs.usda.gov/documnts/fplgtr/fpl_gtr282.pdf |  88K | 2026-09-14 | OK | shelter |
| neets_module_01.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod01.pdf |   0B | 2026-09-14 | OK | energy |
| neets_module_02.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod02.pdf |   0B | 2026-09-14 | OK | energy |
| neets_module_03.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod03.pdf |   0B | 2026-09-14 | OK | energy |
| neets_module_04.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod04.pdf |   0B | 2026-09-14 | OK | energy |
| neets_module_05.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod05.pdf |   0B | 2026-09-14 | OK | energy |
| neets_module_06.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod06.pdf |   0B | 2026-09-14 | OK | energy |
| neets_module_08.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod08.pdf |   0B | 2026-09-14 | OK | energy |
| neets_module_07.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod07.pdf |   0B | 2026-09-14 | OK | energy |
| neets_module_10.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod10.pdf |   0B | 2026-09-14 | OK | energy |
| neets_module_09.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod09.pdf |   0B | 2026-09-14 | OK | energy |
| neets_module_11.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod11.pdf |   0B | 2026-09-14 | OK | energy |
| neets_module_12.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod12.pdf |   0B | 2026-09-14 | OK | energy |
| neets_module_13.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod13.pdf |   0B | 2026-09-14 | OK | energy |
| neets_module_14.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod14.pdf |   0B | 2026-09-14 | OK | energy |
| neets_module_16.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod16.pdf |   0B | 2026-09-14 | OK | energy |
| neets_module_15.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod15.pdf |   0B | 2026-09-14 | OK | energy |
| neets_module_17.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod17.pdf |   0B | 2026-09-14 | OK | energy |
| neets_module_18.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod18.pdf |   0B | 2026-09-14 | OK | energy |
| neets_module_20.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod20.pdf |   0B | 2026-09-14 | OK | energy |
| neets_module_19.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod19.pdf |   0B | 2026-09-14 | OK | energy |
| neets_module_21.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod21.pdf |   0B | 2026-09-14 | OK | energy |
| neets_module_22.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod22.pdf |   0B | 2026-09-14 | OK | energy |
| neets_module_24.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod24.pdf |   0B | 2026-09-14 | OK | energy |
| neets_module_23.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod23.pdf |   0B | 2026-09-14 | OK | energy |
| fema_wood_gas_generator_1989.pdf | https://archive.org/download/fema-wood-gas/FEMA_Wood_Gas.pdf | 192K | 2026-09-14 | OK | energy |
| fema_are_you_ready_p-2064.pdf | https://www.fema.gov/sites/default/files/2020-03/are-you-ready-guide.pdf | 648K | 2026-09-14 | OK | emergency_mgmt |
| nuclear_war_survival_skills_kearny.pdf | https://oism.org/nwss/nwss.pdf |  81M | 2026-09-14 | OK | nuclear |
| army_combat_medic_handbook.pdf | https://archive.org/download/civilian-and-non-civilian-medical-guides/%28Guide%29%20Combat%20First%20Aid.pdf | 3.6M | 2026-09-14 | OK | medical |
| emergency_war_surgery.pdf | https://archive.org/download/civilian-and-non-civilian-medical-guides/Emergency_War_Surgery_The_Survivalists_Medical_Desk_Reference_Department.pdf | 4.7M | 2026-09-14 | OK | medical |
| tc_4-02.1_medical_evacuation.pdf | https://archive.org/download/civilian-and-non-civilian-medical-guides/ARN30125-ATP_4-02.10-000-WEB-1.pdf | 9.7M | 2026-09-14 | OK | medical |
| fm_4-25.11_first_aid.pdf | https://archive.org/download/civilian-and-non-civilian-medical-guides/FM4.25.11-FIRST_AID.pdf | 2.5M | 2026-09-14 | OK | medical |
| sof_medical_handbook.pdf | https://archive.org/download/civilian-and-non-civilian-medical-guides/Special%20Operations%20Forces%20Medical%20Handbook%20%28%20PDFDrive%20%29.pdf |  40M | 2026-09-14 | OK | HISTORICAL |
| ranger_medic_handbook_2007.pdf | https://archive.org/download/civilian-and-non-civilian-medical-guides/Ranger%20Medic%20Handbook%20%282007%29.pdf | 5.0M | 2026-09-14 | OK | medical |
| st_31-91b_special_forces_medical_1982.pdf | https://archive.org/download/civilian-and-non-civilian-medical-guides/St31-91bUsArmySpecialForcesMedicalHandbook1982.pdf |  20M | 2026-09-14 | OK | HISTORICAL |
| paho_who_dead_bodies_disasters.pdf | https://iris.paho.org/bitstream/handle/10665.2/49631/9789275116951_eng.pdf?sequence=1&isAllowed=y | - | 2026-09-14 | FAIL (not PDF) | medical |
| paho_who_dead_bodies_disasters.pdf | https://iris.paho.org/bitstream/handle/10665.2/34357/9789275117767_eng.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| paho_who_dead_bodies_disasters.pdf | https://www.paho.org/hq/dmdocuments/2009/ems-deadbodies-field-manual.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| who_ipcs_poisoning_management.pdf | https://iris.who.int/bitstream/handle/10665/37329/9241544449.pdf?sequence=1 | - | 2026-09-14 | FAIL (not PDF) | medical |
| who_ipcs_poisoning_management.pdf | https://apps.who.int/iris/bitstream/handle/10665/37329/9241544449.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| who_family_planning_global_handbook.pdf | https://iris.who.int/bitstream/handle/10665/44028/9789241563888_eng.pdf?sequence=1 | - | 2026-09-14 | FAIL (not PDF) | medical |
| who_family_planning_global_handbook.pdf | https://apps.who.int/iris/bitstream/handle/10665/44028/9789241563888_eng.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| cdc_cpsc_co_safety.pdf | https://www.cpsc.gov/s3fs-public/5245-0.pdf | - | 2026-09-14 | FAIL (not PDF) | fire_safety |
| cdc_cpsc_co_safety.pdf | https://www.cdc.gov/niosh/topics/co/pdfs/2013-219.pdf | - | 2026-09-14 | FAIL (not PDF) | fire_safety |
| nfpa_wildfire_creating_defensible_space.pdf | https://www.nfpa.org/~/media/Files/Public-Education/Resources/Safety-tip-sheets/WildfireLeaflet.pdf | - | 2026-09-14 | FAIL (not PDF) | fire_safety |
| nfpa_wildfire_creating_defensible_space.pdf | https://www.nfpa.org/api/download?category=Public-Education&path=%2FFiles%2FPublic-Education%2FResources%2FSafety-tip-sheets%2FWildfireLeaflet.pdf | - | 2026-09-14 | FAIL (not PDF) | fire_safety |
| usfs_home_ignition_guide.pdf | https://www.fs.usda.gov/sites/default/files/fs_media/fs_document/pubfulltext_0000024701.pdf | - | 2026-09-14 | FAIL (not PDF) | fire_safety |
| usfs_home_ignition_guide.pdf | https://www.fs.usda.gov/treesearch/pubs/download/43128.pdf | - | 2026-09-14 | FAIL (not PDF) | fire_safety |
| who_pocket_book_hospital_care_children.pdf | https://iris.who.int/bitstream/handle/10665/81170/9789241548373_eng.pdf?sequence=1 | - | 2026-09-14 | FAIL (not PDF) | medical |
| who_pocket_book_hospital_care_children.pdf | https://apps.who.int/iris/bitstream/handle/10665/10120/9789241546775_eng.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| who_surgical_care_district_hospital.pdf | https://iris.who.int/bitstream/handle/10665/42564/0WHO_MSD_2003.7.pdf?sequence=1 | - | 2026-09-14 | FAIL (not PDF) | medical |
| who_surgical_care_district_hospital.pdf | https://apps.who.int/iris/bitstream/handle/10665/42564/0WHO_MSD_2003.7.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| who_imci_chart_booklet.pdf | https://iris.who.int/bitstream/handle/10665/104772/9789241506588_eng.pdf?sequence=1 | - | 2026-09-14 | FAIL (not PDF) | medical |
| who_imci_chart_booklet.pdf | https://apps.who.int/iris/bitstream/handle/10665/104772/9789241506588_eng.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| who_mhgap_intervention_guide_v2.pdf | https://iris.who.int/bitstream/handle/10665/250239/9789241549790-eng.pdf?sequence=1 | - | 2026-09-14 | FAIL (not PDF) | medical |
| who_mhgap_intervention_guide_v2.pdf | https://apps.who.int/iris/bitstream/handle/10665/250239/9789241549790-eng.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| who_psychological_first_aid.pdf | https://iris.who.int/bitstream/handle/10665/44615/9789241548205_eng.pdf?sequence=1 | - | 2026-09-14 | FAIL (not PDF) | medical |
| who_psychological_first_aid.pdf | https://apps.who.int/iris/bitstream/handle/10665/44615/9789241548205_eng.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| who_drinking_water_quality_4th_ed.pdf | https://iris.who.int/bitstream/handle/10665/44584/9789241548151_eng.pdf?sequence=1 | - | 2026-09-14 | FAIL (not PDF) | medical |
| who_drinking_water_quality_4th_ed.pdf | https://apps.who.int/iris/bitstream/handle/10665/44584/9789241548151_eng.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| msf_clinical_guidelines.pdf | https://medicalguidelines.msf.org/sites/default/files/MSF_CG_en.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| msf_clinical_guidelines.pdf | https://cdn.msf.org/sites/msf.org/files/2021-03/MSF_CG_en.pdf | - | 2026-09-14 | FAIL (curl) | medical |
| msf_essential_drugs.pdf | https://medicalguidelines.msf.org/sites/default/files/MSF_ED_en.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| msf_essential_drugs.pdf | https://cdn.msf.org/sites/msf.org/files/2021-03/MSF_ED_en.pdf | - | 2026-09-14 | FAIL (curl) | medical |
| msf_obstetrics.pdf | https://medicalguidelines.msf.org/sites/default/files/MSF_OB_en.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| msf_obstetrics.pdf | https://cdn.msf.org/sites/msf.org/files/2021-03/MSF_OB_en.pdf | - | 2026-09-14 | FAIL (curl) | medical |
| msf_tuberculosis.pdf | https://medicalguidelines.msf.org/sites/default/files/MSF_TB_en.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| msf_tuberculosis.pdf | https://cdn.msf.org/sites/msf.org/files/2021-03/MSF_TB_en.pdf | - | 2026-09-14 | FAIL (curl) | medical |
| where_there_is_no_psychiatrist.pdf | https://www.rcpsych.ac.uk/docs/default-source/improving-care/better-mh-policy/college-reports/college-report-cr174.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| where_there_is_no_psychiatrist.pdf | https://www.who.int/mental_health/resources/en/wtenopsychiatrist.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| helping_babies_breathe.pdf | https://www.helpingbabiesbreathe.org/docs/HBBLearnerGuide2ndEdition.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| helping_babies_breathe.pdf | https://www.who.int/pmnch/media/news/2010/helping_babies_breathe.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| hesperian_where_there_is_no_dentist.pdf | https://store.hesperian.org/assets/extras/B007E_wtind_2015.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| hesperian_where_there_is_no_dentist.pdf | https://hesperian.org/wp-content/uploads/pdf/en_dent_2015/en_dent_2015.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| hesperian_where_women_have_no_doctor.pdf | https://store.hesperian.org/assets/extras/B007F_wwhnd_2013.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| hesperian_where_women_have_no_doctor.pdf | https://hesperian.org/wp-content/uploads/pdf/en_wwhnd_2013/en_wwhnd_2013.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| hesperian_book_for_midwives.pdf | https://store.hesperian.org/assets/extras/B007D_mw_2017.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| hesperian_book_for_midwives.pdf | https://hesperian.org/wp-content/uploads/pdf/en_mw_2017/en_mw_2017.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| hesperian_donde_no_hay_doctor_es.pdf | https://hesperian.org/wp-content/uploads/pdf/es_wtnd_2013/es_wtnd_2013.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| hesperian_donde_no_hay_doctor_es.pdf | https://store.hesperian.org/assets/extras/B007ES_wtnd_2013.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| epa_emergency_disinfection.pdf | https://www.epa.gov/sites/default/files/2015-08/documents/emergency_disinfection.pdf | - | 2026-09-14 | FAIL (not PDF) | water |
| epa_emergency_disinfection.pdf | https://www.epa.gov/ground-water-and-drinking-water/emergency-disinfection-drinking-water | - | 2026-09-14 | FAIL (not PDF) | water |
| sodis_manual_en.pdf | https://www.sodis.ch/methode/anwendung/ausbildungsmaterial/dokumente_material/english/sodis_manual.pdf | - | 2026-09-14 | FAIL (not PDF) | water |
| sodis_manual_en.pdf | https://eawag-sandbox.ch/fileadmin/Domain1/Abteilungen/sandec/schwerpunkte/swm/SODIS/SODIS/Dokumente/Manuals/SODIS_Manual_English.pdf | - | 2026-09-14 | FAIL (curl) | water |
| fm_10-52_water_supply.pdf | https://irp.fas.org/doddir/army/fm10-52.pdf | - | 2026-09-14 | FAIL (not PDF) | water |
| fm_10-52_water_supply.pdf | https://archive.org/download/FM1052/FM_10-52.pdf | - | 2026-09-14 | FAIL (not PDF) | water |
| humanure_handbook_3rd_ed.pdf | https://humanurehandbook.com/downloads/Humanure_Handbook_3rd_Edition.pdf | - | 2026-09-14 | FAIL (not PDF) | sanitation |
| humanure_handbook_3rd_ed.pdf | https://compostingtoilet.org/humanure.pdf | - | 2026-09-14 | FAIL (curl) | sanitation |
| cawst_biosand_filter_manual.pdf | https://www.cawst.org/assets/Uploads/resources/CAWST-BSF-Manual-2012.pdf | - | 2026-09-14 | FAIL (not PDF) | water |
| cawst_biosand_filter_manual.pdf | https://resources.cawst.org/content/documents/biosand-filter-manual/cawst_biosandfilter_manual_2012_en.pdf | - | 2026-09-14 | FAIL (not PDF) | water |
| usda_canning_guide_01.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/usda-completeGuide-01.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_01.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/guide_1.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_01.pdf | https://nchfp.uga.edu/publications/usda/GUIDE1Moreinfo.html | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_02.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/usda-completeGuide-02.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_02.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/guide_2.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_02.pdf | https://nchfp.uga.edu/publications/usda/GUIDE2Moreinfo.html | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_03.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/usda-completeGuide-03.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_03.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/guide_3.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_03.pdf | https://nchfp.uga.edu/publications/usda/GUIDE3Moreinfo.html | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_04.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/usda-completeGuide-04.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_04.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/guide_4.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_04.pdf | https://nchfp.uga.edu/publications/usda/GUIDE4Moreinfo.html | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_05.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/usda-completeGuide-05.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_05.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/guide_5.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_05.pdf | https://nchfp.uga.edu/publications/usda/GUIDE5Moreinfo.html | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_06.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/usda-completeGuide-06.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_06.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/guide_6.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_06.pdf | https://nchfp.uga.edu/publications/usda/GUIDE6Moreinfo.html | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_07.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/usda-completeGuide-07.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_07.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/guide_7.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_07.pdf | https://nchfp.uga.edu/publications/usda/GUIDE7Moreinfo.html | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_08.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/usda-completeGuide-08.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_08.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/guide_8.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_08.pdf | https://nchfp.uga.edu/publications/usda/GUIDE8Moreinfo.html | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_09.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/usda-completeGuide-09.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_09.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/guide_9.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_09.pdf | https://nchfp.uga.edu/publications/usda/GUIDE9Moreinfo.html | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_plants_checklist.csv | https://plants.usda.gov/csvdownload | - | 2026-09-14 | FAIL (too small) | food_preservation |
| fm_21-76_survival.pdf | https://archive.org/download/FM2176USArmySurvivalManual/FM_21-76_US_Army_Survival_Manual.pdf | - | 2026-09-14 | FAIL (not PDF) | military_manuals |
| fm_21-76_survival.pdf | https://irp.fas.org/doddir/army/fm21-76.pdf | - | 2026-09-14 | FAIL (not PDF) | military_manuals |
| tc_3-21.76_ranger_handbook.pdf | https://archive.org/download/TC32176RangerHandbook/TC3-21.76_Ranger_Handbook.pdf | - | 2026-09-14 | FAIL (not PDF) | military_manuals |
| tc_3-21.76_ranger_handbook.pdf | https://irp.fas.org/doddir/army/tc3-21-76.pdf | - | 2026-09-14 | FAIL (not PDF) | military_manuals |
| fm_5-426_carpentry.pdf | https://archive.org/download/Fm5426/fm5-426.pdf | - | 2026-09-14 | FAIL (not PDF) | shelter |
| fm_5-426_carpentry.pdf | https://irp.fas.org/doddir/army/fm5-426.pdf | - | 2026-09-14 | FAIL (not PDF) | shelter |
| fm_3-34.471_plumbing.pdf | https://archive.org/download/FM3-34.471/FM_3-34.471.pdf | - | 2026-09-14 | FAIL (not PDF) | shelter |
| fm_3-34.471_plumbing.pdf | https://irp.fas.org/doddir/army/fm3-34-471.pdf | - | 2026-09-14 | FAIL (not PDF) | shelter |
| fm_5-428_concrete_masonry.pdf | https://archive.org/download/FM5-428/FM_5-428.pdf | - | 2026-09-14 | FAIL (not PDF) | shelter |
| fm_5-428_concrete_masonry.pdf | https://irp.fas.org/doddir/army/fm5-428.pdf | - | 2026-09-14 | FAIL (not PDF) | shelter |
| fm_5-34_engineer_field_data.pdf | https://archive.org/download/FM5-34/FM_5-34.pdf | - | 2026-09-14 | FAIL (not PDF) | shelter |
| fm_5-34_engineer_field_data.pdf | https://irp.fas.org/doddir/army/fm5-34.pdf | - | 2026-09-14 | FAIL (not PDF) | shelter |
| fm_5-103_survivability.pdf | https://archive.org/download/FM5-103/FM_5-103.pdf | - | 2026-09-14 | FAIL (not PDF) | military_manuals |
| fm_5-103_survivability.pdf | https://irp.fas.org/doddir/army/fm5-103.pdf | - | 2026-09-14 | FAIL (not PDF) | military_manuals |
| tm_9-8000_automotive_vehicles.pdf | https://archive.org/download/TM9-8000/TM_9-8000.pdf | - | 2026-09-14 | FAIL (not PDF) | military_manuals |
| tm_9-8000_automotive_vehicles.pdf | https://irp.fas.org/doddir/army/tm9-8000.pdf | - | 2026-09-14 | FAIL (not PDF) | military_manuals |
| tc_9-237_welding.pdf | https://archive.org/download/TC9-237/TC_9-237.pdf | - | 2026-09-14 | FAIL (not PDF) | military_manuals |
| tc_9-237_welding.pdf | https://irp.fas.org/doddir/army/tc9-237.pdf | - | 2026-09-14 | FAIL (not PDF) | military_manuals |
| tc_3-25.26_map_reading_land_nav.pdf | https://archive.org/download/TC3-25.26/TC_3-25.26.pdf | - | 2026-09-14 | FAIL (not PDF) | navigation |
| tc_3-25.26_map_reading_land_nav.pdf | https://irp.fas.org/doddir/army/fm3-25-26.pdf | - | 2026-09-14 | FAIL (not PDF) | navigation |
| tc_3-25.26_map_reading_land_nav.pdf | https://armypubs.army.mil/epubs/DR_pubs/DR_a/ARN31301-TC_3-25.26-000-WEB-1.pdf | - | 2026-09-14 | FAIL (not PDF) | navigation |
| bowditch_vol1.pdf | https://msi.nga.mil/api/publications/download?type=view&key=16694272/SFH00000/Bowditch_2019_Part_1.pdf | - | 2026-09-14 | FAIL (not PDF) | navigation |
| bowditch_vol1.pdf | https://www.nga.mil/sites/default/files/atoms/files/Bowditch%20Vol%201.pdf | - | 2026-09-14 | FAIL (not PDF) | navigation |
| usda_wood_handbook_fpl_gtr_282.pdf | https://www.fpl.fs.usda.gov/documnts/fplgtr/fpl_gtr282.pdf | - | 2026-09-14 | FAIL (not PDF) | shelter |
| neets_module_01.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod01.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| neets_module_02.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod02.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| neets_module_03.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod03.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| neets_module_04.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod04.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| neets_module_05.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod05.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| neets_module_06.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod06.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| neets_module_07.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod07.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| neets_module_08.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod08.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| neets_module_09.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod09.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| neets_module_10.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod10.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| neets_module_11.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod11.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| neets_module_12.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod12.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| neets_module_13.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod13.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| neets_module_14.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod14.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| neets_module_15.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod15.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| neets_module_16.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod16.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| neets_module_17.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod17.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| neets_module_18.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod18.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| neets_module_19.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod19.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| neets_module_20.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod20.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| neets_module_21.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod21.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| neets_module_22.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod22.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| neets_module_23.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod23.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| neets_module_24.pdf | https://www.hnsa.org/wp-content/uploads/2014/07/mod24.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| fema_wood_gas_generator_1989.pdf | https://archive.org/download/fema-wood-gas/FEMA_Wood_Gas.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| fema_wood_gas_generator_1989.pdf | https://www.woodgas.com/fema_wood_gasifier.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| fema_are_you_ready.pdf | https://www.fema.gov/sites/default/files/2020-03/are-you-ready-guide.pdf | - | 2026-09-14 | FAIL (not PDF) | emergency_mgmt |
| fema_are_you_ready.pdf | https://www.fema.gov/media-library-data/20130726-1549-20490-0034/p2064.pdf | - | 2026-09-14 | FAIL (not PDF) | emergency_mgmt |
| neets_module_01.pdf | https://archive.org/download/NEETSModules/NEETS%20Module%2001%20-%20Introduction%20to%20Matter%20Energy%20and%20Direct%20Current.pdf | 2.0M | 2026-09-14 | OK | energy |
| neets_module_02.pdf | https://archive.org/download/NEETSModules/NEETS%20Module%2002%20-%20Introduction%20to%20Alternating%20Current%20and%20Transformers.pdf | 3.8M | 2026-09-14 | OK | energy |
| neets_module_03.pdf | https://archive.org/download/NEETSModules/NEETS%20Module%2003-%20Introduction%20to%20Circuit%20Protection%2C%20Control%2C%20and%20Measurement.pdf | 2.3M | 2026-09-14 | OK | energy |
| neets_module_04.pdf | https://archive.org/download/NEETSModules/NEETS%20Module%2004%20-%20Introduction%20to%20Electrical%20Conductors%2C%20Wiring%20Techniques%2C%20and%20Schematic%20Reading.pdf | 1.5M | 2026-09-14 | OK | energy |
| neets_module_05.pdf | https://archive.org/download/NEETSModules/NEETS%20Module%2005%20-%20Introduction%20to%20Generators%20and%20Motors.pdf | 1.3M | 2026-09-14 | OK | energy |
| neets_module_06.pdf | https://archive.org/download/NEETSModules/NEETS%20Module%2006%20-%20Introduction%20to%20Electronic%20Emissions%2C%20Tubes%2C%20and%20Power%20Supplies.pdf | 1.5M | 2026-09-14 | OK | energy |
| neets_module_07.pdf | https://archive.org/download/NEETSModules/NEETS%20Module%2007%20-%20Introduction%20to%20Solid-State%20Devices%20and%20Power%20Supplies.pdf | 2.4M | 2026-09-14 | OK | energy |
| neets_module_08.pdf | https://archive.org/download/NEETSModules/NEETS%20Module%2008%20-%20Introduction%20to%20Amplifiers.pdf | 1.2M | 2026-09-14 | OK | energy |
| neets_module_09.pdf | https://archive.org/download/NEETSModules/NEETS%20Module%2009%20-%20Introduction%20to%20Wave-%20Generation%20and%20Wave-Shaping.pdf | 1.8M | 2026-09-14 | OK | energy |
| neets_module_10.pdf | https://archive.org/download/NEETSModules/NEETS%20Module%2010%20-%20Introduction%20to%20Wave%20Propagation%2C%20Transmission%20Lines%2C%20and%20Antennas.pdf | 2.4M | 2026-09-14 | OK | energy |
| neets_module_11.pdf | https://archive.org/download/NEETSModules/NEETS%20Module%2011%20-%20Microwave%20Principles.pdf | 4.4M | 2026-09-14 | OK | energy |
| neets_module_12.pdf | https://archive.org/download/NEETSModules/NEETS%20Module%2012%20-%20Modulation.pdf | 1.6M | 2026-09-14 | OK | energy |
| neets_module_13.pdf | https://archive.org/download/NEETSModules/NEETS%20Module%2013%20-%20Introduction%20to%20Number%20Systems%20and%20Logic.pdf | 1.1M | 2026-09-14 | OK | energy |
| neets_module_14.pdf | https://archive.org/download/NEETSModules/NEETS%20Module%2014%20-%20Introduction%20to%20Microelectronics.pdf | 6.0M | 2026-09-14 | OK | energy |
| neets_module_15.pdf | https://archive.org/download/NEETSModules/NEETS%20Module%2015%20-%20Principles%20of%20Synchros%2C%20Servos%2C%20and%20Gyros.pdf | 1.6M | 2026-09-14 | OK | energy |
| neets_module_16.pdf | https://archive.org/download/NEETSModules/NEETS%20Module%2016%20-%20Introduction%20to%20Test%20Equipment.pdf | 1.9M | 2026-09-14 | OK | energy |
| neets_module_17.pdf | https://archive.org/download/NEETSModules/NEETS%20Module%2017%20-%20Radio-Frequency%20Communications%20Principles.pdf | 6.2M | 2026-09-14 | OK | energy |
| neets_module_18.pdf | https://archive.org/download/NEETSModules/NEETS%20Module%2018%20-%20Radar%20Principles.pdf | 1.6M | 2026-09-14 | OK | energy |
| neets_module_19.pdf | https://archive.org/download/NEETSModules/NEETS%20Module%2019%20-%20The%20Technician%2527s%20Handbook.pdf | 1.3M | 2026-09-14 | OK | energy |
| neets_module_20.pdf | https://archive.org/download/NEETSModules/NEETS%20Module%2020%20-%20Master%20Glossary.pdf | 500K | 2026-09-14 | OK | energy |
| neets_module_21.pdf | https://archive.org/download/NEETSModules/NEETS%20Module%2021%20-%20Test%20Methods%20and%20Practices.pdf | 1.9M | 2026-09-14 | OK | energy |
| neets_module_22.pdf | https://archive.org/download/NEETSModules/NEETS%20Module%2022%20-%20Introduction%20to%20Digital%20Computers.pdf | 3.7M | 2026-09-14 | OK | energy |
| neets_module_23.pdf | https://archive.org/download/NEETSModules/NEETS%20Module%2023%20-%20Magnetic%20Recording.pdf | 3.0M | 2026-09-14 | OK | energy |
| neets_module_24.pdf | https://archive.org/download/NEETSModules/NEETS%20Module%2024%20-%20Introduction%20to%20Fiber%20Optics.pdf | 1.7M | 2026-09-14 | OK | energy |
| fm_5-426_carpentry.pdf | https://archive.org/download/FM5-426/FM5-426.pdf | 4.4M | 2026-09-14 | OK | shelter |
| fm_5-103_survivability.pdf | https://archive.org/download/fm5-10385/fm5-103(85).pdf | 3.1M | 2026-09-14 | OK | military_manuals |
| tm_9-8000_automotive_vehicles.pdf | https://archive.org/download/tm-9-8000-principles-of-automotive-vehicles-1985/TM9-8000_Principles_of_automotive_vehicles_1985.pdf |  17M | 2026-09-14 | OK | military_manuals |
| tc_3-25.26_map_reading_land_nav.pdf | https://archive.org/download/map-reading-and-land-navigation-tc-3-25-26/Map%20Reading%20and%20Land%20Navigation%20TC%203-25-26.pdf |  10M | 2026-09-14 | OK | navigation |
| fm_5-428_concrete_masonry.pdf | https://archive.org/download/FM_5_428_C_M_1998/FM%205-428%20Concrete%20and%20Masonry%20%281998%29.pdf | 3.8M | 2026-09-14 | OK | shelter |
| fm_5-34_engineer_field_data.pdf | https://archive.org/download/fm-5-34-engineer-field-data-1969/FM_5-34_Engineer_Field_Data_1969.pdf | - | 2026-09-14 | FAIL (not PDF) | shelter |
| tc_9-237_welding.pdf | https://irp.fas.org/doddir/army/tc9-237.pdf | - | 2026-09-14 | FAIL (not PDF) | military_manuals |
| tc_3-21.76_ranger_handbook.pdf | https://archive.org/download/TC32176RangerHandbook/TC_3-21.76_Ranger_Handbook.pdf | - | 2026-09-14 | FAIL (not PDF) | military_manuals |
| fm_21-76_survival.pdf | https://archive.org/download/FM2176USArmySurvivalManual/FM_21-76_US_Army_Survival_Manual.pdf | - | 2026-09-14 | FAIL (not PDF) | military_manuals |
| fm_3-34.471_plumbing.pdf | https://irp.fas.org/doddir/army/fm3-34-471.pdf | - | 2026-09-14 | FAIL (not PDF) | shelter |
| bowditch_vol1.pdf | https://archive.org/download/bowditch-american-practical-navigator-2019/Bowditch_Vol1.pdf | - | 2026-09-14 | FAIL (not PDF) | navigation |
| usda_wood_handbook_fpl_gtr_282.pdf | https://www.fpl.fs.usda.gov/documnts/fplgtr/fpl_gtr282.pdf | - | 2026-09-14 | FAIL (not PDF) | shelter |
| fema_wood_gas_generator.pdf | https://archive.org/download/FEMAProducerGasGeneration/FEMAProducerGasGeneration.pdf | - | 2026-09-14 | FAIL (not PDF) | energy |
| fema_are_you_ready.pdf | https://www.fema.gov/sites/default/files/2020-03/are-you-ready-guide.pdf | - | 2026-09-14 | FAIL (not PDF) | emergency_mgmt |
| cdc_cpsc_co_safety.pdf | https://www.cpsc.gov/s3fs-public/5245-0.pdf | - | 2026-09-14 | FAIL (not PDF) | fire_safety |
| nfpa_wildfire_tip_sheet.pdf | https://www.nfpa.org/api/download?category=Public-Education&path=%2FFiles%2FPublic-Education%2FResources%2FSafety-tip-sheets%2FWildfireLeaflet.pdf | - | 2026-09-14 | FAIL (not PDF) | fire_safety |
| who_pocket_book_hospital_care_children.pdf | https://iris.who.int/bitstream/handle/10665/81170/9789241548373_eng.pdf?sequence=1&isAllowed=y | - | 2026-09-14 | FAIL (not PDF) | medical |
| who_surgical_care_district_hospital.pdf | https://iris.who.int/bitstream/handle/10665/42564/0WHO_MSD_2003.7.pdf?sequence=1&isAllowed=y | - | 2026-09-14 | FAIL (not PDF) | medical |
| who_imci_chart_booklet.pdf | https://iris.who.int/bitstream/handle/10665/104772/9789241506588_eng.pdf?sequence=1&isAllowed=y | - | 2026-09-14 | FAIL (not PDF) | medical |
| who_mhgap_intervention_guide_v2.pdf | https://iris.who.int/bitstream/handle/10665/250239/9789241549790-eng.pdf?sequence=1&isAllowed=y | - | 2026-09-14 | FAIL (not PDF) | medical |
| who_psychological_first_aid.pdf | https://iris.who.int/bitstream/handle/10665/44615/9789241548205_eng.pdf?sequence=1&isAllowed=y | - | 2026-09-14 | FAIL (not PDF) | medical |
| who_drinking_water_quality_4th_ed.pdf | https://iris.who.int/bitstream/handle/10665/44584/9789241548151_eng.pdf?sequence=1&isAllowed=y | - | 2026-09-14 | FAIL (not PDF) | medical |
| who_ipcs_poisoning_management.pdf | https://iris.who.int/bitstream/handle/10665/37329/9241544449.pdf?sequence=1&isAllowed=y | - | 2026-09-14 | FAIL (not PDF) | medical |
| who_family_planning_global_handbook.pdf | https://iris.who.int/bitstream/handle/10665/44028/9789241563888_eng.pdf?sequence=1&isAllowed=y | - | 2026-09-14 | FAIL (not PDF) | medical |
| paho_who_dead_bodies_disasters.pdf | https://iris.paho.org/bitstream/handle/10665.2/49631/9789275116951_eng.pdf?sequence=1&isAllowed=y | - | 2026-09-14 | FAIL (not PDF) | medical |
| msf_clinical_guidelines.pdf | https://medicalguidelines.msf.org/sites/default/files/clinical-guidelines-24761695.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| msf_essential_drugs.pdf | https://medicalguidelines.msf.org/sites/default/files/essential-drugs-24762483.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| hesperian_where_there_is_no_dentist.pdf | https://store.hesperian.org/assets/extras/B007E_wtind_2015.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| hesperian_where_women_have_no_doctor.pdf | https://store.hesperian.org/assets/extras/B007F_wwhnd_2013.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| hesperian_book_for_midwives.pdf | https://store.hesperian.org/assets/extras/B007D_mw_2017.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| hesperian_donde_no_hay_doctor_es.pdf | https://hesperian.org/wp-content/uploads/pdf/es_wtnd_2013/es_wtnd_2013.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| epa_emergency_disinfection.pdf | https://www.epa.gov/sites/default/files/2015-08/documents/emergency_disinfection.pdf | - | 2026-09-14 | FAIL (not PDF) | water |
| sodis_manual.pdf | https://www.sodis.ch/methode/anwendung/ausbildungsmaterial/dokumente_material/english/sodis_manual.pdf | - | 2026-09-14 | FAIL (not PDF) | water |
| humanure_handbook_3rd_ed.pdf | https://humanurehandbook.com/downloads/Humanure_Handbook_3rd_Edition.pdf | - | 2026-09-14 | FAIL (not PDF) | sanitation |
| cawst_biosand_filter_manual.pdf | https://www.cawst.org/assets/Uploads/resources/CAWST-BSF-Manual-2012.pdf | - | 2026-09-14 | FAIL (not PDF) | water |
| fm_10-52_water_supply.pdf | https://irp.fas.org/doddir/army/fm10-52.pdf | - | 2026-09-14 | FAIL (not PDF) | water |
| where_there_is_no_psychiatrist.pdf | https://www.rcpsych.ac.uk/docs/default-source/improving-care/better-mh-policy/college-reports/college-report-cr174.pdf | - | 2026-09-14 | FAIL (not PDF) | medical |
| helping_babies_breathe.pdf | https://www.aap.org/en/patient-care/helping-babies-breathe/ | - | 2026-09-14 | FAIL (not PDF) | medical |
| usda_canning_guide_01.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/usda-completeGuide-01.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_02.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/usda-completeGuide-02.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_03.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/usda-completeGuide-03.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_04.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/usda-completeGuide-04.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_05.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/usda-completeGuide-05.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_06.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/usda-completeGuide-06.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_07.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/usda-completeGuide-07.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_08.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/usda-completeGuide-08.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| usda_canning_guide_09.pdf | https://nchfp.uga.edu/sites/default/files/media/documents/usda-completeGuide-09.pdf | - | 2026-09-14 | FAIL (not PDF) | food_preservation |
| tc_3-21.76_ranger_handbook.pdf | https://archive.org/download/tc-3-21.76-ranger-handbook-2017/TC%203-21.76%20Ranger%20Handbook%20%202017.pdf |  21M | 2026-09-14 | OK | military_manuals |
| fm_21-76_survival.pdf | https://archive.org/download/fm-21-76-us-army-survival-manual/FM%2021-76%20US%20ARMY%20SURVIVAL%20MANUAL.pdf | 2.8M | 2026-09-14 | OK | military_manuals |
| fm_5-34_engineer_field_data.pdf | https://archive.org/download/fm-5-34-engineer-field-data-1969/FM%205-34%20Engineer%20Field%20Data%20%201969.pdf |  18M | 2026-09-14 | OK | shelter |
| usda_wood_handbook.pdf | https://archive.org/download/wood-handbook/Wood%20Handbook.pdf |  15M | 2026-09-14 | OK | shelter |
| fema_wood_gas_generator.pdf | https://archive.org/download/FEMAEmergencyGassifer/FEMA_emergency_gassifer.pdf | 1.9M | 2026-09-14 | OK | energy |
| fm_3-34.471_plumbing.pdf | https://archive.org/download/fm3-34-471-plumbing/FM_3-34.471_Plumbing.pdf | - | 2026-09-14 | FAIL | shelter |
| tc_9-237_welding.pdf | https://archive.org/download/TM9-237/TM9-237.pdf |  27M | 2026-09-14 | OK | military_manuals |
| fm_3-34.471_plumbing.pdf | - | - | 2026-09-14 | FAIL (URL not found) | shelter |
| hesperian_where_there_is_no_dentist.pdf | https://archive.org/download/where-there-is-no-dentist-hesperian-2010/Where_there_is_no_dentist_-_Hesperian_2010.pdf | 6.5M | 2026-09-14 | OK | medical |
| hesperian_where_women_have_no_doctor.pdf | https://archive.org/download/wherewomenhaveno0000unse/wherewomenhaveno0000unse.pdf | - | 2026-09-14 | FAIL | medical |
| hesperian_book_for_midwives.pdf | https://archive.org/download/bookformidwivesm00klei/bookformidwivesm00klei.pdf | - | 2026-09-14 | FAIL | medical |
| hesperian_donde_no_hay_doctor_mujeres_es.pdf | https://archive.org/download/dondenohaydoctor0000unse/dondenohaydoctor0000unse.pdf | - | 2026-09-14 | FAIL | medical |
| usda_complete_guide_home_canning_2015.pdf | https://archive.org/download/usda-complete-guide-to-home-canning-2015-revision/USDA-Complete-Guide-to-Home-Canning-2015-revision.pdf |  17M | 2026-09-14 | OK | food_preservation |
| usda_canning_guide_01.pdf | https://archive.org/download/guide-01-home-can-rev-0715/GUIDE01_HomeCan_rev0715.pdf | 3.6M | 2026-09-14 | OK | food_preservation |
| sodis_manual.pdf | https://archive.org/download/SolarWaterDisinfection-English-Sodis/sodis.pdf | 5.3M | 2026-09-14 | OK | water |
| cawst_biosand_filter_manual.pdf | https://archive.org/download/biosand-filter-construction-manual/Biosand%20Filter%20Construction%20Manual.pdf | 5.7M | 2026-09-14 | OK | water |
| fm_10-52_water_supply.pdf | https://archive.org/download/militarymanualsfm10521/FM_10-52.pdf | - | 2026-09-14 | FAIL | water |
| humanure_handbook_3rd_ed.pdf | https://humanurehandbook.com/downloads/The_Humanure_Handbook.pdf | - | 2026-09-14 | FAIL | sanitation |
| who_pocket_book_hospital_care_children.pdf | https://apps.who.int/iris/handle/10665/10120/9789241546775_eng.pdf | - | 2026-09-14 | FAIL | medical |
| who_mhgap_intervention_guide_v2.pdf | https://apps.who.int/iris/rest/bitstreams/655702/retrieve | - | 2026-09-14 | FAIL | medical |
| who_psychological_first_aid.pdf | https://apps.who.int/iris/rest/bitstreams/655703/retrieve | - | 2026-09-14 | FAIL | medical |
| where_there_is_no_psychiatrist.pdf | https://www.rcpsych.ac.uk/docs/default-source/improving-care/better-mh-policy/college-reports/college-report-cr174.pdf | - | 2026-09-14 | FAIL | medical |
| helping_babies_breathe_2nd_ed.pdf | https://www.helpingbabiesbreathe.org/docs/HBBLearnerGuide2ndEdition.pdf | - | 2026-09-14 | FAIL | medical |
| fm_10-52_water_supply.pdf | https://archive.org/download/ost-military-doctrine-fm10_52/fm10_52.pdf | 8.0M | 2026-09-14 | OK | water |
| hesperian_where_women_have_no_doctor.pdf | https://archive.org/download/wherewomenhaveno0000unse/ | - | 2026-09-14 | FAIL (login required) | medical |
| hesperian_book_for_midwives.pdf | https://archive.org/download/bookformidwivesm00klei/ | - | 2026-09-14 | FAIL (login required) | medical |
| hesperian_donde_no_hay_doctor_mujeres_es.pdf | https://archive.org/download/dondenohaydoctor0000unse/ | - | 2026-09-14 | FAIL (login required) | medical |
| humanure_handbook_3rd_ed.pdf | https://humanurehandbook.com/downloads/ | - | 2026-09-14 | FAIL (404) | sanitation |
| fm_3-34.471_plumbing.pdf | - | - | 2026-09-14 | FAIL (not found) | shelter |
| who_pocket_book_hospital_care_children.pdf | https://iris.who.int/handle/10665/10120 | - | 2026-09-14 | FAIL (WHO blocks anon download) | medical |
| who_surgical_care_district_hospital.pdf | https://iris.who.int/handle/10665/42564 | - | 2026-09-14 | FAIL (WHO blocks anon download) | medical |
| who_imci_chart_booklet.pdf | https://iris.who.int/handle/10665/104772 | - | 2026-09-14 | FAIL (WHO blocks anon download) | medical |
| who_mhgap_intervention_guide_v2.pdf | https://iris.who.int/handle/10665/250239 | - | 2026-09-14 | FAIL (WHO blocks anon download) | medical |
| who_psychological_first_aid.pdf | https://iris.who.int/handle/10665/44615 | - | 2026-09-14 | FAIL (WHO blocks anon download) | medical |
| who_drinking_water_quality_4th_ed.pdf | https://iris.who.int/handle/10665/44584 | - | 2026-09-14 | FAIL (WHO blocks anon download) | medical |
| who_ipcs_poisoning_management.pdf | https://iris.who.int/handle/10665/37329 | - | 2026-09-14 | FAIL (WHO blocks anon download) | medical |
| who_family_planning_global_handbook.pdf | https://iris.who.int/handle/10665/44028 | - | 2026-09-14 | FAIL (WHO blocks anon download) | medical |
| paho_who_dead_bodies_disasters.pdf | https://iris.who.int/handle/10665.2/49631 | - | 2026-09-14 | FAIL (WHO blocks anon download) | medical |
| msf_clinical_guidelines.pdf | https://www.msf.org/sites/default/files/msf_clinical_guidelines_9th_ed.pdf | - | 2026-09-14 | FAIL | medical |
| msf_essential_drugs.pdf | https://www.msf.org/sites/default/files/msf_essential_drugs_2016.pdf | - | 2026-09-14 | FAIL | medical |
| where_there_is_no_psychiatrist.pdf | https://www.cambridge.org/core/services/aop-cambridge-core/content/view/where-there-is-no-psychiatrist.pdf | - | 2026-09-14 | FAIL | medical |
| helping_babies_breathe.pdf | https://www.who.int/publications/m/item/helping-babies-breathe-facilitator-guide | - | 2026-09-14 | FAIL | medical |
| fema_are_you_ready.pdf | https://archive.org/download/areyoureadyindep0000vari/areyoureadyindep0000vari.pdf | - | 2026-09-14 | FAIL | emergency_mgmt |

## Session Summary (2026-09-14)

- **Actual PDFs on disk (verified):** 50 new files + 19 existing Hesperian = 69 total
- **Deduplicated OK log entries:** 93 (includes earlier false-positives since cleaned up)
- **Total docs size on disk:** 401 MB
- **Notable failures requiring follow-up:**
  - WHO IRIS books (8 titles): iris.who.int blocks anonymous download — need browser session or publisher mirror
  - MSF Clinical/Drugs/OB/TB guides: medicalguidelines.msf.org URL pattern changed
  - Hesperian (Where Women Have No Doctor, Book for Midwives, Spanish ES): archive.org login-gated
  - Humanure Handbook 3rd ed.: humanurehandbook.com 404
  - FM 3-34.471 Plumbing: no free public mirror found
  - FEMA Are You Ready P-2064: fema.gov redirects to HTML; archive.org copy login-gated
  - Fire safety PDFs (NFPA wildfire, CPSC CO, USFS): publisher sites return HTML
  - USDA NCHFP canning guides 2-9 (URL pattern changed)
  - Where There Is No Psychiatrist (RCPsych paywall)
| msf_clinical_guidelines.pdf | https://medicalguidelines.msf.org/sites/default/files/2026-05/guideline-170-en.pdf | 6.4M | 2026-09-14 | OK (retry, main session) | medical/msf |
| msf_essential_drugs.pdf | https://medicalguidelines.msf.org/sites/default/files/pdf/guideline-339-en.pdf | 2.7M | 2026-09-14 | OK (retry, main session) | medical/msf |
| msf_obstetrics_newborn.pdf | https://medicalguidelines.msf.org/sites/default/files/pdf/guideline-449-en.pdf | 4.7M | 2026-09-14 | OK (retry, main session) | medical/msf |

## Retry Session (2026-09-15) — WHO UUID bitstream + alternate sources

| filename | source_url | size | date | status | category |
|---|---|---|---|---|---|
| who_pocket_book_hospital_care_children.pdf | https://iris.who.int/server/api/core/bitstreams/8f110da0-22e6-4ef1-90e4-c9f1b7daa363/content | 3.0M | 2026-09-15 | OK | medical |
| who_mhgap_intervention_guide_v2.pdf | https://iris.who.int/server/api/core/bitstreams/788dd77e-1d5f-49ee-86d2-18f7d78d1ffd/content | 7.9M | 2026-09-15 | OK | medical |
| who_psychological_first_aid.pdf | https://iris.who.int/server/api/core/bitstreams/e7e129fb-b306-496d-84a5-67bb70abc130/content | 1.4M | 2026-09-15 | OK | medical |
| who_drinking_water_quality_4th_ed.pdf | https://iris.who.int/server/api/core/bitstreams/b437749a-43f7-472f-a6d9-42596e8ac0ae/content | 5.2M | 2026-09-15 | OK | medical |
| who_surgical_care_district_hospital.pdf | https://iris.who.int/server/api/core/bitstreams/ba36d3cb-2481-4eda-a613-20959eb3c0d2/content | 6.9M | 2026-09-15 | OK | medical |
| who_family_planning_global_handbook.pdf | https://iris.who.int/server/api/core/bitstreams/de000f17-3c66-492d-8b10-1a2bdac7e5c6/content | 2.6M | 2026-09-15 | OK | medical |
| who_imci_chart_booklet.pdf | https://iris.who.int/server/api/core/bitstreams/739f7127-02cc-437b-bcf8-9658eb2d4256/content | 873K | 2026-09-15 | OK | medical |
| fm_3-34.471_plumbing.pdf | https://archive.org/download/FM_3_34_471_P_2001/FM%203-34-471%20Plumbing%2C%20pipe%20fitting%2C%20and%20sewerage%20(2001).pdf | 3.4M | 2026-09-15 | OK | shelter |
| usfs_home_ignition_guide.pdf | https://research.fs.usda.gov/download/treesearch/43128.pdf | 896K | 2026-09-15 | OK | fire_safety |
| nfpa_wildfire_hiz_checklist.pdf | https://content.nfpa.org/-/media/Project/Storefront/Catalog/Files/Wildfire/WildfireHIZChecklist.pdf | 507K | 2026-09-15 | OK | fire_safety |
| nfpa_firewise_noncombustible_zone.pdf | https://www.nfpa.org/-/media/Project/Storefront/Catalog/Files/Firewise/Fact-sheets/FirewiseFactSheetsImmediateNoncombustibleZone.pdf | 500K | 2026-09-15 | OK | fire_safety |
| who_ipcs_poisoning_management.pdf | - | - | 2026-09-15 | FAIL (WHO IRIS blocks anon; correct handle unknown; no mirror found) | medical |
| paho_who_dead_bodies_disasters.pdf | - | - | 2026-09-15 | FAIL (PAHO blocks all anon access; no open mirror found) | medical |
| fema_are_you_ready_p-2064.pdf | - | - | 2026-09-15 | FAIL (fema.gov/ready.gov 403; govinfo.gov no item; archive.org offline at time of retry) | emergency_mgmt |
| cdc_cpsc_co_safety.pdf | - | - | 2026-09-15 | FAIL (cpsc.gov 403; cdc.gov 403; no open CDN mirror found) | fire_safety |
| nfpa_wildfire_rfwildfire_report.pdf | - | - | 2026-09-15 | FAIL (NFPA removed rfwildfire.pdf; new URL 404; login required for full report) | fire_safety |
| humanure_handbook_3rd_ed.pdf | - | - | 2026-09-15 | FAIL (humanurehandbook.com 404; archive.org item login-gated; no free mirror) | sanitation |
| where_there_is_no_psychiatrist.pdf | - | - | 2026-09-15 | FAIL (RCPsych paywall; Cambridge paywall; no open access version found) | medical |
| helping_babies_breathe_2nd_ed.pdf | - | - | 2026-09-15 | FAIL (AAP paywalled; helpingbabiesbreathe.org requires login; no open mirror) | medical |

## Remaining FAIL List (as of 2026-09-15)

- **who_ipcs_poisoning_management**: WHO IRIS anon-blocks all bitstream downloads; correct handle unclear (10665/37329 is wrong item); no open publisher mirror
- **paho_who_dead_bodies_disasters**: PAHO iris.paho.org blocks all anon API and bitstream access; no open mirror found
- **fema_are_you_ready_p-2064**: fema.gov and ready.gov return 403; govinfo.gov no matching package; archive.org CDX offline at retry time — worth re-trying archive.org CDX when it's back up
- **cdc_cpsc_co_safety**: cpsc.gov and cdc.gov both return 403 for all PDF paths tried; no open CDN available
- **nfpa_wildfire_rfwildfire_report**: NFPA removed the rfwildfire.pdf from all tested CDN paths; login/purchase required; 2 substitute NFPA wildfire PDFs obtained (HIZ checklist + Firewise fact sheet)
- **humanure_handbook_3rd_ed**: 3rd ed. not freely available; archive.org lending-gated; author site 404; no open copy found — the owner may need to purchase or request from author
- **where_there_is_no_psychiatrist**: RCPsych CR174 no longer at known URL; Cambridge paywall; no OA version via CORE or WHO
- **helping_babies_breathe_2nd_ed**: AAP distributes only via paid curriculum; helpingbabiesbreathe.org requires login; no institutional open-access copy found
[2026-09-14 22:33] REPLACED who_mhgap_intervention_guide_v2.pdf — prior copy was GREEK edition (wrong bitstream UUID); English v2.0 3.5MB verified via langcheck
[2026-09-14 22:40] WHO UUID-scrape audit (the owner caught Greek mhGAP): 4 of 7 WHO grabs were WRONG ITEMS/EDITIONS. Replaced with verified-correct: mhGAP v2 EN 3.5M, Surgical Care District Hospital 6.6M, IMCI Chart Booklet 1.3M, Family Planning Global Handbook 2018 ed 7.8M. Pocket Book/PFA/Drinking Water verified correct. Lesson: UUID scrape from who.int pages returns related-publication links too — ALWAYS verify title via pdftotext after download.

## Site Mirrors (wget, 2026-09-15) — library/mirrors/

| mirror | source | size | files | date | status | notes |
|---|---|---|---|---|---|---|
| nchfp/ | nchfp.uga.edu | 159M | 1317 | 2026-09-15 | DONE | Full site incl. GUIDE01-07 PDFs, factsheets, BWC/PC sp2025; wget exit 8 (a few 404s: links_home, search) |
| ready_gov/ | www.ready.gov | - | - | 2026-09-15 | IN PROGRESS | sequential runner step 2/7 |
| journeytoforever/ | journeytoforever.org | - | - | 2026-09-15 | QUEUED | step 3/7 |
| sheldonbrown/ | www.sheldonbrown.com | - | - | 2026-09-15 | QUEUED | step 4/7 |
| hesperian/ | en.hesperian.org/hhg (HealthWiki) | - | - | 2026-09-15 | QUEUED | step 5/7 — the owner pre-approved wget fallback for 3 email-gated titles |
| meshtastic_aredn/meshtastic_docs/ | meshtastic.org/docs | - | - | 2026-09-15 | QUEUED | step 6/7 |
| meshtastic_aredn/aredn_docs/ | docs.arednmesh.org | - | - | 2026-09-15 | QUEUED | step 6b/7 |
| meshtastic_aredn/releases/ | GitHub meshtastic/firmware latest + downloads.arednmesh.org 4.26.7.0 | - | - | 2026-09-15 | QUEUED | step 7/7 — esp32/esp32s3/esp32c3/nrf52840/rp2040 zips; AREDN ath79/ipq40xx/x86_64 common devices |
| USDA extension PDFs | state extension sites | - | - | 2026-09-15 | NEEDS-ENUMERATION | MASTER_LIST lists BUILD ~2GB but no specific PDFs enumerated; full-domain crawls skipped per plan |

Runner log: logs/mirrors.log; script: logs/run_mirrors_rest.sh

## TCCC / JTS Clinical Practice Guidelines (jts.health.mil) — 2026-09-16

| filename | source_url | size | date | status | category |
|---|---|---|---|---|---|
| DD_Form_1380_TCCC_Card.pdf | https://jts.health.mil/assets/docs/forms/DD_Form_1380_TCCC_Card.pdf | 462K | 2026-09-16 | VERIFIED | tccc |
| DD_Form_1380_TCCC_Card_Instructions.pdf | https://jts.health.mil/assets/docs/forms/DD_Form_1380_TCCC_Card_Instructions.pdf | 278K | 2026-09-16 | VERIFIED | tccc |
| Documentation_Requirements_Combat_Casualty_Care.pdf | https://jts.health.mil/assets/docs/cpgs/Documentation_Requirements_for_Combat_Casualty_Care_18_Sep_2020_ID11.pdf | 704K | 2026-09-16 | VERIFIED | tccc |
| CPG_Index.pdf | https://jts.health.mil/assets/docs/cpgs/CPG_Index.pdf | 1.3M | 2026-09-16 | VERIFIED | tccc |
| Prolonged_Casualty_Care_Guidelines.pdf | https://jts.health.mil/assets/docs/cpgs/Prolonged_Casualty_Care_Guidelines_21_Dec_2021_ID91.pdf | 12M | 2026-09-16 | VERIFIED | tccc |
| Prehospital_Blood_Transfusion.pdf | https://jts.health.mil/assets/docs/cpgs/Prehospital_Blood_Transfusion_30_Oct_2020_ID82.pdf | 578K | 2026-09-16 | VERIFIED | tccc |
| Airway_Management_in_Trauma.pdf | https://jts.health.mil/assets/docs/cpgs/Airway_Management_in_Trauma_28_Jan_2026_ID39.pdf | 1.9M | 2026-09-16 | VERIFIED | tccc |
| Hypothermia_Prevention_Treatment.pdf | https://jts.health.mil/assets/docs/cpgs/Hypothermia_Prevention_Treatment_07_Jun_2023_ID23.pdf | 1.3M | 2026-09-16 | VERIFIED | tccc |
| Damage_Control_Resuscitation.pdf | https://jts.health.mil/assets/docs/cpgs/Damage_Control_Resuscitation_12_Jul_2019_ID18.pdf | 1.0M | 2026-09-16 | VERIFIED | tccc |
| Wartime_Thoracic_Injury.pdf | https://jts.health.mil/assets/docs/cpgs/Wartime_Thoracic_Injury_26_Dec_2018_ID74.pdf | 1.1M | 2026-09-16 | VERIFIED | tccc |
| War_Wounds_Debridement_and_Irrigation.pdf | https://jts.health.mil/assets/docs/cpgs/War_Wounds_Debridement_and_Irrigation_27_Sep_2021_ID31.pdf | 590K | 2026-09-16 | VERIFIED | tccc |
| Burn_Care.pdf | https://jts.health.mil/assets/docs/cpgs/Burn_Care_CPG_10_June_2025_ID12_v1.3.pdf | 2.8M | 2026-09-16 | VERIFIED | tccc |
| Vascular_Injury.pdf | https://jts.health.mil/assets/docs/cpgs/Vascular_Injury_09_Apr_2025_ID46_v1.2.pdf | 2.8M | 2026-09-16 | VERIFIED | tccc |
| En_Route_Care_Patient_Packaging.pdf | https://jts.health.mil/assets/docs/cpgs/En_Route_Care_Patient_Packaging_21_Aug_2024_ID97_v1.2.pdf | 1.3M | 2026-09-16 | VERIFIED | tccc |
| Extremity_Compartment_Syndrome_Fasciotomy.pdf | https://jts.health.mil/assets/docs/cpgs/Extremity_Compartment_Syndrome_and_Fasciotomy_ID17_21_May_2026.pdf | 1.6M | 2026-09-16 | VERIFIED | tccc |
| TBI_Traumatic_Brain_Injury_PFC.pdf | https://jts.health.mil/assets/docs/cpgs/Traumatic_Brain_Injury_PFC_06_Dec_2017_ID63.pdf | 1.3M | 2026-09-16 | VERIFIED | tccc |
| High_Bilateral_Amputations_Blast_Injury.pdf | https://jts.health.mil/assets/docs/cpgs/High_Bilateral_Amputations_Dismounted_Complex_Blast_Injury_05_Aug_2024_ID22_v1.2.pdf | 1.8M | 2026-09-16 | VERIFIED | tccc |
| Wound_Management_PFC.pdf | https://jts.health.mil/assets/docs/cpgs/Wound_Management_PFC_24_Jul_2017_ID62.pdf | 2.6M | 2026-09-16 | VERIFIED | tccc |

NOT FOUND on jts.health.mil (paywalled to deployedmedicine.com login):
- TCCC Guidelines full PDF (medical personnel) — jts.health.mil/index.cfm/committees/cotccc/guidelines links to deployedmedicine.com/market/11/content/40
- TCCC Quick Reference Guide — links to deployedmedicine.com/market/11/content/87
- TCCC Handbook — not referenced anywhere on jts.health.mil
- Role-based curriculum skill cards (ASM/CLS/CMC/CPP) — curriculum page redirects to deployedmedicine.com/instructors (login required)
[2026-09-16 11:53:43] DONE TCCC_Guidelines_2024-01-25.pdf via archive.org (deployedmedicine gate bypassed; ed. 25 Jan 2024 — verify against deployedmedicine for newer ed. when convenient)
[2026-09-16 11:54:00] DONE TCCC_Guidelines_2024-01-25.pdf 291K title-verified via archive.org (deployedmedicine login not needed for core doc)
[2026-09-16 12:05] INTEGRITY PASS (main): 0 undersized ZIMs; 0 undersized ISOs; all 33 ZIM magic headers OK (5a494d04); all CD3WD ISO file-headers OK; Geofabrik us-latest.osm.pbf md5 VERIFIED (9621db59...); langcheck clean (only known NOTEXT: 1982 SF medical scan). 3 tiny PDFs inside Survivor Library bulk (2 slide-rule images legit, 1 suspect 1956 NBC scan 2.6KB — bulk-dump quality, noted). Title audit of ~110 curated PDFs delegated to agent → title_audit.md.
[2026-09-16 12:08:53] TITLE-AUDIT FIXES: renamed icrc_first_aid_armed_conflicts (was mislabeled army_combat_medic_handbook), atp_4-02.10_theater_hospitalization (was mislabeled tc_4-02.1), tm_9-237_welding (was tc_); moved 2 misfiled Hesperian PDFs to own folders; deleted usfs_home_ignition_guide (was a 1968 elm-disease paper). Re-downloads delegated: real USFS HIZ guide, real medevac ATP, real IMCI chart booklet, better FM 5-34.
[2026-09-16 12:41:07] AUDIT-FIX ROUND 2: fm_4-02.2_medical_evacuation.pdf (renamed from atp_ — never renumbered), who_imci_chart_booklet.pdf 2008 chart ed (43pp, IRIS-metadata verified; pdftotext blind due to font encoding — KNOWN OK), fm_5-34 replaced with readable 2003 re-OCR (shelter/). USFS HIZ guide: no accessible copy exists; nfpa_wildfire_hiz_checklist.pdf covers — item CLOSED.
[2026-09-16 13:06:32] SURVIVOR LIBRARY COMPLETE: 7448/7448 PDFs, 113G (final file needed %5B bracket encoding). CD3WD12 105/105.
