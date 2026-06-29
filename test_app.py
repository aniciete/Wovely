import unittest
import io
import os
import json
import tempfile
from unittest.mock import patch
import app
import database

class TestApp(unittest.TestCase):

    def setUp(self):
        # Create a temp file path for test database
        self.db_fd, self.db_path = tempfile.mkstemp()
        app.DB_PATH = self.db_path
        database.init_db(self.db_path)
        
        # Configure Flask app for testing
        app.app.config["TESTING"] = True
        app.app.config["UPLOAD_FOLDER"] = tempfile.mkdtemp()
        self.client = app.app.test_client()

    def tearDown(self):
        # Cleanup DB
        os.close(self.db_fd)
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            
        # Cleanup Upload folder
        upload_folder = app.app.config["UPLOAD_FOLDER"]
        if os.path.exists(upload_folder):
            for f in os.listdir(upload_folder):
                os.remove(os.path.join(upload_folder, f))
            os.rmdir(upload_folder)

    def test_index_serves_html(self):
        """Verify the main route serves the HTML single-page app."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Wovely", response.data)
        self.assertIn(b"Upload Extractor", response.data)

    def test_api_runs_empty(self):
        """Verify API history list returns empty array on clean database."""
        response = self.client.get("/api/runs")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode("utf-8"))
        self.assertEqual(data, [])

    def test_api_extract_missing_file(self):
        """Verify API extraction fails with 400 when video file is missing."""
        response = self.client.post("/api/extract", data={
            "model": "gemini-3.1-flash-lite"
        })
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data.decode("utf-8"))
        self.assertIn("error", data)

    @patch("app.embed_run_values")
    @patch("app.run_extraction")
    def test_api_extract_success(self, mock_run, mock_embed):
        """Verify successful video upload triggers extraction and logs to database."""
        mock_result = {
            "source_video": "mock_test.mp4",
            "model": "gemini-3.1-flash-lite",
            "run_metadata": {
                "total_input_tokens": 500,
                "total_output_tokens": 150,
                "estimated_cost_usd": 0.0001
            },
            "chunks": [
                {
                    "chunk_index": 0,
                    "time_range_seconds": [0.0, 10.0],
                    "status": "ok",
                    "people": [
                        {
                            "person_label": "person_1",
                            "hair": {"color": "black", "texture": "straight", "length": "short", "style": "down"},
                            "top": {"type": "t-shirt", "color": "blue", "fit": "fitted", "fabric": "cotton", "pattern": "solid", "details": []},
                            "bottom": {"type": "jeans", "color": "blue", "fit": "slim", "fabric": "denim", "pattern": "solid", "details": []}
                        }
                    ]
                }
            ]
        }
        mock_run.return_value = mock_result

        # Create dummy file bytes for upload
        video_data = (io.BytesIO(b"fake mp4 video bytes"), "mock_test.mp4")
        response = self.client.post("/api/extract", data={
            "video": video_data,
            "model": "gemini-3.1-flash-lite",
            "dry_run": "false",
            "minor_possible": "false"
        }, content_type="multipart/form-data")

        self.assertEqual(response.status_code, 200)
        res_json = json.loads(response.data.decode("utf-8"))
        self.assertEqual(res_json["source_video"], "mock_test.mp4")
        self.assertIn("db_id", res_json)
        
        # Verify it was inserted in database history
        run_id = res_json["db_id"]
        runs = database.get_all_runs(self.db_path)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["id"], run_id)

    @patch("app.run_extraction")
    def test_api_extract_dry_run(self, mock_run):
        """Verify dry run outputs details but does NOT write to database."""
        mock_run.return_value = {
            "source_video": "mock_dry.mp4",
            "model": "gemini-3.1-flash-lite",
            "status": "dry_run",
            "duration_seconds": 15.0
        }

        video_data = (io.BytesIO(b"fake dry run bytes"), "mock_dry.mp4")
        response = self.client.post("/api/extract", data={
            "video": video_data,
            "dry_run": "true"
        }, content_type="multipart/form-data")

        self.assertEqual(response.status_code, 200)
        res_json = json.loads(response.data.decode("utf-8"))
        self.assertEqual(res_json["status"], "dry_run")
        self.assertNotIn("db_id", res_json)
        
        # Verify database is still empty
        runs = database.get_all_runs(self.db_path)
        self.assertEqual(len(runs), 0)

    @patch("app.run_extraction")
    def test_api_extract_safety_abort(self, mock_run):
        """Verify safety abortion response on minor flag trigger."""
        from extractor import SafetyError
        mock_run.side_effect = SafetyError("Footage contains or may contain minors. Refusing to process for safety.")

        video_data = (io.BytesIO(b"fake minor bytes"), "minor_detected.mp4")
        response = self.client.post("/api/extract", data={
            "video": video_data,
            "minor_possible": "true"
        }, content_type="multipart/form-data")

        self.assertEqual(response.status_code, 400)
        res_json = json.loads(response.data.decode("utf-8"))
        self.assertIn("minors", res_json["error"])

    def test_api_delete_run(self):
        """Verify deleting a run via DELETE endpoint works."""
        # Insert a run to delete
        run_id = database.save_run(self.db_path, {
            "source_video": "to_be_deleted.mp4",
            "model": "gemini-3.1-flash-lite",
            "chunks": []
        })
        
        # Verify run exists
        detail = database.get_run_detail(self.db_path, run_id)
        self.assertIsNotNone(detail)
        
        # Send DELETE request
        response = self.client.delete(f"/api/runs/{run_id}")
        self.assertEqual(response.status_code, 200)
        res_json = json.loads(response.data.decode("utf-8"))
        self.assertTrue(res_json["success"])
        
        # Verify run detail is now empty
        detail = database.get_run_detail(self.db_path, run_id)
        self.assertIsNone(detail)

    def test_api_constellation_empty(self):
        """Verify constellation endpoint returns an empty array when no people records exist."""
        response = self.client.get("/api/constellation?mode=full")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode("utf-8"))
        self.assertEqual(data, [])

    @patch("app.embed_run_values")
    def test_api_constellation_and_similar_endpoints(self, mock_embed):
        """Verify constellation and similar matching endpoints with mock records."""
        # Save a mock run with outfit detail
        run_id = database.save_run(self.db_path, {
            "source_video": "turnaround_amy.mp4",
            "model": "gemini-3.1-flash-lite",
            "chunks": [
                {
                    "chunk_index": 0,
                    "time_range_seconds": [0.0, 5.0],
                    "status": "ok",
                    "people": [
                        {
                            "person_label": "Amy",
                            "hair": {"color": "blonde", "texture": "wavy", "length": "long", "style": "half-up"},
                            "top": {"type": "halter top", "color": "red", "fit": "fitted", "fabric": "knit", "pattern": "solid", "details": ["ribbed"]},
                            "bottom": {"type": "jeans", "color": "blue", "fit": "slim", "fabric": "denim", "pattern": "solid", "details": []}
                        }
                    ]
                }
            ]
        })
        
        # Verify constellation output
        response = self.client.get("/api/constellation?mode=full")
        self.assertEqual(response.status_code, 200)
        points = json.loads(response.data.decode("utf-8"))
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0]["person_label"], "Amy")
        self.assertEqual(points[0]["dominant_color"], "red")
        
        # Verify similar endpoint returns empty list because there are no other runs to compare to
        response = self.client.get(f"/api/runs/{run_id}/similar?mode=full")
        self.assertEqual(response.status_code, 200)
        matches = json.loads(response.data.decode("utf-8"))
        self.assertEqual(matches, [])

        # Verify POST embed endpoint returns success
        response = self.client.post(f"/api/runs/{run_id}/embed")
        self.assertEqual(response.status_code, 200)
        res_json = json.loads(response.data.decode("utf-8"))
        self.assertTrue(res_json["success"])

if __name__ == "__main__":
    unittest.main()
