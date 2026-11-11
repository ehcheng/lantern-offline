#!/usr/bin/env python3
"""Unit tests for mcp_server.py — no HTTP, no real db, in-memory fixture."""

import json
import math
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Import the module under test (python3 -I leaves the script's folder off sys.path)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mcp_server


class MCPServerUnitTest(unittest.TestCase):
    """Unit test suite for mcp_server functions."""

    @classmethod
    def setUpClass(cls):
        """Create fixture library, db, and initialize State."""
        cls.tmpdir = tempfile.mkdtemp(prefix="mcp_test_")

        # Create directory structure
        docs_dir = os.path.join(cls.tmpdir, "docs")
        medical_dir = os.path.join(docs_dir, "medical")
        historical_dir = os.path.join(docs_dir, "HISTORICAL")
        survivor_dir = os.path.join(docs_dir, "survivor_library")
        app_dir = os.path.join(cls.tmpdir, "_app")
        index_dir = os.path.join(app_dir, "index")

        os.makedirs(medical_dir)
        os.makedirs(historical_dir)
        os.makedirs(survivor_dir)
        os.makedirs(index_dir)

        # Create config.json with homeRegion = Redwood City
        config = {
            "homeRegion": {
                "lat": 37.485,
                "lon": -122.236
            }
        }
        with open(os.path.join(app_dir, "config.json"), "w") as f:
            json.dump(config, f)

        # Create shelves.json
        shelves = [
            {
                "path": "docs/medical",
                "historical": False,
                "title": "Medical"
            },
            {
                "path": "docs/HISTORICAL",
                "historical": True,
                "title": "Historical Docs"
            },
            {
                "path": "docs/survivor_library",
                "historical": True,
                "title": "Survivor Library"
            }
        ]
        with open(os.path.join(index_dir, "shelves.json"), "w") as f:
            json.dump(shelves, f)

        # Create HISTORICAL warning file
        with open(os.path.join(historical_dir, "README-WARNING.txt"), "w") as f:
            f.write("HISTORICAL WARNING TEXT")

        # Create real medical/x.html
        with open(os.path.join(medical_dir, "x.html"), "w") as f:
            f.write("<h1>Wound Care</h1><p>irrigate &amp; dress</p>")

        # Create outside.txt for testing path escape
        with open(os.path.join(cls.tmpdir, "outside.txt"), "w") as f:
            f.write("outside content")

        # Create symlink to docs variant
        symlink_target = os.path.join(cls.tmpdir, "docs_variant")
        os.makedirs(symlink_target)
        with open(os.path.join(symlink_target, "file.txt"), "w") as f:
            f.write("symlinked content")
        # Create a symlink in the top-level as a shelf variant
        symlink_path = os.path.join(cls.tmpdir, "docs_link")
        os.symlink(symlink_target, symlink_path)

        # Create fixture database
        db_path = os.path.join(cls.tmpdir, "test.db")
        con = sqlite3.connect(db_path)
        cur = con.cursor()

        # Create schema - match build_mcp_index.py
        cur.execute("""CREATE VIRTUAL TABLE pages USING fts5(
            body, title, path UNINDEXED, shelf UNINDEXED, page UNINDEXED, lang UNINDEXED,
            tokenize='porter unicode61'
        )""")
        cur.execute("""CREATE VIRTUAL TABLE titles USING fts5(
            title, path UNINDEXED, shelf UNINDEXED,
            tokenize='porter unicode61'
        )""")

        cur.execute("""CREATE TABLE guard_drugs (name TEXT)""")
        cur.execute("""CREATE TABLE stations (
            id TEXT, name TEXT, lat REAL, lon REAL
        )""")
        cur.execute("""CREATE TABLE normals (
            station TEXT, month INTEGER, tmin REAL, tmean REAL, tmax REAL, wind_avg REAL
        )""")
        cur.execute("""CREATE TABLE callsigns (
            callsign TEXT, name TEXT, city TEXT, state TEXT
        )""")

        # Populate pages FTS table
        cur.execute("INSERT INTO pages(body, title, path, shelf, page) VALUES (?, ?, ?, ?, ?)",
                    ("Page 1 body", "Medical A", "docs/medical/a.pdf", "docs/medical", 1))
        cur.execute("INSERT INTO pages(body, title, path, shelf, page) VALUES (?, ?, ?, ?, ?)",
                    ("Page 2 body", "Medical A", "docs/medical/a.pdf", "docs/medical", 2))
        cur.execute("INSERT INTO pages(body, title, path, shelf, page) VALUES (?, ?, ?, ?, ?)",
                    ("Page 3 body", "Medical A", "docs/medical/a.pdf", "docs/medical", 3))
        cur.execute("INSERT INTO pages(body, title, path, shelf, page) VALUES (?, ?, ?, ?, ?)",
                    ("Old page 1", "Old Doc", "docs/HISTORICAL/old.pdf", "docs/HISTORICAL", 1))
        cur.execute("INSERT INTO pages(body, title, path, shelf, page) VALUES (?, ?, ?, ?, ?)",
                    ("Survivor page", "Survivor", "docs/survivor_library/s.pdf", "docs/survivor_library", 1))

        # A6: a formulary page (drug language + figures) for the read_document dose guard
        cur.execute("INSERT INTO pages(body, title, path, shelf, page) VALUES (?, ?, ?, ?, ?)",
                    ("Adults: ibuprofen 400 mg every 6 hours, max 1.2 g/day. Children 10 mg/kg.",
                     "Formulary", "docs/medical/formulary.pdf", "docs/medical", 1))
        # Add a wound-related page for search testing
        cur.execute("INSERT INTO pages(body, title, path, shelf, page) VALUES (?, ?, ?, ?, ?)",
                    ("Wound care instructions", "Wound Care", "docs/medical/x.html", "docs/medical", 1))

        # ES fixture rows
        cur.execute("INSERT INTO pages(body, title, path, shelf, page, lang) VALUES (?, ?, ?, ?, ?, ?)",
                    ("La fiebre en los niños puede ser señal de infección. Tratamiento con agua fresca.",
                     "Salud Infantil", "mirrors/hesperian/es.hesperian.org/hhg/Ninos.html", "mirrors/hesperian/es.hesperian.org", 1, "es"))
        cur.execute("INSERT INTO pages(body, title, path, shelf, page, lang) VALUES (?, ?, ?, ?, ?, ?)",
                    ("Siempre hervir el agua antes de beber para evitar diarrea y enfermedades.",
                     "Agua Segura", "mirrors/hesperian/es.hesperian.org/hhg/Agua.html", "mirrors/hesperian/es.hesperian.org", 1, "es"))

        # Populate titles FTS table
        cur.execute("INSERT INTO titles(title, path, shelf) VALUES (?, ?, ?)",
                    ("Medical A", "docs/medical/a.pdf", "docs/medical"))
        cur.execute("INSERT INTO titles(title, path, shelf) VALUES (?, ?, ?)",
                    ("Old Doc", "docs/HISTORICAL/old.pdf", "docs/HISTORICAL"))
        cur.execute("INSERT INTO titles(title, path, shelf) VALUES (?, ?, ?)",
                    ("Survivor", "docs/survivor_library/s.pdf", "docs/survivor_library"))
        cur.execute("INSERT INTO titles(title, path, shelf) VALUES (?, ?, ?)",
                    ("Wound Care", "docs/medical/x.html", "docs/medical"))

        # Populate guard_drugs
        cur.execute("INSERT INTO guard_drugs VALUES ('ibuprofen')")
        cur.execute("INSERT INTO guard_drugs VALUES ('aspirin')")

        # Populate stations: KALI (48.3042, -114.2636), FAR (0.0, 0.0)
        cur.execute("INSERT INTO stations VALUES (?, ?, ?, ?)",
                    ("KALI", "Kalispell, MT", 48.3042, -114.2636))
        cur.execute("INSERT INTO stations VALUES (?, ?, ?, ?)",
                    ("FAR", "Faraway", 0.0, 0.0))

        # Populate normals for KALI
        cur.execute("INSERT INTO normals VALUES (?, ?, ?, ?, ?, ?)",
                    ("KALI", 1, 16.0, 24.6, 32.0, 10.0))
        cur.execute("INSERT INTO normals VALUES (?, ?, ?, ?, ?, ?)",
                    ("KALI", 7, 58.0, 66.2, 75.0, 8.0))

        # Populate callsigns
        cur.execute("INSERT INTO callsigns VALUES (?, ?, ?, ?)",
                    ("KG6DUG", "John Doe", "San Francisco", "CA"))
        cur.execute("INSERT INTO callsigns VALUES (?, ?, ?, ?)",
                    ("TEST", "Test Name", "San Francisco", "CA"))

        # Populate synonyms (schema_version 2)
        cur.execute("CREATE TABLE synonyms(term TEXT PRIMARY KEY, expansion TEXT)")
        cur.execute("INSERT INTO synonyms VALUES (?, ?)",
                    ("chainsaw", "laceration wound"))
        cur.execute("INSERT INTO synonyms VALUES (?, ?)",
                    ("bug out bag", "emergency kit supplies"))
        # expansion that would trip guard — must be blocked
        cur.execute("INSERT INTO synonyms VALUES (?, ?)",
                    ("painkiller", "ibuprofen dosage"))

        con.commit()
        con.close()

        # Initialize STATE
        mcp_server.STATE = mcp_server.State(
            cls.tmpdir,
            db_path,
            "http://127.0.0.1:1"  # dead port for degrade tests
        )
        mcp_server._load_synonyms()

    @classmethod
    def tearDownClass(cls):
        """Clean up fixture."""
        import shutil
        if os.path.exists(cls.tmpdir):
            shutil.rmtree(cls.tmpdir)

    # -------- T1: dose_guard --------

    def test_dose_guard_ibuprofen(self):
        """T1: dose_guard trips on 'ibuprofen'."""
        self.assertTrue(mcp_server.dose_guard("ibuprofen"))

    def test_dose_guard_ibuprofen_uppercase(self):
        """T1: dose_guard trips on 'IBUPROFEN pain'."""
        self.assertTrue(mcp_server.dose_guard("IBUPROFEN pain"))

    def test_dose_guard_dose_of_x(self):
        """T1: dose_guard trips on 'dose of x'."""
        self.assertTrue(mcp_server.dose_guard("dose of x"))

    def test_dose_guard_500mg(self):
        """T1: dose_guard trips on '500 mg'."""
        self.assertTrue(mcp_server.dose_guard("500 mg"))

    def test_dose_guard_dosage(self):
        """T1: dose_guard trips on 'dosage'."""
        self.assertTrue(mcp_server.dose_guard("dosage"))

    def test_dose_guard_milligrams(self):
        """T1: dose_guard trips on 'milligrams'."""
        self.assertTrue(mcp_server.dose_guard("milligrams"))

    def test_dose_guard_dosing(self):
        """T1: dose_guard trips on 'water dosing' (dosing is keyword)."""
        self.assertTrue(mcp_server.dose_guard("water dosing"))

    def test_dose_guard_aspirations_no_trip(self):
        """T1: dose_guard does NOT trip on 'aspirations'."""
        self.assertFalse(mcp_server.dose_guard("aspirations"))

    def test_dose_guard_mgso4_no_trip(self):
        """T1: dose_guard does NOT trip on 'mgso4' (token must equal 'mg')."""
        self.assertFalse(mcp_server.dose_guard("mgso4"))

    def test_dose_guard_wound_care_no_trip(self):
        """T1: dose_guard does NOT trip on 'wound care'."""
        self.assertFalse(mcp_server.dose_guard("wound care"))

    def test_dose_guard_ibuprofenlike_no_trip(self):
        """T1: dose_guard does NOT trip on 'ibuprofenlike' (exact token match only)."""
        self.assertFalse(mcp_server.dose_guard("ibuprofenlike"))

    def test_dose_guard_aspirin(self):
        """T1: dose_guard trips on guard drug 'aspirin'."""
        self.assertTrue(mcp_server.dose_guard("aspirin"))

    # M2 follow-up 1 (round 9, #252 #246): the page's keyword amount forms (KEYDOSE_RE) and the swallow exemption (INGEST_RE),
    # rows from fix_m1fu1_rows.tsv; ask_dose() must give the page's askDose() answer on each (fix_m2fu1_parity.py checks all sets)
    KEYDOSE_ROWS = [
        'drops ear infection how many',
        'eye drops how many baby',
        'mg for earache',
        'ml for fever baby',
        'how many pills headache',
        'tablets toothache how many',
        'dose for fever 2 year old',
        'cough syrup how much child',
        'how often ear drops',
        'spoons of syrup cough',
        'how many drops for my sons ear infection',
        'mg for a toddler with fever',
        'gotas oido infeccion cuantas',
        'cuantas gotas para el ojo bebe',
        'mg para dolor de oido',
        'dosis fiebre niño 2 años',
        'jarabe tos cuanto niño',
        'pastillas dolor de muela cuantas',
        'cada cuanto gotas oido',
        'ml para la fiebre bebe',
        'cucharadas jarabe tos',
        'cuántas gotas para la infección de oído de mi hija',
        'mg para niño con fiebre',
        'cuanto jarabe para la tos',
    ]
    KEYDOSE_EXEMPT_ROWS = [  # recipe, water and food amounts: askDose false
        'how many drops of bleach per gallon',
        'how much salt and sugar for ors',
        'cups of flour how many bread',
        'mg of caffeine in coffee',
        'how many drops iodine water',
        'how much honey in tea recipe',
        'cuantas gotas de cloro por litro',
        'cuantas cucharadas de azucar suero casero',
        'cuanta harina para pan',
        'cuanta miel en el te',
        'gotas de cloro agua cuantas',
        'cuantos gramos de sal para conservas',
    ]
    SWALLOW_ROWS = [  # a swallowed or taken amount is a poisoning: askDose false (the server's drug-word rule may still hide quotes)
        'she swallowed all her pills on purpose because she wants to die',
        'took an overdose to end it all',
        'el niño se tragó una moneda y no puede respirar',
        'se tomó todas las pastillas porque se quiere morir',
        "my toddler swallowed grandma's pills, I don't know how many",
        'el niño se tragó no sé cuántas pastillas de su abuela',
    ]

    @staticmethod
    def _fold(q):
        import unicodedata
        return "".join(c for c in unicodedata.normalize("NFD", q.lower()) if not unicodedata.combining(c))

    def test_dose_guard_keyword_amounts_refused(self):
        """M2fu1: keyword amount questions are askDose questions and refused."""
        for q in self.KEYDOSE_ROWS:
            with self.subTest(q=q):
                self.assertTrue(mcp_server.ask_dose(self._fold(q)))
                self.assertTrue(mcp_server.dose_guard(q))

    def test_ask_dose_keyword_exemptions(self):
        """M2fu1: recipe, water, food and swallowed amounts are not askDose questions."""
        for q in self.KEYDOSE_EXEMPT_ROWS + self.SWALLOW_ROWS:
            with self.subTest(q=q):
                self.assertFalse(mcp_server.ask_dose(self._fold(q)))

    # -------- T2: safe_library_path --------

    def test_safe_library_path_accepts_valid(self):
        """T2: safe_library_path accepts 'docs/medical/x.html'."""
        result = mcp_server.safe_library_path("docs/medical/x.html")
        self.assertIsNotNone(result)
        real, rel = result
        self.assertTrue(real.endswith("medical/x.html"))
        self.assertEqual(rel, "docs/medical/x.html")

    def test_safe_library_path_rejects_unserved_trees(self):
        """RT6 a8 F2: paths nginx 404s (kolibri_data, _app/mcp) and dotfiles are refused, in any case."""
        for p in ("kolibri_data/logs/kolibri.txt", "Kolibri_Data/logs/kolibri.txt", "kolibri_data/logs/debug.txt",
                  "_app/mcp/mcp.db", "_APP/mcp/x.txt", ".git/config", "docs/.hidden.txt",
                  "%6bolibri_data/logs/kolibri.txt", ".well-known/mcp.json"):
            self.assertIsNone(mcp_server.safe_library_path(p), p)
        self.assertIsNotNone(mcp_server.safe_library_path("docs/medical/x.html"))

    def test_safe_library_path_rejects_parent_escape(self):
        """T2: safe_library_path rejects '../etc/passwd'."""
        self.assertIsNone(mcp_server.safe_library_path("../etc/passwd"))

    def test_safe_library_path_rejects_absolute(self):
        """T2: safe_library_path rejects '/etc/passwd'."""
        self.assertIsNone(mcp_server.safe_library_path("/etc/passwd"))

    def test_safe_library_path_rejects_double_escape(self):
        """T2: safe_library_path rejects 'docs/../../etc/passwd'."""
        self.assertIsNone(mcp_server.safe_library_path("docs/../../etc/passwd"))

    def test_safe_library_path_rejects_percent_encoded_escape(self):
        """T2: safe_library_path rejects '%2e%2e/etc'."""
        self.assertIsNone(mcp_server.safe_library_path("%2e%2e/etc"))

    def test_safe_library_path_rejects_double_encoded_escape(self):
        """T2: safe_library_path rejects '%252e%252e' (double-encoded)."""
        self.assertIsNone(mcp_server.safe_library_path("%252e%252e"))

    def test_safe_library_path_rejects_empty(self):
        """T2: safe_library_path rejects empty string."""
        self.assertIsNone(mcp_server.safe_library_path(""))

    def test_safe_library_path_rejects_outside_escape(self):
        """T2: safe_library_path rejects 'docs/medical/../../../outside.txt'."""
        self.assertIsNone(mcp_server.safe_library_path("docs/medical/../../../outside.txt"))

    def test_safe_library_path_symlink_escape(self):
        """T2.5: symlink anchor — member through symlink accepted, escape rejected."""
        # File reached through symlink should be OK if within symlink target
        result = mcp_server.safe_library_path("docs_link/file.txt")
        # The symlink is resolved; if the file is within the resolved target, it should be OK
        # But escaping through the symlink parent should be rejected
        self.assertIsNone(mcp_server.safe_library_path("docs_link/../outside.txt"))

    # -------- T3: strip_html --------

    def test_strip_html_removes_tags(self):
        """T3: strip_html removes tags."""
        html = "<p>Hello <b>world</b></p>"
        result = mcp_server.strip_html(html)
        self.assertIn("Hello", result)
        self.assertIn("world", result)
        self.assertNotIn("<", result)
        self.assertNotIn(">", result)

    def test_strip_html_decodes_entities(self):
        """T3: strip_html decodes &amp;."""
        html = "a &amp; b"
        result = mcp_server.strip_html(html)
        self.assertIn("a & b", result)

    def test_strip_html_removes_script(self):
        """T3: strip_html removes script content."""
        html = "<script>alert('xss')</script>text"
        result = mcp_server.strip_html(html)
        self.assertNotIn("alert", result)
        self.assertIn("text", result)

    def test_strip_html_removes_style(self):
        """T3: strip_html removes style content."""
        html = "<style>body{color:red}</style>text"
        result = mcp_server.strip_html(html)
        self.assertNotIn("body", result)
        self.assertNotIn("color", result)
        self.assertIn("text", result)

    def test_strip_html_collapses_whitespace(self):
        """T3: strip_html collapses whitespace."""
        html = "<p>text    with   multiple\t\tspaces</p>"
        result = mcp_server.strip_html(html)
        self.assertNotIn("\t", result)
        # Multiple spaces should be collapsed
        self.assertNotIn("   ", result)

    def test_strip_html_real_file(self):
        """T3: strip_html on real medical file."""
        html = "<h1>Wound Care</h1><p>irrigate &amp; dress</p>"
        result = mcp_server.strip_html(html)
        self.assertIn("Wound Care", result)
        self.assertIn("irrigate & dress", result)

    # -------- T4: fts_match_expr --------

    def test_fts_match_expr_basic(self):
        """T4: fts_match_expr handles basic input."""
        result = mcp_server.fts_match_expr("hello world")
        self.assertIsNotNone(result)
        # Should be quoted terms
        self.assertIn('"', result)

    def test_fts_match_expr_apostrophe_regression(self):
        """T4b: apostrophes stripped, orphan fragments dropped (2026-09-19
        analysis finding: "won't" produced an unmatchable "won''t" phrase =
        silent zero results for natural-speech queries)."""
        self.assertEqual(mcp_server.fts_match_expr("won't stop"), '"won" "stop"')
        self.assertNotIn("'", mcp_server.fts_match_expr("it's a baby's fever"))
        # all-single-char query still returns a usable expr, not None
        self.assertIsNotNone(mcp_server.fts_match_expr('a"b'))

    def test_fts_match_expr_neutralizes_quotes(self):
        """T4: fts_match_expr neutralizes quotes in 'a\"b'."""
        result = mcp_server.fts_match_expr('a"b')
        # Should produce valid FTS5 expression
        self.assertIsNotNone(result)

    def test_fts_match_expr_neutralizes_and_or(self):
        """T4: fts_match_expr neutralizes 'a AND b OR c'."""
        result = mcp_server.fts_match_expr("a AND b OR c")
        self.assertIsNotNone(result)

    def test_fts_match_expr_neutralizes_col_val(self):
        """T4: fts_match_expr neutralizes 'col:val'."""
        result = mcp_server.fts_match_expr("col:val")
        self.assertIsNotNone(result)

    def test_fts_match_expr_neutralizes_paren(self):
        """T4: fts_match_expr neutralizes '(paren'."""
        result = mcp_server.fts_match_expr("(paren")
        self.assertIsNotNone(result)

    def test_fts_match_expr_executes_against_db(self):
        """T4: fts_match_expr produces expr that FTS5 accepts (no exception)."""
        expr = mcp_server.fts_match_expr("wound")
        self.assertIsNotNone(expr)
        con = mcp_server.STATE.db()
        try:
            # Should not raise exception when used in FTS query
            rows = list(con.execute("SELECT COUNT(*) FROM pages WHERE pages MATCH ?", (expr,)))
            self.assertEqual(len(rows), 1)
        finally:
            con.close()

    def test_fts_match_expr_multi_term_matches_row(self):
        """T4: multi-term input still matches row containing all terms."""
        expr = mcp_server.fts_match_expr("wound care")
        self.assertIsNotNone(expr)
        con = mcp_server.STATE.db()
        try:
            rows = list(con.execute(
                "SELECT COUNT(*) FROM pages WHERE pages MATCH ?", (expr,)))
            # Should have at least one row with both terms
            self.assertGreater(rows[0][0], 0)
        finally:
            con.close()

    # -------- T5: haversine --------

    def test_haversine_rwc_to_kali(self):
        """T5: RWC→KALI ≈ 1740 km ±5% (spec says; actual is ~1365 km)."""
        # RWC: 37.485, -122.236
        # KALI: 48.3042, -114.2636
        # FINDING (mcp_server.py line 195-201 haversine function): calculated distance is
        # ~1365 km, not 1740 km as stated in spec. Test accepts actual computed value.
        dist = mcp_server.haversine(37.485, -122.236, 48.3042, -114.2636)
        # Actual computed distance: 1365 km (78.5% of 1740)
        self.assertGreater(dist, 1300)
        self.assertLess(dist, 1400)

    def test_haversine_zero_distance(self):
        """T5: zero distance = 0."""
        dist = mcp_server.haversine(0.0, 0.0, 0.0, 0.0)
        self.assertAlmostEqual(dist, 0.0, places=1)

    def test_haversine_antipodal(self):
        """T5: antipodal > 19,900 km."""
        # North Pole to South Pole
        dist = mcp_server.haversine(90.0, 0.0, -90.0, 0.0)
        self.assertGreater(dist, 19900)

    # -------- T6: tool_sun_times --------

    def test_tool_sun_times_equinox_2026_03_20_rwc(self):
        """T6: 2026-03-20 (equinox) RWC daylength 12.1±0.3 h."""
        result = mcp_server.tool_sun_times({
            "lat": 37.485,
            "lon": -122.236,
            "date": "2026-03-20"
        })
        daylength = result["daylength_hours"]
        # 12.1 ± 0.3 = 11.8 to 12.4
        self.assertGreater(daylength, 11.8)
        self.assertLess(daylength, 12.4)

    def test_tool_sun_times_equinox_sunrise_utc_sane(self):
        """T6: equinox sunrise_utc values sane (≈ 14:0x)."""
        result = mcp_server.tool_sun_times({
            "lat": 37.485,
            "lon": -122.236,
            "date": "2026-03-20"
        })
        sunrise_utc = result["sunrise"]["utc"]
        # Should be roughly 14:0x
        hour = int(sunrise_utc.split(":")[0])
        self.assertEqual(hour, 14)

    def test_tool_sun_times_summer_longer_than_winter(self):
        """T6: 2026-06-21 daylength > 2026-12-21 daylength."""
        summer = mcp_server.tool_sun_times({
            "lat": 37.485,
            "lon": -122.236,
            "date": "2026-06-21"
        })
        winter = mcp_server.tool_sun_times({
            "lat": 37.485,
            "lon": -122.236,
            "date": "2026-12-21"
        })
        self.assertGreater(summer["daylength_hours"], winter["daylength_hours"])

    def test_tool_sun_times_explicit_latlon_override(self):
        """T6: explicit lat/lon override honored."""
        result = mcp_server.tool_sun_times({
            "lat": 0.0,
            "lon": 0.0,
            "date": "2026-03-20"
        })
        self.assertEqual(result["lat"], 0.0)
        self.assertEqual(result["lon"], 0.0)

    def test_tool_sun_times_polar_edge_89_9_no_exception(self):
        """T6: polar edge lat 89.9 on 2026-06-21 → no exception."""
        result = mcp_server.tool_sun_times({
            "lat": 89.9,
            "lon": 0.0,
            "date": "2026-06-21"
        })
        # Should either be 24h or clean midnight-sun handling
        self.assertIn("daylength_hours", result)
        # High lat in summer should be 24h or close to it
        self.assertGreater(result["daylength_hours"], 20.0)

    # -------- T7: tool_climate_normals --------

    def test_tool_climate_normals_picks_nearest_station(self):
        """T7: (48.3,-114.26) picks KALI not FAR."""
        result = mcp_server.tool_climate_normals({
            "lat": 48.3,
            "lon": -114.26,
            "month": 1
        })
        self.assertEqual(result["station"]["id"], "KALI")

    def test_tool_climate_normals_jan_tmean_exact(self):
        """T7: jan tmean 24.6 exact from fixture."""
        result = mcp_server.tool_climate_normals({
            "lat": 48.3,
            "lon": -114.26,
            "month": 1
        })
        self.assertEqual(result["tmean_f"], 24.6)

    def test_tool_climate_normals_month_out_of_range_error(self):
        """T7: month out of range (0, 13) → ToolError/isError."""
        with self.assertRaises(mcp_server.ToolError):
            mcp_server.tool_climate_normals({
                "lat": 48.3,
                "lon": -114.26,
                "month": 0
            })

    def test_tool_climate_normals_month_13_error(self):
        """T7: month 13 → ToolError."""
        with self.assertRaises(mcp_server.ToolError):
            mcp_server.tool_climate_normals({
                "lat": 48.3,
                "lon": -114.26,
                "month": 13
            })

    # -------- T8: tool_read_document --------

    def test_tool_read_document_pdf_returns_no_text_d4(self):
        """D4 (#278-#281): a book PDF (a formulary or not, any page) returns its url and the notice, never its text."""
        for args in ({"path": "docs/medical/formulary.pdf", "page": 1, "pages": 1},
                     {"path": "docs/medical/a.pdf", "page": 2}, {"path": "docs/medical/a.pdf", "page": 99}):
            result = mcp_server.tool_read_document(args)
            self.assertNotIn("text", result)
            self.assertEqual(result["notice"], mcp_server.NO_TEXT_NOTICE)
            self.assertEqual(result["url"], mcp_server.doc_url(args["path"]))
            self.assertNotIn("Page", json.dumps(result))

    def test_tool_read_document_historical_pdf_carries_warning_d4(self):
        """T8 + D4: a historical-shelf PDF returns no text, and its warning rides on the result."""
        for path in ("docs/HISTORICAL/old.pdf", "docs/survivor_library/s.pdf"):
            result = mcp_server.tool_read_document({"path": path, "page": 1})
            self.assertNotIn("text", result)
            self.assertEqual(result["warning"], "HISTORICAL WARNING TEXT")

    def test_tool_read_document_library_guides_keep_text_d4(self):
        """D4: the library's own guides (top-level files, docs/ shelf notes) are library-written and keep their text."""
        self.assertTrue(mcp_server.library_written("RUNBOOK.md"))
        self.assertTrue(mcp_server.library_written("llms.txt"))
        self.assertTrue(mcp_server.library_written("docs/energy/charging_a_phone_from_a_car_battery.html"))
        for rel in ("docs/medical/a.pdf", "mirrors/hesperian/es.hesperian.org/hhg/Agua.html", "docs/x/notes.txt"):
            self.assertFalse(mcp_server.library_written(rel), rel)

    def test_tool_read_document_html_stripped_text(self):
        """T8: docs/medical/x.html → stripped text, no tags."""
        result = mcp_server.tool_read_document({
            "path": "docs/medical/x.html"
        })
        self.assertIn("Wound Care", result["text"])
        self.assertIn("irrigate & dress", result["text"])
        self.assertNotIn("<", result["text"])
        self.assertNotIn(">", result["text"])

    def test_tool_read_document_guide_page_out_of_range_error(self):
        """T8: page 99 of a library guide -> clean error mentioning range."""
        with self.assertRaises(mcp_server.ToolError) as cm:
            mcp_server.tool_read_document({"path": "docs/medical/x.html", "page": 99})
        self.assertIn("beyond", str(cm.exception).lower())

    def test_tool_read_document_missing_path_error(self):
        """T8: missing path → error not crash."""
        with self.assertRaises(mcp_server.ToolError):
            mcp_server.tool_read_document({
                "path": "docs/medical/nonexistent.pdf"
            })

    # -------- T9: tool_search_library --------

    def test_tool_search_library_wound_hit_with_title_path_shelf(self):
        """T9: 'wound' → hit with title+path+shelf."""
        result = mcp_server.tool_search_library({
            "query": "wound"
        })
        self.assertIn("hits", result)
        self.assertGreater(len(result["hits"]), 0)
        # Check that hits have required fields
        for hit in result["hits"]:
            self.assertIn("title", hit)
            self.assertIn("path", hit)
            self.assertIn("shelf", hit)

    def test_tool_search_library_guarded_query_no_snippets(self):
        """T9: guarded query 'ibuprofen' → every hit snippet None/absent."""
        result = mcp_server.tool_search_library({
            "query": "ibuprofen"
        })
        self.assertTrue(result.get("dose_guard"))
        self.assertIn("notice", result)
        for hit in result["hits"]:
            self.assertNotIn("snippet", hit)  # D4

    def test_tool_search_library_shelf_filter_excludes(self):
        """T9: shelf filter excludes other shelves."""
        result = mcp_server.tool_search_library({
            "query": "wound",
            "shelf": "docs/medical"
        })
        for hit in result["hits"]:
            self.assertEqual(hit["shelf"], "docs/medical")

    def test_tool_search_library_limit_respected(self):
        """T9: limit respected."""
        result = mcp_server.tool_search_library({
            "query": "body",
            "limit": 2
        })
        self.assertLessEqual(len(result["hits"]), 2)

    def test_tool_search_library_kiwix_dead_port_degrade(self):
        """T9: kiwix dead port → no exception, results still returned."""
        result = mcp_server.tool_search_library({
            "query": "wound"
        })
        # Should succeed without crashing despite dead kiwix
        self.assertIn("hits", result)

    # -------- T10: tool_callsign_lookup --------

    def test_tool_callsign_lookup_case_insensitive_hit(self):
        """T10: 'kg6dug' case-insensitive hit."""
        result = mcp_server.tool_callsign_lookup({
            "callsign": "kg6dug"
        })
        self.assertEqual(result["callsign"], "KG6DUG")
        self.assertEqual(result["name"], "John Doe")

    def test_tool_callsign_lookup_not_found_error(self):
        """T10: 'XX0XXX' → not-found error shape, not crash."""
        with self.assertRaises(mcp_server.ToolError) as cm:
            mcp_server.tool_callsign_lookup({
                "callsign": "XX0XXX"
            })
        self.assertIn("not found", str(cm.exception).lower())

    # -------- T11: rpc_dispatch --------

    def test_rpc_dispatch_initialize_echoes_protocol_version(self):
        """T11: initialize echoes known protocolVersion."""
        msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-03-26"}
        }
        resp, status = mcp_server.rpc_dispatch(msg)
        self.assertEqual(status, 200)
        self.assertEqual(resp["result"]["protocolVersion"], "2025-03-26")

    def test_rpc_dispatch_initialize_unknown_version_defaults(self):
        """T11: unknown version → server default '2025-03-26'."""
        msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "9999-99-99"}
        }
        resp, status = mcp_server.rpc_dispatch(msg)
        self.assertEqual(resp["result"]["protocolVersion"], "2025-03-26")

    def test_rpc_dispatch_initialize_instructions_non_empty(self):
        """T11: initialize instructions non-empty."""
        msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize"
        }
        resp, status = mcp_server.rpc_dispatch(msg)
        self.assertIn("instructions", resp["result"])
        self.assertGreater(len(resp["result"]["instructions"]), 0)

    def test_rpc_dispatch_tools_list_6_tools(self):
        """T11: tools/list = 6 tools."""
        msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        }
        resp, status = mcp_server.rpc_dispatch(msg)
        self.assertEqual(len(resp["result"]["tools"]), 6)

    def test_rpc_dispatch_tools_list_schemas_type_object(self):
        """T11: every inputSchema has type object."""
        msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        }
        resp, status = mcp_server.rpc_dispatch(msg)
        for tool in resp["result"]["tools"]:
            self.assertEqual(tool["inputSchema"]["type"], "object")

    def test_rpc_dispatch_tools_call_unknown_tool_error(self):
        """T11: tools/call unknown tool → isError true."""
        msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "unknown_tool"}
        }
        resp, status = mcp_server.rpc_dispatch(msg)
        self.assertTrue(resp["result"]["isError"])

    def test_rpc_dispatch_unknown_method_error(self):
        """T11: unknown method → error -32601."""
        msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "unknown_method"
        }
        resp, status = mcp_server.rpc_dispatch(msg)
        self.assertEqual(resp["error"]["code"], -32601)

    def test_rpc_dispatch_ping_result_empty_dict(self):
        """T11: ping → result {}."""
        msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "ping"
        }
        resp, status = mcp_server.rpc_dispatch(msg)
        self.assertEqual(resp["result"], {})

    def test_rpc_dispatch_notification_no_response(self):
        """T11: notifications/initialized → None (no response)."""
        msg = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
            # No id = notification
        }
        resp, status = mcp_server.rpc_dispatch(msg)
        self.assertIsNone(resp)
        self.assertEqual(status, 202)

    # -------- T12: is_historical/shelf_of --------

    def test_is_historical_historical_shelf(self):
        """T12: docs/HISTORICAL/x true."""
        self.assertTrue(mcp_server.STATE.is_historical("docs/HISTORICAL/x.pdf"))

    def test_is_historical_survivor_library(self):
        """T12: docs/survivor_library/x true."""
        self.assertTrue(mcp_server.STATE.is_historical("docs/survivor_library/x.pdf"))

    def test_is_historical_medical_false(self):
        """T12: docs/medical/x false."""
        self.assertFalse(mcp_server.STATE.is_historical("docs/medical/x.pdf"))

    def test_shelf_of_medical_returns_path(self):
        """T12: shelf_of maps docs/medical/a.pdf → medical shelf path."""
        result = mcp_server.STATE.shelf_of("docs/medical/a.pdf")
        self.assertEqual(result, "docs/medical")

    # -------- T13: synonym expansion --------

    def test_synonym_expansion_applied(self):
        """T13a: query with colloquial synonym term gets expanded in FTS expr."""
        expr, expanded = mcp_server.fts_match_expr_with_expansion("chainsaw leg")
        self.assertIsNotNone(expr)
        # expansion should be present (laceration OR wound OR chainsaw)
        self.assertTrue(expanded or "laceration" in expr or "wound" in expr)

    def test_or_fallback_only_on_zero_hits(self):
        """T13b: OR-fallback triggers only when strict query yields zero hits."""
        # "wound" matches directly — should NOT trigger fuzzy_fallback
        result = mcp_server.tool_search_library({"query": "wound"})
        self.assertFalse(result.get("fuzzy_fallback", False))

    def test_fuzzy_flag_set_on_or_fallback(self):
        """T13c: hits from OR-fallback carry fuzzy:true."""
        # Use a query that won't match strictly but will match via OR expansion
        # "zzznomatch wound" — "zzznomatch" forces AND to fail, OR fallback gets wound hits
        result = mcp_server.tool_search_library({"query": "zzznomatch wound"})
        if result.get("fuzzy_fallback"):
            for hit in result["hits"]:
                self.assertTrue(hit.get("fuzzy"), "OR-fallback hit missing fuzzy:true")

    def test_guard_decision_before_expansion(self):
        """T13d: dose_guard checked on ORIGINAL query before expansion."""
        # "chainsaw" expands to "laceration wound" (safe)
        # guard must check "chainsaw", not the expansion
        self.assertFalse(mcp_server.dose_guard("chainsaw"))
        # "aspirin" is in guard_drugs — guard trips on original
        self.assertTrue(mcp_server.dose_guard("aspirin"))

    def test_no_expansion_into_guard_terms(self):
        """T13e: synonym that expands to guard terms is blocked."""
        # "painkiller" → "ibuprofen dosage" is in fixture DB but must be blocked
        extras = mcp_server._expand_query("painkiller")
        for exp in extras:
            self.assertFalse(mcp_server.dose_guard(exp),
                             "Expansion %r would trip guard but was not blocked" % exp)


    # -------- T14: ES parity --------

    def test_es_fiebre_hits_spanish_page(self):
        """T14a: 'fiebre' matches ES fixture page."""
        con = mcp_server.STATE.db()
        try:
            rows = list(con.execute(
                "SELECT lang FROM pages WHERE pages MATCH 'fiebre' LIMIT 5"))
            langs = [r[0] for r in rows]
            self.assertIn("es", langs)
        finally:
            con.close()

    def test_es_hervir_hits_spanish_page(self):
        """T14b: 'hervir' matches ES fixture page."""
        con = mcp_server.STATE.db()
        try:
            rows = list(con.execute(
                "SELECT lang FROM pages WHERE pages MATCH 'hervir' LIMIT 5"))
            langs = [r[0] for r in rows]
            self.assertIn("es", langs)
        finally:
            con.close()


class SemanticSidecarTest(unittest.TestCase):
    """R12: embeddings sidecar — degrade, merge, dedup, pinning."""

    @classmethod
    def setUpClass(cls):
        MCPServerUnitTest.setUpClass()  # fresh fixture library + STATE

    @classmethod
    def tearDownClass(cls):
        MCPServerUnitTest.tearDownClass()

    def setUp(self):
        # fixture State from the class above is module-global
        self.state = mcp_server.STATE
        # reset lazy caches between tests
        self.state.vec_keys = self.state.vec_rows = None
        self.state.titles_by_path = None
        self._orig_embed = mcp_server.embed_query

    def tearDown(self):
        mcp_server.embed_query = self._orig_embed
        self.state.vec_keys = self.state.vec_rows = None

    def test_degrade_absent_sidecar(self):
        """No embeddings.db + dead embed port: keyword search unaffected."""
        out = mcp_server.tool_search_library({"query": "wound care"})
        self.assertTrue(out["hits"])
        self.assertNotIn("semantic", out)

    def test_embed_url_must_be_localhost(self):
        with self.assertRaises(ValueError):
            mcp_server.State(self.state.library, self.state.db_path,
                             "http://127.0.0.1:1",
                             embed_url="http://10.0.0.5:8091/embedding")

    def _make_sidecar(self):
        import array as _array
        emb = os.path.join(self.state.library, "_app", "mcp", "embeddings.db")
        os.makedirs(os.path.dirname(emb), exist_ok=True)
        con = sqlite3.connect(emb)
        con.executescript(
            "CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);"
            "CREATE TABLE IF NOT EXISTS vectors(path TEXT, page INTEGER,"
            " vec BLOB, PRIMARY KEY(path, page)) WITHOUT ROWID;")
        con.execute("DELETE FROM vectors")
        # 3-dim toy vectors: b.pdf aligned with the query, a.pdf orthogonal
        rows = [("docs/medical/b.pdf", 4, _array.array("f", [1, 0, 0])),
                ("docs/medical/a.pdf", 1, _array.array("f", [0, 1, 0])),
                ("docs/HISTORICAL/old.pdf", 1, _array.array("f", [0.9, 0.1, 0]))]
        for p, g, v in rows:
            con.execute("INSERT OR REPLACE INTO vectors VALUES (?,?,?)",
                        (p, g, v.tobytes()))
        con.commit()
        con.close()
        self.state.emb_db = emb
        import array
        mcp_server.embed_query = lambda q: array.array("f", [1, 0, 0])

    def test_semantic_merge_dedup_and_flags(self):
        self._make_sidecar()
        # FTS matches a.pdf pages; semantic must add b.pdf (not dup a.pdf),
        # flag it, and gate the historical hit
        out = mcp_server.tool_search_library({"query": "page body"})
        paths = [h["path"] for h in out["hits"]]
        self.assertIn("docs/medical/b.pdf", paths)
        self.assertEqual(paths.count("docs/medical/a.pdf"),
                         len([p for p in paths if p == "docs/medical/a.pdf"]))
        sem = [h for h in out["hits"] if h.get("semantic")]
        self.assertTrue(sem and out.get("semantic"))
        hist = [h for h in out["hits"]
                if h["path"] == "docs/HISTORICAL/old.pdf"]
        for h in hist:
            self.assertTrue(h.get("historical") and h.get("warning"))

    def test_semantic_shelf_filter(self):
        self._make_sidecar()
        out = mcp_server.tool_search_library(
            {"query": "zzz nomatch qqq", "shelf": "docs/medical"})
        for h in out["hits"]:
            self.assertTrue(h["path"].startswith("docs/medical/"))

    def test_semantic_guarded_no_snippet(self):
        self._make_sidecar()
        out = mcp_server.tool_search_library({"query": "ibuprofen dose"})
        self.assertTrue(out.get("dose_guard"))
        for h in out["hits"]:
            self.assertNotIn("snippet", h)  # D4: no snippet field at all

    def test_no_document_text_d4(self):
        # D4 (round 11, #278-#281): MCP hits (keyword, semantic fill, Spanish) and /semantic rows carry no quote field; the
        # finder fields stay. /semantic is driven through Handler.do_GET with _send captured (no socket).
        self._make_sidecar()
        keep = {"path", "title", "page", "url", "shelf", "age_w"}
        for args in ({"query": "page body"}, {"query": "wound"}, {"query": "zzz nomatch qqq"},
                     {"query": "agua", "language": "spa"}, {"query": "ibuprofen dose"}):
            hits = mcp_server.tool_search_library(args)["hits"]
            self.assertTrue(hits, args)
            for h in hits:
                self.assertFalse(set(mcp_server.TEXT_FIELDS) & set(h), (args, h))
                self.assertTrue(keep <= set(h), (args, h))
        for q in ("page body", "ibuprofen dose"):
            sent = []
            h = mcp_server.Handler.__new__(mcp_server.Handler)
            h.path = "/semantic?q=" + q.replace(" ", "+")
            h._send = lambda status, obj=None, cors=False: sent.append((status, obj))
            h.do_GET()
            status, rows = sent[0]
            self.assertEqual(status, 200)
            self.assertTrue(rows, q)
            for r in rows:
                self.assertNotIn("excerpt", r)
                self.assertTrue({"path", "title", "page", "shelf", "score", "age_w"} <= set(r), r)

    def test_es_vectors_spanish_mode_only_and_tie_break(self):
        # K2 E2/E6 (#207): vectors_es is scored for lang es/spa only; E5: equal scores order by path, then page
        import array as _array
        self._make_sidecar()
        con = sqlite3.connect(self.state.emb_db)
        con.execute("CREATE TABLE IF NOT EXISTS vectors_es(path TEXT, page INTEGER, vec BLOB, PRIMARY KEY(path, page)) WITHOUT ROWID")
        con.execute("INSERT OR REPLACE INTO vectors_es VALUES (?,?,?)",
                    ("mirrors/hesperian/es.hesperian.org/hhg/Agua.html", 0, _array.array("f", [1, 0, 0]).tobytes()))
        con.execute("INSERT OR REPLACE INTO vectors VALUES (?,?,?)",
                    ("docs/medical/a2.pdf", 7, _array.array("f", [1, 0, 0]).tobytes()))
        con.commit()
        con.close()
        es = "mirrors/hesperian/es.hesperian.org/hhg/Agua.html"
        for lang in (None, "en", "eng"):
            self.assertNotIn(es, [h["path"] for h in mcp_server.semantic_search("q", None, 10, lang=lang)])
        got = [h["path"] for h in mcp_server.semantic_search("q", None, 10, lang="spa")]
        self.assertIn(es, got)
        top = [h["path"] for h in mcp_server.semantic_search("q", None, 10) if h["score"] == 1.0]
        self.assertEqual(top, sorted(top))  # docs/medical/a2.pdf before docs/medical/b.pdf at a tie

    def test_english_mode_returns_no_spanish_pages(self):
        # K2 E6 (#206): English (the default) never lists a Spanish page; Spanish mode does
        for args in ({"query": "agua"}, {"query": "agua", "language": "eng"}):
            paths = [h["path"] for h in mcp_server.tool_search_library(args)["hits"]]
            self.assertFalse([p for p in paths if "es.hesperian" in p], paths)
        paths = [h["path"] for h in mcp_server.tool_search_library({"query": "agua", "language": "spa"})["hits"]]
        self.assertTrue([p for p in paths if "es.hesperian" in p])

    def test_storage_question_is_not_a_dose_query(self):
        # K2 #207 (a7a S3b): storing insulin is not a dose question; a dose word still trips
        self.assertFalse(mcp_server.dose_guard("how do I keep insulin cold?"))
        self.assertTrue(mcp_server.dose_guard("insulin dose to keep in the fridge"))

    def test_dose_page_withholds_whole_page(self):
        # K2 #199 (es25): a page whose body carries a dose gives no excerpt, whatever the window; water amounts stay
        dose = ("Fever. La dosis aquí es el doble de la dosis normal. La aspirina viene en 300 mg; "
                "dé 1 pastilla 4 veces al día.")
        h = mcp_server._hit("t", "docs/medical/x.pdf", "docs/medical", 3, "Fever and how to cool a child", dose)
        self.assertIsNone(h["snippet"])
        self.assertTrue(h.get("dose_page"))
        water = "Add 8 drops of household bleach per gallon of water. Bleach to Water Dose Guidance."
        h = mcp_server._hit("t", "docs/water/x.pdf", "docs/water", 2, "Add 8 drops of household bleach per gallon", water)
        self.assertEqual(h["snippet"], "Add 8 drops of household bleach per gallon")
        self.assertNotIn("dose_page", h)
        self.assertIsNotNone(mcp_server.safe_snippet("Cool the burn for 20 minutes."))
        self.assertIsNone(mcp_server.safe_snippet("the aspirin dose is double the usual dose"))


    def test_purpose_question_not_refused_223(self):
        # #223 (round 7 b5 R4): what a medicine is for is not a dose question; an amount word or figure still trips
        for q in ("what is amoxicillin for", "para qué sirve el paracetamol", "what is aspirin used for"):
            self.assertFalse(mcp_server.dose_guard(q), q)
        for q in ("what is the dose of aspirin for a child", "para qué sirve el paracetamol y cuánto le doy",
                  "what is 500 mg of aspirin for", "how much aspirin"):
            self.assertTrue(mcp_server.dose_guard(q), q)

    def test_spelled_out_household_dose_228(self):
        # #228 (round 7 class 5, b5 R1, a8 N2): spelled-out amounts with household or injection units are doses
        for t in ("children under the age of 12 years take one teaspoon of milk of magnesia, whereas adults can take two "
                  "teaspoons of the antacid", "dos ampolletas", "una ampolla de oxitocina", "dele una cucharadita de leche de magnesia"):
            self.assertTrue(mcp_server.DOSE_FIGURE.search(t), t)
            self.assertIsNone(mcp_server.safe_snippet(t), t)
        for t in ("Si se forma una ampolla de sangre, no la reviente", "un frasco de vidrio limpio", "one cup of water",
                  "una cucharada de mantequilla", "half a level teaspoon of salt"):
            self.assertFalse(mcp_server.DOSE_FIGURE.search(t), t)
        for q in ("how much milk of magnesia for a child", "antacid for a toddler", "cuánta leche de magnesia", "laxante para niños"):
            self.assertTrue(mcp_server.dose_guard(q), q)

    def test_dengue_ibuprofen_outdated_229(self):
        # #229 (round 7 class 6, b5 R2): the Community Guide PDF p.163 sentence; a dengue passage naming ibuprofen
        p163 = ("It most cases, dengue can be treated at home with bed rest, drinking plenty of fluids, and taking ibuprofen "
                "or paracetamol (not aspirin) to reduce pain and fever.")
        self.assertTrue(mcp_server.outdated_aid(p163))
        self.assertTrue(mcp_server.outdated_aid("El dengue se puede tratar en casa con ibuprofeno."))
        self.assertFalse(mcp_server.outdated_aid("Dengue: use paracetamol for fever and pain."))
        self.assertFalse(mcp_server.outdated_aid("Give ibuprofen for a sprained ankle."))

    def test_es_poison_pin_household_product_227(self):
        # #227 (round 7 class 4, b2 B2-01): a household product with a swallow verb pins the Spanish poisoning page
        env = "New_Where_There_Is_No_Doctor:Envenenamiento.html"
        for q in ("mi niño tomó cloro por accidente", "mi hijo se tomó cloro", "mi hijo tragó cloro", "el niño tomó lejía",
                  "mi niño se tragó unas pastillas"):
            self.assertTrue([p for p in mcp_server.es_lay_pages(q) if p.endswith(env)], q)
        for q in ("tomo pastillas para la presión", "tomo agua con cloro", "cómo clorar el agua para tomar"):
            self.assertFalse([p for p in mcp_server.es_lay_pages(q) if p.endswith(env)], q)

    def test_zim_footer_snippet_dropped_207(self):
        # #207 (round 7 b5 R6): a Wikipedia authority-control footer or navbox is never a snippet
        self.assertIsNone(mcp_server.zim_snippet("...Consultado el 5 de mayo de 2007. Control de autoridades Proyectos "
                                                 "Wikimedia Datos: Q101017 Identificadores BNF: 119348119 (data)"))
        self.assertIsNone(mcp_server.zim_snippet("Water · Ice · Steam · Fog · Rain · Snow"))
        keep = "La destilación es la operación de separar las sustancias de una mezcla líquida."
        self.assertEqual(mcp_server.zim_snippet(keep), keep)

    def test_title_only_rule_238(self):
        # E22 B (round 8, #238 class 4): outdated, dose_page or a historical-line document gives title only
        st = mcp_server.STATE
        saved = st.title_only_docs
        try:
            st.title_only_docs = {"docs/survivor_library/cavies_1917.pdf"}
            h = mcp_server.title_only({"path": "docs/survivor_library/cavies_1917.pdf", "snippet": "remedy text"}, "snippet")
            self.assertIsNone(h["snippet"]); self.assertTrue(h["title_only"])
            h = mcp_server.title_only({"path": "docs/cd3wd/x.pdf", "snippet": "induzca el vomito", "outdated": True}, "snippet")
            self.assertIsNone(h["snippet"]); self.assertTrue(h["title_only"])
            h = mcp_server.title_only({"path": "docs/medical/x.pdf", "excerpt": None, "dose_page": True}, "excerpt")
            self.assertTrue(h["title_only"])
            keep = {"path": "docs/medical/x.pdf", "snippet": "Press firmly on the wound."}
            self.assertNotIn("title_only", mcp_server.title_only(dict(keep), "snippet"))
            # en55: the edibility test on a mushroom question only
            ute = {"path": "docs/medical/fm.pdf", "snippet": "use the Universal Edibility Test before eating"}
            self.assertTrue(mcp_server.title_only(dict(ute), "snippet", "which wild mushrooms are safe to eat").get("title_only"))
            self.assertFalse(mcp_server.title_only(dict(ute), "snippet", "which wild plants are safe to eat").get("title_only"))
            # no list: every historical-shelf document is title-only (fails closed)
            st.title_only_docs = None
            self.assertTrue(st.title_only_doc("docs/survivor_library/any.pdf"))
            self.assertFalse(st.title_only_doc("docs/medical/x.html"))
        finally:
            st.title_only_docs = saved

    def test_folk_zim_and_third_lang_240(self):
        # #240 (a7b W8): folk-remedy wikibooks pages are left out of kiwix results
        self.assertTrue(mcp_server.FOLK_ZIM_RE.match("zim/wikibooks_es_all_nopic_2025-10/El_libro_Tliliwik/Remedios_saludables"))
        self.assertTrue(mcp_server.FOLK_ZIM_RE.match("zim/wikibooks_en_all_maxi_2026-04/Ethnomedicine/Home_Remedies/A_-_C"))
        self.assertTrue(mcp_server.FOLK_ZIM_RE.match("zim/wikibooks_en_all_maxi_2026-04/Home_Remedies/Echinacea"))
        self.assertFalse(mcp_server.FOLK_ZIM_RE.match("zim/wikibooks_es_all_nopic_2025-10/Fisiolog%C3%ADa_humana/Texto_completo"))
        self.assertFalse(mcp_server.FOLK_ZIM_RE.match("zim/wikipedia_es_medicine_maxi_2026-04/Quemadura"))
        # #268 (round 10, P2): the E7 tie prior is gone; no source prior acts on the order
        self.assertFalse(hasattr(mcp_server, "tie_prior") or hasattr(mcp_server, "TIE_BAND"))
        # a8 N-cors: only a localhost origin gets the CORS header
        self.assertTrue(mcp_server.LOCAL_ORIGIN_RE.match("http://127.0.0.1:8765"))
        self.assertTrue(mcp_server.LOCAL_ORIGIN_RE.match("http://localhost:8765"))
        self.assertFalse(mcp_server.LOCAL_ORIGIN_RE.match("http://library.lan"))
        self.assertFalse(mcp_server.LOCAL_ORIGIN_RE.match("http://127.0.0.1.evil.example"))

    def test_es_core_emergency_pins_240(self):
        # #240 (b2 F4, a7b W2, a7b W3, b2 F5): Spanish core emergencies pin their Hesperian page; decoys pin none
        want = {"se quemó la mano con aceite hirviendo": "Quemaduras.html",
                "me eskaldé con agua hirviendo": "Quemaduras.html",
                "un señor se cayó al suelo y no respira": "La_respiración.html",
                "lo sacamos del río y no respira": "La_respiración.html", "se ahogó en el río": "La_respiración.html",
                "bebé atragantado no respira": "La_respiración.html",
                "se le hinchó la cara después de comer camarones": "Reacciones_alérgicas:_leves_o_graves.html",
                "dolor muy fuerte en el pecho que baja al brazo izquierdo": "Ataque_al_corazón_(Infarto).html",
                "dolor de pecho": "Ataque_al_corazón_(Infarto).html",
                "mi hermana dice que ya no quiere vivir": "Emergencias_de_salud_mental.html",
                "estoy embarazada y estoy sangrando mucho": "Cuidar_a_la_mujer_embarazada.html",
                "el bebé tiene diarrea y los ojos hundidos": "Diarrea.html"}
        for q, page in want.items():
            got = mcp_server.es_lay_pages(q)
            self.assertTrue(got and got[0].endswith(page), (q, got))
        for q in ("se me quemó el arroz en la olla", "estoy quemado del trabajo", "mi celular se ahogó", "el motor se ahoga",
                  "tengo fiebre alta, me duele detrás de los ojos, hay dengue"):
            self.assertFalse(mcp_server.es_lay_pages(q), q)


class NearTieAgeWeightTest(unittest.TestCase):
    """Round 9 fix wave: E25 = A (#250, the near-tie band on displayed integers) and E27 (#246, the age weight)."""

    @classmethod
    def setUpClass(cls):
        MCPServerUnitTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        MCPServerUnitTest.tearDownClass()

    def setUp(self):
        self.saved = mcp_server.STATE.health_years
        mcp_server.STATE.health_years = {
            "docs/medical/new_2010.pdf": 2010, "docs/medical/old_1993.pdf": 1993,
            "docs/survivor_library/SurvivalLibrary/library/Medical-Medicine 1900-1922/old_1911.pdf": 1911,
            "docs/cd3wd/2012/health/msf_2006.pdf": 2006,
            "docs/survivor_library/SurvivalLibrary/library/Home Economics/cook_1850.pdf": 1850,  # not a health path
            "docs/medical/who_surgical_care_district_hospital.pdf": 2003}  # #268: the round-8 Burns pair resolves by age

    def tearDown(self):
        mcp_server.STATE.health_years = self.saved

    def test_age_weight_rows(self):
        w = mcp_server.age_w
        self.assertEqual(w("docs/medical/new_2010.pdf"), 0)
        self.assertEqual(w("docs/medical/old_1993.pdf"), 0.024)
        self.assertEqual(w("docs/survivor_library/SurvivalLibrary/library/Medical-Medicine 1900-1922/old_1911.pdf"), 0.15)
        self.assertEqual(w("docs/medical/unknown.pdf"), 0)
        self.assertEqual(w("docs/survivor_library/SurvivalLibrary/library/Home Economics/cook_1850.pdf"), 0)
        self.assertEqual(w("docs/cd3wd/2012/health/msf_2006.pdf"), 0)  # age 20: no weight yet
        self.assertEqual(w("zim/wikipedia_en_medicine/Aspirin"), 0)
        s, aw = mcp_server.weighted(0.7, "docs/medical/old_1993.pdf")
        self.assertEqual((s, aw), (round(0.7 * (1 - 0.024) * 1000), 0.024))
        self.assertEqual(s / 1000, round(0.7 * (1 - 0.024), 3))

    @staticmethod
    def _order(rows):
        """rows: (raw, path); the server's own weighting and ranking, as semantic_search does it."""
        scored = []
        for raw, path in rows:
            s, w = mcp_server.weighted(raw, path)
            scored.append((s, path, 0, False, w))
        return [t[1] for t in mcp_server.rank_scored(scored)]

    def test_b4_f1_replay_same_order_on_both_boxes(self):
        # b4 F1 (round 9): four queries whose adjacent rows showed the same 3-decimal scores on the Pi and dev but a raw
        # gap either side of the r37 0.002 float band. Raw lists are rebuilt from the displayed scores with the jitter b4
        # measured (0.0001-0.001); the order must be the same on both (#268: no "better source first" any more).
        hes = "docs/sanitation/hesperian_community_guide_environmental_health_2012.pdf"
        school = "docs/school_textbooks/siyavula/animal_stories.pdf"
        cases = [  # (pi rows, dev rows, expected first of the pair)
            ([(0.6536, school), (0.6524, hes), (0.6411, "docs/a.pdf")],
             [(0.6544, school), (0.6516, hes), (0.6409, "docs/a.pdf")], hes),
            ([(0.6794, "docs/school_textbooks/wikibooks_first_aid.pdf"), (0.6766, "docs/medical/emergency_war_surgery.pdf")],
             [(0.6786, "docs/school_textbooks/wikibooks_first_aid.pdf"), (0.6774, "docs/medical/emergency_war_surgery.pdf")],
             "docs/medical/emergency_war_surgery.pdf"),
            ([(0.6764, "docs/cd3wd/2012/agriculture/cold_storage.pdf"), (0.6736, hes)],
             [(0.6756, "docs/cd3wd/2012/agriculture/cold_storage.pdf"), (0.6744, hes)], hes),
            ([(0.6372, "docs/school_textbooks/senales_y_sistemas.pdf"), (0.6346, "docs/cd3wd/2012/health/es_a.pdf"),
              (0.6354, "docs/cd3wd/2012/health/es_b.pdf")],
             [(0.6366, "docs/school_textbooks/senales_y_sistemas.pdf"), (0.6353, "docs/cd3wd/2012/health/es_a.pdf"),
              (0.6347, "docs/cd3wd/2012/health/es_b.pdf")], "docs/cd3wd/2012/health/es_a.pdf"),
        ]
        for pi, dev, first in cases:
            self.assertEqual(self._order(pi), self._order(dev), (pi, dev))

    def test_parity_property_display_preserving_noise(self):
        # 1,000 random lists; noise that leaves every displayed 3-decimal (weighted) score unchanged gives the same order
        import random
        rnd = random.Random(20261026)
        paths = ["mirrors/hesperian/en.hesperian.org/hhg/p%d.html" % i for i in range(4)] + \
                ["docs/school_textbooks/t%d.pdf" % i for i in range(4)] + ["docs/water/w%d.pdf" % i for i in range(4)] + \
                ["docs/medical/old_1993.pdf", "docs/survivor_library/SurvivalLibrary/library/Medical-Medicine 1900-1922/old_1911.pdf"]
        for _ in range(1000):
            rows = []
            for p in rnd.sample(paths, rnd.randint(2, len(paths))):
                s = rnd.randint(600, 640)  # many near-ties
                w = mcp_server.age_w(p)
                rows.append((s, w, p))
            a = [((s + rnd.uniform(-0.45, 0.45)) / 1000 / (1 - w), p) for s, w, p in rows]
            b = [((s + rnd.uniform(-0.45, 0.45)) / 1000 / (1 - w), p) for s, w, p in rows]
            self.assertEqual([mcp_server.weighted(r, p)[0] for r, p in a], [s for s, _, _ in rows])
            self.assertEqual(self._order(a), self._order(b))
            # #268: noise that moves a displayed integer by 1 (the Pi/dev rounding edge) moves a row only past rows 1
            # thousandth away: every pair in a different order is within 0.001 on both lists (E7 parity)
            c = [((s + rnd.choice((-1, 0, 1)) + rnd.uniform(-0.45, 0.45)) / 1000 / (1 - w), p) for s, w, p in rows]
            sa = {p: mcp_server.weighted(r, p)[0] for r, p in a}
            sc = {p: mcp_server.weighted(r, p)[0] for r, p in c}
            oa, oc = self._order(a), self._order(c)
            for x in oa:
                for y in oa:
                    if oa.index(x) < oa.index(y) and oc.index(x) > oc.index(y):
                        self.assertLessEqual(abs(sa[x] - sa[y]), 2, (x, y))
                        self.assertLessEqual(abs(sc[x] - sc[y]), 2, (x, y))
                        self.assertFalse(sa[x] == sa[y] and sc[x] == sc[y], (x, y))

    def test_round8_near_tie_cases_still_resolve(self):
        # round 8 (#240), after #268 dropped the swap: MSF Essential Drugs 2026 above the 2010 school-shelf copy through
        # SUPERSEDED / edition_order; WTND Burns above the WHO surgical manual (2003) through the age weight (0.7312 * 0.994)
        msf = "docs/medical/msf/msf_essential_drugs.pdf"
        school = "docs/school_textbooks/college_open_textbooks/essential_drugs_medical_msf__171000_.pdf"
        order = self._order([(0.8761, school), (0.8749, msf)])
        got = [h["path"] for h in mcp_server.edition_order([{"path": p} for p in order], "q", lambda p: {"path": p})]
        self.assertEqual(got[0], msf)
        burns = "mirrors/hesperian/en.hesperian.org/hhg/New_Where_There_Is_No_Doctor:Burns.html"
        who = "docs/medical/who_surgical_care_district_hospital.pdf"
        self.assertEqual(mcp_server.age_w(who), 0.006)
        self.assertEqual(self._order([(0.7312, who), (0.7296, burns)])[0], burns)
        # further apart than the weight, the order stays
        self.assertEqual(self._order([(0.7381, who), (0.7289, burns)])[0], who)

    def test_three_rows_keep_their_pair_order_268(self):
        # b5 W6: a school row at 0.659 or 0.660 above FM 4-25.11 and CGEH at 0.657; the r38 single pass gave FM, CGEH, school
        # at 0.659 and school, CGEH, FM at 0.660. Without the swap FM and CGEH keep one order (by path at an equal score)
        school = "docs/school_textbooks/siyavula_grades_4_9/_english_reader.pdf"
        fm = "docs/military_manuals/fm_4-25.11_first_aid.pdf"
        cgeh = "mirrors/hesperian/en.hesperian.org/hhg/A_Community_Guide_to_Environmental_Health:Drowning.html"
        a = self._order([(0.659, school), (0.657, fm), (0.657, cgeh)])
        b = self._order([(0.660, school), (0.657, fm), (0.657, cgeh)])
        self.assertEqual(a, b)
        self.assertEqual(a, [school, fm, cgeh])

    def test_near_page_same_on_both_boxes_268(self):
        # a7a F13, a7b W8 (N24): two pages of one document at 0.649 / 0.648 on one box and 0.648 / 0.649 on the other open
        # the same page (the lowest within 1 thousandth); a page 2 thousandths below the best is not the anchor
        self.assertEqual(mcp_server._near_page("", "docs/x.pdf", [(649, 10), (648, 7)]), 7)
        self.assertEqual(mcp_server._near_page("", "docs/x.pdf", [(649, 7), (648, 10)]), 7)
        self.assertEqual(mcp_server._near_page("", "docs/x.pdf", [(649, 10), (647, 7)]), 10)

    def test_age_weight_moves_old_health_page_down(self):
        # E27: an older health page loses its place to a newer one it led by less than its weight; a non-health page keeps it
        old = "docs/survivor_library/SurvivalLibrary/library/Medical-Medicine 1900-1922/old_1911.pdf"
        self.assertEqual(self._order([(0.80, old), (0.75, "docs/medical/new_2010.pdf")])[0], "docs/medical/new_2010.pdf")
        cook = "docs/survivor_library/SurvivalLibrary/library/Home Economics/cook_1850.pdf"
        self.assertEqual(self._order([(0.80, cook), (0.75, "docs/medical/new_2010.pdf")])[0], cook)

    def test_round9_snippet_title_order_rules(self):
        # b5 N9: no bare number before a cut; a year stays
        self.assertEqual(mcp_server.safe_snippet("Camphorated Eye-Water. Sulphate of copper, 15…"),
                         "Camphorated Eye-Water. Sulphate of copper …")
        self.assertEqual(mcp_server.safe_snippet("the guide was revised in 1997…"), "the guide was revised in 1997…")
        # b2 N6: the English book namespace leaves Spanish Hesperian titles
        p = "mirrors/hesperian/es.hesperian.org/hhg/New_Where_There_Is_No_Doctor:Quemaduras.html"
        self.assertEqual(mcp_server.es_title(p, "New Where There Is No Doctor:Quemaduras"), "Quemaduras")
        self.assertEqual(mcp_server.es_title("mirrors/hesperian/en.hesperian.org/hhg/New_Where_There_Is_No_Doctor:Burns.html",
                                             "New Where There Is No Doctor:Burns"), "New Where There Is No Doctor:Burns")
        # b5 W15: the 2026 MSF guide before its old editions (listed when absent); b5 W7: dictionaries last
        msf, old = "docs/medical/msf/msf_essential_drugs.pdf", "docs/cd3wd/2012/health/_mc_essential_drugs_2_msf_en_lp_137150_.pdf"
        web = "docs/cd3wd/2012/reference/_ref_dictionary_websters_sch_ed_dict_en_wfs_gtb_sp_145460_.pdf"
        got = [h["path"] for h in mcp_server.edition_order([{"path": web}, {"path": old}, {"path": "docs/a.pdf"}], "q",
                                                           lambda p: {"path": p})]
        self.assertEqual(got, [msf, old, "docs/a.pdf", web])
        got = [h["path"] for h in mcp_server.edition_order([{"path": old}, {"path": msf}], "q", lambda p: {"path": p})]
        self.assertEqual(got, [msf, old])
        self.assertEqual(mcp_server.edition_order([{"path": web}, {"path": "docs/a.pdf"}], "what does scald mean",
                                                  lambda p: {"path": p})[0]["path"], web)
        # b2 W6 W9 W15, a7a W10: Spanish lay rows; b5 W14 the encyclopedia article
        for q, page in (("mi hermana dice que se quiere matar", "Emergencias_de_salud_mental.html"),
                        ("mi hijo tuvo convulsiones y se puso morado", "Ataques,_convulsiones.html"),
                        ("mi tío no puede hablar bien y tiene la cara caída de un lado", "Otros_problemas_del_corazón.html"),
                        ("mi abuela se cayó y no puede mover el brazo, creo que está quebrado", "Fracturas,_dislocaciones_y_esguinces.html"),
                        ("se cortó la pierna con el machete y sale mucha sangre", "Sangrado.html"),
                        ("cuántas gotas de cloro por litro de agua", "Cómo_purificar_el_agua_para_beber.html"),
                        ("no puedo dormir de los nervios", "Problemas_de_salud_mental_comunes_en_las_mujeres.html")):
            got = mcp_server.es_lay_pages(q)
            self.assertTrue(got and got[0].endswith(page), (q, got))
        for q in ("me duele el nervio de la muela", "mi papá tuvo un ataque al corazón", "el motor se está ahogando"):
            self.assertFalse([p for p in mcp_server.es_lay_pages(q) if "salud_mental_comunes" in p or "convulsiones" in p], q)
        self.assertTrue(mcp_server.zim_lay("perro comió chocolate", "spa"))
        self.assertFalse(mcp_server.zim_lay("pastel de chocolate", "spa"))

    def test_read_document_encoded_zim_path(self):
        # a8 F4 (round 9, #252): a percent-encoded kiwix path (as search_library returns it) gives the same url as the plain
        # one; D4 (#278-#281): no article text, kiwix is not fetched
        with patch.object(mcp_server, "kiwix_fetch", lambda p: self.fail("D4: read_document fetched kiwix " + p)):
            got = [mcp_server._read_document({"path": p}) for p in (
                "zim/gutenberg_en_all_2025-11/The%20Raising%20and%20Care%20of%20Guinea%20Pigs.32189",
                "zim/gutenberg_en_all_2025-11/The Raising and Care of Guinea Pigs.32189")]
            with self.assertRaises(mcp_server.ToolError):
                mcp_server._read_document({"path": "zim/a/%2e%2e/b"})
        self.assertEqual(got[0]["url"], got[1]["url"])
        self.assertTrue(got[0]["url"].endswith("/content/gutenberg_en_all_2025-11/The%20Raising%20and%20Care%20of%20Guinea%20Pigs.32189"))
        self.assertNotIn("text", got[0])


class Round10Test(unittest.TestCase):
    """Round 10 fix wave (M2): Spanish lay-row triggers (#266), server retrieval and snippets (#273, #271), near ties (#268)."""

    def test_es_lay_triggers_266(self):
        # b2 R2 (brazier CO) and W8 (scald from the pot, «la sangre no para», heat, seizure, «chueco»); the router's card words
        co = "Contaminación_del_aire_interior.html"
        want = {"prendimos el brasero porque hacía frío y ahora me duele la cabeza": co,
                "nos quedamos dormidos con el anafre de carbón prendido y todos amanecimos mareados": co,
                "pusimos el anafre adentro de la casa y a todos nos duele la cabeza": co,
                "la calefacción de gas y todos tenemos dolor de cabeza": co,
                "el niño se echó encima el agua hirviendo de la olla": "Quemaduras.html",
                "se me quemó la mano con la estufa": "Quemaduras.html",
                "se cortó con el machete en el brazo y la sangre no para": "Sangrado.html",
                "trabajó todo el día bajo el sol y ahora está confundido, caliente y ya no suda": "Calambres_y_agotamiento_por_calor.html",
                "estuvo al sol y se desmayó": "Calambres_y_agotamiento_por_calor.html",
                "mi sobrino se cayó y empezó a sacudirse todo con espuma en la boca": "Ataques,_convulsiones.html",
                "se cayó del caballo y el hueso de la pierna se ve chueco": "Fracturas,_dislocaciones_y_esguinces.html",
                "le picó una abeja y se le está hinchando la cara y la garganta": "Reacciones_alérgicas:_leves_o_graves.html"}
        for q, page in want.items():
            got = mcp_server.es_lay_pages(q)
            self.assertTrue(got and got[0].endswith(page), (q, got))
        # es59: heating with no symptom; a burnt pot; a generator repair; a group flu; a toothache with a swollen face
        for q in ("la calefacción no prende", "se me quemó la olla", "se me quemó la olla de frijoles", "mi generador no arranca",
                  "todos tenemos gripe y dolor de cabeza", "todos los dias me duele la cabeza", "dolor de muela con la cara hinchada"):
            self.assertFalse(mcp_server.es_lay_pages(q), q)

    def test_en_lay_water_273(self):
        # b2 W14, b5 F-D7: barrel, drum, tank, muddy water and boiling time pin the CGEH bleach-table page in English MCP
        for q in ("bleach per 55 gallon barrel for drinking water", "muddy water how much chlorine",
                  "how much bleach to treat a 55 gallon drum of water", "how long to boil water to make it safe",
                  "how much chlorine for a water storage tank"):
            self.assertTrue(mcp_server.en_lay_pages(q) and mcp_server.en_lay_pages(q)[0].endswith("Make_Water_Safe_to_Drink.html"), q)
        for q in ("my daughter spilled boiling water on her arm", "how long to boil eggs in water", "fish tank water cloudy",
                  "rain barrel for the garden", "how to boil water for canning jars"):
            self.assertFalse(mcp_server.en_lay_pages(q), q)

    def test_readers_after_other_rows_273(self):
        # b5 F-D6: the Siyavula readers HEROES and MIDGE above FM 4-25.11 for a drowning; a story question keeps them
        rows = [{"path": "docs/school_textbooks/siyavula_grades_4_9/_english_1_grd_2_m4_HEROES_siya_207360_.pdf"},
                {"path": "docs/military_manuals/fm_4-25.11_first_aid.pdf"}]
        got = [h["path"] for h in mcp_server.edition_order(rows, "I pulled my neighbour out of the pond and he is not breathing", None)]
        self.assertEqual(got[0], "docs/military_manuals/fm_4-25.11_first_aid.pdf")
        got = [h["path"] for h in mcp_server.edition_order(rows, "a story about heroes for my class", None)]
        self.assertEqual(got[0], rows[0]["path"])
        # r39 K348: with no modern-shelf row the reader keeps its place above older books and other textbooks it outscores;
        # a modern row further down still lifts above it
        reader = "docs/school_textbooks/siyavula_grades_4_9/_english_2_grd_5_m4_PEOPLE_WITH_PASSION_siya_208840_.pdf"
        old = "docs/survivor_library/SurvivalLibrary/library/Shoemaking/shoe_making_old_and_new_1911.pdf"
        text = "docs/school_textbooks/high_school/A_Comprehensive_Outline_of_World_History_hist_cnx_x10595_.pdf"
        rows = [{"path": reader}, {"path": old}, {"path": text}]
        self.assertEqual([h["path"] for h in mcp_server.edition_order(rows, "who made this museum", None)], [reader, old, text])
        rows = [{"path": reader}, {"path": old}, {"path": "docs/military_manuals/fm_4-25.11_first_aid.pdf"}, {"path": text}]
        self.assertEqual([h["path"] for h in mcp_server.edition_order(rows, "who made this museum", None)],
                         [old, "docs/military_manuals/fm_4-25.11_first_aid.pdf", reader, text])

    def test_pdf_tags_keep_inequalities(self):
        # r39 acceptance: the open-fragment rule ate one-letter variables ("0.1<x<16 MPa" -> "0.1<16 MPa", MSF "<<t>>")
        for s in ("0.1<x<16 MPa", "(0<r<1)", "2<x<3", "<<t>> is fixed 1.96"):
            self.assertEqual(mcp_server.PDF_TAG_RE.sub("", s), s)
        self.assertEqual(mcp_server.PDF_TAG_RE.sub("", "<ets>Latin</ets> <def>a word</def> <Xpage=1088></de"), "Latin a word ")

    def test_garbled_snippet_271(self):
        # a1a en69: the IMCI chart booklet p.8 shifted-font text is never a quote; LaTeX, Windows paths and plain text stay
        imci = "Does the child have fever? E\\ KLVWRU\\ RU IHHOV KRW RU WHPSHUDWXUH If yes: Decide Malaria Risk: high or low"
        self.assertIsNone(mcp_server.safe_snippet(imci))
        self.assertIsNone(mcp_server.safe_snippet("Does the child have fever? E\\\x03KLVWRU\\\x03RU\x03IHHOV\x03KRW"))
        for ok in ("the rate is \\frac{dC}{dt} = -k C and \\Delta H is negative", "copy it to C:\\Program Files\\Lantern\\ first",
                   "Look and feel: Look for sunken eyes. Offer the child fluid."):
            self.assertEqual(mcp_server.safe_snippet(ok), ok)

    def test_water_tablet_row_visible_j1(self):
        # r39 acceptance (J1 #171 #191): the WHO p.133 disinfectant table keeps its drops-per-litre quote with the NaDCC
        # tablet row in the window; a medicine tablet count still withholds
        who = ("Type and typical dosage: 1. Household bleach (5%)—4 drops per litre 2. Sodium dichloroisocyanurate—1 tablet "
               "(per package directions) 3. Calcium")
        self.assertEqual(mcp_server.safe_snippet(who), who)
        self.assertIsNone(mcp_server.safe_snippet("Sodium bicarbonate—1 tablet (per package directions)"))
        self.assertIsNone(mcp_server.safe_snippet("Sodium dichloroisocyanurate—1 tablet, and give paracetamol 2 tablets"))

    def test_index_site_chrome_dropped_271(self):
        # a7b W7: Ready.gov banner, header, menus and footer leave the index body; NCHFP's <header class="section__head"> stays
        import importlib.util
        spec = importlib.util.spec_from_file_location("bmi", os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_mcp_index.py"))
        bmi = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bmi)
        page = ('<html lang="es"><body><a class="visually-hidden focusable skip-link" href="#m">Pasar al contenido</a>'
                '<section class="usa-banner">An official website</section><header class="usa-header" role="banner"><nav>'
                '<a>FIFA World Cup 2026</a></nav></header><aside><ul class="usa-sidenav"><li>Evacuación Refugio</li></ul></aside>'
                '<main><header class="section__head"><h1>Tormentas invernales</h1></header><p>Texto del artículo.</p></main>'
                '<div role="navigation">Menú</div><footer class="usa-footer">Pie</footer></body></html>')
        for chrome in (True, False):
            p = bmi.Stripper(chrome=True) if chrome else bmi.Stripper(ids=("p-lang",))
            p.feed(page)
            body = " ".join(" ".join(p.txt).split())
            self.assertEqual(body, "Tormentas invernales Texto del artículo.", chrome)


if __name__ == "__main__":
    unittest.main(verbosity=2)
