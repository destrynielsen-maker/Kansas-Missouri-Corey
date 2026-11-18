# Metro expansion — jurisdiction source audit (2026-11-18)

Scope: Kansas City, Kansas / Wyandotte County first; adjacent sources surveyed.
This is a **source registry and integration backlog**, not a count of active new construction permits.

| City | Public evidence | Sales search | Integration decision |
| --- | --- | --- | --- |
| Kansas City, KS (Wyandotte) | Official Unified Government Accela public building permit search | https://aca-prod.accela.com/UG/Cap/CapHome.aspx?TabName=Home&module=Building | **Portal-only:** 162 listed services inspected across four UG public GIS catalogs on Nov 18, 2026; none had permit-related service names. No validated bulk endpoint. Weekly source-health monitoring is enabled; GIS inspection cannot replace the Accela permit record |
| Independence, MO | City-managed Open Independence six-column public JSON API verified | https://apps.indepmo.org/comdev/SearchPermitStatus | **Automated**; strict issue-date and construction filters. Individual permit status/inspection fields unavailable. See [API evidence](independence-api.md). |
| Lenexa, KS | Official public Accela search; monthly permit activity reports | https://aca-prod.accela.com/LENEXA/Default.aspx | **Portal/report:** verify whether any published monthly detail offers row-level IDs and dates before proposing an adapter |
| Shawnee, KS | City building department directs users to Citizenserve for searches | https://www.citizenserve.com/shawnee | **Portal-only:** no validated bulk API |
| Kansas City, MO | City's current city-issued permit dataset | https://compasskc.kcmo.org/ | **Active source:** qualified building permits loaded |
| Overland Park, KS | ArcGIS Building Permit Report | https://overlandparkks.tylerportico.com/portal/ | **Active source:** qualified building permits loaded |
| Olathe, KS | ArcGIS Building Permits | https://energov.olatheks.org/ | **Active source:** qualified building permits loaded |
| Lee's Summit, MO | ArcGIS Development_Public/MapServer/29 | https://cityview2.iharriscomputer.com/leessummitmoportal/ | **Active source:** qualified building permits loaded |

Sources:
- https://aca-prod.accela.com/UG/Cap/CapHome.aspx?TabName=Home&module=Building
- https://apps.indepmo.org/Apps/OpenData/Home
- https://opendata.independencemo.gov/dataset?code=V1BUILDINGPERMITS
- https://www.cityofshawnee.org/212/Building-Permits-Inspections
- https://www.lenexa.com/Business-Development/Design-Construction/Building-Permit-Reports

## Next integration gates

1. Confirm stable public machine-readable endpoint (no login, no bypassing restrictions).
2. Validate issuer, date fields, one stable record ID, work class, status, and street address.
3. Verify pagination, date bounds, stale/empty-feed failure safety and links.
4. Add one jurisdiction at a time behind automated tests.
5. Record verified source freshness and check multiple real records manually.

**No fabricated permit-detail links.** When official data lacks direct record URLs, link to the public human-search page, show the permit number, and keep raw source URLs in a separate column.

See the [draft public-records/CSV API request](wyandotte-permit-data-request.md) if obtaining a stable agency feed requires a manual request. This draft has not been submitted.

## Wyandotte source-health monitor

- Public Unified Government ArcGIS directories: [root](https://gisweb.wycokck.org/arcgis/rest/services), [GISPUB](https://gisweb.wycokck.org/arcgis/rest/services/GISPUB), [UGMAPS](https://gisweb.wycokck.org/arcgis/rest/services/UGMAPS), and [GISPW](https://gisweb.wycokck.org/arcgis/rest/services/GISPW).
- Verified November 18, 2026: 2 root services, 102 GISPUB services, 16 UGMAPS services, and 42 GISPW services. No permit-named public service among these 162 listings.
- Catalog names are not records. A new candidate remains unverified until issuer, permit numbers, dates, work class, status and address are checked against official records.
- The public GISEDITS folder requires sign-in and is deliberately **not** accessed.
- Weekly source monitor: `.github/workflows/check-wyandotte.yml`; report: `docs/data/source_health.json`.
- KCK Accela manual search remains available: https://aca-prod.accela.com/UG/Cap/CapHome.aspx?TabName=Home&module=Building
- The [HBA regional permit reports](https://kchba.org/where-are-we-building/) provide aggregate jurisdiction activity, not specific project leads. Do not include these totals as individual permits.
