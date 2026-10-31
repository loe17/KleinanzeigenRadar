import sys
import time
import unittest
from app.database import (
    init_db,
    create_search,
    get_all_searches,
    get_search,
    update_search,
    delete_search,
    save_result,
    get_results,
    update_result_status,
    mark_all_results_as_read,
    get_stats,
    save_settings,
    get_settings
)
from app.scraper import matches_keywords, build_search_url, parse_price
from app.updater import check_for_github_update

class TestKleinanzeigenRadar(unittest.TestCase):
    def setUp(self):
        init_db()

    def test_price_parsing(self):
        self.assertEqual(parse_price("120 € VB"), 120.0)
        self.assertEqual(parse_price("1.250 €"), 1250.0)
        self.assertEqual(parse_price("Zu verschenken"), 0.0)
        self.assertEqual(parse_price("35,50 €"), 35.5)

    def test_clean_slug(self):
        from app.scraper import clean_slug
        self.assertEqual(clean_slug("Dell Latitude"), "dell-latitude")
        self.assertEqual(clean_slug("Lenovo T480s (14 Zoll)"), "lenovo-t480s-14-zoll")
        self.assertEqual(clean_slug("Große Käufe"), "grosse-kaeufe")

    def test_search_url_building(self):
        search = {
            "query": "Macbook",
            "postal_code": "10115",
            "radius": 20,
            "min_price": 200,
            "max_price": 800
        }
        url = build_search_url(search)
        self.assertIn("preis:200:800", url)
        self.assertIn("10115/umkreis:20", url)
        self.assertIn("macbook", url)
        self.assertTrue(url.startswith("https://www.kleinanzeigen.de/s-"))

    def test_keyword_matching(self):
        # 1. Matching in description
        search = {
            "keywords": "M1, 16GB",
            "case_sensitive": False,
            "search_in_description": True
        }
        matched, reason = matches_keywords(
            search,
            title="Apple Laptop Top Zustand",
            description="Verkaufe mein MacBook mit M1 Chip und 16GB RAM.",
            ocr_text=""
        )
        self.assertTrue(matched)
        self.assertIn("Beschreibung", reason)

        # 2. Matching in OCR Text (from photos)
        search_ocr = {
            "keywords": "A2337",
            "case_sensitive": False,
            "search_in_description": False
        }
        matched_ocr, reason_ocr = matches_keywords(
            search_ocr,
            title="MacBook Laptop",
            description="Verkaufe Laptop",
            ocr_text="Model No: A2337 EMC 3598"
        )
        self.assertTrue(matched_ocr)
        self.assertIn("Bild-Text", reason_ocr)

        # 3. Negative keyword exclusion
        search_neg = {
            "keywords": "MacBook, -defekt",
            "case_sensitive": False,
            "search_in_description": True
        }
        matched_neg, reason_neg = matches_keywords(
            search_neg,
            title="MacBook Pro",
            description="Leider defekt, für Bastler",
            ocr_text=""
        )
        self.assertFalse(matched_neg)
        self.assertIn("Ausgeschlossen", reason_neg)

        # 4. Case sensitivity
        search_case = {
            "keywords": "PRO",
            "case_sensitive": True,
            "search_in_description": True
        }
        matched_case_no, _ = matches_keywords(search_case, "MacBook pro", "", "")
        self.assertFalse(matched_case_no)

        matched_case_yes, _ = matches_keywords(search_case, "MacBook PRO", "", "")
        self.assertTrue(matched_case_yes)

    def test_database_crud(self):
        from app.database import clear_results
        # Search CRUD
        s_id = create_search({
            "name": "Test Search",
            "query": "Thinkpad",
            "keywords": "T480",
            "min_price": 100,
            "max_price": 300,
            "postal_code": "50667",
            "radius": 30,
            "shipping_type": "shipping_only"
        })
        self.assertIsNotNone(s_id)

        s = get_search(s_id)
        self.assertEqual(s["name"], "Test Search")
        self.assertEqual(s["query"], "Thinkpad")
        self.assertTrue(len(s.get("terms", [])) >= 1)
        self.assertTrue("created_at_formatted" in s)
        self.assertTrue("last_run_formatted" in s)
        self.assertIn("Uhr", s["created_at_formatted"])

        pfx = f"test_{int(time.time()*1000)}"
        # Result creation
        res_id = save_result({
            "search_id": s_id,
            "kleinanzeigen_id": f"{pfx}_9999",
            "title": "Lenovo Thinkpad T480 i5 16GB",
            "price": "180 €",
            "price_num": 180.0,
            "location": "50667 Köln",
            "shipping_possible": True,
            "url": "https://www.kleinanzeigen.de/s-anzeige/test/9999",
            "thumbnail_url": "",
            "images": ["https://img.kleinanzeigen.de/1.jpg"],
            "description": "Schönes Thinkpad",
            "ocr_text": "Model: T480",
            "match_reason": "Treffer in Titel"
        })
        self.assertIsNotNone(res_id)

        # Duplicate check
        dup_id = save_result({
            "search_id": s_id,
            "kleinanzeigen_id": f"{pfx}_9999",
            "title": "Lenovo Thinkpad T480 i5 16GB",
            "url": "https://www.kleinanzeigen.de/s-anzeige/test/9999"
        })
        self.assertIsNone(dup_id, "Duplicate ads should return None")

        # Second result for sort testing
        res_id2 = save_result({
            "search_id": s_id,
            "kleinanzeigen_id": f"{pfx}_8888",
            "title": "Lenovo Thinkpad T480s 8GB",
            "price": "90 €",
            "price_num": 90.0,
            "location": "50667 Köln",
            "shipping_possible": True,
            "url": "https://www.kleinanzeigen.de/s-anzeige/test/8888",
            "description": "Top Zustand",
            "match_reason": "Treffer in Titel"
        })
        self.assertIsNotNone(res_id2)

        # Get results with sort_by
        results_asc = get_results(search_id=s_id, sort_by="price_asc")
        self.assertEqual(results_asc[0]["price_num"], 90.0)
        self.assertEqual(results_asc[1]["price_num"], 180.0)

        results_desc = get_results(search_id=s_id, sort_by="price_desc")
        self.assertEqual(results_desc[0]["price_num"], 180.0)
        self.assertEqual(results_desc[1]["price_num"], 90.0)

        # Test clear_results
        clear_results(search_id=s_id)
        results_after_clear = get_results(search_id=s_id)
        self.assertEqual(len(results_after_clear), 0)

        # Recreate result for remaining checks
        res_id3 = save_result({
            "search_id": s_id,
            "kleinanzeigen_id": f"{pfx}_7777",
            "title": "Lenovo Thinkpad T480 i7",
            "price": "220 €",
            "price_num": 220.0,
            "url": "https://www.kleinanzeigen.de/s-anzeige/test/7777"
        })
        # Status update
        update_result_status(res_id3, "starred")
        results_starred = get_results(search_id=s_id, status="starred")
        self.assertEqual(len(results_starred), 1)

        # Stats
        stats = get_stats()
        self.assertGreaterEqual(stats["total_searches"], 1)
        self.assertGreaterEqual(stats["starred_results"], 1)

        # Settings
        save_settings({"telegram_chat_id": "12345678"})
        settings = get_settings()
        self.assertEqual(settings.get("telegram_chat_id"), "12345678")

        # Cleanup
        delete_search(s_id)
        self.assertIsNone(get_search(s_id))

    def test_strict_and_keyword_matching(self):
        # All positive keywords must be present somewhere across title, description, or OCR
        search = {
            "keywords": "Dell, Latitude, 3510",
            "case_sensitive": False,
            "search_in_description": True,
            "ocr_images": True
        }
        # 1. All present (Dell & Latitude in title, 3510 in desc) -> MATCH
        matched, reason = matches_keywords(
            search,
            title="Dell Latitude Notebook",
            description="Modell 3510 mit Intel i5",
            ocr_text=""
        )
        self.assertTrue(matched)

        # 2. One missing (3510 missing everywhere) -> REJECT
        matched_missing, reason_missing = matches_keywords(
            search,
            title="Dell Latitude Notebook",
            description="Modell 5400 mit Intel i5",
            ocr_text=""
        )
        self.assertFalse(matched_missing)
        self.assertIn("3510", reason_missing)

        # 3. One in OCR text (Dell & Latitude in title, 3510 found by OCR on photo) -> MATCH
        matched_ocr, reason_ocr = matches_keywords(
            search,
            title="Dell Latitude Notebook",
            description="Guter Zustand, siehe Typenschild",
            ocr_text="Service Tag 12345 Latitude 3510 Regulatory"
        )
        self.assertTrue(matched_ocr)

        # 4. Exclude keyword present -> REJECT
        search_neg = {
            "keywords": "Dell, Latitude, -defekt",
            "case_sensitive": False,
            "search_in_description": True,
            "ocr_images": False
        }
        matched_neg, reason_neg = matches_keywords(
            search_neg,
            title="Dell Latitude Laptop defekt",
            description="Geht nicht an",
            ocr_text=""
        )
        self.assertFalse(matched_neg)
        self.assertIn("Ausgeschlossen", reason_neg)

        # 5. Wildcard matching inside words (*15* vs 15 vs 15*)
        search_wildcard = {
            "terms": [
                {"text": "Latitude", "type": "include"},
                {"text": "*15*", "type": "include"}
            ],
            "case_sensitive": False,
            "search_in_description": True
        }
        # Matches '15Zoll' inside title
        m1, _ = matches_keywords(search_wildcard, "Dell Latitude 15Zoll", "", "")
        self.assertTrue(m1)

        # Matches 'XPS15' inside title
        m2, _ = matches_keywords(search_wildcard, "Dell Latitude XPS15", "", "")
        self.assertTrue(m2)

        # Exact word '15' does NOT match '15Zoll' or '2015'
        search_exact = {
            "terms": [
                {"text": "Latitude", "type": "include"},
                {"text": "15", "type": "include"}
            ],
            "case_sensitive": False,
            "search_in_description": True
        }
        m3, _ = matches_keywords(search_exact, "Dell Latitude 15Zoll", "", "")
        self.assertFalse(m3)
        m4, _ = matches_keywords(search_exact, "Dell Latitude 15 Zoll", "", "")
        self.assertTrue(m4)

        # Prefix wildcard '15*' matches '15Zoll' but not 'XPS15'
        search_prefix = {
            "terms": [
                {"text": "Latitude", "type": "include"},
                {"text": "15*", "type": "include"}
            ],
            "case_sensitive": False,
            "search_in_description": True
        }
        m5, _ = matches_keywords(search_prefix, "Dell Latitude 15Zoll", "", "")
        self.assertTrue(m5)
        m6, _ = matches_keywords(search_prefix, "Dell Latitude XPS15", "", "")
        self.assertFalse(m6)

        # Wildcard exclusion (-*defekt* excludes 'Teildefekt')
        search_wild_ex = {
            "terms": [
                {"text": "Latitude", "type": "include"},
                {"text": "*defekt*", "type": "exclude"}
            ],
            "case_sensitive": False,
            "search_in_description": True
        }
        m7, _ = matches_keywords(search_wild_ex, "Dell Latitude", "Teildefekt fuer Bastler", "")
        self.assertFalse(m7)

        # Flexible sub-word / unit matching (*16*GB matches 16GB, 16 GB, RAM: 16 GB)
        search_unit_wild = {
            "terms": [
                {"text": "Lenovo", "type": "include"},
                {"text": "*16*GB", "type": "include"}
            ],
            "case_sensitive": False,
            "search_in_description": True
        }
        m8, _ = matches_keywords(search_unit_wild, "Lenovo T480 16GB", "", "")
        self.assertTrue(m8)
        m9, _ = matches_keywords(search_unit_wild, "Lenovo T480", "Ausstattung: 16 GB Arbeitsspeicher", "")
        self.assertTrue(m9)
        m10, _ = matches_keywords(search_unit_wild, "Lenovo T480", "RAM: 16 GB DDR4", "")
        self.assertTrue(m10)
        m11, _ = matches_keywords(search_unit_wild, "Lenovo T480 8GB RAM", "", "")
        self.assertFalse(m11)

        # Automatic space tolerance between numbers and units (16GB matches 16 GB)
        search_unit_norm = {
            "terms": [
                {"text": "Lenovo", "type": "include"},
                {"text": "16GB", "type": "include"}
            ],
            "case_sensitive": False,
            "search_in_description": True
        }
        m12, _ = matches_keywords(search_unit_norm, "Lenovo Laptop 16 GB", "", "")
        self.assertTrue(m12)

        # Screen size matching: 15*" or 15" matches 15,6 Zoll, 15 Zoll, 15", 15,6", 15-Zoll, 15 inch
        search_screen = {
            "terms": [
                {"text": "Laptop", "type": "include"},
                {"text": '15*"', "type": "include"}
            ],
            "case_sensitive": False,
            "search_in_description": True
        }
        m13, _ = matches_keywords(search_screen, "Laptop 15,6 Zoll 16GB", "", "")
        self.assertTrue(m13)
        m14, _ = matches_keywords(search_screen, "Laptop 15 Zoll", "", "")
        self.assertTrue(m14)
        m15, _ = matches_keywords(search_screen, "Laptop 15,6\"", "", "")
        self.assertTrue(m15)
        m16, _ = matches_keywords(search_screen, "Dell Latitude 15-Zoll", "Top Laptop", "")
        self.assertTrue(m16)

        # Synonym matching: Laptop matches Notebook
        search_synonym = {
            "terms": [
                {"text": "Laptop", "type": "include"}
            ],
            "case_sensitive": False,
            "search_in_description": True
        }
        m17, _ = matches_keywords(search_synonym, "Gebrauchtes Notebook", "", "")
        self.assertTrue(m17)

        # ODER-Syntax (|) Tests:
        # 1. Beliebige Gegenstände: Sofa | Couch
        search_or_furniture = {
            "terms": [
                {"text": "Sofa | Couch", "type": "include"}
            ],
            "case_sensitive": False,
            "search_in_description": True
        }
        m18, r18 = matches_keywords(search_or_furniture, "Gemütliches Sofa in Berlin", "", "")
        self.assertTrue(m18)
        self.assertIn("Sofa", r18)
        m19, r19 = matches_keywords(search_or_furniture, "Schöne Couch abzugeben", "", "")
        self.assertTrue(m19)
        self.assertIn("Couch", r19)
        m20, _ = matches_keywords(search_or_furniture, "Küchentisch aus Holz", "", "")
        self.assertFalse(m20)

        # ODER mit Wildcard: Sofa | *couch* findet auch Eckcouch
        search_or_wild = {
            "terms": [
                {"text": "Sofa | *couch*", "type": "include"}
            ],
            "case_sensitive": False,
            "search_in_description": True
        }
        m_wild, r_wild = matches_keywords(search_or_wild, "Schöne Eckcouch abzugeben", "", "")
        self.assertTrue(m_wild)
        self.assertIn("couch", r_wild.lower())

        # 2. Kombination: ODER-Begriff UND Einheitenbegriff
        search_or_combo = {
            "terms": [
                {"text": "Laptop | Notebook", "type": "include"},
                {"text": "*16*GB", "type": "include"}
            ],
            "case_sensitive": False,
            "search_in_description": True
        }
        m21, _ = matches_keywords(search_or_combo, "HP Laptop 16GB RAM", "", "")
        self.assertTrue(m21)
        m22, _ = matches_keywords(search_or_combo, "Dell Notebook 16 GB", "", "")
        self.assertTrue(m22)
        m23, _ = matches_keywords(search_or_combo, "Dell Notebook 8 GB", "", "")
        self.assertFalse(m23)  # Fehlt 16GB

        # 3. Ausschluss mit ODER: defekt | schaden
        search_or_exclude = {
            "terms": [
                {"text": "Laptop", "type": "include"},
                {"text": "defekt | schaden", "type": "exclude"}
            ],
            "case_sensitive": False,
            "search_in_description": True
        }
        m24, _ = matches_keywords(search_or_exclude, "Laptop voll funktionsfähig", "", "")
        self.assertTrue(m24)
        m25, _ = matches_keywords(search_or_exclude, "Laptop leider defekt", "", "")
        self.assertFalse(m25)
        m26, _ = matches_keywords(search_or_exclude, "Laptop mit Schaden", "", "")
        self.assertFalse(m26)

        # Ausschluss mit ODER und Wildcard: defekt | *schaden* schließt auch Gehäuseschaden aus
        search_or_exclude_wild = {
            "terms": [
                {"text": "Laptop", "type": "include"},
                {"text": "defekt | *schaden*", "type": "exclude"}
            ],
            "case_sensitive": False,
            "search_in_description": True
        }
        m27, _ = matches_keywords(search_or_exclude_wild, "Laptop mit Gehäuseschaden", "", "")
        self.assertFalse(m27)

    def test_search_url_pagination(self):
        from app.scraper import build_search_url_for_query
        url_p1 = build_search_url_for_query("Laptop", max_price=250, page=1)
        self.assertNotIn("seite:", url_p1)
        url_p2 = build_search_url_for_query("Laptop", max_price=250, page=2)
        self.assertIn("seite:2", url_p2)
        self.assertIn("preis::250", url_p2)

    def test_search_queries_with_or_syntax(self):
        from app.scraper import fetch_live_result_count
        # Test that OR in preview count splits and queries both alternatives
        # (Mocking build_search_url_for_query isn't needed, but testing that | doesn't crash)
        count = fetch_live_result_count("Laptop | Notebook", max_price=250)
        self.assertIsInstance(count, int)

    def test_scan_progress_tracking(self):
        from app.watcher import get_scan_progress, set_scan_progress
        # Default empty progress
        prog = get_scan_progress(99999)
        self.assertFalse(prog["is_scanning"])
        self.assertEqual(prog["progress"], 100)

        # Set progress
        set_scan_progress(99999, 50, "Prüfe Anzeige 5 von 10...", is_scanning=True, found_count=2)
        prog_updated = get_scan_progress(99999)
        self.assertTrue(prog_updated["is_scanning"])
        self.assertEqual(prog_updated["progress"], 50)
        self.assertEqual(prog_updated["found_count"], 2)
        self.assertIn("5 von 10", prog_updated["status"])

    def test_relative_time_formatting(self):
        from app.database import format_relative_time
        self.assertEqual(format_relative_time("Heute, 14:30"), "Heute, 14:30")
        self.assertEqual(format_relative_time("Gestern, 09:15"), "Gestern, 09:15")
        self.assertEqual(format_relative_time(""), "")

    def test_price_history_and_reduction(self):
        s_id = create_search({
            "name": "Price Reduction Test",
            "query": "Thinkpad",
            "keywords": "T480",
            "shipping_type": "all"
        })
        ad_key = f"test_price_drop_{time.time()}"
        # 1. Erste Speicherung mit 200 €
        r1_id = save_result({
            "search_id": s_id,
            "kleinanzeigen_id": ad_key,
            "title": "Lenovo ThinkPad T480 Top",
            "price": "200 €",
            "price_num": 200.0,
            "url": f"https://www.kleinanzeigen.de/s-anzeige/test/{ad_key}",
            "published_date": "Heute, 10:00"
        })
        self.assertIsNotNone(r1_id)

        # 2. Zweite Speicherung (Preissenkung auf 160 €)
        r2_id = save_result({
            "search_id": s_id,
            "kleinanzeigen_id": ad_key,
            "title": "Lenovo ThinkPad T480 Top",
            "price": "160 €",
            "price_num": 160.0,
            "url": f"https://www.kleinanzeigen.de/s-anzeige/test/{ad_key}",
            "published_date": "Heute, 10:00"
        })
        self.assertIsNone(r2_id)  # Duplikate liefern None zurück

        # 3. Prüfe Ergebnisse über get_results
        results = get_results(search_id=s_id)
        self.assertEqual(len(results), 1)
        r = results[0]
        self.assertEqual(r["price"], "160 €")
        self.assertTrue(r["price_reduced"])
        self.assertEqual(r["old_price"], "200 €")
        self.assertEqual(r["price_diff"], "-40 € (-20%)")
        self.assertGreaterEqual(len(r["price_history"]), 2)
        self.assertEqual(r["price_history"][0]["price_text"], "200 €")
        self.assertEqual(r["price_history"][1]["price_text"], "160 €")

        delete_search(s_id)

    def test_match_reason_snippets(self):
        search = {
            "keywords": "Thinkpad, 16GB",
            "case_sensitive": False,
            "search_in_description": True
        }
        matched, reason = matches_keywords(
            search,
            title="Lenovo Thinkpad T480",
            description="Ausstattung: Intel Core i5, 16GB RAM und 512GB SSD.",
            ocr_text=""
        )
        self.assertTrue(matched)
        self.assertIn("Titel ('Thinkpad')", reason)
        self.assertIn("Beschreibung: '16GB'", reason)

    def test_updater_module(self):
        from app.config import VERSION
        self.assertEqual(VERSION, "0.3.0")
        update_info = check_for_github_update()
        self.assertIn("current_version", update_info)
        self.assertEqual(update_info["current_version"], "0.3.0")

    def test_multi_pipe_or_syntax(self):
        search = {
            "keywords": "Thinkpad, T480 | T490 | T14",
            "case_sensitive": False,
            "search_in_description": True
        }
        # Matches T480
        m1, _ = matches_keywords(search, title="Lenovo Thinkpad T480", description="", ocr_text="")
        self.assertTrue(m1)

        # Matches T490
        m2, _ = matches_keywords(search, title="Lenovo Thinkpad T490", description="", ocr_text="")
        self.assertTrue(m2)

        # Matches T14
        m3, _ = matches_keywords(search, title="Lenovo Thinkpad T14 Gen 2", description="", ocr_text="")
        self.assertTrue(m3)

        # Does not match X280
        m4, _ = matches_keywords(search, title="Lenovo Thinkpad X280", description="", ocr_text="")
        self.assertFalse(m4)

    def test_recheck_and_notes_persistence(self):
        from app.database import (
            create_search,
            save_result,
            get_results,
            update_result_notes,
            update_result_status,
            recheck_existing_results_for_search
        )
        s_id = create_search({
            "name": "Recheck Test",
            "query": "Laptop",
            "keywords": "i7, 16GB",
            "min_price": 100,
            "max_price": 500,
            "search_in_description": True
        })

        uid1 = f"rec_1_{time.time()}"
        uid2 = f"rec_2_{time.time()}"
        r1_id = save_result({
            "search_id": s_id,
            "kleinanzeigen_id": uid1,
            "title": "Laptop i7 16GB RAM",
            "price": "300 €",
            "price_num": 300.0,
            "location": "Berlin",
            "url": "https://kleinanzeigen.de/rec1",
            "description": "Top Zustand",
            "ocr_text": "",
            "match_reason": "Treffer"
        })
        r2_id = save_result({
            "search_id": s_id,
            "kleinanzeigen_id": uid2,
            "title": "Laptop i3 4GB RAM",
            "price": "150 €",
            "price_num": 150.0,
            "location": "Hamburg",
            "url": "https://kleinanzeigen.de/rec2",
            "description": "Einfaches Notebook",
            "ocr_text": "",
            "match_reason": "Treffer"
        })

        # Set note and star on r1
        update_result_notes(r1_id, "Wichtig: Akku fast neu")
        update_result_status(r1_id, "starred")

        # Update search criteria: must have "i7"
        stats = recheck_existing_results_for_search(s_id)
        self.assertEqual(stats["kept"], 1)
        self.assertEqual(stats["removed"], 1)

        remaining = get_results(search_id=s_id)
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["id"], r1_id)
        self.assertEqual(remaining[0]["notes"], "Wichtig: Akku fast neu")
        self.assertEqual(remaining[0]["status"], "starred")

    def test_ai_engine_heuristics(self):
        from app.ai_engine import evaluate_deal_score, evaluate_safety_risk, generate_negotiation_reply

        # Test deal score
        deal = evaluate_deal_score(
            title="Apple MacBook Air M1 8GB 256GB",
            price=250.0,
            description="MacBook Air M1 in gutem Zustand mit OVP und Ladekabel.",
            max_budget=400.0
        )
        self.assertIn("score", deal)
        self.assertGreaterEqual(deal["score"], 0)
        self.assertLessEqual(deal["score"], 100)
        self.assertIn("verdict", deal)

        # Test safety score with scam phrase
        safety_scam = evaluate_safety_risk(
            title="iPhone 15 Pro neu versiegelt",
            price=200.0,
            description="Verkauf nur mit Zahlung per PayPal Freunde und Familie oder Gutscheinkarten."
        )
        self.assertIn("risk_level", safety_scam)
        self.assertIn(safety_scam["risk_level"], ["mittel", "hoch"])
        self.assertGreater(len(safety_scam.get("flags", [])), 0)

        # Test negotiation generator
        neg = generate_negotiation_reply(
            title="Sony WH-1000XM4 Kopfhörer",
            current_price=150.0,
            description="Kopfhörer OVP",
            target_price=120.0,
            style="freundlich",
            stop_condition="abbrechen wenn unter 110",
            ai_settings={"ai_provider": "heuristic"}
        )
        self.assertIn("reply_text", neg)
        self.assertTrue(len(neg["reply_text"]) > 10)
        self.assertIn("120", neg["reply_text"])

    def test_facebook_scraper_basics(self):
        from app.facebook_scraper import build_fb_search_url, parse_fb_price

        url = build_fb_search_url(
            query="Gartenmoebel",
            min_price=50,
            max_price=200,
            location_slug="berlin"
        )
        self.assertIn("marketplace", url)
        self.assertIn("minPrice=50", url)
        self.assertIn("maxPrice=200", url)

        self.assertEqual(parse_fb_price("80 €"), 80.0)
        self.assertEqual(parse_fb_price("Kostenlos"), 0.0)
        self.assertEqual(parse_fb_price("€ 1.250"), 1250.0)

if __name__ == "__main__":
    unittest.main()

