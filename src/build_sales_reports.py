#!/usr/bin/env python3
"""Generate truthful public field-coverage and independently sourced builder rollups.

City permit fields are never populated from unsupported guesses. A separately
researched builder company is NOT a city-verified permit contractor.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
PERMITS = ROOT / "docs/data/permits.json"
RESEARCH = ROOT / "docs/data/builders.json"
FIELD_REPORT = ROOT / "docs/data/sales_field_coverage.json"
RANKINGS = ROOT / "docs/data/builder_rankings.json"
ALLOWED_EVIDENCE = ("exact_address_listing", "planning_drawing", "project_gc_announcement")
FIELDS = {
    "project_description": "project",
    "work_class": "work_class",
    "valuation": "valuation",
    "units": "units",
    "square_feet": "square_feet",
    "application_date": "application_date",
    "last_inspection_date": "last_inspection_date",
    "expiration_date": "expiration_date",
    "parcel_number": "parcel_number",
}


def addr(value) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[.,]", "", str(value or "")).strip()).upper()


def validate_evidence(entry: dict) -> None:
    if not isinstance(entry, dict):
        raise ValueError("Invalid builder research entry")
    for key in ("id", "address", "issued", "jurisdiction", "builder", "evidence_type", "evidence_url"):
        if not isinstance(entry.get(key), str) or not entry[key].strip():
            raise ValueError("Builder research entry missing " + key)
    url = urlsplit(entry["evidence_url"])
    if url.scheme != "https" or not url.netloc or url.username or url.password:
        raise ValueError("Builder research evidence URL must be a public HTTPS link")
    if entry["evidence_type"] not in ALLOWED_EVIDENCE:
        raise ValueError("Unsupported builder evidence category")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", entry["issued"]):
        raise ValueError("Missing original builder research issue date")
    if len(entry["builder"]) > 140 or len(entry.get("qualification") or "") > 600:
        raise ValueError("Unexpected research text size")


def build(snapshot: dict, research: dict) -> tuple[dict, dict]:
    if not isinstance(snapshot.get("permits"), list) or not snapshot.get("generated_at"):
        raise ValueError("Published permit snapshot is missing")
    if not isinstance(research, dict) or not isinstance(research.get("entries"), list):
        raise ValueError("Builder research source is missing")
    if len(snapshot["permits"]) != snapshot.get("count"):
        raise ValueError("Permit snapshot count mismatch")
    by_id = {r["id"]: r for r in snapshot["permits"]}
    if len(by_id) != len(snapshot["permits"]):
        raise ValueError("Duplicate official permit identifiers")
    known: dict[str, dict] = {}
    aged_out = 0
    for e in research["entries"]:
        validate_evidence(e)
        if e["id"] in known:
            raise ValueError("Duplicated builder research ID")
        p = by_id.get(e["id"])
        if p is None:
            aged_out += 1
            continue  # Records naturally leave the rolling 120-day window.
        if any((e["jurisdiction"] != p["jurisdiction"],
                e["issued"] != p["issued"],
                addr(e["address"]) != addr(p["address"]))):
            raise ValueError("Independent builder attribution does not match exact official permit evidence: " + e["id"])
        known[e["id"]] = e

    by_city = defaultdict(list)
    for p in snapshot["permits"]:
        by_city[p["jurisdiction"]].append(p)
    coverage = {}
    for city, rows in sorted(by_city.items()):
        present = {}
        for label, key in FIELDS.items():
            present[label] = sum(p.get(key) is not None and p.get(key) != "" for p in rows)
        present["direct_official_permit_url"] = sum(p.get("link_kind") == "record" for p in rows)
        present["independent_builder_company"] = sum(p["id"] in known for p in rows)
        present["permit_id"] = sum(bool(p.get("permit_number")) for p in rows)
        present["issued_date"] = sum(bool(p.get("issued")) for p in rows)
        present["site_address"] = sum(bool(p.get("address")) for p in rows)
        coverage[city] = {"permits": len(rows), "fields_available": present,
            "builder_not_established": len(rows) - present["independent_builder_company"]}
    cutoff = date.fromisoformat(snapshot["generated_at"][:10])
    group = defaultdict(list)
    for p in snapshot["permits"]:
        if p["id"] in known:
            group[known[p["id"]]["builder"]].append((p, known[p["id"]]))
    rankings = []
    for company, matches in group.items():
        years = []
        unique_project_ids = set()
        for p, evidence in matches:
            age = (cutoff - date.fromisoformat(p["issued"])).days
            years.append((age,p["issued"]))
            unique_project_ids.add(evidence.get("project_group") or p.get("site_group_id") or p["id"])
        rankings.append({
            "builder": company,
            "permit_count": len(matches),
            "estimated_distinct_project_groups": len(unique_project_ids),
            "issued_last_30_days": sum(0 <= age <= 30 for age, _ in years),
            "issued_last_90_days": sum(0 <= age <= 90 for age, _ in years),
            "last_issued_date": max(issued for _, issued in years),
            "jurisdictions": sorted({p["jurisdiction"] for p, _ in matches}),
            "evidence_types": sorted({e["evidence_type"] for _, e in matches}),
            "permit_ids": sorted(p["id"] for p, _ in matches),
        })
    rankings.sort(key=lambda x: (-x["issued_last_90_days"], -x["permit_count"], x["builder"].casefold()))
    for rank, b in enumerate(rankings, 1):
        b["rank"] = rank
    total = len(snapshot["permits"])
    field_summary = {
        "source_snapshot": snapshot["generated_at"],
        "research_reviewed_on": research.get("reviewed_on"),
        "total_permits": total,
        "builder_research_matched_permits": len(known),
        "builder_research_unmatched_permits": total-len(known),
        "research_entries_aged_out": aged_out,
        "sourced_company_count": len(rankings),
        "field_scope": "Municipal permit source fields plus separately sourced business-name evidence; no personal contacts.",
        "jurisdictions": coverage,
    }
    builder_report = {
        "source_snapshot": snapshot["generated_at"],
        "research_reviewed_on": research.get("reviewed_on"),
        "ranking_basis": "Independently researched company associations to exact current permit IDs. Permit counts are not unique construction projects or permit-confirmed general contractors.",
        "total_sourced_builder_permits": len(known),
        "builder_companies": len(rankings),
        "builders": rankings,
    }
    return field_summary, builder_report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--permits", type=Path, default=PERMITS)
    p.add_argument("--research", type=Path, default=RESEARCH)
    p.add_argument("--coverage-output", type=Path, default=FIELD_REPORT)
    p.add_argument("--rankings-output", type=Path, default=RANKINGS)
    args=p.parse_args()
    snapshot=json.loads(args.permits.read_text(encoding="utf-8"))
    research=json.loads(args.research.read_text(encoding="utf-8"))
    coverage,rankings=build(snapshot,research)
    for path,data in ((args.coverage_output,coverage),(args.rankings_output,rankings)):
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp=path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        tmp.replace(path)
    print("Field coverage:",coverage["total_permits"],"permits; sourced builder matches",
          coverage["builder_research_matched_permits"],"companies",coverage["sourced_company_count"])
    for city,v in coverage["jurisdictions"].items():
        print(city, v["permits"],"permits;",
              v["fields_available"]["independent_builder_company"],"researched builder matches;",
              v["fields_available"]["square_feet"],"published square-footage values")


if __name__ == "__main__":
    main()
