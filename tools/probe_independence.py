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
HINTS = re.compile(r"V1BUILDINGPERMITS|/api/[a-z0-9_/?=&.-]+|apiBaseUrl|NEXT_PUBLIC|fetch\(|/datasets?|export|download", re.I)


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = []
        self.links = []
    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        if tag == "a" and props.get("href"):
            self.links.append(props["href"])
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


def probe_documented_backend(session):
    """The city's published JS explicitly GETs /api/config and uses apiBaseUrl."""
    config_url="https://opendata.independencemo.gov/api/config"
    try:
        r=safe_get(session,config_url)
        print("CONFIG_STATUS",r.status_code,"type",r.headers.get("content-type","?"))
        if r.status_code!=200:return
        conf=r.json()
        if not isinstance(conf,dict):
            print("CONFIG_UNEXPECTED_FORMAT");return
        print("CONFIG_FIELDS",sorted(conf.keys()))
        api=conf.get("apiBaseUrl")
        if not isinstance(api,str) or not api.startswith("https://"):
            print("CONFIG_NO_HTTPS_BACKEND");return
        from urllib.parse import urlsplit
        host=urlsplit(api).hostname or ""
        print("BACKEND_ORIGIN",host,"base_path",urlsplit(api).path)
        if not (host.endswith(".independencemo.gov") or host.endswith(".indepmo.org")):
            print("BACKEND_DOMAIN_REQUIRES_MANUAL_VALIDATION");return
        dataset_url=urljoin(api.rstrip("/")+"/","opendata/dataset?code=V1BUILDINGPERMITS")
        try:
            resp=session.get(dataset_url,headers={"Accept":"application/json"},timeout=(8,25),stream=True,allow_redirects=True)
            if urlsplit(resp.url).hostname != host:
                print("DATASET_UNEXPECTED_REDIRECT",urlsplit(resp.url).hostname);return
            print("DATASET_RESPONSE",resp.status_code,resp.headers.get("content-type","?"),"size",resp.headers.get("content-length","?"))
            if resp.status_code!=200:
                print("DATASET_REJECTION",resp.text[:190]);return
            buffer=bytearray()
            for chunk in resp.iter_content(65536):
                buffer.extend(chunk)
                if len(buffer)>6_000_000:
                    print("DATASET_TOO_LARGE_FOR_PROBE");return
            try:
                payload=__import__("json").loads(bytes(buffer))
            except ValueError as e:
                print("DATASET_INVALID_JSON",str(e)[:130]);return
            print("DATASET_TOP_TYPE",type(payload).__name__,"length",len(buffer))
            if isinstance(payload,dict):
                print("DATASET_KEYS",sorted(payload.keys())[:35])
                print("DATASET_META",{"code":payload.get("dataSetCode"),"name":payload.get("dataSetName"),
                      "status":payload.get("status"),"lastUpdated":payload.get("lastUpdated"),
                      "currentDataStore_type":type(payload.get("currentDataStore")).__name__})
                fields=payload.get("dataSetFields") or []
                rows=payload.get("dataSetData") or []
                print("FIELD_DEFS",[(i,f.get("title"),f.get("fieldType"),f.get("id")) for i,f in enumerate(fields) if isinstance(f,dict)])
                print("ROW_WIDTHS",sorted({len(row) for row in rows if isinstance(row,list)}))
                from datetime import datetime, date, timedelta
                from collections import Counter
                def cell(row,i):
                    return row[i].get("value") if isinstance(row,list) and len(row)>i and isinstance(row[i],dict) else None
                def dparse(s):
                    if not s:return None
                    for fmt in ("%m/%d/%Y","%Y-%m-%d"):
                        try:return datetime.strptime(str(s).strip()[:10],fmt).date()
                        except ValueError:pass
                    return None
                cutoff=date(2026,7,21)
                recents=[row for row in rows if isinstance(row,list) and (dparse(cell(row,2)) or date(1900,1,1))>=cutoff]
                dates=[dparse(cell(row,2)) for row in rows if isinstance(row,list) and dparse(cell(row,2))]
                print("ISSUED_DATE_RANGE",min(dates) if dates else None,max(dates) if dates else None,
                      "WITH_DATES",len(dates),"RECENT_120D",len(recents))
                print("RECENT_TYPE_COUNTS",Counter(str(cell(row,3)) for row in recents).most_common(10))
                print("RECENT_WORK_COUNTS",Counter(str(cell(row,4)) for row in recents).most_common(45))
                print("RECENT_PERMIT_UNIQUENESS",len(set(str(cell(row,0)) for row in recents)), "rows",len(recents))
                print("RECENT_BLANK_ADDRESS",sum(not cell(row,1) for row in recents))
                print("RECENT_SAMPLE",[(str(cell(row,0)),str(cell(row,2)),str(cell(row,3)),str(cell(row,4))) for row in recents[:8]])

                for field_idx,f in enumerate(fields):
                    if not isinstance(f,dict):continue
                    title=str(f.get("title") or "")
                    if "date" in title.lower() or "issued" in title.lower():
                        print("DATE_FIELD",field_idx,"sample",[(row[field_idx] if field_idx<len(row) else None) for row in rows[:4]],
                              "tail",[(row[field_idx] if field_idx<len(row) else None) for row in rows[-3:]])
                    elif "type" in title.lower() or "description" in title.lower():
                        from collections import Counter
                        count=Counter(str(row[field_idx])[:90] for row in rows if isinstance(row,list) and len(row)>field_idx)
                        print("TYPE_FIELD",field_idx,"top_25",count.most_common(25))
                    elif "permit" in title.lower() and "number" in title.lower():
                        print("PERMIT_ID_SAMPLES",field_idx,[str(row[field_idx])[:45] for row in rows[:4] if isinstance(row,list) and len(row)>field_idx])
                for k,v in payload.items():
                    if isinstance(v,list):
                        print("DATASET_LIST_KEY",k,"count",len(v))
                        if v:
                            print("DATASET_LIST_SAMPLE_TYPE",type(v[0]).__name__,"FIELDS",list(v[0].keys())[:40] if isinstance(v[0],dict) else "non-object")
                    elif isinstance(v,dict):
                        print("DATASET_OBJECT_KEY",k,"FIELDS",list(v.keys())[:30])
            elif isinstance(payload,list):
                print("DATASET_RECORD_COUNT",len(payload))
                if payload and isinstance(payload[0],dict):
                    print("DATASET_RECORD_KEYS",list(payload[0].keys())[:40])
        except (requests.RequestException,ValueError) as e:
            print("DATASET_ERROR",type(e).__name__,str(e)[:220])
    except (requests.RequestException,ValueError) as e:
        print("CONFIG_ERROR",type(e).__name__,str(e)[:200])


def main():
    s=requests.Session()
    s.headers.update({"User-Agent":"Kansas-Missouri-Construction-Intelligence/SourceAudit (public metadata only)"})
    probe_documented_backend(s)
    for url in PAGES:
        try:
            r=safe_get(s,url)
            print("PAGE",r.status_code,"final",r.url,"length",len(r.content),"type",r.headers.get("content-type","?"))
            if r.status_code != 200 or "html" not in r.headers.get("content-type",""):
                continue
            parser=Assets()
            parser.feed(r.text)
            assets=[urljoin(r.url,x) for x in parser.assets]
            available_links=[urljoin(r.url,x) for x in parser.links]
            matches=[x for x in available_links if re.search(r"(csv|json|api|download|BuildingPermits)",x,re.I)]
            print("DOWNLOAD_LINKS",matches[:15])
            date_strings=re.findall(r"\b(?:1[01]|[1-9])/\d{1,2}/2026\b",r.text)
            print("HTML_DATE_SPAN",date_strings[:5],date_strings[-5:],"unique",len(set(date_strings)))
            assets=list(dict.fromkeys(x for x in assets if urlsplit(x).hostname in ALLOWED))
            print("PUBLIC_ASSETS",[(urlsplit(a).path) for a in assets[:14]])
            print("PAGE_HINTS",list(dict.fromkeys(m.group(0) for m in HINTS.finditer(r.text)))[:15])
            if "opendata.independencemo.gov" not in r.url:continue
            for asset in [a for a in assets if a.endswith(".js")][:13]:
                try:
                    result=safe_get(s,asset)
                    print("ASSET",result.status_code,urlsplit(result.url).path,"length",len(result.content))
                    if result.status_code!=200 or len(result.content)>1_500_000:
                        continue
                    snippet=[]
                    for match in list(HINTS.finditer(result.text))[:45]:
                        start=max(0,match.start()-65)
                        end=min(len(result.text),match.end()+115)
                        context=result.text[start:end].replace("\n"," ")
                        context=re.sub(r"(?:Bearer|token|api[_-]?key)[\"']?\s*[:=]\s*[\"'][^\"']+", "[redacted]",context,flags=re.I)
                        snippet.append(context[:230])
                    print("ASSET_HINTS",snippet[:20])
                except (requests.RequestException,ValueError) as e:
                    print("ASSET_ERROR",type(e).__name__,str(e)[:180])
        except (requests.RequestException,ValueError) as e:
            print("PAGE_ERROR",url,type(e).__name__,str(e)[:200])


if __name__=="__main__":
    main()
