#!/usr/bin/env bash
# download_librivox.sh — Curated LibriVox audiobook downloader
# Idempotent: skips existing files >= 100 KiB with an MP3 header. Log: logs/librivox.log
# Never uses archive.org /compress/ endpoint. Lists real filenames via metadata API.
# Launch via: screen -dmS librivox bash fetch/download_librivox.sh
ROOT=$(cd "$(dirname "$0")/.." && pwd)
set -uo pipefail

BASE=$ROOT/library/audio/librivox
LOG=$ROOT/logs/librivox.log
# FIXES #161 (red team 10-09 a4 W1): the old 1 MiB floor deleted 37 real sections (short fables, intros,
# the last Oz chapter: 480 KB-1.04 MB at 64 kbps). A truncated download is caught by the header check instead.
MIN_BYTES=102400   # 100 KiB

# MP3 header: ID3v2 tag ("ID3") or an MPEG frame sync (0xFFE0 mask) in the first 2 bytes
mp3_header_ok() {
    local hex
    hex=$(head -c 3 "$1" 2>/dev/null | xxd -p)
    [[ $hex == 494433* || $hex =~ ^ff[ef] ]]
}

mkdir -p "$BASE"/{01_young_child,02_child,03_teen,04_adult,05_elder_comfort}
mkdir -p "$(dirname "$LOG")"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }

# Download one file with size gate and idempotent skip
dl_file() {
    local url="$1" dest="$2"
    local name
    name=$(basename "$dest")
    if [[ -f "$dest" ]]; then
        local sz
        sz=$(stat -f%z "$dest" 2>/dev/null || stat -c%s "$dest" 2>/dev/null || echo 0)
        if (( sz >= MIN_BYTES )) && mp3_header_ok "$dest"; then
            log "SKIP $name (${sz} bytes)"
            return 0
        else
            log "PARTIAL $name (${sz} bytes) — re-downloading"
            rm -f "$dest"
        fi
    fi
    log "DL $name"
    if curl -fsSL --retry 3 --retry-delay 5 --connect-timeout 30 --max-time 600 \
            -o "$dest" "$url" 2>>"$LOG"; then
        local sz
        sz=$(stat -f%z "$dest" 2>/dev/null || stat -c%s "$dest" 2>/dev/null || echo 0)
        if (( sz >= MIN_BYTES )) && mp3_header_ok "$dest"; then
            log "DONE $name (${sz} bytes)"
        else
            log "FAIL-SMALL-OR-BAD-HEADER $name (${sz} bytes) — removing"
            rm -f "$dest"
            return 1
        fi
    else
        log "FAIL $name (curl error)"
        rm -f "$dest"
        return 1
    fi
}

# Download all 64kb MP3s for an archive.org identifier into a directory.
# Falls back to all MP3s if no _64kb.mp3 files exist (some old recordings).
download_book() {
    local identifier="$1" dest_dir="$2" slug="$3"
    local book_dir="${dest_dir}/${slug}"
    mkdir -p "$book_dir"
    log "=== BEGIN $identifier -> $slug ==="

    # Fetch metadata
    local meta_url="https://archive.org/metadata/${identifier}"
    local meta_json
    if ! meta_json=$(curl -fsSL --retry 3 --connect-timeout 20 "$meta_url" 2>>"$LOG"); then
        log "FAIL metadata fetch for $identifier"
        return 1
    fi

    # Extract 64kb MP3 filenames (prefer _64kb.mp3; fallback to plain .mp3 if none)
    local filenames
    filenames=$(echo "$meta_json" | python3 -c "
import sys, json, urllib.parse
d = json.load(sys.stdin)
files = d.get('files', [])
names_64 = [f['name'] for f in files if f.get('name','').endswith('_64kb.mp3')]
names_all = [f['name'] for f in files if f.get('name','').endswith('.mp3')
             and not f.get('name','').endswith('_128kb.mp3')]
chosen = names_64 if names_64 else names_all
for n in chosen:
    print(urllib.parse.quote(n, safe=''))
" 2>>"$LOG")

    if [[ -z "$filenames" ]]; then
        log "WARN no MP3 files found for $identifier"
        return 1
    fi

    local count=0 ok=0
    while IFS= read -r encoded_name; do
        [[ -z "$encoded_name" ]] && continue
        local raw_name
        raw_name=$(python3 -c "import urllib.parse,sys; print(urllib.parse.unquote(sys.argv[1]))" "$encoded_name")
        local url="https://archive.org/download/${identifier}/${encoded_name}"
        local dest="${book_dir}/${raw_name}"
        (( count++ )) || true
        dl_file "$url" "$dest" && (( ok++ )) || true
    done <<< "$filenames"

    log "=== END $identifier: ${ok}/${count} files OK ==="
}

log "======================================"
log "download_librivox.sh START"
log "======================================"

# ─── 01_young_child ───────────────────────────────────────────────────────────
# Great Big Treasury of Beatrix Potter — solo narrator, 97MB @ 64kb
download_book "potter_treasury_librivox"                   "$BASE/01_young_child" "beatrix_potter_treasury"
# Fables of Aesop and Others — well-rated solo/group, 241MB @ 64kb
download_book "fables_of_aesop_2003_librivox"              "$BASE/01_young_child" "aesop_fables"
# The Real Mother Goose — solo, 53MB @ 64kb
download_book "real_mother_goose_ah_librivox"              "$BASE/01_young_child" "mother_goose"
# Just So Stories (Kipling) v1 solo, 112MB @ 64kb
download_book "just_so_stories_1004_librivox"              "$BASE/01_young_child" "just_so_stories"
# The Wonderful Wizard of Oz — version 1 solo, 103MB @ 64kb
download_book "wizard_of_oz"                               "$BASE/01_young_child" "wizard_of_oz"
# Winnie-the-Pooh v4 — solo, 70MB @ 64kb (PD since 2022, LibriVox recording exists)
download_book "winnie-the-pooh_v4_cb_2212_librivox"        "$BASE/01_young_child" "winnie_the_pooh"

# ─── 02_child ─────────────────────────────────────────────────────────────────
# Alice's Adventures in Wonderland v7 — solo, 87MB @ 64kb
download_book "alicesadventuresinwonderland_2005_librivox" "$BASE/02_child" "alice_in_wonderland"
# Peter Pan v2 — solo (shorter than Peter and Wendy expanded), 133MB @ 64kb
download_book "peterpan_0801_librivox"                     "$BASE/02_child" "peter_pan"
# The Jungle Book — solo, 149MB @ 64kb
download_book "thejunglebook_pc_librivox"                  "$BASE/02_child" "jungle_book"
# The Secret Garden — solo v2, 191MB @ 64kb
download_book "secret_garden_version2_librivox"            "$BASE/02_child" "secret_garden"
# Anne of Green Gables — dramatic reading (best available), 265MB @ 64kb
download_book "anneofgreengables_1102_librivox"            "$BASE/02_child" "anne_of_green_gables"
# Treasure Island — solo, 150MB @ 64kb
download_book "treasure_island_1307_librivox"              "$BASE/02_child" "treasure_island"
# The Adventures of Tom Sawyer v1 — solo, 186MB @ 64kb
download_book "tom_sawyer_librivox"                        "$BASE/02_child" "tom_sawyer"
# The Wind in the Willows — solo (ap), 190MB @ 64kb
download_book "wind_willows_ap_librivox"                   "$BASE/02_child" "wind_in_the_willows"
# Heidi — solo, 268MB @ 64kb
download_book "heidi_solo_librivox"                        "$BASE/02_child" "heidi"
# Black Beauty — solo, 172MB @ 64kb
download_book "blackbeauty_librivox"                       "$BASE/02_child" "black_beauty"
# The Swiss Family Robinson — solo, 352MB @ 64kb
download_book "swiss_family_robinson_librivox"             "$BASE/02_child" "swiss_family_robinson"
# Grimm's Fairy Stories — solo, 152MB @ 64kb
download_book "grimmsfairystories_2201_librivox"           "$BASE/02_child" "grimms_fairy_tales"
# Faery Tales from Hans Christian Andersen — solo, 438MB @ 64kb
download_book "faery_tales_andersen_1706_librivox"         "$BASE/02_child" "andersens_fairy_tales"

# ─── 03_teen ──────────────────────────────────────────────────────────────────
# Adventures of Huckleberry Finn v3 — solo, 311MB @ 64kb
download_book "adventures_huckleberryfinn_ver03_0904"      "$BASE/03_teen" "huckleberry_finn"
# The Call of the Wild v5 — solo, 101MB @ 64kb
download_book "callofthewild_5_2007_librivox"              "$BASE/03_teen" "call_of_the_wild"
# White Fang v2 — solo, 212MB @ 64kb
download_book "whitefang2_1010_librivox"                   "$BASE/03_teen" "white_fang"
# The Adventures of Sherlock Holmes v5 — solo, 264MB @ 64kb
download_book "the_adventures_of_sherlock_holmes_v5_1904_librivox" "$BASE/03_teen" "sherlock_holmes"
# Twenty Thousand Leagues Under the Sea — solo, 453MB @ 64kb
download_book "20000_leagues_under_the_seas_librivox"      "$BASE/03_teen" "twenty_thousand_leagues"
# Around the World in Eighty Days — dramatic reading v5, 177MB @ 64kb
download_book "aroundtheworldin80days_1505_librivox"       "$BASE/03_teen" "around_world_80_days"
# The Count of Monte Cristo — solo, 1368MB @ 64kb (large but complete)
download_book "countofmontecristo_1303_librivox"           "$BASE/03_teen" "count_of_monte_cristo"
# Jane Eyre — solo, 566MB @ 64kb
download_book "jane_eyre_librivox"                         "$BASE/03_teen" "jane_eyre"
# Frankenstein (1831 edition) — solo, 240MB @ 64kb
download_book "frankenstein1831_tac_librivox"              "$BASE/03_teen" "frankenstein"
# Dracula v4 — solo, 428MB @ 64kb
download_book "dracula_v4_1903_librivox"                   "$BASE/03_teen" "dracula"
# The Time Machine v3 — solo, 101MB @ 64kb
download_book "timemachine_sjm_librivox"                   "$BASE/03_teen" "time_machine"
# The War of the Worlds v4 — solo, 162MB @ 64kb
download_book "war_worlds_v4_an_1907_librivox"             "$BASE/03_teen" "war_of_the_worlds"
# Little Women — dramatic reading, 481MB @ 64kb
download_book "little_women_1101_librivox"                 "$BASE/03_teen" "little_women"

# ─── 04_adult ─────────────────────────────────────────────────────────────────
# Pride and Prejudice — dramatic reading, 329MB @ 64kb
download_book "prideandprejudice_1107_librivox"            "$BASE/04_adult" "pride_and_prejudice"
# Great Expectations — solo, 492MB @ 64kb
download_book "great_expectations_v2_1211_librivox"        "$BASE/04_adult" "great_expectations"
# A Tale of Two Cities v4 — solo, 370MB @ 64kb
download_book "tale_of_two_cities_version_4_1506_librivox" "$BASE/04_adult" "tale_of_two_cities"
# Meditations (Marcus Aurelius) — solo, 132MB @ 64kb
download_book "themeditationsofmarcusaurelius_1801_librivox" "$BASE/04_adult" "meditations_aurelius"
# The Art of War (Sun Tzu) v3 — solo, 37MB @ 64kb
download_book "artofwar3_pc_librivox"                      "$BASE/04_adult" "art_of_war"
# The Autobiography of Benjamin Franklin — solo, 200MB @ 64kb
download_book "autobiography_1912_librivox"                "$BASE/04_adult" "autobiography_franklin"
# Narrative of the Life of Frederick Douglass v2 — solo, 112MB @ 64kb
download_book "narrativeofthelife_1606_librivox"           "$BASE/04_adult" "narrative_douglass"
# Essays, First Series (Emerson) v2 — solo, 231MB @ 64kb
download_book "essaysfirstseries_1207_librivox"            "$BASE/04_adult" "essays_emerson_first_series"
# NOTE: Moby Dick (677MB), Crime & Punishment (546MB), Walden (329MB), Odyssey (296MB)
# budget expanded 09-16 (the owner: disk abundant) — re-added the 4 dropped titles:
download_book "moby_dick_librivox"                         "$BASE/04_adult" "moby_dick"
download_book "crime_punishment_1511_librivox"             "$BASE/04_adult" "crime_and_punishment"
download_book "walden_librivox"                            "$BASE/04_adult" "walden"
download_book "odyssey_2409_librivox"                      "$BASE/04_adult" "odyssey"

# ─── 05_elder_comfort ─────────────────────────────────────────────────────────
# A Christmas Carol — solo, 97MB @ 64kb
download_book "christmas_carol_1111_librivox"              "$BASE/05_elder_comfort" "christmas_carol"
# My Man Jeeves (Wodehouse) — solo, 143MB @ 64kb
download_book "my_man_jeeves_librivox"                     "$BASE/05_elder_comfort" "my_man_jeeves"
# Right Ho, Jeeves (Wodehouse) — solo, 218MB @ 64kb
download_book "right_ho_jeeves_librivox"                   "$BASE/05_elder_comfort" "right_ho_jeeves"
# O Henry: The Four Million — solo, 152MB @ 64kb
download_book "four_million_librivox"                      "$BASE/05_elder_comfort" "o_henry_four_million"
# O Henry: Cabbages and Kings — solo, 176MB @ 64kb
download_book "cabbageskings_1403_librivox"                "$BASE/05_elder_comfort" "o_henry_cabbages_and_kings"
# O Henry: Heart of the West — solo, 232MB @ 64kb
download_book "heartofthewest_1312_librivox"               "$BASE/05_elder_comfort" "o_henry_heart_of_west"
# The Importance of Being Earnest (Wilde) — solo, 63MB @ 64kb
download_book "being_earnest_librivox"                     "$BASE/05_elder_comfort" "importance_of_being_earnest"
# Psalms (KJV) — solo reading, 145MB @ 64kb
download_book "psalms_kjv_1202_librivox"                   "$BASE/05_elder_comfort" "psalms_kjv"

log "======================================"
log "download_librivox.sh COMPLETE"
log "======================================"
