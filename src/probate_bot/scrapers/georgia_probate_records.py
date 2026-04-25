from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin

from probate_bot.models import ProbateBotError
from probate_bot.models import ProbateLead, SearchRequest
from probate_bot.scoring import score_lead
from probate_bot.scrapers.base import BaseScraper


class GeorgiaProbateRecordsScraper(BaseScraper):
    search_url = "https://www.georgiaprobaterecords.com/Estates/SearchEstates.aspx"

    def run(self, request: SearchRequest) -> list[ProbateLead]:
        try:
            from playwright.sync_api import sync_playwright
        except ModuleNotFoundError as exc:
            raise ProbateBotError(
                "Playwright is not installed. Run `pip install -e .` and `playwright install chromium` first."
            ) from exc

        leads: list[ProbateLead] = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=request.headless)
            page = browser.new_page()

            for county in request.counties:
                county_leads = self._scrape_county(page, county, request)
                leads.extend(county_leads[: request.max_results_per_county])

            browser.close()
        return leads

    def _scrape_county(self, page, county: str, request: SearchRequest) -> list[ProbateLead]:
        page.goto(self.search_url, wait_until="domcontentloaded")
        page.wait_for_timeout(1000)

        page.locator("#ctl00_cpMain_ddlCounty").click()
        county_option = page.locator("#ctl00_cpMain_ddlCounty_DropDown .rddlItem", has_text=county)
        county_option.first.click()

        if request.date_field == "deceased":
            start_input = "#ctl00_cpMain_txtDeceasedStartDate_dateInput"
            end_input = "#ctl00_cpMain_txtDeceasedEndDate_dateInput"
        else:
            start_input = "#ctl00_cpMain_txtFiledStartDate_dateInput"
            end_input = "#ctl00_cpMain_txtFiledEndDate_dateInput"

        if request.start_date:
            page.locator(start_input).fill(self._portal_date(request.start_date))
            page.locator(start_input).press("Tab")
        if request.end_date:
            page.locator(end_input).fill(self._portal_date(request.end_date))
            page.locator(end_input).press("Tab")

        page.locator("#ctl00_cpMain_btnSearch_input").click()

        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        detail_links = self._collect_detail_links_paginated(page, request.max_results_per_county)
        county_leads: list[ProbateLead] = []
        for detail_link in detail_links:
            lead = self._parse_detail(page, county, detail_link)
            county_leads.append(score_lead(lead))

        return county_leads

    def _collect_detail_entries(self, page) -> list[tuple[str, str]]:
        entries: list[tuple[str, str]] = []
        for locator in page.locator("#ctl00_cpMain_rgEstates_ctl00 a[href*='EstateDetails.aspx?RECID=']").all():
            href = locator.get_attribute("href") or ""
            if "EstateDetails.aspx?RECID=" in href:
                absolute = urljoin(page.url, href)
                case_no = locator.inner_text().strip()
                entries.append((case_no, absolute))
        return list(dict.fromkeys(entries))

    def _collect_detail_links_paginated(self, page, max_results: int) -> list[str]:
        entries: list[tuple[str, str]] = []
        seen_signatures: set[str] = set()
        while len(entries) < max_results:
            page_entries = self._collect_detail_entries(page)
            entries.extend(page_entries)
            entries = list(dict.fromkeys(entries))
            if len(entries) >= max_results:
                break

            signature = self._results_signature(page)
            if signature in seen_signatures:
                break
            seen_signatures.add(signature)

            if not self._go_to_next_page(page, signature):
                break

        # Portal sort controls are inconsistent; rank by parsed case-number recency locally.
        ranked = sorted(entries, key=lambda item: self._case_sort_key(item[0]), reverse=True)
        return [url for _, url in ranked[:max_results]]

    def _results_signature(self, page) -> str:
        first = page.locator("#ctl00_cpMain_rgEstates_ctl00 a[href*='EstateDetails.aspx?RECID=']")
        first_case = first.first.inner_text().strip() if first.count() else ""
        current_page = page.locator("#ctl00_cpMain_rgEstates_ctl00 a.rgCurrentPage")
        current_page_text = current_page.first.inner_text().strip() if current_page.count() else "1"
        return f"{current_page_text}|{first_case}"

    def _go_to_next_page(self, page, previous_signature: str) -> bool:
        clicked = page.evaluate(
            """
            () => {
              const selector = '#ctl00_cpMain_rgEstates_ctl00 a[href*="ctl00$cpMain$rgEstates$ctl00$ctl03$ctl01$"]';
              const links = [...document.querySelectorAll(selector)]
                .filter(a => a.offsetParent !== null)
                .map(a => ({
                  text: (a.textContent || '').trim(),
                  className: a.className || '',
                  node: a,
                }));
              if (!links.length) return false;

              const current = links.find(l => l.className.includes('rgCurrentPage'));
              let target = null;
              if (current && /^\\d+$/.test(current.text)) {
                const nextText = String(parseInt(current.text, 10) + 1);
                target = links.find(l => l.text === nextText)?.node || null;
              }
              if (!target) {
                target = links.find(l => l.text === '...')?.node || null;
              }
              if (!target) return false;
              target.click();
              return true;
            }
            """
        )
        if not clicked:
            return False

        # Telerik updates this grid via partial postback. Wait until page marker actually changes.
        for _ in range(24):
            page.wait_for_timeout(300)
            if self._results_signature(page) != previous_signature:
                return True
        return False

    def _case_sort_key(self, case_number: str) -> tuple[int, int, int]:
        case_number = (case_number or "").strip().upper()
        match_legacy = re.search(r"\bE-+(\d{2})-(\d+)\b", case_number)
        if match_legacy:
            yy = int(match_legacy.group(1))
            serial = int(match_legacy.group(2))
            year = 2000 + yy
            return (year, serial, len(case_number))

        match_modern = re.search(r"\b(\d{2})-[A-Z]-(\d+)\b", case_number)
        if match_modern:
            yy = int(match_modern.group(1))
            serial = int(match_modern.group(2))
            year = 2000 + yy
            return (year, serial, len(case_number))

        digits = re.findall(r"\d+", case_number)
        if digits:
            return (1900, int(digits[-1]), len(case_number))
        return (0, 0, 0)

    def _parse_detail(self, page, county: str, detail_url: str) -> ProbateLead:
        page.goto(detail_url, wait_until="domcontentloaded")
        page.wait_for_timeout(500)

        body_text = page.locator("body").inner_text()
        line_items = [line.strip() for line in body_text.splitlines() if line.strip()]

        decedent_name = self._value_after(line_items, "Decedent")
        case_number = self._value_after(line_items, "Case #")
        status = self._value_after(line_items, "Status")
        died = self._value_after(line_items, "Died")
        property_address = self._best_address(line_items)
        filings = self._section_values(line_items, marker="FILINGS", stop_markers=("Documents are not certified.",))
        filing_date = self._first_filing_date(line_items)
        petitioners = self._extract_petitioners(line_items)

        lead = ProbateLead(
            state="ga",
            county=county,
            source_system="georgiaprobaterecords",
            source_url=detail_url,
            case_number=case_number,
            case_name=decedent_name or case_number,
            decedent_name=decedent_name,
            status=status,
            filing_date=filing_date,
            date_of_death=died,
            property_address=property_address,
            petitioner_names=petitioners,
            filings=filings,
            raw={"body_excerpt": "\n".join(line_items[:80])},
        )
        return lead

    def _value_after(self, line_items: list[str], label: str) -> str:
        for index, line in enumerate(line_items):
            if line == label and index + 1 < len(line_items):
                return line_items[index + 1]
        return ""

    def _best_address(self, line_items: list[str]) -> str:
        for index, line in enumerate(line_items):
            if re.match(r"^\d{1,6}\s", line):
                city = line_items[index + 1] if index + 1 < len(line_items) else ""
                if city and "," in city:
                    return f"{line} {city}"
                return line
        return ""

    def _section_values(
        self,
        line_items: list[str],
        marker: str,
        stop_markers: tuple[str, ...],
    ) -> list[str]:
        capture = False
        values: list[str] = []
        for line in line_items:
            if line == marker:
                capture = True
                continue
            if capture and line in stop_markers:
                break
            if capture and self._is_probable_filing_name(line):
                values.append(line)
        return list(dict.fromkeys(values))

    def _extract_petitioners(self, line_items: list[str]) -> list[str]:
        values: list[str] = []
        for index, line in enumerate(line_items):
            if line == "Petitioner" and index + 1 < len(line_items):
                values.append(line_items[index + 1])
        return list(dict.fromkeys(values))

    def _first_filing_date(self, line_items: list[str]) -> str:
        date_pattern = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}$")
        in_filings = False
        for line in line_items:
            if line == "FILINGS":
                in_filings = True
                continue
            if in_filings and line == "Documents are not certified.":
                break
            if in_filings and date_pattern.match(line):
                return line
        return ""

    def _is_probable_filing_name(self, value: str) -> bool:
        return bool(
            value
            and value.upper() == value
            and len(value) > 4
            and not re.search(r"\d{1,2}/\d{1,2}/\d{2,4}", value)
        )

    def _portal_date(self, value: str) -> str:
        if re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}$", value):
            return value
        parsed = datetime.strptime(value, "%Y-%m-%d")
        return parsed.strftime("%m/%d/%Y")
