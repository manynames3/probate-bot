from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from urllib.parse import urljoin

from probate_bot.models import ProbateBotError
from probate_bot.models import ProbateLead, SearchRequest
from probate_bot.scoring import score_lead
from probate_bot.scrapers.base import BaseScraper


class CobbBenchmarkScraper(BaseScraper):
    home_url = "https://probateonline.cobbcounty.gov/BenchmarkWeb/Home.aspx/Search"

    def run(self, request: SearchRequest) -> list[ProbateLead]:
        try:
            from playwright.sync_api import sync_playwright
        except ModuleNotFoundError as exc:
            raise ProbateBotError(
                "Playwright is not installed. Run `pip install -e .` and `playwright install chromium` first."
            ) from exc

        leads: list[ProbateLead] = []
        seen_case_numbers: set[str] = set()
        crawl_dates = self._date_range(request.start_date, request.end_date)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=request.headless)
            page = browser.new_page()
            page.goto(self.home_url, wait_until="domcontentloaded")
            page.wait_for_timeout(1200)
            page.get_by_text("Court Docket", exact=True).click()
            page.wait_for_timeout(1200)

            for run_date in crawl_dates:
                if len(leads) >= request.max_results_per_county:
                    break
                self._run_docket_search(page, run_date)
                case_detail_urls = self._collect_case_detail_urls(page)
                for detail_url in case_detail_urls:
                    if len(leads) >= request.max_results_per_county:
                        break
                    lead = self._parse_case_detail(page, detail_url)
                    if not lead.case_number or lead.case_number in seen_case_numbers:
                        continue
                    seen_case_numbers.add(lead.case_number)
                    leads.append(score_lead(lead))

            browser.close()
        return leads

    def _run_docket_search(self, page, run_date: date) -> None:
        page.locator("#fromDate").fill(run_date.strftime("%-m/%-d/%Y"))
        page.locator("#fromDate").press("Tab")
        page.locator("button[type='submit']").first.click()
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(1000)

    def _collect_case_detail_urls(self, page) -> list[str]:
        event_links = page.locator("a[title='List Cases']")
        detail_urls: list[str] = []
        event_hrefs = [
            href
            for href in (
                event_links.evaluate_all("els => els.map(el => el.getAttribute('href') || '')")
                if event_links.count()
                else []
            )
            if href
        ]

        for event_href in event_hrefs:
            event_url = urljoin(page.url, event_href)
            page.goto(event_url, wait_until="domcontentloaded")
            page.wait_for_timeout(900)

            links = page.locator("a[href*='/BenchmarkWeb/CourtCase.aspx/Details/']")
            hrefs = [
                href
                for href in (
                    links.evaluate_all("els => els.map(el => el.getAttribute('href') || '')")
                    if links.count()
                    else []
                )
                if href
            ]
            for href in hrefs:
                detail_urls.append(urljoin(page.url, href))

        return list(dict.fromkeys(detail_urls))

    def _parse_case_detail(self, page, detail_url: str) -> ProbateLead:
        page.goto(detail_url, wait_until="domcontentloaded")
        page.wait_for_timeout(900)
        body_text = page.locator("body").inner_text()
        line_items = [line.strip() for line in body_text.splitlines() if line.strip()]

        case_heading = self._find_heading(line_items)
        case_number = self._extract_case_number(case_heading) or self._value_after(line_items, "Case Number:")
        party_name = self._extract_party_name(case_heading)
        filing_date = self._value_after(line_items, "Clerk File Date:")
        status = self._value_after(line_items, "Status:")
        case_type = self._value_after(line_items, "Case Type:")
        court_type = self._value_after(line_items, "Court Type:")
        petitioners = self._extract_party_roles(
            line_items,
            roles={
                "PETITIONER",
                "EXECUTOR",
                "ADMINISTRATOR",
                "GUARDIAN/CONSERVATOR",
            },
        )
        filings = self._extract_filing_events(line_items)

        lead = ProbateLead(
            state="ga",
            county="Cobb",
            source_system="cobb-benchmark-docket",
            source_url=detail_url,
            case_number=case_number,
            case_name=case_heading or case_number,
            decedent_name=party_name,
            status=status,
            filing_date=filing_date,
            petitioner_names=petitioners,
            filings=[value for value in [case_type, court_type, *filings] if value],
            raw={"body_excerpt": "\n".join(line_items[:120])},
        )
        return lead

    def _find_heading(self, line_items: list[str]) -> str:
        for line in line_items:
            if re.match(r"^\d{2}-[A-Z]-\d+", line):
                return line
        return ""

    def _extract_case_number(self, heading: str) -> str:
        match = re.search(r"\b\d{2}-[A-Z]-\d+\b", heading)
        return match.group(0) if match else ""

    def _extract_party_name(self, heading: str) -> str:
        if " - " in heading:
            return heading.split(" - ", 1)[1].strip()
        return ""

    def _value_after(self, line_items: list[str], label: str) -> str:
        for index, line in enumerate(line_items):
            if line == label and index + 1 < len(line_items):
                return line_items[index + 1]
        return ""

    def _extract_party_roles(self, line_items: list[str], roles: set[str]) -> list[str]:
        values: list[str] = []
        for index, line in enumerate(line_items):
            if line in roles and index + 1 < len(line_items):
                values.append(line_items[index + 1])
        return list(dict.fromkeys(values))

    def _extract_filing_events(self, line_items: list[str]) -> list[str]:
        events: list[str] = []
        in_events = False
        for line in line_items:
            if line == "EVENTS":
                in_events = True
                continue
            if in_events and line == "CASE DOCKETS":
                break
            if in_events and self._looks_like_event_name(line):
                events.append(line)
        return list(dict.fromkeys(events))

    def _looks_like_event_name(self, value: str) -> bool:
        if not value:
            return False
        if re.search(r"\d{1,2}/\d{1,2}/\d{2,4}", value):
            return False
        if value.endswith("AM") or value.endswith("PM"):
            return False
        return bool(re.search(r"[A-Z]", value))

    def _date_range(self, start_date: str | None, end_date: str | None) -> list[date]:
        if start_date and end_date:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            if end < start:
                start, end = end, start
        elif end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            start = end
        elif start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = start
        else:
            start = date.today()
            end = start

        results: list[date] = []
        cursor = start
        while cursor <= end:
            results.append(cursor)
            cursor += timedelta(days=1)
        return results
