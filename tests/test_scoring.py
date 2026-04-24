import unittest

from probate_bot.models import ProbateLead
from probate_bot.scoring import looks_like_street_address, score_lead


class ScoringTests(unittest.TestCase):
    def test_looks_like_street_address_detects_common_pattern(self):
        self.assertTrue(looks_like_street_address("2335 Ambassador Drive Lithia Springs, GA 30122"))

    def test_score_lead_rewards_open_estate_with_address_and_petitioner(self):
        lead = ProbateLead(
            state="ga",
            county="Douglas",
            source_system="georgiaprobaterecords",
            source_url="https://example.com",
            decedent_name="Allesia Lashon Anderson",
            status="OPEN",
            property_address="2335 Ambassador Drive Lithia Springs, GA 30122",
            petitioner_names=["Cynthia Anderson"],
            filings=["PETITION FOR TEMPORARY LETTERS OF ADMINISTRATION"],
            filing_date="2019-02-04",
            date_of_death="2017-02-09",
        )

        scored = score_lead(lead)
        self.assertGreaterEqual(scored.lead_score, 80)
        self.assertIn("open estate", scored.lead_reasons)


if __name__ == "__main__":
    unittest.main()
