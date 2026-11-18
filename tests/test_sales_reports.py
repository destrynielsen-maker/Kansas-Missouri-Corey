import copy
import sys
import unittest
from pathlib import Path
from datetime import datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from build_sales_reports import build, validate_evidence


def permit(id, builder=False):
    return {"id":id,"permit_number":id.split(":")[-1],"issued":"2026-11-13",
            "address":"123 Main St.","jurisdiction":"Kansas City, MO","state":"MO",
            "category":"Single-family","site_group_id":"site-1",
            "valuation":None,"square_feet":None,"project":"","link_kind":"search"}


def evidence(id, company="Homebuilder LLC"):
    return {"id":id,"issued":"2026-11-13","address":"123 MAIN ST",
            "jurisdiction":"Kansas City, MO","builder":company,
            "evidence_type":"exact_address_listing","evidence_url":"https://builder.example.com/home/1",
            "qualification":"Builder shown by exact-address listing, not by city permit."}


def snapshot():
    rows=[permit("kcmo:P001"),permit("kcmo:P002")]
    return {"generated_at":"2026-11-18T18:00:00+00:00","count":2,"permits":rows}


class BuilderReportTests(unittest.TestCase):
    def test_exact_evidence_creates_company_rollup(self):
        official=snapshot()
        research={"reviewed_on":"2026-11-18","entries":[evidence("kcmo:P001")]}
        coverage,rank=build(official,research)
        self.assertEqual(coverage["total_permits"],2)
        self.assertEqual(coverage["builder_research_matched_permits"],1)
        self.assertEqual(coverage["jurisdictions"]["Kansas City, MO"]["fields_available"]["valuation"],0)
        self.assertEqual(coverage["jurisdictions"]["Kansas City, MO"]["fields_available"]["square_feet"],0)
        self.assertEqual(coverage["jurisdictions"]["Kansas City, MO"]["fields_available"]["independent_builder_company"],1)
        self.assertEqual(rank["builders"][0]["permit_count"],1)

    def test_conflicting_builder_address_is_rejected(self):
        other=evidence("kcmo:P001")
        other["address"]="101 Different Ave"
        with self.assertRaisesRegex(ValueError,"does not match exact"):
            build(snapshot(),{"entries":[other]})

    def test_source_aged_out_does_not_block_refresh(self):
        c,r=build(snapshot(),{"entries":[evidence("kcmo:OLD")]})
        self.assertEqual(c["research_entries_aged_out"],1)
        self.assertEqual(c["builder_research_matched_permits"],0)
        self.assertEqual(r["builders"],[])

    def test_same_development_counts_permits_and_distinct_projects_separately(self):
        official=snapshot()
        extra=[evidence("kcmo:P001"),evidence("kcmo:P002")]
        for x in extra:
            x["project_group"]="Promise Place"
        c,r=build(official,{"entries":extra})
        self.assertEqual(r["builders"][0]["permit_count"],2)
        self.assertEqual(r["builders"][0]["estimated_distinct_project_groups"],1)

    def test_bad_source_url_or_evidence_is_rejected(self):
        r=evidence("kcmo:P001")
        r["evidence_url"]="javascript:alert(1)"
        with self.assertRaisesRegex(ValueError,"HTTPS"):
            validate_evidence(r)
        r["evidence_url"]="https://builder.example.com/home"
        r["evidence_type"]="definite_licensed_gc"
        with self.assertRaisesRegex(ValueError,"Unsupported"):
            validate_evidence(r)

    def test_duplicates_are_rejected(self):
        x=evidence("kcmo:P001")
        with self.assertRaisesRegex(ValueError,"Duplicated"):
            build(snapshot(),{"entries":[x,copy.deepcopy(x)]})


if __name__=="__main__":
    unittest.main()
