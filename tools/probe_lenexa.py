#!/usr/bin/env python3
"""Public-source evidence probe for Lenexa permit reports.

This is a metadata-only probe, not a permit adapter and not an excuse to
assume city-level monthly summary counts are individual permit records.
"""
from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
import requests

ROOT = Path(__file__).resolve().parents[1]
REPORTS = "https://www.lenexa.com/Business-Development/Design-Construction/Building-Permit-Reports"
PORTAL = "https://aca-prod.accela.com/LENEXA/Default.aspx"
COUNTY_SERVICE = "https://maps.jocogov.org/ArcGIS/rest/services/Permits/MapServer"
CITY_HOSTS = frozenset(("lenexa.com", "www.lenexa.com"))
MONTHS = ("07", "08", "09", "10")
VERSIONS = ("1", "2")
# Candidate URLs must not be displayed as established sources unless the
# server actually verifies they are PDFs.
CANDIDATES = tuple(
    "https://www.lenexa.com/files/sharedassets/city/v/{}/business-development/bpr/"
    "2026-building-permit-reports/{}-2026-building-permit-report.pdf".format(v, m)
    for v in VERSIONS for m in MONTHS
)

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls=[]
    def handle_starttag(self,tag,attrs):
        if tag!="a":return
        for k,v in attrs:
            if k=="href" and v:self.urls.append(v)

def official_city(url):
    u=urlsplit(url)
    return u.scheme=="https" and u.hostname in CITY_HOSTS

def probe(session):
    evidence={"source":"City of Lenexa monthly permit reports","report_page":REPORTS,
              "human_permit_search":PORTAL,"confirmed_report_pdfs":[],
              "monthly_report_links_found":[],"unconfirmed_candidates":[],
              "county_legacy_service_status":"unverified",
              "verified_row_level_feed":False,"notes":[]}
    try:
        r=session.get(REPORTS,timeout=(8,22),allow_redirects=True)
        r.raise_for_status()
        if not official_city(r.url):raise ValueError("Report page redirected outside the city")
        if len(r.content)>1_000_000:raise ValueError("Report page unexpectedly large")
        evidence["report_page_http_status"]=r.status_code
        parser=Links()
        parser.feed(r.text)
        candidates=[urljoin(r.url,x) for x in parser.urls
                    if x.lower().split("?")[0].endswith(".pdf") and official_city(urljoin(r.url,x))]
        evidence["monthly_report_links_found"]=sorted(set(candidates))[:100]
        print("REPORT_PAGE",r.status_code,"HTML_BYTES",len(r.content),"PDF_LINKS",len(candidates))
    except (requests.RequestException,ValueError) as e:
        evidence["notes"].append("Official report page could not be parsed: "+type(e).__name__)
        print("REPORT_PAGE_ERROR",type(e).__name__,str(e)[:150])

    for url in CANDIDATES:
        try:
            r=session.get(url,timeout=(8,16),stream=True,allow_redirects=True,
                          headers={"Range":"bytes=0-31","Accept":"application/pdf"})
            if not official_city(r.url):
                raise ValueError("PDF response redirected outside city")
            part=b""
            for chunk in r.iter_content(64):
                part+=chunk
                if len(part)>=32:break
            if r.status_code in (200,206) and part.startswith(b"%PDF-"):
                evidence["confirmed_report_pdfs"].append(r.url)
                print("CONFIRMED_CITY_PDF",r.url,r.status_code)
            else:
                evidence["unconfirmed_candidates"].append(
                    {"month":url.rsplit("/",1)[-1][:2],"version":url.split("/v/")[1].split("/")[0],
                     "status":r.status_code,"response_type":r.headers.get("content-type","")[:60]})
        except (requests.RequestException,ValueError) as e:
            evidence["unconfirmed_candidates"].append({"url_template_month":url.rsplit("/",1)[-1][:2],
                                                          "error":type(e).__name__})
    print("CONFIRMED_CITY_PDFS",len(evidence["confirmed_report_pdfs"]),
          "UNCONFIRMED",len(evidence["unconfirmed_candidates"]))
    # AIMS explicitly describes an old county Permits MapServer on its
    # historical documentation, but it may no longer be published.
    try:
        r=session.get(COUNTY_SERVICE,params={"f":"json"},timeout=(8,16),allow_redirects=False)
        if r.status_code==200:
            payload=r.json()
            evidence["county_legacy_service_status"] = (
                "api_error_or_not_a_map_service" if "error" in payload
                else "reachable_requires_issuer_and_freshness_validation"
                if isinstance(payload.get("layers"),list) else "unverified_payload"
            )
        else:
            evidence["county_legacy_service_status"]="HTTP "+str(r.status_code)
    except (requests.RequestException,ValueError) as e:
        evidence["county_legacy_service_status"]="unavailable: "+type(e).__name__
    print("COUNTY_LEGACY_PERMITS",evidence["county_legacy_service_status"])
    evidence["notes"].append(
        "City monthly permit reports can contain summary activity and >=$250k named commercial projects, "
        "but do not by themselves establish an individual permit ID, issuance day, or residential site for every entry."
    )
    return evidence

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    s=requests.Session()
    s.headers.update({"User-Agent":"Kansas-Missouri-Construction-Intelligence/Lenexa-SourceAudit (public metadata only)"})
    result=probe(s)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("SOURCE_SCOPE",result["source"])
    return 0

if __name__=="__main__":
    raise SystemExit(main())
