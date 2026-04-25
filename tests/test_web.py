import tempfile
import unittest
from pathlib import Path

from probate_bot.models import ProbateLead
from probate_bot.storage import ensure_database, upsert_leads
from probate_bot.web import create_app


class WebTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.db_path = str(Path(self.tmpdir.name) / "probate.sqlite")
        ensure_database(self.db_path)
        upsert_leads(
            self.db_path,
            [
                ProbateLead(
                    state="ga",
                    county="Hall",
                    source_system="georgiaprobaterecords",
                    source_url="https://example.com/lead/1",
                    case_number="E-01-001",
                    case_name="Estate of Jane Doe",
                    decedent_name="Jane Doe",
                    status="OPEN",
                    filing_date="2026-04-24",
                    property_address="123 Main St, Gainesville, GA",
                    petitioner_names=["John Doe"],
                    lead_score=87,
                    lead_reasons=["open estate"],
                )
            ],
        )
        self.app = create_app(self.db_path)
        self.client = self.app.test_client()

    def test_index_renders_dashboard_data(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Probate lead sync, storage, and review.", body)
        self.assertIn("Jane Doe", body)
        self.assertIn("123 Main St, Gainesville, GA", body)

    def test_export_csv_returns_attachment(self):
        response = self.client.get("/export/csv")

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment; filename=probate-leads.csv", response.headers["Content-Disposition"])
        body = response.get_data(as_text=True)
        self.assertIn("case_number", body)
        self.assertIn("E-01-001", body)
        response.close()


if __name__ == "__main__":
    unittest.main()
