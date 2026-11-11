# T7b: Group description judgment — 30 random shelf groups (second pass)

**Counts:** 24 MATCH, 0 VAGUE, 0 MISMATCH, 6 flagged for date range errors.

| Group Key | Verdict | Reason | Suggested Rewrite |
|-----------|---------|--------|-------------------|
| Livestock-Rabbits and Cavies | MATCH | Files 1857–1922 match rabbits/cavies topic and historical range | — |
| audio/librivox/03_teen/frankenstein | MATCH | Mary Shelley's Frankenstein audiobook chapters; plot summary accurate | — |
| Sliderules and Abacus | MATCH (flagged) | Files span 1847–2012, outliers (1847, 1962, 1965, 2012) bracket stated 1850–1950 range | "Calculating without electricity: slide rule and abacus instruction. Dates span 1847–2012." |
| docs/cd3wd/2015_highschool | MATCH | High-school subject ISO CDs from 2015 match description | — |
| mirrors/meshtastic_aredn | MATCH | Meshtastic firmware files (.zip, .json) match topic | — |
| docs/plant_id/rose_hips | MATCH | Plant ID photos, foraging tips, edibility notes align with description | — |
| tools/android | MATCH | Kiwix, Organic Maps, OsmAnd APK files match multi-app description (2 sentences) | — |
| docs/survivor_library/Papermaking | MATCH | PDFs 1855–1920 cover papermaking by hand and machine; historical suffix standard | — |
| maps/organicmaps | MATCH | US region .mwm files for Organic Maps offline navigation | — |
| docs/plant_id/lambsquarters | MATCH | Plant ID images, cultivation/cooking guidance match edible cooked plant description | — |
| docs/survivor_library/Airships | MATCH | PDFs 1885–1936 on balloons, dirigibles, aircraft; all within stated 1850–1950 range | — |
| docs/mit_ocw/8.04_quantum_physics | MATCH | Single MIT OCW course archive (8.04 Spring 2016) matches description | — |
| tools/llamafile | MATCH | Single executable binary for offline AI model inference | — |
| docs/survivor_library/Wood-Carpentry | MATCH | PDFs 1827–1920 cover carpentry, joinery, framing; historical suffix standard | — |
| docs/survivor_library/Tobacco | MATCH (flagged) | File "a_pipe_of_tobacco...1744" is 106-year outlier; files 1744–1909 | "Growing and curing tobacco. Historical scan, 1744–1950 (includes rare 1744 text)." |
| mirrors/hesperian | MATCH | Hesperian health guides in multiple languages (Amharic, Arabic, etc.) with HTML/assets | — |
| docs/survivor_library/Christmas | MATCH | Period Christmas stories, songs, crafts from 1872–1922; historical suffix standard | — |
| tools/whisper | MATCH | Whisper speech-to-text tool, C++ implementation, and GGML model weights | — |
| docs/plant_id/wild_ginger | MATCH | Plant ID images with detailed toxicity/health warning (3 sentences, justified) | — |
| docs/survivor_library/Wagon and Coach Building | MATCH (flagged) | File "a_treatise_on_carriages_vol_1_1796" is 54-year lower outlier; spans 1796–1966 | "Building wagons, carriages and wheels. Historical scan, 1796–1950." |
| maps/osmand | MATCH | OsmAnd offline navigation map files (.obf.zip) for US regions | — |
| audio/librivox/02_child/black_beauty | MATCH | Anna Sewell's Black Beauty audiobook chapters; plot summary accurate | — |
| docs/survivor_library/Boilermaker | MATCH | PDFs on steam boilers, riveting, plate work from 1873–1923; historical suffix standard | — |
| maps/topo_ca | MATCH | USGS topographic quad PDFs for California (terrain, trails, evacuation routes) | — |
| docs/survivor_library/Smithing | MATCH (flagged) | File "deformation_processing_stainless_steel_nasa_1966" is 16-year upper outlier; spans 1887–1966 | "Blacksmithing: forge, anvil, tool making, horseshoeing. Historical scan, mostly 1850–1966." |
| docs/cd3wd/2015_primary | MATCH | Primary/junior-high school subject ISO CDs (math, science, preschool) from 2015 | — |
| docs/survivor_library/Berries | MATCH (flagged) | File "floating_row_cover...1989" is 39-year upper outlier; spans 1854–1989 | "Growing small fruit: strawberries, raspberries, currants, grapes. Historical scan, mostly 1850–1989." |
| docs/cd3wd/2012_dvd | MATCH | CD3WD 2012 DVD images (ISO files) of full development-technology collection | — |
| docs/plant_id/wood_sorrel | MATCH | Plant ID photos with foraging guidance (edible, lemony, oxalate caution) | — |
| audio/librivox/02_child/secret_garden | MATCH | Frances Hodgson Burnett's The Secret Garden audiobook chapters; plot summary accurate | — |

**Assessment:**

Strong performance: all 30 descriptions fit their folder contents and file types. No VAGUE or MISMATCH verdicts. Six survivor_library groups show date-range ceiling/floor inconsistencies: Tobacco includes a 1744 text (106 years before the stated "mostly 1850–1950" lower bound), Wagon and Coach Building starts at 1796 (54 years early), Berries extends to 1989 (39 years beyond stated ceiling), Smithing to 1966 (16 years over), Sliderules to 2012 (well past both bounds), and Airships (actually within bounds at 1885–1936). These are not description errors per se, but rather floor/ceiling mismatches between the stated historical range and actual contents. Recommend updating the four worst offenders (Tobacco, Wagon, Berries, Smithing) to match actual file date ranges before next seal.
