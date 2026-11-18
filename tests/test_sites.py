"""Conservative site matching: same address, not assumed same construction project."""
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import ingest
import audit_snapshot

def record(id, number, address, city="Kansas City, MO", state="MO"):
    return {"id":id,"permit_number":number,"address":address,
            "jurisdiction":city,"state":state,"category":"Single-family","issued":"2026-11-17"}

class SiteGroupingTests(unittest.TestCase):
    def test_exact_city_and_address_group_only(self):
        rows=[
            record("a","P-001","123 Main St."),
            record("b","P-002"," 123 MAIN ST "),
            record("c","P-003","123 Main St Apt 2"),
            record("d","P-004","123 Main St","Kansas City, KS","KS"),
            record("e","P-005",""),
            record("f","P-006",""),
        ]
        stats=ingest.annotate_site_groups(rows)
        self.assertEqual(stats,{"unique_sites":5,"multiple_permit_sites":1,"permits_on_multiple_permit_sites":2})
        self.assertEqual(rows[0]["site_group_id"],rows[1]["site_group_id"])
        self.assertNotEqual(rows[0]["site_group_id"],rows[2]["site_group_id"])
        self.assertNotEqual(rows[0]["site_group_id"],rows[3]["site_group_id"])
        self.assertNotEqual(rows[4]["site_group_id"],rows[5]["site_group_id"])
        self.assertEqual(rows[0]["site_permit_count"],2)
        self.assertEqual(rows[0]["site_related_permits"],["P-002","P-001"])
        self.assertEqual(rows[4]["site_group_basis"],"unverified_address")

    def test_site_counts_are_deterministic_regardless_of_row_order(self):
        r1=[record("a","001","100 Main St"),record("b","002","100 Main St"),record("c","003","102 Main St")]
        r2=list(reversed([dict(r) for r in r1]))
        self.assertEqual(ingest.annotate_site_groups(r1),ingest.annotate_site_groups(r2))
        self.assertEqual({x["id"]:x["site_group_id"] for x in r1},{x["id"]:x["site_group_id"] for x in r2})

    def test_invalid_jurisdiction_refuses_group(self):
        with self.assertRaises(ValueError):
            ingest.annotate_site_groups([{"id":"x","permit_number":"1","address":"100 Main","state":"MO","jurisdiction":""}])

    def test_audit_does_not_accept_inflated_counts(self):
        import copy
        snap={
            "generated_at":"2026-11-18T12:00:00Z",
            "count":2,"sources":[{"name":"Kansas City, MO"}],
            "permits":[]
        }
        for i in (1,2):
            row=record("kcmo:"+str(i),"P"+str(i),"100 Main")
            row.update({"permit_url":"https://compasskc.kcmo.org/",
                        "source_url":"https://data.kcmo.org/resource/w8jz-wjgn.json",
                        "score":80,"link_kind":"search","start_date":None,"start_date_source":"not_published",
                        "inspection_evidence":"date_not_reported","last_inspection_date":None})
            snap["permits"].append(row)
        snap["site_stats"]=ingest.annotate_site_groups(snap["permits"])
        self.assertEqual(audit_snapshot.summarize(snap)["site_stats"]["unique_sites"],1)
        snap["permits"][0]["site_permit_count"]=3
        with self.assertRaisesRegex(ValueError,"Site permit count"):
            audit_snapshot.summarize(snap)

if __name__ == "__main__":
    unittest.main()
