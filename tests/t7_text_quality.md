# T7a: text quality of 200 random docs/ PDFs, pages 1-3 (read_document)

Deterministic metric (the haiku judge's two passes disagreed, 77% vs 34% OK, and its table was incomplete, so it is not used): share of whitespace tokens that contain a 3+ letter run and no stray symbols. OK >= 0.70, NOISY 0.50-0.70, GARBLED < 0.50, BLANK < 80 chars. Pages 1-3 of scanned books are often plates/covers, so GARBLED here means 'front matter unreadable', not 'book unreadable'.

| verdict | n |
|---|---|
| GARBLED | 8 |
| NOISY | 32 |
| OK | 160 |

| verdict | clean-token ratio | tokens | path | first 70 chars |
|---|---|---|---|---|
| GARBLED | 0.42 | 152 | `docs/survivor_library/SurvivalLibrary/library/Conduct of Life/the_matter_of_manner_1863.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| GARBLED | 0.44 | 145 | `docs/survivor_library/SurvivalLibrary/library/Economics/outlines_of_economic_theory_1899.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| GARBLED | 0.45 | 146 | `docs/survivor_library/SurvivalLibrary/library/Musical Instruments/primitive_percussion_instruments_for_modern_use_1938.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| GARBLED | 0.47 | 146 | `docs/survivor_library/SurvivalLibrary/library/Livestock-Cattle/essays_on_the_soiling_of_cattle_1862.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| GARBLED | 0.48 | 136 | `docs/survivor_library/SurvivalLibrary/library/Home Economics/clever_cooking_vol_1_1896.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| GARBLED | 0.49 | 135 | `docs/survivor_library/SurvivalLibrary/library/Smithing/the_tinsmiths_helper_and_pattern_book_1901.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| GARBLED | 0.49 | 169 | `docs/survivor_library/SurvivalLibrary/library/Leisure-Whist/whist_and_duplicate_whist_1900.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| GARBLED | 0.49 | 138 | `docs/survivor_library/SurvivalLibrary/library/Boy Scout Manuals/indian_scout_talks-a_guide_for_boy_scouts_and_campfire_girls_1914.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.55 | 117 | `docs/survivor_library/SurvivalLibrary/library/Veterinary/guide_and_protection_for_stock_owners_1879.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.57 | 157 | `docs/survivor_library/SurvivalLibrary/library/Weaving/practical_loom_fixing_1917.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.62 | 150 | `docs/survivor_library/SurvivalLibrary/library/Teaching-Readers/the_new_mcguffey_5th_reader_1901.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.62 | 143 | `docs/survivor_library/SurvivalLibrary/library/Silk Culture/history_of_the_discovery_in_california_of_a_native_silk_worm_1887.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.62 | 106 | `docs/survivor_library/SurvivalLibrary/library/Mechanical Drawing/the_practice_of_mechanical_drawing_for_self_instruction_1895.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.63 | 177 | `docs/survivor_library/SurvivalLibrary/library/Papermaking/chapters_on_papermaking_vol_5_1908.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.64 | 129 | `docs/survivor_library/SurvivalLibrary/library/Farming/cyclopedia_of_american_agriculture_vol_2-1909.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.64 | 124 | `docs/survivor_library/SurvivalLibrary/library/Airships/spherical_ballooning-some_of_the_requirements_1917.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.64 | 102 | `docs/survivor_library/SurvivalLibrary/library/Encyclopedias/american_and_canadian_sportsmans_encyclopedia_1913.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.64 | 183 | `docs/survivor_library/SurvivalLibrary/library/Firearms Manuals/blueprints-ppsh41-yugo49-57-american180-browning1919.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.64 | 165 | `docs/survivor_library/SurvivalLibrary/library/Medical-Anesthesia/on_the_physiological_effects_of_sulphuric_ether_1850.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.64 | 160 | `docs/survivor_library/SurvivalLibrary/library/Sanitation/which-sanitation_and_sanatory_remedies_1892.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.65 | 167 | `docs/survivor_library/SurvivalLibrary/library/Chemistry/text_book_of_chemistry_for_nurses_and_students_of_home_economics_1920.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.66 | 174 | `docs/survivor_library/SurvivalLibrary/library/Sanitation/cyclopedia_of_heating_plumbing_and_sanitation_vol_4_1909.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.66 | 123 | `docs/survivor_library/SurvivalLibrary/library/Teaching-Readers/the_story_of_our_continent-a_reader_of_north_america_1893.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.66 | 138 | `docs/survivor_library/SurvivalLibrary/library/Fish Culture/fish_culture_compared_in_importance_with_agriculture_1872.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.66 | 97 | `docs/survivor_library/SurvivalLibrary/library/Knitting-Lace-Needlepoint/art_needlework_1891.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.66 | 101 | `docs/survivor_library/SurvivalLibrary/library/Teaching-Readers/texas_literature_reader_1916.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.67 | 116 | `docs/survivor_library/SurvivalLibrary/library/History-American/old_world_steps_to_american_history_1915.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.68 | 134 | `docs/survivor_library/SurvivalLibrary/library/Medical-Diagnostics/the_diagnosis_of_diseases_of_the_spinal_cord_1901.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.68 | 185 | `docs/survivor_library/SurvivalLibrary/library/Railroads/broke_down_what_i_should_do-1890.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.69 | 108 | `docs/survivor_library/SurvivalLibrary/library/Medical-Diagnostics/medical_diagnosis_for_the_use_of_practitioners_and_students_1909.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.69 | 153 | `docs/survivor_library/SurvivalLibrary/library/Encyclopedias/winstons_cumulative_loose_leaf_encyclopedia_vol_03_1918.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.69 | 93 | `docs/survivor_library/SurvivalLibrary/library/Economics/the_principles_of_economics_with_practical_problems_1904.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.69 | 138 | `docs/survivor_library/SurvivalLibrary/library/Botany/lessons_in_elementary_botany_for_secondary_schools_1896.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.69 | 129 | `docs/survivor_library/SurvivalLibrary/library/Beekeeping/australian_bee_lore_and_bee_culture_1912.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.69 | 171 | `docs/survivor_library/SurvivalLibrary/library/Firearms Manuals/imi_dessert_eagle_semi_automatic_handgun.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.69 | 110 | `docs/survivor_library/SurvivalLibrary/library/Medical-Diagnostics/elements_of_surgical_diagnosis_1884.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.69 | 124 | `docs/survivor_library/SurvivalLibrary/library/Medical-Diagnostics/practical_diagnosis-use_of_symptoms_and_signs_in_diagnosis_of_disease_1907.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.70 | 164 | `docs/survivor_library/SurvivalLibrary/library/Firearms Manuals/ruger_77_nm.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.70 | 119 | `docs/survivor_library/SurvivalLibrary/library/Surveying/the_principles_of_surveying_1960.pdf` | Everything in this folder is pre-2010 and kept for background/context  |
| NOISY | 0.70 | 163 | `docs/survivor_library/SurvivalLibrary/library/Steam Engines/the_steam_jacket_practically_considered_as_an_efficient_fuel_economiser_1895.pdf` | Everything in this folder is pre-2010 and kept for background/context  |

8 GARBLED/BLANK, 8 of them on historical shelves. Modern shelves: 0.
