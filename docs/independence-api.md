# Independence, Missouri — official municipal permit API

**Verified November 18, 2026.** This is public municipal data, not an authenticated search or third-party scrape.

The Open Independence application obtains its configuration from https://opendata.independencemo.gov/api/config and its public browser code requests opendata/dataset?code=V1BUILDINGPERMITS from the city-operated backend.

- Human-friendly dataset: https://opendata.independencemo.gov/dataset?code=V1BUILDINGPERMITS
- Official API: https://apps.independencemo.gov/opendata/api/opendata/dataset?code=V1BUILDINGPERMITS
- Human permit-status search: https://apps.indepmo.org/comdev/SearchPermitStatus
- Dataset code: V1BUILDINGPERMITS; municipal title: Building Permits - Active
- Municipal lastUpdated: 2026-11-18T00:14:12.7292293
- Six exact ordered field titles: Permit Number, Address, Date Issued, Type, Construction Description, Construction Value
- Rows are arrays of six cell objects; each cell has a title and value.

## Verified data counts

Of **1,742 raw records**, **882 have an issue date in July 21–November 18, 2026**. Older records and missing issuance dates remain in the city dataset, so do not treat its title as proof of current status.

| Qualifying building type | Leads |
| --- | ---: |
| New single-family | 19 |
| Multifamily / duplex | 3 |
| New commercial | 6 |
| Structural additions | 10 |
| **Total** | **38** |

The five-city integration-run total was 814 qualified permits (776 from existing four cities plus 38 from Independence), as of November 18, 2026.

## Evidence and safety gates

- Adapter rejects unexpected dataset code/name, missing or changed column titles, malformed cells, and a municipal update date older than 14 days.
- All public data is read via GET without credentials. No undocumented per-row endpoint is invented.
- The published dataset has **no individual permit-status field, last-inspection field or verified construction start date**. Leads display Status not published; neither the word Active in the dataset title nor a recent issue date implies construction has begun.
- Only Residential or Commercial permit types are eligible, and the work description must clearly indicate new housing, new commercial construction, multifamily/duplex, or a structural addition.
- Roofing, trade work, signs, repairs, tenant finish, pools, decks and remodeling are excluded.
- The salesperson link opens the city's human permit-status search. The raw source link opens the **entire agency JSON dataset**, labeled Raw dataset rather than Raw record.
- Site grouping and quality audits apply; an unavailable, stale, or malformed new feed blocks publication of a misleading partial dataset.

## Verification run

- Live API and schema probe: https://github.com/destrynielsen-maker/Kansas-Missouri-Corey/actions/runs/44372357188
- First five-city import: https://github.com/destrynielsen-maker/Kansas-Missouri-Corey/actions/runs/44373019692
- Code: src/ingest.py; contract tests: tests/test_independence.py; source audit: src/audit_snapshot.py.
