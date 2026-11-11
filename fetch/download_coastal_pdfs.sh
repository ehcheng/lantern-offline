#!/usr/bin/env bash
# Download and hard-verify coastal foraging reference PDFs.
# Verification: %PDF header + >100KB + pdftotext first-page topic match.
# Logs to logs/coastal_pdfs.log
ROOT=$(cd "$(dirname "$0")/.." && pwd)

set -uo pipefail

OUTDIR="$ROOT/library/docs/foraging_coastal"
LOG="$ROOT/logs/coastal_pdfs.log"

mkdir -p "$OUTDIR"
mkdir -p "$(dirname "$LOG")"

log() { echo "$*" | tee -a "$LOG"; }
ts()  { date -u "+%Y-%m-%dT%H:%M:%SZ"; }

log "=== download_coastal_pdfs.sh $(ts) ==="

# Hard verification: PDF header + size > 100KB + pdftotext first-page keyword match
verify_pdf() {
    local path="$1"; shift
    local keywords=("$@")
    # Header check
    if ! head -c 4 "$path" 2>/dev/null | grep -q "%PDF"; then
        log "  [FAIL-header] not a PDF: $path"
        return 1
    fi
    # Size check
    local size
    size=$(wc -c < "$path" 2>/dev/null || echo 0)
    if (( size < 102400 )); then
        log "  [FAIL-size] only ${size} bytes: $path"
        return 1
    fi
    # Topic check via pdftotext
    if command -v pdftotext &>/dev/null; then
        local text
        text=$(pdftotext -f 1 -l 3 "$path" - 2>/dev/null | tr '[:upper:]' '[:lower:]')
        local matched=0
        for kw in "${keywords[@]}"; do
            if echo "$text" | grep -q "$kw"; then
                matched=1
                break
            fi
        done
        if (( matched == 0 )); then
            log "  [FAIL-topic] keywords (${keywords[*]}) not found in first 3 pages: $path"
            return 1
        fi
    else
        log "  [WARN] pdftotext not found — skipping topic check"
    fi
    log "  [VERIFY-OK] $(wc -c < "$path") bytes — $path"
    return 0
}

try_download() {
    local url="$1"
    local dest="$2"
    # Try wget first (handles redirects well), fall back to curl
    if command -v wget &>/dev/null; then
        wget -q --timeout=60 --tries=2 -O "$dest" "$url" 2>>"$LOG" && return 0
    fi
    curl -sL --max-time 60 --retry 2 -o "$dest" "$url" 2>>"$LOG" && return 0
    return 1
}

# ── DOC 1: Biotoxin / PSP + domoic acid ──────────────────────────────────────
log ""
log "--- [1/4] Biotoxin: PSP + domoic acid ---"

BIOTOXIN_DEST="$OUTDIR/cdph_marine_biotoxins.pdf"
BIOTOXIN_OK=0

if [[ -f "$BIOTOXIN_DEST" ]]; then
    if verify_pdf "$BIOTOXIN_DEST" "shellfish" "biotoxin" "paralytic" "domoic"; then
        log "  [CACHED-OK] $BIOTOXIN_DEST"
        BIOTOXIN_OK=1
    else
        rm -f "$BIOTOXIN_DEST"
    fi
fi

if (( BIOTOXIN_OK == 0 )); then
    # Try CDPH Marine Biotoxin FAQ / fact sheets
    BIOTOXIN_URLS=(
        # CDPH environmental health fact sheet (direct PDF known path)
        "https://www.cdph.ca.gov/Programs/CEH/DRSEM/CDPH%20Document%20Library/EnvironmentalHealth/MarineAndFreshwaterSafety/shellfish-marine-biotoxin-shellfish-safety.pdf"
        # NOAA HAB explainer PDF
        "https://oceanservice.noaa.gov/hazards/hab/media/hab-fact-sheet.pdf"
        # Washington DOH PSP fact sheet
        "https://doh.wa.gov/sites/default/files/legacy/Documents/Pubs/332-013.pdf"
        # CDPH shellfish safety info sheet
        "https://www.cdph.ca.gov/Programs/CEH/DRSEM/CDPH%20Document%20Library/EnvironmentalHealth/MarineAndFreshwaterSafety/PoisoningFact_Sheet.pdf"
    )
    for url in "${BIOTOXIN_URLS[@]}"; do
        log "  Trying: $url"
        tmp="$OUTDIR/.tmp_biotoxin.pdf"
        if try_download "$url" "$tmp"; then
            if verify_pdf "$tmp" "shellfish" "paralytic" "biotoxin" "domoic" "psp" "poisoning"; then
                mv "$tmp" "$BIOTOXIN_DEST"
                log "  [OK] Saved: $BIOTOXIN_DEST"
                BIOTOXIN_OK=1
                break
            else
                log "  [REJECTED] $url"
            fi
        else
            log "  [DOWNLOAD-FAIL] $url"
        fi
        rm -f "$tmp"
        sleep 2
    done
    if (( BIOTOXIN_OK == 0 )); then
        log "  [NOT-FOUND] No biotoxin PDF verified — manual download needed"
    fi
fi

# ── DOC 2: CDFW Ocean Sport Fishing Regulations ───────────────────────────────
log ""
log "--- [2/4] CDFW Ocean Sport Fishing Regulations ---"

CDFW_DEST="$OUTDIR/cdfw_ocean_sport_fishing_regs.pdf"
CDFW_OK=0

if [[ -f "$CDFW_DEST" ]]; then
    if verify_pdf "$CDFW_DEST" "fishing" "california" "limit" "license" "season" "regulation"; then
        log "  [CACHED-OK] $CDFW_DEST"
        CDFW_OK=1
    else
        rm -f "$CDFW_DEST"
    fi
fi

if (( CDFW_OK == 0 )); then
    CDFW_URLS=(
        # CDFW direct current ocean regs booklet (year varies in URL; try several)
        "https://nrm.dfg.ca.gov/FileHandler.ashx?DocumentID=224152"
        "https://nrm.dfg.ca.gov/FileHandler.ashx?DocumentID=213572"
        "https://nrm.dfg.ca.gov/FileHandler.ashx?DocumentID=205752"
        "https://nrm.dfg.ca.gov/FileHandler.ashx?DocumentID=198832"
        # Stable page redirects
        "https://www.wildlife.ca.gov/Regulations/Sport-Fishing/Ocean"
    )
    for url in "${CDFW_URLS[@]}"; do
        log "  Trying: $url"
        tmp="$OUTDIR/.tmp_cdfw.pdf"
        if try_download "$url" "$tmp"; then
            if verify_pdf "$tmp" "fishing" "california" "limit" "license" "regulation" "halibut" "salmon" "rockfish" "dungeness"; then
                mv "$tmp" "$CDFW_DEST"
                log "  [OK] Saved: $CDFW_DEST"
                CDFW_OK=1
                break
            else
                log "  [REJECTED] $url"
            fi
        else
            log "  [DOWNLOAD-FAIL] $url"
        fi
        rm -f "$tmp"
        sleep 2
    done
    if (( CDFW_OK == 0 )); then
        log "  [NOT-FOUND] CDFW regs PDF not auto-retrieved (CDFW uses session/JS redirects). Manual: https://www.wildlife.ca.gov/Regulations/Sport-Fishing/Ocean"
    fi
fi

# ── DOC 3: Shellfish ID Guide (.gov/.edu) ─────────────────────────────────────
log ""
log "--- [3/4] Shellfish ID Guide (Sea Grant / .gov/.edu) ---"

SHELLID_DEST="$OUTDIR/shellfish_id_guide.pdf"
SHELLID_OK=0

if [[ -f "$SHELLID_DEST" ]]; then
    if verify_pdf "$SHELLID_DEST" "shellfish" "clam" "oyster" "mussel" "identification"; then
        log "  [CACHED-OK] $SHELLID_DEST"
        SHELLID_OK=1
    else
        rm -f "$SHELLID_DEST"
    fi
fi

if (( SHELLID_OK == 0 )); then
    SHELLID_URLS=(
        # WA Sea Grant shellfish guide
        "https://wsg.washington.edu/wordpress/wp-content/uploads/2017/12/WSG-RecGuidebook_final.pdf"
        # NOAA Pacific Coast shellfish
        "https://www.fisheries.noaa.gov/s3/dam-migration/pacific_coast_shellfish_id.pdf"
        # California Sea Grant shellfish aquaculture/ID
        "https://caseagrant.ucsd.edu/sites/default/files/ShellfishGuidebook-LR.pdf"
        # Oregon Sea Grant coastal shellfish
        "https://seagrant.oregonstate.edu/sites/seagrant.oregonstate.edu/files/sgpubs/onlinepubs/g88001.pdf"
    )
    for url in "${SHELLID_URLS[@]}"; do
        log "  Trying: $url"
        tmp="$OUTDIR/.tmp_shellid.pdf"
        if try_download "$url" "$tmp"; then
            if verify_pdf "$tmp" "shellfish" "clam" "oyster" "mussel" "identification" "bivalve"; then
                mv "$tmp" "$SHELLID_DEST"
                log "  [OK] Saved: $SHELLID_DEST"
                SHELLID_OK=1
                break
            else
                log "  [REJECTED] $url"
            fi
        else
            log "  [DOWNLOAD-FAIL] $url"
        fi
        rm -f "$tmp"
        sleep 2
    done
    if (( SHELLID_OK == 0 )); then
        log "  [NOT-FOUND] No shellfish ID PDF verified"
    fi
fi

# ── DOC 4: Seaweed Harvesting/ID Guide ───────────────────────────────────────
log ""
log "--- [4/4] Seaweed Harvesting/ID Guide (.edu/Sea Grant) ---"

SEAWEED_DEST="$OUTDIR/seaweed_harvesting_guide.pdf"
SEAWEED_OK=0

if [[ -f "$SEAWEED_DEST" ]]; then
    if verify_pdf "$SEAWEED_DEST" "seaweed" "kelp" "algae" "harvest"; then
        log "  [CACHED-OK] $SEAWEED_DEST"
        SEAWEED_OK=1
    else
        rm -f "$SEAWEED_DEST"
    fi
fi

if (( SEAWEED_OK == 0 )); then
    SEAWEED_URLS=(
        # UCSC/MBARI seaweed guide
        "https://serc.carnegiescience.edu/sites/default/files/seaweed_identification_guide.pdf"
        # Oregon Sea Grant seaweed harvest
        "https://seagrant.oregonstate.edu/sites/seagrant.oregonstate.edu/files/sgpubs/onlinepubs/g88003.pdf"
        # Maine Sea Grant edible seaweed (widely linked educational PDF)
        "https://seagrant.umaine.edu/files/2020/01/SeaweedHarvestersHandbook.pdf"
        # WA Sea Grant seaweed
        "https://wsg.washington.edu/wordpress/wp-content/uploads/2020/01/seaweed-harvesting-guide.pdf"
    )
    for url in "${SEAWEED_URLS[@]}"; do
        log "  Trying: $url"
        tmp="$OUTDIR/.tmp_seaweed.pdf"
        if try_download "$url" "$tmp"; then
            if verify_pdf "$tmp" "seaweed" "kelp" "algae" "harvest" "intertidal" "marine"; then
                mv "$tmp" "$SEAWEED_DEST"
                log "  [OK] Saved: $SEAWEED_DEST"
                SEAWEED_OK=1
                break
            else
                log "  [REJECTED] $url"
            fi
        else
            log "  [DOWNLOAD-FAIL] $url"
        fi
        rm -f "$tmp"
        sleep 2
    done
    if (( SEAWEED_OK == 0 )); then
        log "  [NOT-FOUND] No seaweed guide PDF verified"
    fi
fi

# ── Summary ───────────────────────────────────────────────────────────────────
log ""
log "=== SUMMARY $(ts) ==="
log "DOC 1 biotoxin: $([ $BIOTOXIN_OK -eq 1 ] && echo OK || echo MISSING)"
log "DOC 2 CDFW regs: $([ $CDFW_OK -eq 1 ] && echo OK || echo MISSING)"
log "DOC 3 shellfish ID: $([ $SHELLID_OK -eq 1 ] && echo OK || echo MISSING)"
log "DOC 4 seaweed guide: $([ $SEAWEED_OK -eq 1 ] && echo OK || echo MISSING)"
log "Output dir: $OUTDIR"

# ── Write README.md ───────────────────────────────────────────────────────────
README="$OUTDIR/README.md"
log ""
log "Writing $README"

cat > "$README" << 'READMEOF'
# Coastal Foraging Reference Documents

> **Biotoxin closures are state-monitored — if the hotline is unreachable, treat May–October mussels as quarantined by default.**

California Biotoxin Hotline: 1-800-553-4133 (CA Dept of Public Health, Marine Biotoxin Monitoring Program)

## Documents

### cdph_marine_biotoxins.pdf
California Dept of Public Health marine biotoxin fact sheet covering paralytic shellfish poisoning (PSP) and domoic acid (amnesic shellfish poisoning). Explains closure triggers, symptoms, and safe harvesting windows. Download date: see log at logs/coastal_pdfs.log.

### cdfw_ocean_sport_fishing_regs.pdf
California Dept of Fish & Wildlife Ocean Sport Fishing Regulations booklet. Contains take limits, open seasons, size limits, and license requirements for shellfish and finfish. Verify against current year at: https://www.wildlife.ca.gov/Regulations/Sport-Fishing/Ocean

### shellfish_id_guide.pdf
Shellfish species identification guide from a Sea Grant or .gov/.edu source. Covers bivalve morphology, shell features, and common Pacific Coast species including mussels, clams, and oysters.

### seaweed_harvesting_guide.pdf
Seaweed harvesting and identification guide from a Sea Grant or .edu source. Covers edible species, harvest regulations, and safe preparation.

## Important Safety Notes

- PSP (paralytic shellfish poisoning) toxins are **not destroyed by cooking**. No visual, smell, or taste test can detect them.
- Domoic acid causes amnesic shellfish poisoning. Razor clams and anchovies concentrate it heavily.
- California closes harvesting based on routine monitoring — check closures at https://www.cdph.ca.gov/Programs/CEH/DRSEM/Pages/smb/default.aspx
- Dungeness crab: separate domoic acid closures apply to viscera — discard it, eat only the meat.
- Abalone: red abalone is **closed to sport fishing** statewide as of 2018 (do not harvest).
READMEOF

log "[README] Written: $README"
log "=== done ==="
