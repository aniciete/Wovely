import unittest
import os
import tempfile
import sqlite3
from database import init_db, save_run, get_all_runs, get_run_detail, delete_run, get_db_connection

class TestDatabase(unittest.TestCase):

    def setUp(self):
        # Create a temp file path for sqlite DB
        self.db_fd, self.db_path = tempfile.mkstemp()
        init_db(self.db_path)

    def tearDown(self):
        os.close(self.db_fd)
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_init_db_creates_tables(self):
        """Verify wovely schema runs and people tables exist."""
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        
        # Query sqlite_master to verify tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        self.assertIn("runs", tables)
        self.assertIn("people", tables)
        conn.close()

    def test_save_run_and_retrieve(self):
        """Verify saving a complete run payload and querying it back details."""
        mock_result = {
            "source_video": "test_video.mp4",
            "model": "gemini-3.1-flash-lite",
            "run_metadata": {
                "total_input_tokens": 100,
                "total_output_tokens": 20,
                "estimated_cost_usd": 0.005
            },
            "chunks": [
                {
                    "chunk_index": 0,
                    "time_range_seconds": [0.0, 45.0],
                    "status": "ok",
                    "people": [
                        {
                            "person_label": "person_1",
                            "hair": {"color": "blonde", "texture": "wavy", "length": "long", "style": "down"},
                            "top": {"type": "t-shirt", "color": "white", "fit": "fitted", "fabric": "cotton", "pattern": "solid", "details": ["V-neck"]},
                            "bottom": {"type": "jeans", "color": "blue", "fit": "slim", "fabric": "denim", "pattern": "solid", "details": []}
                        }
                    ]
                }
            ]
        }
        
        # Save run
        run_id = save_run(self.db_path, mock_result)
        self.assertIsNotNone(run_id)
        
        # Retrieve details
        detail = get_run_detail(self.db_path, run_id)
        self.assertIsNotNone(detail)
        self.assertEqual(detail["source_video"], "test_video.mp4")
        self.assertEqual(detail["model"], "gemini-3.1-flash-lite")
        self.assertEqual(detail["status"], "ok")
        self.assertEqual(detail["duration_sec"], 45.0)
        self.assertEqual(detail["input_tokens"], 100)
        self.assertEqual(detail["output_tokens"], 20)
        self.assertEqual(detail["est_cost_usd"], 0.005)
        
        # Check people mapping
        self.assertEqual(len(detail["people"]), 1)
        person = detail["people"][0]
        self.assertEqual(person["person_label"], "person_1")
        self.assertEqual(person["hair"]["color"], "blonde")
        self.assertEqual(person["top"]["type"], "t-shirt")
        self.assertEqual(person["top"]["color"], "white")
        self.assertEqual(person["top"]["fit"], "fitted")
        self.assertEqual(person["top"]["details"], ["V-neck"])
        self.assertEqual(person["bottom"]["type"], "jeans")
        self.assertEqual(person["bottom"]["color"], "blue")

    def test_delete_run_cascades(self):
        """Verify deleting a run cascades deletion of people rows."""
        mock_result = {
            "source_video": "video_to_delete.mp4",
            "model": "gemini-3.1-flash-lite",
            "chunks": [
                {
                    "chunk_index": 0,
                    "people": [
                        {
                            "person_label": "person_del",
                            "hair": {"color": "brown", "texture": None, "length": None, "style": None},
                            "top": {"type": "shirt", "color": "red", "fit": None, "fabric": None, "pattern": None, "details": []},
                            "bottom": {"type": "pants", "color": "black", "fit": None, "fabric": None, "pattern": None, "details": []}
                        }
                    ]
                }
            ]
        }
        
        run_id = save_run(self.db_path, mock_result)
        
        # Verify people records exist
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM people WHERE run_id = ?", (run_id,))
        self.assertEqual(cursor.fetchone()[0], 1)
        conn.close()
        
        # Delete run
        deleted = delete_run(self.db_path, run_id)
        self.assertTrue(deleted)
        
        # Check cascade delete worked
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM people WHERE run_id = ?", (run_id,))
        self.assertEqual(cursor.fetchone()[0], 0)
        
        # Check run itself was deleted
        cursor.execute("SELECT count(*) FROM runs WHERE id = ?", (run_id,))
        self.assertEqual(cursor.fetchone()[0], 0)
        conn.close()

    def test_get_all_runs_ordered(self):
        """Verify that get_all_runs returns list in order of most recent first."""
        run1 = {
            "source_video": "first_video.mp4",
            "model": "gemini-3.1-flash-lite",
            "chunks": []
        }
        run2 = {
            "source_video": "second_video.mp4",
            "model": "gemini-3.1-flash-lite",
            "chunks": []
        }
        
        save_run(self.db_path, run1)
        save_run(self.db_path, run2)
        
        runs = get_all_runs(self.db_path)
        self.assertEqual(len(runs), 2)
        # SQLite created_at defaults to datetime('now') which is identical for instantaneous inserts,
        # but the sequential autoincrement ID maps to order of insertion.
        # Let's verify both are retrieved correctly.
        self.assertEqual(runs[0]["source_video"], "second_video.mp4")
        self.assertEqual(runs[1]["source_video"], "first_video.mp4")

if __name__ == "__main__":
    unittest.main()
