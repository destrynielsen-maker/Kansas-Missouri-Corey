# Kansas–Missouri Construction Intelligence

Public-source construction permit leads for the Kansas City metro, covering Missouri and Kansas.

## First release

The first data adapters target **Kansas City, MO** (Open Data KC), **Overland Park, KS** (city ArcGIS), **Olathe, KS** (city ArcGIS), and **Lee's Summit, MO** (city ArcGIS). Kansas City, KS and Lenexa have verified public search portals but are not bulk-imported yet.

The dashboard prioritizes new construction and additions, lets a salesperson filter/search/export leads, and shows the **public permit/detail lookup before the underlying machine-readable source**. If a source does not publish a verified direct record URL, the primary link is clearly labeled **Search permit**, with the permit number next to it; we do not fabricate deep links.

No live permit counts are asserted until a successful ingestion run. Source data is official but may be delayed; permit issuance alone does not prove the project has started.

## Operating

- `python -m pip install -r requirements.txt`
- `python -m unittest discover -s tests -v`
- `python src/ingest.py --days 120`
- Open `docs/index.html` via a local web server or enable GitHub Pages from **main /docs**.
- GitHub Actions workflow `Refresh permit data` supports scheduled runs and manual **Run workflow** (Actions > Refresh permit data).

## Technical rules

- Four independent official adapters, paginated HTTP requests, bounded timeouts and retries.
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

Not affiliated with any of these municipalities.
