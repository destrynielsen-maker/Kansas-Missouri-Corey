#!/usr/bin/env python3
"""Load recent Kansas City metro building permits from municipal open-data APIs.

No login scraping, no synthetic records, and no fabricated direct permit URLs.
A failed source blocks publication of the new snapshot.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "data" / "permits.json"
SOURCES = {
    "kcmo": {
        "name": "Kansas City, MO", "state": "MO", "county": "",
        "kind": "socrata",
        "api": "https://data.kcmo.org/resource/w8jz-wjgn.json",
        "source": "https://data.kcmo.org/d/w8jz-wjgn",
        "portal": "https://compasskc.kcmo.org/",
    },
    "overland_park": {
        "name": "Overland Park, KS", "state": "KS", "county": "Johnson",
        "kind": "arcgis",
        "api": "https://maps.opkansas.org/mapping/rest/services/MixedInfo/Building_Permit_Report/MapServer/0",
        "source": "https://maps.opkansas.org/mapping/rest/services/MixedInfo/Building_Permit_Report/MapServer/0",
        "portal": "https://overlandparkks.tylerportico.com/portal/",
        "date_field": "IssueDate", "number_field": "CaseNumber",
    },
    "olathe": {
        "name": "Olathe, KS", "state": "KS", "county": "Johnson",
        "kind": "arcgis",
        "api": "https://arcgis.olatheks.org/arcgis/rest/services/Planning/Development/MapServer/0",
        "source": "https://arcgis.olatheks.org/arcgis/rest/services/Planning/Development/MapServer/0",
        "portal": "https://energov.olatheks.org/",
        "date_field": "ISSUEDATE", "number_field": "PERMITNUMBER",
    },
    "lees_summit": {
        "name": "Lee's Summit, MO", "state": "MO", "county": "",
        "kind": "arcgis",
        "api": "https://maps.cityofls.net/arcgis/rest/services/Development_Public/MapServer/29",
        "source": "https://maps.cityofls.net/arcgis/rest/services/Development_Public/MapServer/29",
        "portal": "https://cityview2.iharriscomputer.com/leessummitmoportal/",
        "date_field": "dateissued", "number_field": "PermitNumber",
    },
}

SKIP_TYPES = re.compile(
    r"\b(electrical|plumbing|mechanical|mech|elec|plumb|water heater|furnace|hvac|"
    r"solar|sign|fence|demolition|roofing|fire alarm|gas service|"
    r"sewer|excavation|water main|sprinkler|land disturbance|site improvement|"
    r"grading only|pool|spa|generator)\b", re.IGNORECASE
)


def session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=2, connect=2, read=1, backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": "Kansas-Missouri-Construction-Intelligence/1.0 (public municipal data)", "Accept": "application/json"})
    return s


def fetch_json(s: requests.Session, url: str, params: dict) -> dict | list:
    response = s.get(url, params=params, timeout=(10, 25))
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict) and "error" in payload:
        raise RuntimeError("Agency API error: " + str(payload["error"])[:260])
    if not isinstance(payload, (list, dict)):
        raise ValueError("Unexpected municipal API response")
    return payload


def to_date(value) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value / 1000 if value > 1e11 else value, timezone.utc).date()
        except (ValueError, OverflowError, OSError):
            return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def number(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        n = float(str(value).replace(",", "").replace("$", ""))
        if not 0 <= n <= 1_000_000_000:
            return None
        return round(n, 2)
    except (ValueError, TypeError):
        return None


def safe_url(value) -> str | None:
    if not isinstance(value, str):
        return None
    s = value.strip()
    return s if len(s) < 2000 and re.match(r"^https://[A-Za-z0-9.-]+(?:[:/]|$)", s) else None


def classify(ptype: str, work: str, description: str = "") -> str:
    """Conservatively select structural construction, never type-match 'family' inside remodels.

    Work class is authoritative when specific; a project name cannot turn a tenant
    finish or mechanical repair into new construction.
    """
    kind = (ptype or "").lower().replace("-", " ")
    wc = (work or "").lower().replace("-", " ")
    project = (description or "").lower().replace("-", " ")
    combined = kind + " " + wc
    if SKIP_TYPES.search(combined):
        return "Other"
    # More specific non-structural work. Exclude these BEFORE searching for 'new'.
    if re.search(r"\b(deck|covered deck|porch|fence|wall|pool|accessory structure|"
                 r"detached accessory|carport repair|water heater|gas line|"
                 r"solar|repair|miscellaneous structure|change of tenant|change of occupancy)\b", wc):
        return "Other"
    if re.search(r"\b(addition|expansion|expand)\b", wc):
        return "Addition"
    if re.search(r"\b(remodel|renovat\w*|tenant finish|interior alteration|alteration)\b", wc):
        return "Remodel"
    # Where work class is only 'New' or a 'Building Shell' it is interpreted with type.
    is_new = bool(re.search(r"\bnew\b", wc) or re.search(r"\bnew\b", kind))
    dwelling = bool(re.search(r"\b(single family|singlefamily|sfr|one family)\b", combined))
    attached = bool(re.search(r"\b(multi family|multifamily|apartment|townhome|townhouse|duplex|two family)\b", combined))
    if attached and (is_new or re.search(r"^(duplex|multi family|townhouse|townhome)$", wc)):
        return "Multifamily"
    if dwelling and (is_new or wc.strip() == "single family"):
        return "Single-family"
    if re.search(r"\b(residential)\b", kind) and is_new and not attached:
        return "Single-family"
    commercial = bool(re.search(r"\b(commercial|industrial|warehouse|business|new shell building)\b", kind))
    if is_new and commercial:
        return "Commercial"
    if commercial and re.search(r"\b(building shell|shell building)\b", wc):
        return "Commercial"
    if commercial and re.search(r"\b(footing|foundation)\b", wc) and re.search(
        r"\b(new construction|new building|building \d+|facility|commerce center)\b", project
    ):
        return "Commercial"
    # Some municipalities encode the use in their work class rather than permit type.
    if re.search(r"\b(new restaurant|new retail|new warehouse|new shell building|new commercial)\b", wc):
        return "Commercial"
    return "Other"

def lead_score(category: str, issued: date, today: date, valuation: float | None) -> int:
    base = {"Single-family": 65, "Multifamily": 75, "Commercial": 61, "Addition": 45, "Remodel": 25, "Other": 12}[category]
    age = (today - issued).days
    freshness = 20 if age <= 7 else 14 if age <= 30 else 7 if age <= 90 else 0
    value = 17 if valuation is not None and valuation >= 1_000_000 else 10 if valuation is not None and valuation >= 250_000 else 0
    return min(100, base + freshness + value)


def source_record_url(cfg: dict, permit_number: str) -> str:
    # A row-level machine-data reference, never mislabeled as the human permit page.
    if cfg["kind"] == "socrata":
        return cfg["api"] + "?" + urlencode({"permit_number": permit_number})
    field = cfg["number_field"]
    # Escape quote for ArcGIS SQL string literal, then URL-encode whole expression.
    return cfg["api"] + "/query?" + urlencode({
        "where": field + " = '" + permit_number.replace("'", "''") + "'",
        "outFields": "*", "returnGeometry": "false", "f": "pjson",
    })



def milestone_date(value, issued: date, today: date, label: str, warnings: list[str], *,
                   allow_future: bool = False, before_issue: bool = False) -> str | None:
    """Only accept a bounded, chronologically credible date; preserve evidence warnings."""
    d = to_date(value)
    if d is None:
        return None
    if d.year < 1980 or (not allow_future and d > today + timedelta(days=2)):
        warnings.append(label + "_invalid_or_future")
        return None
    if before_issue:
        if d > issued:
            warnings.append(label + "_after_issue")
            return None
    elif d < issued:
        warnings.append(label + "_before_issue")
        return None
    return d.isoformat()


def extract_timeline(cfg_key: str, raw: dict, issued: date, today: date) -> dict:
    """Official agency dates only, NOT estimated start dates or fabricated build stages.

    Sources with no inspection field are distinguished from sources with a blank field.
    A last-inspection date signals an inspection RECORD, not construction progress.
    """
    warnings: list[str] = []
    if cfg_key == "kcmo":
        row = raw
        applied_raw = row.get("application_date")
        inspected_raw = row.get("last_inspection_date")
        expiry_raw = row.get("expiration_date")
        final_raw = row.get("finaled_date")
        inspection_supported = True
    elif cfg_key == "overland_park":
        row = raw.get("attributes", raw)
        applied_raw = row.get("ApplyDate")
        inspected_raw = row.get("LastInspectionDate")
        expiry_raw = row.get("ExpireDate")
        final_raw = row.get("FinalizedDate")
        inspection_supported = True
    elif cfg_key == "lees_summit":
        row = raw.get("attributes", raw)
        applied_raw = None
        inspected_raw = None
        expiry_raw = row.get("dateExpiration")
        final_raw = None
        inspection_supported = False
    else:
        applied_raw = inspected_raw = expiry_raw = final_raw = None
        inspection_supported = False
    applied = milestone_date(applied_raw, issued, today, "application", warnings, before_issue=True)
    inspected = milestone_date(inspected_raw, issued, today, "inspection", warnings)
    expires = milestone_date(expiry_raw, issued, today, "expiration", warnings, allow_future=True)
    finalized = milestone_date(final_raw, issued, today, "finaled", warnings)
    evidence = ("inspection_recorded" if inspected else
                "date_not_reported" if inspection_supported else "field_not_published")
    return {
        "application_date": applied,
        "last_inspection_date": inspected,
        "expiration_date": expires,
        "finaled_date": finalized,
        "start_date": None,
        "start_date_source": "not_published",
        "inspection_evidence": evidence,
        "timeline_warnings": warnings,
        "timeline_source": SOURCES[cfg_key]["source"],
    }


def normalize(cfg_key: str, raw: dict, today: date, cutoff: date) -> dict | None:
    cfg = SOURCES[cfg_key]
    if cfg_key == "kcmo":
        permit_no = str(raw.get("permit_number") or "").strip()
        issued = to_date(raw.get("issue_date"))
        ptype, work = str(raw.get("permit_type") or ""), str(raw.get("work_class") or "")
        description = str(raw.get("project") or "")
        address = " ".join(str(raw.get(k) or "").strip() for k in ("main_address_line1", "main_address_line2")).strip()
        status = str(raw.get("permit_status") or "")
        valuation = number(raw.get("valuation"))
        # A council district is NOT a county; do not mislabel it.
        county = ""
        direct_url = None
        units, sq_ft = None, None
    else:
        attrs = raw.get("attributes", raw)
        if not isinstance(attrs, dict):
            return None
        if cfg_key == "overland_park":
            permit_no = str(attrs.get("CaseNumber") or "").strip()
            issued = to_date(attrs.get("IssueDate"))
            ptype, work = str(attrs.get("PermitType") or ""), str(attrs.get("WorkClass") or "")
            description = str(attrs.get("Description") or attrs.get("Project") or "")
            address = " ".join(str(attrs.get(k) or "").strip() for k in ("MainAddressLine1", "MainAddressLine2")).strip()
            status = str(attrs.get("PermitStatus") or "")
            valuation = number(attrs.get("Valuation"))
            units, sq_ft = number(attrs.get("NumberUnits")), number(attrs.get("SquareFeet"))
            direct_url = safe_url(attrs.get("More_Info"))
        elif cfg_key == "olathe":
            permit_no = str(attrs.get("PERMITNUMBER") or "").strip()
            issued = to_date(attrs.get("ISSUEDATE"))
            ptype, work = str(attrs.get("PermitType") or ""), str(attrs.get("PermitWorkclass") or "")
            description = str(attrs.get("DESCRIPTION") or "")
            address = str(attrs.get("ADDRESS") or "").strip()
            status = str(attrs.get("PermitStatus") or "")
            valuation = number(attrs.get("VALUE"))
            units, sq_ft, direct_url = None, None, None
        else:
            permit_no = str(attrs.get("PermitNumber") or "").strip()
            issued = to_date(attrs.get("dateissued"))
            ptype, work = str(attrs.get("PermitType") or ""), ""
            description = ""
            address = str(attrs.get("Location") or "").strip()
            status = str(attrs.get("Status") or "")
            valuation = None
            units, sq_ft, direct_url = None, None, None
        county = cfg["county"]

    if not permit_no or not issued or issued < cutoff or issued > today + timedelta(days=2):
        return None
    if re.search(r"\b(closed|finaled|final|complete|completed|voided|void|cancelled|canceled|"
                 r"expired|suspended|hold|temporary occupancy|substantial completion|in plan review|"
                 r"ready for issuance)\b", status, re.IGNORECASE):
        return None
    timeline = extract_timeline(cfg_key, raw, issued, today)
    if timeline["finaled_date"] is not None:
        return None  # Published completion overrides a stale issued status.
    category = classify(ptype, work, description)
    # This is a NEW BUILD + structural addition lead list, not a general permit dump.
    if category not in ("Single-family", "Multifamily", "Commercial", "Addition"):
        return None
    # A source's $0 valuation generally means unreported, not a free project.
    if valuation == 0:
        valuation = None
    url = source_record_url(cfg, permit_no)
    return {
        "id": cfg_key + ":" + permit_no,
        "permit_number": permit_no,
        "jurisdiction": cfg["name"],
        "state": cfg["state"],
        "county": county,
        "issued": issued.isoformat(),
        "permit_type": ptype,
        "work_class": work,
        "category": category,
        "status": status,
        "address": address,
        "project": description if description not in ("", "]") else "",
        "valuation": valuation,
        "units": int(units) if units is not None else None,
        "square_feet": int(sq_ft) if sq_ft is not None else None,
        "score": lead_score(category, issued, today, valuation),
        "permit_url": direct_url or cfg["portal"],
        "link_kind": "record" if direct_url else "search",
        "source_url": url,
        "source_home": cfg["source"],
        **timeline,
    }


def fetch_socrata(s: requests.Session, cfg: dict, cutoff: date, today: date) -> list[dict]:
    result = []
    where = (
        "issue_date >= '" + cutoff.isoformat() + "T00:00:00' AND "
        "issue_date < '" + (today + timedelta(days=3)).isoformat() + "T00:00:00' "
        "AND permit_type like '%Building%'"
    )
    limit = 1000
    for offset in range(0, 20000, limit):
        page = fetch_json(s, cfg["api"], {
            "$where": where, "$order": "issue_date DESC, permit_number ASC",
            "$limit": limit, "$offset": offset,
        })
        if not isinstance(page, list):
            raise ValueError("Socrata returned a non-list payload")
        result.extend(page)
        if len(page) < limit:
            return result
    raise RuntimeError("Socrata pagination safety cap reached; refusing partial publication")


def fetch_arcgis(s: requests.Session, cfg: dict, cutoff: date, today: date) -> list[dict]:
    result = []
    limit = 500
    endpoint = cfg["api"] + "/query"
    for offset in range(0, 10000, limit):
        page = fetch_json(s, endpoint, {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "false",
            "orderByFields": cfg["date_field"] + " DESC",
            "resultOffset": offset,
            "resultRecordCount": limit,
            "f": "json",
        })
        if not isinstance(page, dict) or not isinstance(page.get("features"), list):
            raise ValueError("ArcGIS returned a non-feature payload")
        features = page["features"]
        result.extend(features)
        if not features:
            return result
        dated = [to_date((r.get("attributes") or {}).get(cfg["date_field"])) for r in features]
        # Query is explicitly sorted by issue date DESC; older rows end the scan.
        if any(d is not None and d < cutoff for d in dated):
            return result
        if len(features) < limit and not page.get("exceededTransferLimit"):
            return result
    raise RuntimeError("ArcGIS pagination safety cap reached; refusing partial publication")



def canonical_site_address(address: str | None) -> str | None:
    """Conservative same-address match; preserve unit/lot numbers.

    Only cosmetic case, whitespace and period/comma differences are normalized.
    Never group by subdivision, ZIP, project name, or fuzzy street similarity.
    """
    if not isinstance(address, str):
        return None
    clean = re.sub(r"\s+", " ", re.sub(r"[.,]", "", address).strip()).upper()
    if clean in ("", "UNKNOWN", "NOT PROVIDED", "ADDRESS NOT PUBLISHED", "TBD", "N/A", "NA"):
        return None
    return clean


def annotate_site_groups(records: list[dict]) -> dict:
    """Annotate a snapshot with probable SAME-SITE permit clusters.

    Matching a street address within an issuing jurisdiction is NOT proof that
    records describe one construction project, development, or customer.
    Empty addresses always remain individual permit records.
    """
    from collections import defaultdict
    from hashlib import sha256

    grouped = defaultdict(list)
    for record in records:
        address = canonical_site_address(record.get("address"))
        locality = (record.get("state") or "").strip() + "|" + (record.get("jurisdiction") or "").strip()
        if not locality or locality.startswith("|"):
            raise ValueError("Cannot group a permit without its jurisdiction and state")
        basis = "same_normalized_address" if address else "unverified_address"
        key = locality + "|address|" + address if address else locality + "|permit|" + str(record["id"])
        record["site_group_id"] = "site-" + sha256(key.encode("utf-8")).hexdigest()[:20]
        record["site_group_basis"] = basis
        grouped[key].append(record)

    for members in grouped.values():
        ordered = sorted(members, key=lambda r: (r.get("issued") or "", r.get("permit_number") or ""), reverse=True)
        permits = [r["permit_number"] for r in ordered]
        categories = sorted({r.get("category") for r in members if r.get("category")})
        for record in members:
            record["site_permit_count"] = len(members)
            record["site_related_permits"] = permits
            record["site_categories"] = categories

    return {
        "unique_sites": len(grouped),
        "multiple_permit_sites": sum(len(members) > 1 for members in grouped.values()),
        "permits_on_multiple_permit_sites": sum(len(members) for members in grouped.values() if len(members) > 1),
    }


def build(days: int = 120, s: requests.Session | None = None, today: date | None = None) -> dict:
    today = today or datetime.now(timezone.utc).date()
    cutoff = today - timedelta(days=days)
    s = s or session()
    all_records: dict[str, dict] = {}
    diagnostics = []
    errors = []
    for key, cfg in SOURCES.items():
        try:
            rows = (fetch_socrata(s, cfg, cutoff, today) if cfg["kind"] == "socrata"
                    else fetch_arcgis(s, cfg, cutoff, today))
            if not rows:
                raise RuntimeError("No records returned; cannot verify source health")
            imported = 0
            newest = None
            for row in rows:
                item = normalize(key, row, today, cutoff)
                if item:
                    all_records[item["id"]] = item
                    imported += 1
                    newest = max(newest or item["issued"], item["issued"])
            diagnostics.append({
                "key": key, "name": cfg["name"], "state": cfg["state"],
                "status": "ok", "raw_examined": len(rows),
                "count": len([i for i in all_records.values() if i["jurisdiction"] == cfg["name"]]),
                "latest_issue": newest, "source_url": cfg["source"], "portal_url": cfg["portal"],
            })
            print(cfg["name"] + ": " + str(imported) + " eligible permits from " + str(len(rows)) + " examined")
        except (requests.RequestException, ValueError, RuntimeError, KeyError, TypeError) as exc:
            errors.append(cfg["name"] + ": " + str(exc)[:320])
    if errors:
        raise RuntimeError("Data refresh ABORTED; prior snapshot preserved:\n" + "\n".join(errors))
    if not all_records:
        raise RuntimeError("All sources returned zero eligible permits; refusing blank snapshot")
    records = sorted(all_records.values(), key=lambda r: (-r["score"], r["issued"], r["id"]), reverse=False)
    site_stats = annotate_site_groups(records)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "window_days": days, "count": len(records), "site_stats": site_stats,
        "sources": diagnostics, "permits": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=120)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not 7 <= args.days <= 365:
        parser.error("--days must be between 7 and 365")
    try:
        payload = build(args.days)
        if not args.dry_run:
            OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            temporary = OUTPUT.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            temporary.replace(OUTPUT)
        print("Validated " + str(payload["count"]) + " permits; " + ("dry run" if args.dry_run else "snapshot saved"))
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
