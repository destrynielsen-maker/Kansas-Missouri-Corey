"""Lenexa planning prospects must never be treated as issued construction permits."""
import json
import unittest
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"docs/data/lenexa_planning.json"
PERMITS=ROOT/"docs/data/permits.json"

class LenexaPlanningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(DATA.read_text(encoding="utf-8"))

    def test_official_source_and_review_date(self):
        d=self.data
        self.assertEqual(d["jurisdiction"],"Lenexa, KS")
        self.assertEqual(d["reviewed_on"],"2026-11-18")
        self.assertEqual(d["source_section"],"Pending applications")
        self.assertEqual(urlsplit(d["source_url"]).hostname,"www.lenexa.com")
        self.assertIn("Planning-Commission",d["source_url"])

    def test_no_issued_permit_claims(self):
        d=self.data
        self.assertIs(d["verified_permit_feed"],False)
        self.assertEqual(d["permit_records_in_dataset"],0)
        self.assertIn("NOT building permits",d["disclaimer"])
        for entry in d["opportunities"]:
            self.assertIsNone(entry["permit_number"])
            self.assertIsNone(entry["permit_issue_date"])
            self.assertIsNone(entry["construction_start"])
            self.assertEqual(entry["source_url"],d["source_url"])

    def test_clear_status_and_unique_project_evidence(self):
        entries=self.data["opportunities"]
        self.assertEqual(len(entries),11)
        self.assertEqual(len({x["id"] for x in entries}),len(entries))
        self.assertEqual(sum(x["application_status"]=="On hold" for x in entries),1)
        self.assertEqual(sum(x["application_status"]=="Pending" for x in entries),10)
        for item in entries:
            self.assertTrue(item["id"].startswith("lenexa-plan-"))
            for field in ["project","location","proposed_work","planning_stage","category"]:
                self.assertIsInstance(item[field],str)
                self.assertTrue(item[field].strip())
            self.assertIn(item["location_precision"],["address","approximate"])

    def test_planning_items_not_published_as_permits(self):
        snapshot=json.loads(PERMITS.read_text(encoding="utf-8"))
        self.assertNotIn("Lenexa, KS",{x["jurisdiction"] for x in snapshot.get("permits",[])})
        self.assertEqual(snapshot.get("count"),len(snapshot.get("permits",[])))

if __name__=="__main__":
    unittest.main()
