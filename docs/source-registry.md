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

### Public and convenient, but not wired yet

- Cobb County, GA
  - Official page: `https://www.cobbcounty.gov/probate-court/case-status-records-search`
  - Public search portal: `https://probateonline.cobbcounty.gov/BenchmarkWeb/Home.aspx/Search`
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
- The current MVP reliably collects county-scoped result pages and estate detail pages.
- The next engineering pass should improve newest-first navigation and deeper pagination inside the Georgia results grid.
