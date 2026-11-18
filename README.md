# Kansas–Missouri Construction Intelligence

Public-source construction permit leads for the Kansas City metro, covering Missouri and Kansas.

## Site-level prospecting

The default dashboard view groups permits only when issuing jurisdiction and exact normalized street address match (case, whitespace, periods and commas ignored; unit numbers preserved). This is a **same-address cluster**, not proof of the same project, developer, customer, or builder. Select **Individual permits** to see every original agency row. The count and list of related permits reflect current filters, while the full 120-day site count is retained in CSV exports. Site view exports one representative highest-scored permit per matching address; permit view exports all qualifying permits.

See [`docs/source-audit.md`](docs/source-audit.md) for pending Kansas City, KS, Lenexa and Shawnee integrations. Wyandotte’s four official public GIS catalog directories are now checked weekly without harvesting permit data; and [Independence API evidence](docs/independence-api.md) for the verified fifth feed. **Portal-only jurisdictions are not counted as live feeds.**

## Current coverage

Five live adapters cover **Kansas City, MO** (Socrata), **Overland Park, KS**, **Olathe, KS**, **Lee's Summit, MO** (municipal ArcGIS), and **Independence, MO** (city-operated Open Independence JSON API). Kansas City, KS and Lenexa remain public-search-only until their official bulk datasets can be verified. Independence's dataset is titled Active, but individual permit statuses, inspection dates, and construction starts are not published.

The dashboard prioritizes new construction and additions, lets a salesperson filter/search/export leads, and shows the **public permit/detail lookup before the underlying machine-readable source**. If a source does not publish a verified direct record URL, the primary link is clearly labeled **Search permit**, with the permit number next to it; we do not fabricate deep links.

No live permit counts are asserted until a successful ingestion run. Source data is official but may be delayed; permit issuance alone does not prove the project has started.

## Construction timelines and sales follow-up

The pipeline preserves available agency-reported **application**, **issuance**, **last-inspection**, **expiration**, and **finalization** dates. Missing inspection fields are explicitly different from empty ones.

**No confirmed construction-start or completion date is invented.** Last-inspection date proves only that a record of an inspection date exists, not that construction began or reached a particular phase. Finalized or closed permits are excluded from the active leads. Dates with impossible chronology are withheld and flagged.

The browser shows official-activity filters and clearly labeled **sales follow-up suggestions** based on permit age: 0–7, 8–30, 31–90, and 91+ days. These are sales cadence recommendations, not construction schedules. CSV exports include official dates, provenance and follow-up labels.

## Public dashboard deployment

The repo includes `.github/workflows/pages.yml` which deploys the static `docs/` site from `main`. If Pages is not enabled, its owner must go to **Settings → Pages → Build and deployment → Source: GitHub Actions** once. Expected site address: `https://destrynielsen-maker.github.io/Kansas-Missouri-Corey/` (not considered live until a successful Pages deployment).

After setup, manually use **Actions → Publish construction lead dashboard → Run workflow** or let changes to `docs/` on `main` deploy. Source refresh jobs only commit to `main`; feature branches verify data without publishing.

## Operating

- `python -m pip install -r requirements.txt`
- `python -m unittest discover -s tests -v`
- `python src/ingest.py --days 120`
- Open `docs/index.html` via a local web server or enable GitHub Pages from **main /docs**.
- GitHub Actions workflow `Refresh permit data` supports scheduled runs and manual **Run workflow** (Actions > Refresh permit data).

## Technical rules

- Five independent official adapters: paginated Socrata and ArcGIS feeds plus a schema-validated bounded municipal JSON dataset for Independence; freshness checks, timeouts and retries.
- Only recent building-related permits, with date and valuation sanity checks and deduplication.
- A failed or empty mandatory source prevents publishing a misleading empty dataset.
- No private credentials in browser code or repository; no scraping gated portals.
- Original agency/source URL stays with every record; permit lookup is placed first.
- Refresh publishes a dated JSON snapshot under `docs/data/permits.json`, and the dashboard displays snapshot freshness.

See `docs/data/coverage.json` for verified portals and staged jurisdictions. For GitHub Pages, go to **Settings > Pages > Deploy from a branch > main > /docs** if not enabled.

## Government sources

- Kansas City, MO: https://data.kcmo.org/d/w8jz-wjgn
- Overland Park, KS: https://maps.opkansas.org/mapping/rest/services/MixedInfo/Building_Permit_Report/MapServer/0
- Olathe, KS: https://arcgis.olatheks.org/arcgis/rest/services/Planning/Development/MapServer/0
- Lee's Summit, MO: https://maps.cityofls.net/arcgis/rest/services/Development_Public/MapServer/29
- Independence, MO: https://opendata.independencemo.gov/dataset?code=V1BUILDINGPERMITS

Not affiliated with any of these municipalities.

## Wyandotte/Kansas City, KS source-health tracking

Run **Actions → Check Wyandotte public data catalogs → Run workflow**. The weekly job checks four public official UG ArcGIS service-name lists, documents whether any candidate permit-named service appeared, and updates `docs/data/source_health.json` on `main` only. The result is an API source discovery report, not issued permit records. A catalog request failure is labeled **incomplete** rather than falsely claiming no feed exists. The job never accesses login-gated service folders or Accela transactions.

Current dashboard continues to count only five verified city feeds. Manual KCK building-permit search: https://aca-prod.accela.com/UG/Cap/CapHome.aspx?TabName=Home&module=Building.
