# Metro expansion — jurisdiction source audit (2026-11-18)

Scope: Kansas City, Kansas / Wyandotte County first; adjacent sources surveyed.
This is a **source registry and integration backlog**, not a count of active new construction permits.

| City | Public evidence | Sales search | Integration decision |
| --- | --- | --- | --- |
| Kansas City, KS (Wyandotte) | Official Unified Government Accela public building permit search | https://aca-prod.accela.com/UG/Cap/CapHome.aspx?TabName=Home&module=Building | **Portal-only:** no validated row-level public API; do not harvest interactive search or pretend it is a bulk feed |
| Independence, MO | Official Open Independence **Building Permits**, described by the city as “Data Set, API” for permits issued in the past year | https://apps.indepmo.org/apps/BuildingPermits | **Candidate:** confirm documented API endpoint, schema, row identifier, issuance date, and pagination before adding to automated ETL |
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
