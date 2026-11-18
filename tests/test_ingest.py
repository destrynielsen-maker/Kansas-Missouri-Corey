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

    def test_priority_classification_does_not_count_remodels(self):
        self.assertEqual(ingest.classify("CPPU - Building (Residential)", "Single Family - Interior Remodel"), "Remodel")
        self.assertEqual(ingest.classify("CPPU - Building (Residential)", "Single Family - Addition"), "Addition")
        self.assertEqual(ingest.classify("CPPU - Building (Commercial)", "Renovation", "NEW OFFICE TF"), "Remodel")
        self.assertEqual(ingest.classify("CPPU - Building (Commercial)", "New"), "Commercial")

    def test_priority_classification_structural_builds(self):
        self.assertEqual(ingest.classify("Building (Residential)", "New Single Family"), "Single-family")
        self.assertEqual(ingest.classify("Building - Residential", "Single Family", "SFR"), "Single-family")
        self.assertEqual(ingest.classify("CPPU - Building (Residential)", "Townhouse - New"), "Multifamily")
        self.assertEqual(ingest.classify("Building - Commercial", "New Multi Family"), "Multifamily")
        self.assertEqual(ingest.classify("NEW DUPLEX", ""), "Multifamily")
        self.assertEqual(ingest.classify("Building (Commercial)", "New Restaurant"), "Commercial")
        self.assertEqual(ingest.classify("NEW SHELL BUILDING", ""), "Commercial")

    def test_non_building_permits_excluded(self):
        for ptype, work in [
            ("Building (Mech/Elec/Plumb)", "Furnace/AC"),
            ("Building (Mech/Elec/Plumb)", "Electrical Service"),
            ("Building (Residential)", "Fence/Wall"),
            ("Building (Residential)", "Deck"),
            ("Building - Demolition", "Residential"),
            ("Land Disturbance Permit", "Grading Only"),
            ("Building (Commercial)", "Tenant Finish/Remodel"),
            ("CHANGE OF TENANT", ""),
            ("NEW TENANT FINISH", ""),
        ]:
            self.assertIn(ingest.classify(ptype, work), ("Other", "Remodel"), (ptype, work))

    def test_closed_permit_excluded(self):
        base={"permit_number":"CPBR-2026-0001", "issue_date":"2026-10-30",
              "permit_type":"CPPU - Building (Residential)", "work_class":"Single Family - New",
              "main_address_line1":"101 Main"}
        for status in ["Closed","Cancelled","Hold","Complete/Finaled","Suspended"]:
            self.assertIsNone(ingest.normalize("kcmo",{**base,"permit_status":status},TODAY,CUTOFF))

    def test_relevance_filter_excludes_residential_remodel(self):
        base={"permit_number":"CPBR-2026-0001", "issue_date":"2026-10-30",
              "permit_type":"CPPU - Building (Residential)", "work_class":"Single Family - Interior Remodel",
              "main_address_line1":"101 Main","permit_status":"Issued"}
        self.assertIsNone(ingest.normalize("kcmo",base,TODAY,CUTOFF))


    def test_kcmo_milestones_do_not_estimate_groundbreaking(self):
        row={"permit_number":"CPBR-2026-0099", "issue_date":"2026-10-01",
             "permit_type":"CPPU - Building (Residential)", "work_class":"Single Family - New",
             "permit_status":"Issued","main_address_line1":"100 Test Drive",
             "application_date":"2026-09-10","last_inspection_date":"2026-11-15",
             "expiration_date":"2027-04-01"}
        lead=ingest.normalize("kcmo",row,TODAY,CUTOFF)
        self.assertEqual(lead["application_date"],"2026-09-10")
        self.assertEqual(lead["last_inspection_date"],"2026-11-15")
        self.assertEqual(lead["expiration_date"],"2027-04-01")
        self.assertEqual(lead["inspection_evidence"],"inspection_recorded")
        self.assertIsNone(lead["start_date"])
        self.assertEqual(lead["start_date_source"],"not_published")

    def test_overland_park_milestones(self):
        row={"attributes":{"CaseNumber":"BLD-R-26-09","IssueDate":1790812800000,
             "PermitType":"Building (Residential)","WorkClass":"New Single Family",
             "PermitStatus":"Issued","MainAddressLine1":"400 Street",
             "ApplyDate":1788220800000,"LastInspectionDate":1793491200000,
             "ExpireDate":1825027200000}}
        lead=ingest.normalize("overland_park",row,TODAY,CUTOFF)
        self.assertEqual(lead["application_date"],"2026-09-01")
        self.assertEqual(lead["last_inspection_date"],"2026-11-01")
        self.assertEqual(lead["inspection_evidence"],"inspection_recorded")

    def test_missing_inspection_field_is_not_same_as_blank(self):
        kc=ingest.extract_timeline("kcmo",{},TODAY,TODAY)
        self.assertEqual(kc["inspection_evidence"],"date_not_reported")
        ol=ingest.extract_timeline("olathe",{"attributes":{}},TODAY,TODAY)
        self.assertEqual(ol["inspection_evidence"],"field_not_published")
        ls=ingest.extract_timeline("lees_summit",{"attributes":{"dateExpiration":1794700800000}},date(2026,10,1),TODAY)
        self.assertEqual(ls["inspection_evidence"],"field_not_published")
        self.assertEqual(ls["expiration_date"],"2026-11-15")

    def test_finaled_date_blocks_stale_issued_record(self):
        row={"permit_number":"CPBR-2026-0100","issue_date":"2026-10-01",
             "permit_type":"CPPU - Building (Residential)","work_class":"Single Family - New",
             "permit_status":"Issued","main_address_line1":"100 Test Drive",
             "finaled_date":"2026-11-02"}
        self.assertIsNone(ingest.normalize("kcmo",row,TODAY,CUTOFF))

    def test_anomalous_milestones_flagged_not_used(self):
        raw={"last_inspection_date":"2026-09-01","application_date":"2026-10-15",
             "expiration_date":"2026-05-01"}
        timing=ingest.extract_timeline("kcmo",raw,date(2026,10,1),TODAY)
        self.assertIsNone(timing["last_inspection_date"])
        self.assertIsNone(timing["application_date"])
        self.assertIsNone(timing["expiration_date"])
        self.assertEqual(timing["inspection_evidence"],"date_not_reported")
        self.assertIn("inspection_before_issue",timing["timeline_warnings"])
        self.assertIn("application_after_issue",timing["timeline_warnings"])


    def test_overland_park_uses_published_parcel_fee_ward_not_builder(self):
        raw={"attributes":{
            "CaseNumber":"BLD-R-2026-00001","IssueDate":1790812800000,
            "PermitType":"Building (Residential)","WorkClass":"New Single Family",
            "PermitStatus":"Issued","MainAddressLine1":"101 Example St",
            "MainParcelNumber":"NP123-45","TotalFeeAmount":2100.22,"WARD":3,
            "AssignedTo":"Permit Office Staff"
        }}
        item=ingest.normalize("overland_park",raw,TODAY,CUTOFF)
        self.assertEqual(item["parcel_number"],"NP123-45")
        self.assertEqual(item["permit_fee"],2100.22)
        self.assertEqual(item["ward"],"3")
        self.assertNotIn("builder",item)
        self.assertNotIn("contractor",item)

    def test_olathe_ward_is_not_a_builder(self):
        raw={"attributes":{"PERMITNUMBER":"BR26-01","ISSUEDATE":1790812800000,
             "PermitType":"Building - Residential","PermitWorkclass":"Single Family",
             "ADDRESS":"123 Test Lane","WARD":"2"}}
        item=ingest.normalize("olathe",raw,TODAY,CUTOFF)
        self.assertEqual(item["ward"],"2")
        self.assertIsNone(item["parcel_number"])

    def test_lee_summit_internal_record_id_is_not_a_public_deep_link(self):
        raw={"attributes":{"PermitNumber":"PRRES2026001","dateissued":1790812800000,
             "PermitType":"NEW SINGLE FAMILY","Location":"100 First Lane","RecordID":91823}}
        item=ingest.normalize("lees_summit",raw,TODAY,CUTOFF)
        self.assertEqual(item["agency_record_id"],"91823")
        self.assertEqual(item["link_kind"],"search")


    def test_kcmo_published_parcel_is_not_a_person_or_builder(self):
        raw={"permit_number":"CPBR-2026-99999","issue_date":"2026-11-13",
             "permit_type":"CPPU - Building (Residential)","work_class":"Single Family - New",
             "main_address_line1":"123 Main St","permit_status":"Issued",
             "main_parcel_number":"123456789012345"}
        rec=ingest.normalize("kcmo",raw,TODAY,CUTOFF)
        self.assertEqual(rec["parcel_number"],"123456789012345")
        self.assertIsNone(rec["permit_fee"])
        self.assertNotIn("builder",rec)


if __name__ == "__main__":
    unittest.main()
