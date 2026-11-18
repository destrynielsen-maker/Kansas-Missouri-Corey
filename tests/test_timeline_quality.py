"""Protect the published timeline from invented construction starts or inspection evidence."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import audit_snapshot


class SourceEvidenceTests(unittest.TestCase):
    def sample(self):
        return {
            "generated_at":"2026-11-18T12:00:00+00:00",
            "count":1,
            "sources":[{"name":"Kansas City, MO"}],
            "permits":[{
                "id":"kcmo:P001","permit_number":"P001","issued":"2026-11-18",
                "jurisdiction":"Kansas City, MO","state":"MO",
                "category":"Single-family","status":"Issued","score":85,
                "permit_url":"https://compasskc.kcmo.org/",
                "source_url":"https://data.kcmo.org/resource/w8jz-wjgn.json",
                "link_kind":"search","inspection_evidence":"date_not_reported",
                "last_inspection_date":None,"start_date":None,
                "start_date_source":"not_published",
            }],
        }

    def test_valid_unknown_start_retained(self):
        out=audit_snapshot.summarize(self.sample())
        self.assertEqual(out["total_records"],1)

    def test_fabricated_start_rejected(self):
        data=self.sample()
        data["permits"][0]["start_date"]="2026-11-19"
        with self.assertRaisesRegex(ValueError,"Unverified construction start"):
            audit_snapshot.summarize(data)

    def test_inspection_claim_needs_date(self):
        data=self.sample()
        data["permits"][0]["inspection_evidence"]="inspection_recorded"
        with self.assertRaisesRegex(ValueError,"Inspection evidence"):
            audit_snapshot.summarize(data)

    def test_inspection_date_needs_label(self):
        data=self.sample()
        data["permits"][0]["last_inspection_date"]="2026-11-18"
        with self.assertRaisesRegex(ValueError,"Inspection date lacks"):
            audit_snapshot.summarize(data)


if __name__ == "__main__":
    unittest.main()
