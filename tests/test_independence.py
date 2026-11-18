"""Contract tests for Independence's official public dataset, no invented row links."""
from datetime import date
from unittest import TestCase
from unittest.mock import patch
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import ingest

TODAY=date(2026,11,18)
CUTOFF=TODAY-ingest.timedelta(days=120)
FIELDS=list(ingest.INDEPENDENCE_FIELDS)


def make_row(permit,issued,ptype,description,address="100 MAIN ST",value="250000"):
    values={
        "Permit Number":permit,"Address":address,"Date Issued":issued,
        "Type":ptype,"Construction Description":description,"Construction Value":value,
    }
    return [{"title":name,"value":values[name],"containInHeader":"true","columnSpan":"col-span-3",
             "childObjects":[]} for name in FIELDS]


def fixture():
    rows=[
        make_row("2026-0001","11/17/2026","Residential","Single Family New Construction"),
        make_row("2026-0002","11/16/2026","Commercial","New Building w/ Health"),
        make_row("2026-0003","11/15/2026","Commercial","Addition w/o Health"),
        make_row("2026-0004","11/14/2026","Residential","Duplex"),
        make_row("2026-0005","11/13/2026","Commercial","Tenant Finish w/ Health"),
        make_row("2026-0006","11/12/2026","Trade","New Building"),
        make_row("2026-0007","07/01/2026","Residential","Single Family New Construction"),
        make_row("2026-0008","","Residential","Single Family New Construction"),
    ]
    rows += [make_row(f"2026-{x:04d}","11/16/2026","Trade","Electrical") for x in range(9,22)]
    return {
        "dataSetCode":"V1BUILDINGPERMITS","dataSetName":"Building Permits - Active",
        "lastUpdated":"2026-11-18T00:14:12.7292293",
        "status":0,"dataSetFields":[{"title":name,"id":i+457,"fieldType":1} for i,name in enumerate(FIELDS)],
        "dataSetData":rows,
    }


class IndependenceContractTests(TestCase):
    def test_live_schema_shape_and_filtered_new_builds(self):
        with patch.object(ingest,"fetch_json",return_value=fixture()):
            rows,stamp=ingest.fetch_independence(None,ingest.SOURCES["independence"],TODAY)
        self.assertEqual(len(rows),21)
        self.assertTrue(stamp.startswith("2026-11-18"))
        mapped=[ingest.normalize("independence",row,TODAY,CUTOFF) for row in rows]
        kept=[r for r in mapped if r]
        self.assertEqual(len(kept),4)
        self.assertEqual([r["category"] for r in kept],["Single-family","Commercial","Addition","Multifamily"])
        for item in kept:
            self.assertEqual(item["state"],"MO")
            self.assertEqual(item["county"],"Jackson")
            self.assertEqual(item["link_kind"],"search")
            self.assertEqual(item["source_url_scope"],"dataset")
            self.assertEqual(item["status"],"Status not published")
            self.assertIn("SearchPermitStatus",item["permit_url"])
            self.assertEqual(item["source_url"],ingest.SOURCES["independence"]["api"])
            self.assertIsNone(item["start_date"])
            self.assertEqual(item["inspection_evidence"],"field_not_published")

    def test_stale_feed_is_not_accepted(self):
        payload=fixture()
        payload["lastUpdated"]="2026-10-01T00:00:00"
        with patch.object(ingest,"fetch_json",return_value=payload):
            with self.assertRaisesRegex(ValueError,"stale"):
                ingest.fetch_independence(None,ingest.SOURCES["independence"],TODAY)

    def test_field_title_drift_is_blocked(self):
        payload=fixture()
        payload["dataSetFields"][2]["title"]="Date Approved"
        with patch.object(ingest,"fetch_json",return_value=payload):
            with self.assertRaisesRegex(ValueError,"missing required"):
                ingest.fetch_independence(None,ingest.SOURCES["independence"],TODAY)

    def test_nested_cell_mismatch_is_blocked(self):
        payload=fixture()
        payload["dataSetData"][0][2]["title"]="Approved"
        with patch.object(ingest,"fetch_json",return_value=payload):
            with self.assertRaisesRegex(ValueError,"field object changed"):
                ingest.fetch_independence(None,ingest.SOURCES["independence"],TODAY)

    def test_no_fabricated_independence_record_url(self):
        cfg=ingest.SOURCES["independence"]
        self.assertEqual(ingest.source_record_url(cfg,"2026-0001"),cfg["api"])

    def test_municipal_issued_date_format(self):
        self.assertEqual(ingest.to_date("7/8/2026"),date(2026,7,8))
        self.assertEqual(ingest.to_date("11/17/2026"),date(2026,11,17))
        self.assertIsNone(ingest.to_date("not a date"))

    def test_bad_dataset_code_or_scope_rejected(self):
        for field,value in [("dataSetCode","OTHER"),("dataSetName","Old Permits")]:
            payload=fixture()
            payload[field]=value
            with self.subTest(field=field),patch.object(ingest,"fetch_json",return_value=payload):
                with self.assertRaisesRegex(ValueError,"dataset"):
                    ingest.fetch_independence(None,ingest.SOURCES["independence"],TODAY)
