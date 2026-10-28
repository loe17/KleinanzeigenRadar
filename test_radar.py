import sys
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

        # Result creation
        res_id = save_result({
            "search_id": s_id,
            "kleinanzeigen_id": "test_ad_9999",
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
            "kleinanzeigen_id": "test_ad_9999",
            "title": "Lenovo Thinkpad T480 i5 16GB",
            "url": "https://www.kleinanzeigen.de/s-anzeige/test/9999"
        })
        self.assertIsNone(dup_id, "Duplicate ads should return None")

        # Second result for sort testing
        res_id2 = save_result({
            "search_id": s_id,
            "kleinanzeigen_id": "test_ad_8888",
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
            "kleinanzeigen_id": "test_ad_7777",
            "title": "Lenovo Thinkpad T480 i7",
            "price": "220 €",
            "price_num": 220.0,
            "url": "https://www.kleinanzeigen.de/s-anzeige/test/7777"
        })
        # Status update
        update_result_status(res_id3, "starred")
        results_starred = get_results(status="starred")
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

    def test_updater_module(self):
        from app.config import VERSION
        self.assertEqual(VERSION, "0.1.6")
        update_info = check_for_github_update()
        self.assertIn("current_version", update_info)
        self.assertEqual(update_info["current_version"], "0.1.6")

if __name__ == "__main__":
    unittest.main()

