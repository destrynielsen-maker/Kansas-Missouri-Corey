#!/usr/bin/env python3
"""Inspect a bounded list of *public* Wyandotte County official GIS catalogs.

This is source discovery, NOT permit collection. It never guesses an Accela API,
bypasses portal restrictions, or labels a possible service as a verified feed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = "https://gisweb.wycokck.org/arcgis/rest/services"
FOLDERS = ("", "GISPUB", "UGMAPS", "GISPW")
PUBLIC_PORTAL = "https://aca-prod.accela.com/UG/Cap/CapHome.aspx?TabName=Home&module=Building"
SOURCE_DIR = "https://gisweb.wycokck.org/arcgis/rest/services/GISPUB"
OUTPUT = Path(__file__).resolve().parents[1] / "docs/data/source_health.json"

# Narrow on purpose. Parcels, building footprints, zoning, and city limits
# must not be mistaken for *building-permit records*.
RELEVANT = re.compile(r"permit|building[_ ]?inspection|construction[_ ]?application", re.I)


def get_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=2, connect=2, read=1, backoff_factor=1,
                  status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=frozenset(["GET"]))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers["User-Agent"] = "KC-Metro-Construction-Intelligence/1.0 (public source catalog monitor)"
    return s


def catalog_url(folder: str) -> str:
    if folder not in FOLDERS:
        raise ValueError("Folder is not in the explicitly reviewed public set")
    return BASE + ("/" + folder if folder else "")


def inspect(session: requests.Session, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    inspections: list[dict] = []
    candidates: dict[str, dict] = {}
    errors: list[str] = []

    for folder in FOLDERS:
        url = catalog_url(folder)
        try:
            res = session.get(url, params={"f": "pjson"},
                              timeout=(8, 20), allow_redirects=False)
            res.raise_for_status()
            if urlsplit(res.url).hostname != "gisweb.wycokck.org":
                raise ValueError("Catalog host changed unexpectedly")
            if len(res.content) > 1_000_000:
                raise ValueError("Catalog response size unexpectedly large")
            payload = res.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("services"), list):
                raise ValueError("Missing public ArcGIS service catalog")
            if payload.get("error"):
                raise ValueError("ArcGIS source reported an API error")
            services = payload["services"]
            if len(services) > 2000:
                raise ValueError("Public service catalog exceeds bounded size")
            present = []
            for service in services:
                if not isinstance(service, dict):
                    continue
                name, kind = service.get("name"), service.get("type")
                if not isinstance(name, str) or not isinstance(kind, str):
                    continue
                if not RELEVANT.search(name) or kind not in ("FeatureServer", "MapServer"):
                    continue
                key = name + "|" + kind
                candidates[key] = {
                    "service_name": name,
                    "service_kind": kind,
                    "catalog_folder": folder or "(root)",
                    "verified_permit_feed": False,
                    "evidence": "matching_public_service_name_only",
                }
                present.append(name)
            inspections.append({
                "folder": folder or "(root)", "catalog_url": url,
                "result": "ok", "services_checked": len(services),
                "matching_names": sorted(set(present)),
            })
        except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
            errors.append((folder or "(root)") + ": " + type(exc).__name__)
            inspections.append({
                "folder": folder or "(root)", "catalog_url": url,
                "result": "unavailable", "services_checked": None,
                "matching_names": [],
            })

    if errors:
        status = "incomplete_public_catalog_review"
    elif candidates:
        status = "candidate_service_names_require_validation"
    else:
        status = "no_permit_named_service_in_reviewed_public_catalogs"

    return {
        "checked_at_utc": now.astimezone(timezone.utc).isoformat(timespec="seconds"),
        "jurisdiction": "Kansas City, KS / Wyandotte County",
        "method": "public_arcgis_service_catalog_names_only",
        "source_status": status,
        "verified_bulk_permit_feed": False,
        "public_portal_url": PUBLIC_PORTAL,
        "public_gis_directory_url": SOURCE_DIR,
        "catalogs": inspections,
        "candidate_services": sorted(candidates.values(), key=lambda c:(c["service_name"],c["service_kind"])),
        "review_notes": (
            "Only four explicitly named public GIS catalogs were checked. "
            "The absence of a matching name does not prove no public permit API exists elsewhere. "
            "Accela permit lookup is publicly documented but was not harvested or automated. "
            "No permits are imported or inferred from these GIS catalog entries."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = inspect(get_session())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix(".tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(args.output)
    print("Wyandotte public-source catalog check:",result["source_status"])
    for c in result["catalogs"]:
        print("  ",c["folder"],c["result"],"services",c["services_checked"],
              "permit-name matches",len(c["matching_names"]))
    print("Candidate service names:", len(result["candidate_services"]))
    # Incomplete monitoring is visible in the snapshot, not mislabeled as no permits.
    return 0


if __name__ == "__main__":
    sys.exit(main())
