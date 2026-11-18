import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import ingest


TODAY = date(2026, 11, 18)
CUTOFF = date(2026, 7, 21)


class IngestionTests(unittest.TestCase):
    def test_classify_new_homes(self):
        self.assertEqual(ingest.classify("Residential Building", "Single Family - New"), "Single-family")
        self.assertEqual(ingest.classify("NEW MULTI-FAMILY", ""), "Multifamily")
        self.assertEqual(ingest.classify("NEW COMMERCIAL", ""), "Commercial")
        self.assertEqual(ingest.classify("Commercial", "Addition"), "Addition")

    def test_filters_future_permit_and_old_permit(self):
        base = {"permit_number": "CPBR-2026-0001", "permit_type": "Residential Building",
                "work_class": "Single Family - New", "main_address_line1": "101 Main St"}
        self.assertIsNone(ingest.normalize("kcmo", {**base, "issue_date": "2090-01-01"}, TODAY, CUTOFF))
        self.assertIsNone(ingest.normalize("kcmo", {**base, "issue_date": "2019-01-01"}, TODAY, CUTOFF))

    def test_source_record_is_not_portal(self):
        raw = {"permit_number": "CPBR-2026-0001", "issue_date": "2026-11-01T12:00:00",
               "permit_type": "Residential Building", "work_class": "Single Family - New",
               "main_address_line1": "101 Main St"}
        item = ingest.normalize("kcmo", raw, TODAY, CUTOFF)
        self.assertEqual(item["link_kind"], "search")
        self.assertIn("compasskc", item["permit_url"])
        self.assertIn("permit_number=CPBR", item["source_url"])
        self.assertGreater(item["score"], 70)

    def test_arcgis_field_mapping(self):
        raw = {"attributes": {"PERMITNUMBER": "123", "ISSUEDATE": 1794355200000,
               "PermitType": "Building", "PermitWorkclass": "Single Family",
               "ADDRESS": "A Street", "VALUE": 320000}}
        item = ingest.normalize("olathe", raw, TODAY, CUTOFF)
        self.assertEqual(item["jurisdiction"], "Olathe, KS")
        self.assertEqual(item["category"], "Single-family")
        self.assertEqual(item["county"], "Johnson")
        self.assertEqual(item["valuation"], 320000)

    def test_urls_not_fabricated(self):
        self.assertIsNone(ingest.safe_url("javascript:alert(1)"))
        self.assertIsNone(ingest.safe_url("http://example.com"))
        self.assertEqual(ingest.safe_url("https://example.com/permit/1"), "https://example.com/permit/1")

    def test_valuation_outlier_and_valid_zero(self):
        self.assertIsNone(ingest.number("6400000000"))
        self.assertEqual(ingest.number("0"), 0)
        self.assertIsNone(ingest.number("-5"))

    def test_missing_date_not_a_lead(self):
        self.assertIsNone(ingest.normalize("lees_summit", {"attributes": {"PermitNumber": "1"}}, TODAY, CUTOFF))


if __name__ == "__main__":
    unittest.main()
