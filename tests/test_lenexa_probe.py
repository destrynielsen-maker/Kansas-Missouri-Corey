import sys
import unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from probe_lenexa import official_city, Links, CANDIDATES

class LenexaSourceProbeTests(unittest.TestCase):
    def test_only_verified_city_host_allowed(self):
        self.assertTrue(official_city("https://www.lenexa.com/foo.pdf"))
        self.assertTrue(official_city("https://lenexa.com/reports"))
        self.assertFalse(official_city("http://www.lenexa.com/foo.pdf"))
        self.assertFalse(official_city("https://www.lenexa.com.evil.org/file.pdf"))
        self.assertFalse(official_city("https://www.notlenexa.com/file.pdf"))
    def test_candidate_range_is_bounded(self):
        self.assertEqual(len(CANDIDATES),8)
        self.assertTrue(all(x.startswith("https://www.lenexa.com/") for x in CANDIDATES))
        self.assertTrue(all("2026-building-permit-reports" in x for x in CANDIDATES))
    def test_link_parser_ignores_non_anchor_scripts(self):
        p=Links()
        p.feed('<a href="2026/09.pdf">report</a><script src="bad.pdf"></script>')
        self.assertEqual(p.urls,["2026/09.pdf"])
if __name__=="__main__":
    unittest.main()
