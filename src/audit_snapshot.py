#!/usr/bin/env python3
"""Summarize quality of the actually published permits, not guessed feed coverage."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "docs/data/permits.json"
OUTPUT = ROOT / "docs/data/quality.json"


def summarize(snapshot: dict) -> dict:
    permits = snapshot.get("permits", [])
    if not isinstance(permits, list):
        raise ValueError("Snapshot permits must be an array")
    if len(permits) != snapshot.get("count"):
        raise ValueError("Snapshot count does not match permit rows")
    if not snapshot.get("generated_at"):
        raise ValueError("Snapshot is not from a successful live fetch")
    ids = [r.get("id") for r in permits]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate stable permit IDs")
    sources = snapshot.get("sources", [])
    expected = {s["name"] for s in sources}
    actual = {p.get("jurisdiction") for p in permits}
    if not actual.issubset(expected):
        raise ValueError("Unexpected jurisdiction in payload")
    by_city = defaultdict(list)
    flags = []
    for p in permits:
        city = p.get("jurisdiction")
        by_city[city].append(p)
        if not p.get("permit_number"):
            raise ValueError("Published lead has no permit number")
        if not p.get("issued"):
            raise ValueError("Published lead has no issuance date")
        for url_field in ("permit_url", "source_url"):
            u = p.get(url_field, "")
            parsed = urlparse(u)
            if parsed.scheme != "https" or not parsed.netloc:
                raise ValueError(f"Invalid {url_field} for {p.get('id')}")
        if p.get("link_kind") not in ("search", "record"):
            raise ValueError("Unrecognized permit link kind")
        if not isinstance(p.get("score"), int) or not 0 <= p["score"] <= 100:
            raise ValueError("Invalid score")
    results = {}
    for city, rows in sorted(by_city.items()):
        cat = Counter(p.get("category") or "Unknown" for p in rows)
        statuses = Counter(p.get("status") or "(empty)" for p in rows)
        combos = Counter(
            ((p.get("permit_type") or "(empty)").strip(), (p.get("work_class") or "(empty)").strip())
            for p in rows
        )
        link_kinds = Counter(p.get("link_kind") or "missing" for p in rows)
        missing_addr = sum(not p.get("address") for p in rows)
        missing_value = sum(p.get("valuation") is None for p in rows)
        zero_value = sum(p.get("valuation") == 0 for p in rows)
        samples = {}
        for category in ("Single-family", "Multifamily", "Commercial", "Addition", "Remodel", "Other"):
            matching = [p for p in rows if p.get("category") == category]
            samples[category] = [
                {"permit": p.get("permit_number"), "date": p.get("issued"),
                 "type": p.get("permit_type"), "class": p.get("work_class"),
                 "project": (p.get("project") or "")[:110],
                 "address_present": bool(p.get("address")),
                 "direct_record": p.get("link_kind") == "record"}
                for p in matching[:3]
            ]
        results[city] = {
            "count": len(rows), "earliest_issue": min(p["issued"] for p in rows),
            "latest_issue": max(p["issued"] for p in rows),
            "categories": dict(cat.most_common()), "statuses": dict(statuses.most_common(10)),
            "link_kinds": dict(link_kinds), "missing_address": missing_addr,
            "missing_valuation": missing_value, "zero_valuation": zero_value,
            "top_types": [{"permit_type": t, "work_class": w, "count": n}
                          for (t, w), n in combos.most_common(25)],
            "samples_by_category": samples,
        }
        if cat["Other"] > len(rows) // 3:
            flags.append(f"{city}: >33% of records classified Other; check mapping")
        if missing_addr > len(rows) // 5:
            flags.append(f"{city}: >20% of records lack a street address")
    return {
        "source_snapshot": snapshot["generated_at"],
        "total_records": len(permits),
        "by_category": dict(Counter(p.get("category") or "Unknown" for p in permits).most_common()),
        "by_state": dict(Counter(p.get("state") or "Unknown" for p in permits).most_common()),
        "direct_record_count": sum(p.get("link_kind") == "record" for p in permits),
        "public_search_count": sum(p.get("link_kind") == "search" for p in permits),
        "issues_to_review": flags,
        "jurisdictions": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    payload = summarize(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Published source QA:", payload["total_records"], "leads; direct public record links", payload["direct_record_count"])
    for city, entry in payload["jurisdictions"].items():
        print(city, entry["count"], "categories", entry["categories"], "missing address", entry["missing_address"])
    if payload["issues_to_review"]:
        print("Review warnings:", "; ".join(payload["issues_to_review"]))


if __name__ == "__main__":
    main()
