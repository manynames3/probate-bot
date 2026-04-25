# Source Registry

This project is built around county probate sources that were checked on April 23, 2026.

## Georgia

### Supported now

- Hall County, GA
- Henry County, GA
- Douglas County, GA
- Fayette County, GA
- Forsyth County, GA
- Chatham County, GA

These counties are routed through the public Georgia Probate Records estates portal:

- Portal: `https://www.georgiaprobaterecords.com/Estates/SearchEstates.aspx`
- Participating courts list: `https://www.georgiaprobaterecords.com/Courts/CourtInformation.aspx`

### Supported now (direct county adapter)

- Cobb County, GA
  - Official page: `https://www.cobbcounty.gov/probate-court/case-status-records-search`
  - Public portal: `https://probateonline.cobbcounty.gov/BenchmarkWeb/Home.aspx/Search`
  - Adapter path: `Court Docket` -> `List Cases` -> `CourtCase.aspx/Details/...`

### Public and convenient, but not wired yet

- Athens-Clarke County, GA
  - Official page: `https://www.accgov.com/735/Probate-Court`
  - Court portal: `https://athensclarkeprobatecourt.com/`

## South Carolina

South Carolina sources were researched, but are intentionally blocked in this starter because county probate pages warn against using covered public-record personal information for commercial solicitation.

### Examples reviewed

- Dorchester County probate records page:
  - `https://www.dorchestercountysc.gov/government/courts-judicial-services/probate-court/public-records-requests`
- Richland County estates page:
  - `https://www.richlandcountysc.gov/Courts-Safety/Probate-Court/Estates`
- Lexington County probate page and disclaimer path:
  - `https://lex-co.sc.gov/departments/probate-court`

## Notes

- The Georgia adapter was live-validated against Hall County on April 23, 2026.
- The current MVP now supports newest-first sorting and paginated traversal for Georgia grid results.
- Cobb extraction is based on public docket-linked case pages and may not expose the same property-address richness as Georgia estate detail pages.
