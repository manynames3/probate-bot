import sqlite3
import tempfile
import unittest
from pathlib import Path

from probate_bot.models import ProbateLead
from probate_bot.storage import backup_database, create_sync_run, ensure_database, export_leads, upsert_leads


class StorageTests(unittest.TestCase):
    def test_upsert_leads_dedupes_on_case_identity(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "probate.sqlite")
            ensure_database(db_path)

            lead = ProbateLead(
                state="ga",
                county="Hall",
                source_system="georgiaprobaterecords",
                source_url="https://example.com/1",
                case_number="E-01-001",
                case_name="Jane Doe",
                decedent_name="Jane Doe",
            )
            stats_1 = upsert_leads(db_path, [lead])
            stats_2 = upsert_leads(db_path, [lead])

            self.assertEqual(stats_1.inserted, 1)
            self.assertEqual(stats_1.updated, 0)
            self.assertEqual(stats_2.inserted, 0)
            self.assertEqual(stats_2.updated, 1)

            with sqlite3.connect(db_path) as conn:
                row = conn.execute(
                    "SELECT COUNT(*), MAX(run_count) FROM leads WHERE dedupe_key = ?",
                    (lead.dedupe_key(),),
                ).fetchone()

            self.assertEqual(row[0], 1)
            self.assertEqual(row[1], 2)

    def test_create_sync_run_allows_empty_window(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "probate.sqlite")
            ensure_database(db_path)

            run_id = create_sync_run(
                db_path,
                trigger_source="test",
                state="ga",
                counties=["Hall"],
                start_date=None,
                end_date=None,
            )

            self.assertGreater(run_id, 0)

            with sqlite3.connect(db_path) as conn:
                row = conn.execute(
                    "SELECT start_date, end_date, status FROM sync_runs WHERE id = ?",
                    (run_id,),
                ).fetchone()

            self.assertEqual(row[0], "")
            self.assertEqual(row[1], "")
            self.assertEqual(row[2], "running")

    def test_backup_and_export_round_trip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            db_path = str(tmp_path / "probate.sqlite")
            ensure_database(db_path)

            lead = ProbateLead(
                state="ga",
                county="Hall",
                source_system="georgiaprobaterecords",
                source_url="https://example.com/1",
                case_number="E-01-001",
                case_name="Jane Doe",
                decedent_name="Jane Doe",
                status="OPEN",
                petitioner_names=["John Doe"],
                lead_reasons=["open estate"],
            )
            upsert_leads(db_path, [lead])

            exported = export_leads(db_path)
            backup_path = backup_database(db_path, str(tmp_path / "backups"), keep=2)

            self.assertEqual(len(exported), 1)
            self.assertEqual(exported[0].case_number, "E-01-001")
            self.assertTrue(backup_path.exists())


if __name__ == "__main__":
    unittest.main()
