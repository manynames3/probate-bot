import unittest

from probate_bot.scrapers.cobb_benchmark import CobbBenchmarkScraper


class CobbBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.scraper = CobbBenchmarkScraper()

    def test_extract_case_number_from_heading(self):
        case_number = self.scraper._extract_case_number("24-P-2391 - MCCULLOUGH IV, MILES WILLIAM")
        self.assertEqual(case_number, "24-P-2391")

    def test_date_range_inclusive(self):
        dates = self.scraper._date_range("2026-04-22", "2026-04-24")
        self.assertEqual(len(dates), 3)
        self.assertEqual(str(dates[0]), "2026-04-22")
        self.assertEqual(str(dates[-1]), "2026-04-24")


if __name__ == "__main__":
    unittest.main()
