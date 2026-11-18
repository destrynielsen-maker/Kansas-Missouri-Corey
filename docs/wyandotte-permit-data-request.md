# Unified Government / Wyandotte County permit-data request — draft

**Status:** Draft for human submission only. **Not sent.**  
**Jurisdiction of interest:** Kansas City, Kansas / Wyandotte County; explicitly distinguish City of Kansas City, KS permits from permits issued by other Wyandotte County municipalities.

## Proposed message to the Unified Government

Subject: Request for public machine-readable Kansas City, KS building permit issuance records

Hello,

I'm researching public building permit activity in Kansas City, Kansas and Wyandotte County. The Unified Government's Accela Citizen Access public portal already allows individual permit searches. I would like to obtain the corresponding public building-permit issuance records in CSV, spreadsheet or documented API format if available.

For the most recent 12 months, and preferably as a routinely updated monthly or weekly feed, please provide these fields where already public and maintained by the agency:

- Issuing jurisdiction and permit number / stable record identifier
- Permit issuance date and current publicly available status
- Project/street address, city and ZIP code
- Permit type/work class (especially new single-family, duplex/townhouse, multifamily, new commercial construction, and structural additions)
- Brief public work description, approximate valuation, and square footage/unit count when available
- Publicly listed contractor/builder company name (business-level only, if releasable)
- An official public permit detail or search URL, if the system supports it
- Source update timestamp, and guidance on any reporting lags or limitations

I am not requesting user passwords, protected records, personal identity documents, private contacts, plans behind access controls, or entry into non-public Accela endpoints.

If a documented public API or existing recurring report is already available, a link and field definitions would be ideal. Otherwise, please advise on the public-records request process, cost/format options, and how to receive updates.

Thank you.

## Technical intake requirements

1. Validate that the records belong to the intended issuing city/county and do not conflate Kansas City, MO.
2. Confirm an official, permitted data-delivery mechanism. Do not automate login-gated Accela forms or bypass a challenge.
3. Require a stable permit ID, issuance date, work class, site address and public-source evidence.
4. Confirm paging/export size, update frequency, late-arriving records and whether status is reliable.
5. Classify only new structural work and additions; don't mistake trades, signs, fences or inspections for building starts.
6. Display human permit-detail/search links first, and keep raw-source URLs separate.
7. Add a single adapter behind tests and a dry-run QA report before publishing.

## Public endpoints already reviewed

- [Unified Government's public permit search](https://aca-prod.accela.com/UG/Cap/CapHome.aspx?TabName=Home&module=Building)
- [UG ArcGIS public services](https://gisweb.wycokck.org/arcgis/rest/services)
- [GISPUB](https://gisweb.wycokck.org/arcgis/rest/services/GISPUB)
- [UGMAPS](https://gisweb.wycokck.org/arcgis/rest/services/UGMAPS)
- [GISPW](https://gisweb.wycokck.org/arcgis/rest/services/GISPW)

The four reviewed GIS catalogs contained no permit-named service on November 18, 2026 (162 services inspected). This does not establish that no other public dataset exists. The public source monitor re-checks these catalogs weekly without collecting permit records.
