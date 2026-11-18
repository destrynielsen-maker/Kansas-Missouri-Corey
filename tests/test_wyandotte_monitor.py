import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from monitor_wyandotte import inspect, catalog_url, FOLDERS


class FakeResponse:
    def __init__(self, url, services=None, bad=False):
        self.url = url
        self._payload = {"services": services} if not bad else {"error":{"message":"Forbidden"}}
        self.content = b'{"services":[]}'
    def raise_for_status(self):
        pass
    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, by_folder):
        self.by_folder=by_folder
        self.calls=[]
    def get(self,url,params=None,timeout=None,allow_redirects=True):
        self.calls.append((url,params,timeout,allow_redirects))
        folder=url.split("/rest/services",1)[1].strip("/")
        value=self.by_folder.get(folder)
        if isinstance(value,Exception):
            raise value
        return FakeResponse(url,value if value is not None else [])


class SourceMonitoringTests(unittest.TestCase):
    def test_no_false_positive_from_buildings_and_zoning(self):
        s=FakeSession({"GISPUB":[{"name":"GISPUB/Buildings_Footprints","type":"FeatureServer"},
                                 {"name":"GISPUB/Parcel_Polygons","type":"FeatureServer"},
                                 {"name":"GISPUB/Kansas_City_Ks_Zoning","type":"MapServer"}]})
        r=inspect(s,datetime(2026,11,18,tzinfo=timezone.utc))
        self.assertEqual(r["source_status"],"no_permit_named_service_in_reviewed_public_catalogs")
        self.assertFalse(r["verified_bulk_permit_feed"])
        self.assertEqual(r["candidate_services"],[])
        self.assertEqual(len(s.calls),len(FOLDERS))
        self.assertTrue(all(x[3] is False for x in s.calls),"Never follow unapproved redirects")

    def test_named_candidates_are_never_verified_by_monitor(self):
        s=FakeSession({"GISPUB":[{"name":"GISPUB/Building_Permits_Issued","type":"FeatureServer"},
                                 {"name":"GISPUB/Parcel_Polygons","type":"MapServer"}]})
        r=inspect(s)
        self.assertEqual(r["source_status"],"candidate_service_names_require_validation")
        self.assertEqual(len(r["candidate_services"]),1)
        self.assertIs(r["candidate_services"][0]["verified_permit_feed"],False)

    def test_unavailable_catalog_does_not_mean_no_feed(self):
        import requests
        s=FakeSession({"GISPUB": requests.Timeout("blocked")})
        r=inspect(s)
        self.assertEqual(r["source_status"],"incomplete_public_catalog_review")
        self.assertEqual(len([x for x in r["catalogs"] if x["result"]=="unavailable"]),1)

    def test_reject_unreviewed_catalog(self):
        with self.assertRaises(ValueError):
            catalog_url("GISEDITS")
        with self.assertRaises(ValueError):
            catalog_url("../admin")

    def test_source_monitor_has_no_permit_records(self):
        r=inspect(FakeSession({}))
        self.assertNotIn("permits",r)
        self.assertNotIn("permit_count",r)


if __name__=="__main__":
    unittest.main()
