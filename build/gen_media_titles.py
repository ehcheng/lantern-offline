#!/usr/bin/env python3
"""Display titles for the audio/video shelves -> data/media_titles.json {path: title}.
gen_index.resolve_titles() overlays this on every page (titles.json, shelf pages, audio.html, video.html).
FIXES #161 (red team 10-09 a4 W3/W4/N1): Prelinger rows were archive IDs ("DuckandC1951"), preschool rows were
file-name scraps ("rando", "time 24"), LibriVox tracks were "Fablesofaesop 038 aesop 64kb".

Sources, all on disk, no network:
- LibriVox: data/librivox_section_titles.json, the per-file titles from the archive.org metadata
  API for the 52 identifiers in download_librivox.sh (the same strings the ID3 tags carry where tags exist).
- Prelinger: PRELINGER below, copied from archive.org/metadata/<id> on 2026-10-09 (title, date, sound).
- Preschool (CD3WD discs 100212/100213): rules over the file name; WORDS expands the names the disc truncated.
- Khan Academy (FIXES #178, red team 10-10 a4 F2/F3): the lesson name after the disc stem and 3-digit sequence number,
  plus the series ("Basic Addition (Khan Academy: Arithmetic)"); video.html's greedy regex had cut "2008 2d"-style
  scraps. LibriVox rows carry "(Book by Author)" from README.md (a4 F1) and Walden its chapter names (a4 F4: neither
  the ID3 tags nor the archive metadata name them; WALDEN is the book's own table of contents).
Run: python3 build/gen_media_titles.py   then gen_index.py / gen_shelves.py pick it up.
"""
import json, os, re, sys
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = f"{BASE}/library"
OUT = os.environ.get("MEDIA_TITLES_OUT") or f"{BASE}/data/media_titles.json"  # MEDIA_TITLES_OUT: a dry run
SECTIONS = json.load(open(f"{BASE}/data/librivox_section_titles.json"))

def books():
    """slug -> "Title by Author" from the README table; LibriVox edition notes "(Version 4)" dropped, "(KJV)" spelt out"""
    out = {}
    for ln in open(f"{BASE}/data/library_notes/audio/librivox/README.md"):
        c = [x.strip() for x in ln.strip().strip("|").split("|")]
        if len(c) >= 6 and re.fullmatch(r"[a-z0-9_]+", c[0]) and c[0] != "Slug":
            t = re.sub(r"\s*\((Version|dramatic|\d{4} Edition)[^)]*\)", "", c[1]).replace(" (KJV)", ", King James Version")
            out[c[0]] = t if c[2] in ("Various", "Traditional") else f"{t} by {c[2]}"
    assert len(out) == 52, len(out)
    return out
BOOKS = books()

WALDEN = ["Economy", "Where I Lived, and What I Lived For", "Reading", "Sounds", "Solitude", "Visitors", "The Bean-Field",
          "The Village", "The Ponds", "Baker Farm", "Higher Laws", "Brute Neighbors", "House-Warming",
          "Former Inhabitants and Winter Visitors", "Winter Animals", "The Pond in Winter", "Spring", "Conclusion"]

# Khan Academy disc stems (CD3WD, 2011): the series each file name starts with, before the 3-digit lesson number
KHAN = {"math_01_arith": "Arithmetic", "math_02_dev_math": "Developmental math", "math_03_dev_math_2": "Developmental math 2",
        "math_04_pre_algebra": "Pre-algebra", "math_05_pre_algebra_wrkd_exampl_1_MTEL": "Pre-algebra worked examples, MTEL",
        "math_06_Brain_Teasers": "Brain teasers", "math_07_algebra_cr": "Algebra",
        "math_08_algebra_wrkd_exampl_1_cf_stds_test_algebra_I": "Algebra I worked examples, California Standards Test",
        "math_09_algebra_wrkd_exampl_2_ck12org": "Algebra worked examples, CK-12",
        "math_10_algebra_wrkd_exampl_3_cf_stds_test_algebra_2": "Algebra II worked examples, California Standards Test",
        "math_11_algebra_wrkd_exampl_4": "Algebra worked examples 4", "math_12_geometry_cr": "Geometry",
        "math_13_geometry_wrkd_exampl_1_cf_stds_test": "Geometry worked examples, California Standards Test",
        "math_14_Trigonometry": "Trigonometry", "ka_math_14_Trigonometry": "Trigonometry", "math_15_Probability": "Probability",
        "math_16_Statistics": "Statistics", "math_17_Precalculus": "Precalculus", "math_18_Calculus": "Calculus",
        "math_Test_Prep_GMAT_prblm_solving": "GMAT problem solving", "math_Test_Prep_IIT_JEEs": "IIT JEE test prep",
        "math_Test_Prep_sg_math": "Singapore Math", "": "Singapore Math", "Science_01_Biology": "Biology",
        "Science_02_Chemistry": "Chemistry", "Science_03_Physics": "Physics", "Science_05_cosmo_astronomy": "Cosmology and astronomy"}

# FIXES #186 (red team 10-11 a4 F2): file-name scraps the disc left in about 140 lesson names. Whole-name fixes first
# (the file name lost a minus sign, a slash or a caret), then the prefix and suffix rules in tidy_khan().
KHAN_FIX = {"Proof log a B log x B log x A": "Proof of the change-of-base rule for logarithms",
            "i as the Principal Root of 1 a little technical": "i as the Principal Root of -1 (a little technical)",
            "2 ln x x Antiderivative Example": "Antiderivative of 2^(ln x)/x, example",
            "range Variance Standard Deviation as Measures of Dispersion":
                "Range, Variance and Standard Deviation as Measures of Dispersion",
            "cf stds test algebra II": "California Standards Test: Algebra II, introduction",
            "Limit Examples w brain malfunction on first prob part 4": "Limit Examples part 4 (a slip on the first problem)",
            # red team 10-20 a4 F1 (example row): the file name's typo and run-on
            "Trig identies part 3 part 5 if you watch the proofs": "Trig identities part 3, part 5 if you count the proofs",
            # round 8 a4 W1 (#244): the file names dropped "=", "-", "/", "^" and the brackets, so the identity read wrong
            "Trig identities part 2 parr 4 if you watch the proofs": "Trig identities part 2, part 4 if you count the proofs",
            "Proof sin a+b cos a sin b + sin a cos b": "Proof: sin(a + b) = cos a sin b + sin a cos b",
            "Proof cos a+b cos a cos b sin a sin b": "Proof: cos(a + b) = cos a cos b - sin a sin b",
            "Proof log a + log b log ab": "Proof: log a + log b = log ab",
            "Proof lim sin x x": "Proof: lim (sin x)/x = 1 as x goes to 0",
            "Proof d dx x n": "Proof: d/dx x^n = n x^(n-1)",
            "Proof d dx sqrt x": "Proof: d/dx sqrt(x) = 1/(2 sqrt(x))",
            "Proof d dx ln x 1 x": "Proof: d/dx ln x = 1/x",
            "Proof d dx e x e x": "Proof: d/dx e^x = e^x"}
ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}

def tidy_khan(t):
    t = KHAN_FIX.get(t, t)
    t = re.sub(r"^U\d\d L\d T\d we\d ", "", t)                      # "U08 L2 T4 we3 Special Products" (CK-12 unit code)
    t = re.sub(r"^(?:cf stds test )?algebra(?: 2)? (?=[A-Za-z])", "", t)  # "algebra 2 Simplifying Polynomials": the series says it
    t = re.sub(r"^(?:ck12org|prblm solving) ", "", t)
    t = re.sub(r"^sg math ", "Singapore Math ", t)
    t = t.replace("prblm solving", "problem solving")
    t = re.sub(r"^MTEL math Practice Test (\d+) (\d+)$", r"MTEL maths practice test, questions \1 to \2", t)
    t = re.sub(r"free resp nr (\d+)\s*([a-d])?\.?$", r"free response, question \1\2", t)
    t = re.sub(r"free resp nr (\d+) (?:parts )?([a-d](?: [a-d])+)$",
               lambda m: f"free response, question {m[1]}, parts {', '.join(m[2].split())}", t)
    t = re.sub(r"\b(Calculus (?:AB|BC)) free", r"AP \1 free", t)
    t = re.sub(r"\s*(?:new )?HD(?: [Vv]ersion)?$", "", t)           # "Introduction to Ratios new HD version"
    t = re.sub(r"\bpt (I{1,3}|IV|V)\b", lambda m: f"part {ROMAN[m[1]]}", t)
    t = re.sub(r"\bpart(\d)", r"part \1", t)
    t = re.sub(r"(?<=[a-z])(\d+)$", r" \1", t)                      # "Polynomials1"
    t = re.sub(r"\bL Hopital s\b", "L'Hôpital's", t)
    t = re.sub(r"\b([A-Z][a-z]+) s\b", r"\1's", t)                  # "Heron s Formula", "Earth s core"
    return t if t.startswith("i as ") else t[:1].upper() + t[1:]  # the imaginary unit stays lower case

# round 9 a4 W1 (#256, #244): the disc ships these files twice under two names (same decoded-audio md5, same length,
# a4_dup.log; transcripts in redteam_20261026_a4.md). The second name is a lesson the box does not hold, so the row is
# labelled with what plays ("..., second copy") and hidden from the lists, which keep the original once.
SAME = {"math_18_Calculus_008_Proof_lim_sin_x_x.mp4": "math_18_Calculus_007_Squeeze_Theorem.mp4",
        "math_16_Statistics_030_Confidence_Interval_1.mp4": "math_16_Statistics_029_Sampling_Distribution_Example_Problem.mp4",
        "math_16_Statistics_004_Statistics_Sample_Variance.mp4": "math_16_Statistics_002_Statistics_Sample_vs._Population_Mean.mp4",
        "math_Test_Prep_IIT_JEEs_019_IIT_JEE_Symmetric_and_Skew_Symmetric_Matrices.mp4":
            "math_Test_Prep_IIT_JEEs_018_IIT_JEE_Integral_with_Binomial_Expansion.mp4",
        "math_02_dev_math_061_Multiplying_Fractions_Word_Problem.mp4": "math_02_dev_math_060_Multiplying_Fractions_and_Mixed_Numbers.mp4",
        "math_02_dev_math_085_Comparing_Decimals_4.mp4": "math_02_dev_math_082_Comparing_Decimals.mp4",
        "math_02_dev_math_145_Identity_property_of_1_second_example.mp4": "math_02_dev_math_033_Identity_Property_of_1.mp4",
        "math_09_algebra_wrkd_exampl_2_ck12org_104_Adding_Rational_Expressions_Example_3.mp4":
            "math_09_algebra_wrkd_exampl_2_ck12org_103_Adding_Rational_Expressions_Example_2.mp4",
        "math_13_geometry_wrkd_exampl_1_cf_stds_test_006_CA_Geometry_More_on_congruent_and_similar_triangles.mp4":
            "math_13_geometry_wrkd_exampl_1_cf_stds_test_005_CA_Geometry_Similar_Triangles_2.mp4",
        "Science_03_Physics_128_Magnetism_9_Electric_Motors.mp4": "Science_03_Physics_127_Magnetism_8.mp4",
        "math_18_Calculus_016_Calculus_Derivatives_1_(new_1).mp4": "math_18_Calculus_016_Calculus_Derivatives_1.mp4",
        # round 10 a4 F2 (#275): same decoded-audio md5 and length as lessons 43 and 44 (275.4 s, 196.8 s), same board on a
        # 5-frame contact sheet; "old" is not an older recording
        "math_02_dev_math_150_Order_of_Operations_1.mp4": "math_02_dev_math_043_Order_of_Operations.mp4",
        "math_02_dev_math_151_Order_of_Operations_2_old.mp4": "math_02_dev_math_044_Order_of_Operations_2.mp4"}

def khan(rel):
    d, fn = rel.rsplit("/", 1)
    if fn in SAME:
        assert os.path.exists(f"{LIB}/{d}/{SAME[fn]}"), rel
        return khan(f"{d}/{SAME[fn]}").replace(" (Khan Academy: ", ", second copy (Khan Academy: ", 1)
    stem = re.sub(r"\.mp4$", "", fn, flags=re.I)
    if stem.endswith("_titles"):  # 31 s silent disc title card, one per science disc; hidden from the lists (hide: keys)
        return f"Science title card ({'junior high' if '_JHS_' in rel else 'high school'}, silent)"
    m = re.match(r"^(.*?)_?(\d{3})_(.+)$", stem)  # lazy: the FIRST 3-digit group is the lesson number, a year stays in the title
    assert m and m[1] in KHAN, rel
    t = re.sub(r"\bpt (\d)", r"part \1", m[3].replace("_", " ")).strip()
    return f"{tidy_khan(t)} (Khan Academy: {KHAN[m[1]]})"

# archive.org metadata, 2026-10-09. "silent" = the archive copy has no audible soundtrack (0994: max -68 dB on the
# 294 MB master too, and the archive's own ASR transcript is 0 bytes; 201293 and 0790 are intertitle films).
PRELINGER = {
    "0169_Woodworker_The_E01724_10_24_17_24": "The Woodworker (1940, longer cut)",
    "0220_Golden_Harvest_Fifty_Years_of_Calpak_Progress_M06690_00_01_01_00": "Golden Harvest: Fifty Years of Calpak Progress (1950s, fruit and vegetable canning)",
    "0230_Pick_of_the_Pod_01_18_48_00-0037": "Pick of the Pod (1939, pea farming and canning)",
    "0555_Master_Hands_18_27_28_00": "Master Hands (1936, car factory: foundry, forging, assembly)",
    "0790_Maintenance_of_Roads_08_15_00_28": "Maintenance of Roads (late 1920s, silent)",
    # FIXES #208 (red team 10-16 a4 W1): this reel is Part Five only; its title card at 50 s reads "PART FIVE / TRANSPORTING
    # THE INJURED" (stretchers, the four-handed seat, the chair carry), so the label says so, like its Part 2 sibling.
    "0994_Emergency_First_Aid_A_Study_in_Motion_Pictures_to_Aid_Civil_Def_01_00_42_04": "Emergency First Aid, Part 5: Transporting the Injured (1942, silent film: the archive copy has no soundtrack)",
    "201293_Emergency_First_Aid_P2_Bandaging": "Emergency First Aid, Part 2: Bandaging Wounds and Burns (1942, silent film with title cards)",
    # FIXES #197 (a4 N1): the film's own title card says "in the interests of civilian defense" (Ohio Bell); it is a WWII
    # air-raid film (incendiary bombs, no atomic attack), so it gets a plain description rather than the atomic-film tag.
    # FIXES #208 (red team 10-16 a4 W2), judged from the frames (fix_k8 report): enemy bombers overhead and an incendiary bomb
    # flaring in a family's attic, with children in the scenes. No injuries are shown, but the threat (an air attack on your
    # own home) is the one the atomic films are tagged for, and the film sits on the kids page's "Old videos" tile.
    "6139_Ready_on_the_Home_Front_01_22_01_29": "Ready on the Home Front (1940s, wartime civil defence: air-raid warnings and fighting incendiary bombs; bombers and a burning bomb may frighten young children)",
    # D11 = A (10-11): tag, do not remove. The three atomic-attack films carry "may frighten young children".
    "AtomicAl1951": "Atomic Alert (1951, civil defence for schoolchildren; may frighten young children)",
    "Automoti1940": "Automotive Service (1940, car repair trade)",
    "Chickeno1948": "The Chicken of Tomorrow (1948, poultry farming)",
    "DuckandC1951": "Duck and Cover (1951, Bert the Turtle civil defence film; may frighten young children)",
    "FoodforF1943": "Food for Fighters (1943, wartime nutrition)",
    "FromtheG1954": "From the Ground Up (1954, soil and farming; a Nutrilite promotional film)",
    "Looktoth1953": "Look to the Land (1953, soil conservation)",
    "ShakeHan1970": "Shake Hands with Danger (1970s, earthmoving-equipment safety; staged accidents may frighten children)",
    "Survival1951": "Survival Under Atomic Attack (1951, civil defence; may frighten young children)",
    "TimeSave1936": "Time Savers for House Makers (1936, laundry starch advertisement)",
    "victory_garden": "Victory Gardens (1940s, growing vegetables at home)",
    "Woodwork1940": "The Woodworker (1940, carpentry and cabinetmaking)",
}

# the NTSC disc truncates file names at 10 characters after the catalogue number
WORDS = {"flashlig": "flashlight", "toothbru": "toothbrush", "vegetabl": "vegetables", "cauliflowe": "cauliflower",
         "electricdr": "electric drill", "sewingmach": "sewing machine", "washingmac": "washing machine",
         "wheelbarro": "wheelbarrow", "toiletpape": "toilet paper", "bananatree": "banana tree", "cookingpot": "cooking pot",
         "creditcard": "credit card", "friedegg": "fried egg", "icecream": "ice cream", "petrolpump": "petrol pump",
         "policecar": "police car", "racingcar": "racing car", "sparkplug": "spark plug", "streetlamp": "street lamp",
         "woodscrew": "wood screw", "woodstove": "wood stove", "schoolbag": "school bag", "lollypop": "lollipop",
         "toilet_s": "toilet (squat)", "tv": "TV", "footballer": "footballer", "ladybird": "ladybird"}
NOISE = {"dvdp", "pal", "ntsc", "ed", "presch", "video", "sch", "txt", "text", "voic", "voice", "v", "n", "nt", "nv",
         "tnv", "ntnv", "tv", "ntv", "tlv", "ntnvnn", "nts", "lv", "late", "vo", "voi", "no", "read", "words", "count",
         "tttime", "time", "test", "random", "rando", "ran", "all", "az", "a", "z", "1s", "2s", "3s", "4s", "1sec",
         "2sec", "3secs", "4secs", "10s", "10sec", "secs", "sec", "page", "display", "pag", "nr", "hr", "12hr", "24hr",
         "12", "24", "1st", "2nd", "addition", "table", "alice", "in", "wonderland", "ch", "zzz", "3", "bears",
         "stories", "sample", "three", "short", "medium", "long"}

# D11 = A (tag, do not remove). FIXES #197 (red team 10-13 a4 F1): the pictures also play inside the compilations and
# random tests. Checked frame by frame (fix_j5_scan.py, fix_j5_ocr.sh, report redteam_20261013_fix_j5.md): the AK-style
# rifle ("gun") is in both "All the short words" and in all 14 "Words: random test" clips (the two page-display clips
# as a thumbnail); the soldier silhouette aiming a rifle is in both "All the medium words" and in every random test.
# "All the long words" and the letter clips (a separate 26-picture set) have neither.
RIFLE = "shows a rifle"
GUN_WORDS = {"gun": RIFLE, "soldier": "shows a soldier aiming a rifle"}
GUN_SIZES = {"short": RIFLE, "medium": GUN_WORDS["soldier"]}

def tagged(v, tag):
    return f"{v}; {tag}" if v else tag

def voice(s):
    """'tnv' text no voice / 'ntnv' / 'tv' / 'ntv' / 'tlv' late voice, from the file name or the folder."""
    s = s.lower().replace(" ", "")  # the NTSC folder "no_text_no_ voice" has a stray space (FIXES #208, a4 N2)
    if re.search(r"(^|_)(ntnvnn|ntnv|no_text_no_ ?voice)(_|$)", s) or ("nt_nv" in s) or ("no_text" in s and "no_voice" in s):
        return "no text, no voice"
    if re.search(r"(^|_)(tnv|text_no_voice)(_|$)", s) or ("_nv" in s and "_nt" in s) or "no_voice" in s or "no_v" in s:
        return "no voice"
    if re.search(r"(^|_)(tlv|late_voice|late)(_|$)", s) or "late_vo" in s:
        return "late voice"
    if re.search(r"(^|_)(ntv|voice_no_text)(_|$)", s):
        return "voice, no text"
    if re.search(r"(^|_)(tv|voice_and_text|voice)(_|$)", s) or "_voice" in s:
        return "voice and text"
    return ""

PANELS = {"1": "lowercase", "2": "capital", "3": "picture", "4": "word"}

def preschool(rel):
    parts = rel.split("/")
    stem = re.sub(r"\.mp4$", "", parts[-1], flags=re.I)
    folder = "/".join(parts[1:-1]).lower()
    s = re.sub(r"^ed_sch_presch_", "", stem)
    s = re.sub(r"_dvdp_pal.*$", "", s)
    s = re.sub(r"_ntsc$", "", s)
    disc = "PAL" if parts[0].startswith("100212") else "NTSC"
    v = voice(folder) or voice(s)  # folder first: "paint_nv" would read as "nt_nv"
    if not v and disc == "NTSC" and "random_test" in folder:
        v = "no voice"  # FIXES #208 (a4 N2): all 16 NTSC random tests have no audio stream (ffprobe, fix_k8_media.py)
    if stem == "title":
        return f"Disc title card ({disc} disc, silent)"
    if "3_bears" in rel:  # FIXES #186 (a4 F3): 165140 has a narrated AAC track (-25.5 dB), 165150 has no audio stream
        return f"The Story of the Three Bears (68 second sample, {'with narration' if '165140' in s else 'no sound'})"
    m = re.search(r"alice_(\d+)", s)
    if m:
        return f"Alice in Wonderland, chapter {int(m[1])}"
    if "/a_z/" in folder:
        # round 7 a4 W2: every clip is the whole alphabet; they differ only in which of the four panels show. The digits
        # in the name are those panels (frames checked, fix_m6_media.py): 1 lowercase, 2 capital, 3 picture, 4 word.
        # The disc's clip number ("part N") is no order, so the label names the panels instead.
        if "26_all" in s or "all_26" in s:
            return f"Letters A to Z, all 26 on one screen ({v})"
        n = re.search(r"read_az_t[a-z]+_([1-4]+)_\d|read_az_\d_([1-4]+)_|_a_z_([1-4]+)(?:_|$)", s)
        k = next(x for x in n.groups() if x) if n else ""
        what = ", ".join(PANELS[c] for c in k) + (" only" if len(k) == 1 else "")
        return f"Letters A to Z: {what} ({v})" if k else f"Letters A to Z ({v})"
    if "/words/" in folder:
        if "page_display" in s or s.endswith("_4_pag"):
            # FIXES #208 (a4 N2): not a test; a screen recording of a file window scrolling the word-picture folder
            return f"Words: the word pictures in a file window, not a test, {disc} disc ({tagged(v, RIFLE)})"
        if "random_test" in folder:
            k = re.search(r"test_all_(\d)", s)  # NTSC names are truncated to "rando": the set number comes from main()
            tag = f" {k[1]}" if k else ""
            v = tagged(v, RIFLE)  # FIXES #197: all 14 cycle the 233-picture set, the rifle and the soldier included
            return f"Words: random test{tag} ({v})"
        size = next((x for x in ("short", "medium", "long") if x in folder), "")
        m = re.search(r"_\d{6}_(.+)$", s)
        if m and "read_all" not in s:
            w = m[1]
            w = re.sub(r"_(nv|n|nt|nts)$", "", w)
            w = re.sub(r"_(nv|n|nt|nts)$", "", w)
            w = WORDS.get(w, w).replace("_", " ")
            if w in GUN_WORDS:  # D11 = A: tag, do not remove
                v = tagged(v, GUN_WORDS[w])
            return f"Word: {w} ({size} word, {v})" if v else f"Word: {w} ({size} word)"
        if size in GUN_SIZES:  # FIXES #197: the compilation plays the tagged word clip's picture too
            v = tagged(v, GUN_SIZES[size])
        return f"All the {size} words ({v})" if v else f"All the {size} words"
    if "/count/" in folder:
        if "addition" in s:
            return f"Counting: addition ({v})"
        if "table" in s:
            m = re.search(r"table_0?(\d)", s)
            return f"Counting: times table {m[1]} ({v})" if m else f"Counting: times table ({v})"
        down = "100_0" in s
        rnd = "random" in folder or "test" in s or "_nr" in s
        head = "Counting 100 down to 0" if down else "Counting 0 to 100"
        if rnd:
            k = re.search(r"(1st|2nd)", s)
            head = f"Counting: random numbers{' (' + k[1] + ')' if k else ''}"
        return f"{head} ({v})" if v else head
    if "tell_the_time" in folder:
        clock = "24-hour clock" if "24" in folder else "12-hour clock"
        tail = re.sub(r"^.*?(12|24)hr?_?", "", re.sub(r"_\d{6}_", "_", s))
        mins = re.findall(r"(?<!\d)(00|0|15|30|45)(?!\d)", tail)
        mins = [("00" if x == "0" else x) for x in mins]
        if "random" in folder or "test" in s or "144" in s:
            what = "random test"
        elif len(mins) >= 3:
            what = "every quarter hour"
        elif len(mins) == 1:
            what = "on the hour" if mins[0] == "00" else f"at :{mins[0]}"
        else:
            what = ""  # truncated NTSC names ("time_24"): say nothing rather than guess
        head = f"Telling the time, {clock}" + (f": {what}" if what else "")
        return f"{head} ({v})" if v else head
    return ""

# red team 10-20 a4 N3: typos in the archive's section titles (Treasure Island ch. 2 and 5, as the book prints them)
SECTION_FIX = {"Black Dogg ": "Black Dog ", "Blnd Man": "Blind Man"}

def librivox(name):
    t = SECTIONS.get(name, "")
    for a, b in SECTION_FIX.items():
        t = t.replace(a, b)
    t = re.sub(r"^walden_c(\d+)(?: part (\d+))?$",
               lambda m: f"Chapter {int(m[1])}: {WALDEN[int(m[1]) - 1]}" + (f", part {int(m[2])}" if m[2] else ""), t)
    core = re.sub(r"^\d{1,3}\s*[-:.]?\s*", "", t).strip()
    if not core:  # "01" (Jane Eyre): the archive gives only the number
        m = re.search(r"_(\d{1,3})_", name)
        return f"Part {int(m[1])}" if m else t
    # FIXES #186 (a4 F5): Twenty Thousand Leagues restarts its chapter numbers in Part II (files _1-NN, _2-NN)
    m = re.search(r"_([12])-\d\d_", name)
    c = re.match(r"^(\d+): (.+)$", core)
    if m and c:
        return f"Part {'I' * int(m[1])}, chapter {int(c[1])}: {c[2]}"
    return core

# FIXES #186 (a4 F1/F4/F5): headings and hidden rows for the pages. Three non-path key kinds ride in the same file; gen_index
# ignores them (it only looks up file paths). gen_shelves renders them (H2):
#   "group:<folder>"           heading for one video.html group (the folder holding the files, as groupOf() in video.html)
#   "shelfgroup:<shelf>/<dir>" heading for one top-level group on the _app/shelf/video_*.html pages (group_title())
#   "hide:<path>"              a silent disc title card: leave it out of the video lists (left out of the title search too: gen_index, round 10)
PRE_GROUP = {"100212_PRESCHOOL": "PAL disc", "100213_PRESCHOOL_NTSC_READ": "NTSC disc", "dvd_player": "", "read": "Reading",
             "___a_z": "voice and text", "a_z": "Letters A to Z", "a_z_lv_late_voice": "late voice",
             "a_z_nv_no_voice": "no voice", "words": "Words", "words_random_test": "random test",
             "words_nv_no_voice": "no voice", "short": "short words", "medium": "medium words", "long": "long words",
             "count": "Counting", "voice_and_text": "voice and text", "voice_no_text": "voice, no text",
             "text_no_voice": "text, no voice", "no_text_no_voice": "no text, no voice", "no_text_no_ voice": "no text, no voice",
             "random_test": "random test", "tell_the_time": "Telling the time", "12_hour_system": "12-hour clock",
             "24_hour_system": "24-hour clock", "voice": "voice and text", "random_test_12_hour": "random test, 12-hour clock",
             "z_alice_in_wonderland": "Alice in Wonderland", "zzz_3_bears_stories_sample": "The Three Bears, story sample"}
SHELF_GROUP = {
    "video/khan_academy/1101_PRIMARY_MATH": "Primary maths: arithmetic and developmental maths",
    "video/khan_academy/1103_JHS_MATH03": "Junior high maths: developmental maths and pre-algebra",
    "video/khan_academy/1106_JHS_ALGEBRA": "Junior high algebra and brain teasers",
    "video/khan_academy/1108_JHS_MATH08": "Junior high maths: Singapore Math, worked examples, developmental maths",
    "video/khan_academy/1109_JHS_MATH09_ALGEBRA": "Junior high algebra: CK-12 worked examples",
    "video/khan_academy/1111_JHS_MATH11_ALGEBRA": "Junior high algebra: worked examples, set 4",
    "video/khan_academy/1112_JHS_MATH12_GEOMETRY": "Junior high geometry",
    "video/khan_academy/1115_HS_TRI_PROB_STATS": "High school trigonometry, probability and statistics",
    "video/khan_academy/1116_HS_STATS": "High school statistics",
    "video/khan_academy/1117_HS_PRECALC": "High school precalculus and IIT JEE test prep",
    "video/khan_academy/1118_HS_CALC": "High school calculus, part 1",
    "video/khan_academy/1124_HS_CALC2": "High school calculus, part 2",
    "video/khan_academy/1148_JHS_SCIENCE": "Junior high science: biology, chemistry, physics, astronomy",
    "video/khan_academy/1149_HS_SCIENCE": "High school science: biology, chemistry, physics, astronomy",
    "video/preschool/100212_PRESCHOOL": "Preschool clips, PAL disc: letters, words, counting, telling the time, Alice in Wonderland",
    "video/preschool/100213_PRESCHOOL_NTSC_READ": "Preschool clips, NTSC disc: letters, one word per clip, counting, telling the time, the Three Bears"}

def runs(ns):
    """[1, 2, 3, 7] -> "1 to 3 and 7" (a two-number run is written "4, 5")"""
    ns, out = sorted(set(ns)), []
    for x in ns:
        if out and x == out[-1][1] + 1:
            out[-1][1] = x
        else:
            out.append([x, x])
    parts = [f"{a}" if a == b else f"{a}, {b}" if b == a + 1 else f"{a} to {b}" for a, b in out]
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]

def lesson_span(d, h, heads, khan_dirs):
    """red team 10-20 a4 N4: "lessons 1 to 153" while 113, 116, 119, 123 and 124 sit in another folder. A span names a
    lesson only if this folder holds it or no folder does (a gap in the disc); otherwise list the folder's runs."""
    mine = {x for _, x in khan_dirs[d]}
    a, b = min(mine), max(mine)
    elsewhere = {x for e, hh in heads.items() if hh == h and e != d for _, x in khan_dirs[e]} & set(range(a, b + 1))
    if a == b:
        return f"lesson {a}"
    if not elsewhere:
        return f"lessons {a} to {b}"
    if len(elsewhere) <= 6:
        e = sorted(elsewhere)
        return f"lessons {a} to {b} except {', '.join(map(str, e[:-1]))} and {e[-1]}" if len(e) > 1 else f"lessons {a} to {b} except {e[0]}"
    return "lessons " + runs(x for x in range(a, b + 1) if x not in elsewhere)

def extra_keys(out):
    ex, khan_dirs = {}, {}
    for p, t in sorted(out.items()):
        if t.startswith(("Disc title card", "Science title card")) or os.path.basename(p) in SAME:
            ex[f"hide:{p}"] = f"hidden from the lists: {t}"  # unique value: the b5 sweep gates on no repeated value
            if not os.path.basename(p) in SAME:  # a second copy keeps its lesson number in the folder's span
                continue
        d = os.path.dirname(p)
        if d.startswith("video/preschool/"):
            labs = ["Preschool clips"]
            for x in d.split("/")[2:]:
                lab = PRE_GROUP.get(x, PRE_GROUP.get(x.strip("_"), x.strip("_").replace("_", " ")))
                if lab and lab != labs[-1]:  # "Words › Words", "Letters A to Z › Letters A to Z" (a4 F5)
                    labs.append(lab)
            ex[f"group:{d}"] = " › ".join(labs)
        elif d.startswith("video/khan_academy/"):
            khan_dirs.setdefault(d, []).append((re.search(r"\(Khan Academy: ([^)]*)\)", t)[1],
                                                int(re.match(r"^.*?_?(\d{3})_", os.path.basename(p))[1])))
    ex["group:video/prelinger"] = "Old educational films (1920s to 1970s)"
    heads = {}
    for d, rows in khan_dirs.items():
        series = [s for s, _ in Counter(s for s, _ in rows).most_common()]
        if "SCIENCE" in d:
            heads[d] = f"{'Junior high' if '_JHS_' in d else 'High school'} science: " + ", ".join(s.lower() for s in series)
        else:
            heads[d] = " · ".join(series)
    n = Counter(heads.values())
    for d, h in heads.items():
        if n[h] > 1:  # "Developmental math" runs over four discs: say which lessons this folder holds
            h += ", " + lesson_span(d, h, heads, khan_dirs)
        ex[f"group:{d}"] = f"Khan Academy › {h}"
    top = {"/".join(p.split("/")[:3]) for p in out if p.startswith(("video/khan_academy/", "video/preschool/"))}
    # a disc folder without a name fails; a named disc a build did not fetch is just left out
    assert top <= set(SHELF_GROUP), ("disc folders with no shelfgroup name", top - set(SHELF_GROUP))
    ex.update({f"shelfgroup:{k}": v for k, v in SHELF_GROUP.items() if k in top})
    for kind in ("group:", "shelfgroup:"):
        vals = [v for k, v in ex.items() if k.startswith(kind)]
        assert len(vals) == len(set(vals)), ("duplicate headings", kind, [v for v, c in Counter(vals).items() if c > 1])
        assert not [v for v in vals if re.search(r"\b\d{4,}\b|_|MB\b|\bJHS\b|\bMATH\d", v)], "disc code in a heading"
    return ex

def main():
    out = {}
    for dp, _, fn in os.walk(f"{LIB}/audio/librivox"):
        # section titles repeat across books ("Chapter 02" x4): suffix "(Book by Author)" from the README, E3 style, so
        # check_titles' duplicate gate holds, a search hit names the book, and audio.html can read the album heading off
        # the end of any row. Aesop has two different fables called "The Cock and the Fox": the repeat gets ", second"
        # BEFORE the parenthetical so it stays the last thing on the row.
        seen = {}
        for f in sorted(fn):
            if f.endswith(".mp3"):
                rel = os.path.relpath(os.path.join(dp, f), LIB)
                t = librivox(f)
                n = seen[t.lower()] = seen.get(t.lower(), 0) + 1
                if n > 1:
                    t += ", " + ["second", "third", "fourth"][n - 2]
                out[rel] = f"{t} ({BOOKS[os.path.basename(dp)]})"
    for dp, _, fn in os.walk(f"{LIB}/video/prelinger"):
        for f in fn:
            if f.endswith(".mp4"):
                out[f"video/prelinger/{f}"] = PRELINGER.get(f[:-4], "")
    for dp, _, fn in os.walk(f"{LIB}/video/khan_academy"):
        for f in fn:
            if f.endswith(".mp4"):
                rel = os.path.relpath(os.path.join(dp, f), LIB)
                out[rel] = khan(rel)
    for dp, _, fn in os.walk(f"{LIB}/video/preschool"):
        for f in fn:
            if f.endswith(".mp4"):
                rel = os.path.relpath(os.path.join(dp, f), LIB)
                out[rel] = preschool(rel[len("video/preschool/"):])
    # identical labels inside one folder get a running number (six NTSC "time_24" clips are told apart only by id)
    seen = {}
    for p in sorted(out):
        seen.setdefault((os.path.dirname(p), out[p].lower()), []).append(p)  # #186: "intuition"/"Intuition" twins too
    for ps in seen.values():
        if len(ps) > 1:
            for i, p in enumerate(ps, 1):
                # a Khan twin (an old and an HD recording) says "version" and keeps "(Khan Academy: …)" last for video.html
                w = "version" if p.startswith("video/khan_academy/") else "set"
                # and an NTSC random test keeps its rifle tag last: "Words: random test, set 2 (no voice; shows a rifle)" (#197, #208)
                out[p] = re.sub(r"( \((?:Khan Academy: [^)]*|[^)]*shows a rifle)\))?$", lambda m: f", {w} {i}" + (m[1] or ""),
                                out[p], count=1)
    empty = [p for p, t in out.items() if not t]
    assert not empty, f"no title for {empty[:5]}"
    # the PAL and NTSC preschool discs carry the same programmes: a shared label gets its disc so no two paths share a title
    from collections import Counter
    n = Counter(t.lower() for t in out.values())
    for rel, t in out.items():
        if n[t.lower()] > 1 and rel.startswith("video/preschool/"):
            out[rel] = f"{t}, {'PAL' if rel.split('/')[2].startswith('100212') else 'NTSC'} disc"
    # the same programme can sit twice on one disc (two folders): add the folder, then a running number as the last resort
    n = Counter(t.lower() for t in out.values())
    for rel, t in out.items():
        if n[t.lower()] > 1:
            out[rel] = f"{t} ({rel.split('/')[-2].strip('_').replace('_', ' ')})"
    seen = Counter()
    for rel in sorted(out):
        k = out[rel].lower(); seen[k] += 1
        if seen[k] > 1:
            out[rel] = f"{out[rel]} ({seen[k]})"
    for rel in out:  # a4 W1: a second copy names its original as finally labelled ("Calculus Derivatives 1, version 2")
        d, fn = rel.rsplit("/", 1)
        if fn in SAME:
            out[rel] = out[f"{d}/{SAME[fn]}"].replace(" (Khan Academy: ", ", second copy (Khan Academy: ", 1)
    dup = [t for t, k in Counter(t.lower() for t in out.values()).items() if k > 1]
    assert not dup, ("duplicate media titles", dup[:5])
    ex = extra_keys(out)
    print(f"{len(out)} media titles + {len(ex)} group/shelfgroup/hide keys -> {OUT}")
    out.update(ex)
    json.dump(dict(sorted(out.items())), open(OUT, "w"), indent=1, ensure_ascii=False)

if __name__ == "__main__":
    assert runs([1, 2, 3, 7]) == "1 to 3 and 7" and runs([4, 5]) == "4, 5" and runs([9]) == "9"
    pre = "100212_PRESCHOOL/dvd_player/_read/a_z/"
    assert preschool(pre + "a_z_lv_late_voice_/read_az_tlv_134_3_dvdp_pal_ed_presch_video.mp4") == \
        "Letters A to Z: lowercase, picture, word (late voice)"
    assert preschool(pre + "___a_z/read_az_6_1_voice_dvdp_pal_ed_presch_video.mp4") == "Letters A to Z: lowercase only (voice and text)"
    assert preschool("100213_PRESCHOOL_NTSC_READ/dvd_player_/__read/a_z/a_z_lv_late_voice_/"
                     "ed_sch_presch_read_a_z_lv_late_voice_160330_4_a_z_4_late_vo.mp4") == "Letters A to Z: word only (late voice)"
    main()
