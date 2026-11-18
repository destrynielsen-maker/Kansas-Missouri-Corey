"""Bounded diagnostics for the official Independence, Missouri permit portal.

This is NOT an ingestion connector. It requests only public GET pages/assets,
never authenticates, guesses undocumented API routes, or harvests user records.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import requests

PAGES = (
    "https://opendata.independencemo.gov/dataset?code=V1BUILDINGPERMITS",
    "https://opendata.independencemo.gov/",
    "https://apps.indepmo.org/Apps/OpenData/BuildingPermits",
    "https://apps.indepmo.org/Apps/OpenData/BuildingPermits/Sort?head=Date+Issued",
)
ALLOWED = {"opendata.independencemo.gov", "apps.indepmo.org"}
HINTS = re.compile(r"V1BUILDINGPERMITS|api/(?:v\d+/)?[a-z\-_/]+|apiBaseUrl|baseURL|dataset[s]?|download(?:url)?", re.I)


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = []
    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        if tag == "script" and props.get("src"):
            self.assets.append(props["src"])
        if tag == "link" and props.get("rel") in ("modulepreload","preload") and props.get("href"):
            self.assets.append(props["href"])


def safe_get(session, url):
    if urlsplit(url).hostname not in ALLOWED:
        raise ValueError("Blocked nonmunicipal URL")
    r=session.get(url, timeout=(8, 15), allow_redirects=True, headers={"Accept":"text/html,application/json,*/*"})
    if urlsplit(r.url).hostname not in ALLOWED:
        raise ValueError("Unexpected cross-host redirect")
    if len(r.content)>2_000_000:
        raise ValueError("Response exceeds 2 MB")
    return r


def main():
    s=requests.Session()
    s.headers.update({"User-Agent":"Kansas-Missouri-Construction-Intelligence/SourceAudit (public metadata only)"})
    for url in PAGES:
        try:
            r=safe_get(s,url)
            print("PAGE",r.status_code,"final",r.url,"length",len(r.content),"type",r.headers.get("content-type","?"))
            if r.status_code != 200 or "html" not in r.headers.get("content-type",""):
                continue
            parser=Assets()
            parser.feed(r.text)
            assets=[urljoin(r.url,x) for x in parser.assets]
            assets=list(dict.fromkeys(x for x in assets if urlsplit(x).hostname in ALLOWED))
            print("PUBLIC_ASSETS",[(urlsplit(a).path) for a in assets[:14]])
            print("PAGE_HINTS",list(dict.fromkeys(m.group(0) for m in HINTS.finditer(r.text)))[:15])
            if "opendata.independencemo.gov" not in r.url:continue
            for asset in assets[:5]:
                try:
                    result=safe_get(s,asset)
                    print("ASSET",result.status_code,urlsplit(result.url).path,"length",len(result.content))
                    if result.status_code!=200 or len(result.content)>750_000:
                        continue
                    snippet=[]
                    for match in list(HINTS.finditer(result.text))[:12]:
                        start=max(0,match.start()-65)
                        end=min(len(result.text),match.end()+115)
                        context=result.text[start:end].replace("\n"," ")
                        context=re.sub(r"(?:Bearer|token|api[_-]?key)[\"']?\s*[:=]\s*[\"'][^\"']+", "[redacted]",context,flags=re.I)
                        snippet.append(context[:230])
                    print("ASSET_HINTS",snippet[:12])
                except (requests.RequestException,ValueError) as e:
                    print("ASSET_ERROR",type(e).__name__,str(e)[:180])
        except (requests.RequestException,ValueError) as e:
            print("PAGE_ERROR",url,type(e).__name__,str(e)[:200])


if __name__=="__main__":
    main()
