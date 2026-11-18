# Lenexa construction intelligence: official source audit

Reviewed November 18, 2026 — this document distinguishes city planning activity from issued building permits.

## Official city sources

- Planning Commission pending applications: https://www.lenexa.com/Government/Boards-Commissions/Planning-Commission
- Monthly building permit reports: https://www.lenexa.com/Business-Development/Design-Construction/Building-Permit-Reports
- Public Accela permit search: https://aca-prod.accela.com/LENEXA/Default.aspx
- Johnson County AIMS ArcGIS directory: https://maps.jocogov.org/ArcGIS/rest/services

## What can be imported now?

The City's pending applications page lists proposed projects, work, and locations. We manually reviewed 11 structural/site-development candidates for the 2026-11-18 snapshot, including one subdivision application explicitly on hold. The results are in docs/data/lenexa_planning.json and are NOT issued permits. The source publishes no corresponding permit IDs or exact building-permit issue dates for those applications.

The City monthly report format contains residential/commercial aggregate permit totals and occasionally a table of named commercial/apartment projects exceeding a cost threshold. These reports are not a complete row-level source of new single-family permit numbers and addresses. A published 2025 report confirms the format: https://www.lenexa.com/files/sharedassets/city/v/1/business-development/bpr/2025-building-permit-reports/02-2025-building-permit-report.pdf.

An automated bounded metadata check ran Nov 18, 2026 at https://github.com/destrynielsen-maker/Kansas-Missouri-Corey/actions/workflows/probe-lenexa.yml. The official report index returned HTTP 403 to the GitHub runner. Eight candidate 2026 PDF URLs did not validate as PDFs. The old Johnson County AIMS Permits/MapServer endpoint returned an API error or unexpected payload. These are source-discovery/access limitations, not proof that no other official data exists.

A generic ArcGIS Building Permits FeatureServer found in public search is not evidence of Lenexa issuance; confirm issuing agency and geography before adding any such data.

## How to interpret the planning list

- Pending means listed under the city's Pending applications heading at this review date.
- On hold means the city explicitly marked the Watercrest Landing final plat application as on hold.
- Preliminary/final plan or plat are planning-stage descriptions, not confirmed issued permits or construction starts.
- Approximate locations are road corridors or intersections, not verified addresses.
- The snapshot requires manual review. The dashboard flags it stale after 30 days; the city site may change sooner.

## Gate to add Lenexa as an automated issued-permit source

1. Obtain an official authorized CSV, open API, or a detailed permit report with stable record identifiers.
2. Confirm issuer, issued date, status, work class, address, paging, source update frequency and source detail links.
3. Filter only genuine new-building, multifamily, commercial and structural addition records, not trades, roofs, fences, decks, pools or remodels.
4. Preserve public permit lookup before underlying raw source. Pass dry-run and QA checks before counting any permit.

See the drafted, UNSENT data-access request: lenexa-data-request.md
