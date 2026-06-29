import unittest
import os
import shutil
import json
from metadata_writer import (
    build_wovely_payload,
    write_metadata_to_video,
    read_metadata_from_video,
    write_sidecar_metadata,
    EXIFTOOL_BIN
)

MOCK_RUN_DETAIL = {
    "id": 123,
    "model": "gemini-3.1-flash-lite",
    "created_at": "2025-01-15T12:34:56Z",
    "duration_sec": 45.0,
    "status": "success",
    "input_tokens": 13500,
    "output_tokens": 850,
    "est_cost_usd": 0.0014,
    "platform_name": "TikTok",
    "platform_handle": "@amy_fashion",
    "source_video": "sample.mp4",
    "video_filename": "uuid_sample.mp4",
    "people": [
        {
            "id": 1,
            "person_label": "person_1",
            "hair": {"color": "blonde", "texture": "wavy", "length": "long", "style": "down"},
            "top": {
                "type": "halter top", 
                "color": "red", 
                "fit": "fitted", 
                "fabric": "knit", 
                "pattern": "solid", 
                "neckline": "halter", 
                "sleeve_length": "sleeveless", 
                "details": ["ribbed"]
            },
            "bottom": {
                "type": "jeans", 
                "color": "blue", 
                "fit": "slim", 
                "fabric": "denim", 
                "pattern": "solid", 
                "garment_length": "ankle", 
                "details": []
            }
        }
    ]
}

MOCK_POINT = {
    "x": -0.342,
    "y": 0.118,
    "mode": "full"
}

class TestMetadataWriter(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp_tests")
        os.makedirs(self.test_dir, exist_ok=True)
        
        # Paths for temporary test video files
        self.sample_video = os.path.join(self.test_dir, "sample.mp4")
        self.output_video = os.path.join(self.test_dir, "output.mp4")
        
        # Try to find a real mp4 file in the workspace to use as a valid template
        real_mp4 = None
        uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
        if os.path.exists(uploads_dir):
            for f in os.listdir(uploads_dir):
                if f.endswith(".mp4"):
                    real_mp4 = os.path.join(uploads_dir, f)
                    break
                    
        if real_mp4:
            shutil.copy2(real_mp4, self.sample_video)
        else:
            # Fallback to dummy bytes if no real mp4 is found
            with open(self.sample_video, "wb") as f:
                f.write(b"dummy mp4 video data for metadata writing tests")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_build_payload(self):
        """Verify that the generated JSON payload matches the wovely schema."""
        payload = build_wovely_payload(MOCK_RUN_DETAIL, MOCK_POINT)
        
        wovely_data = payload.get("wovely", {})
        self.assertEqual(wovely_data.get("schema_version"), "1.0")
        
        extraction = wovely_data.get("extraction", {})
        self.assertEqual(extraction.get("run_id"), 123)
        self.assertEqual(extraction.get("model"), "gemini-3.1-flash-lite")
        self.assertEqual(extraction.get("duration_seconds"), 45.0)
        
        platform = wovely_data.get("platform_metadata", {})
        self.assertEqual(platform.get("platform"), "TikTok")
        self.assertEqual(platform.get("handle"), "@amy_fashion")
        
        people = wovely_data.get("people", [])
        self.assertEqual(len(people), 1)
        self.assertEqual(people[0]["person_label"], "person_1")
        self.assertEqual(people[0]["hair"]["color"], "blonde")
        self.assertEqual(people[0]["top"]["color"], "red")
        
        self.assertEqual(
            wovely_data.get("semantic_summary"),
            "red fitted knit halter top with halter neckline, sleeveless, ribbed & blue slim denim jeans with ankle length"
        )
        
        constellation = wovely_data.get("constellation", {})
        self.assertEqual(constellation.get("x"), -0.342)
        self.assertEqual(constellation.get("y"), 0.118)
        self.assertEqual(constellation.get("mode"), "full")

    def test_write_and_read_metadata_exiftool(self):
        """Verify round-trip embedding with ExifTool if binary is available."""
        if not shutil.which(EXIFTOOL_BIN):
            self.skipTest("exiftool binary not installed on host")
            
        payload = build_wovely_payload(MOCK_RUN_DETAIL, MOCK_POINT)
        
        # Test copying and writing
        result_path = write_metadata_to_video(self.sample_video, self.output_video, payload)
        self.assertEqual(result_path, self.output_video)
        self.assertTrue(os.path.exists(self.output_video))
        
        # Test reading back
        read_back = read_metadata_from_video(self.output_video)
        self.assertIsNotNone(read_back)
        self.assertEqual(read_back["wovely"]["extraction"]["run_id"], 123)
        self.assertEqual(read_back["wovely"]["platform_metadata"]["platform"], "TikTok")
        self.assertEqual(read_back["wovely"]["people"][0]["top"]["color"], "red")

    def test_sidecar_fallback(self):
        """Verify that writing falls back to sidecar JSON if ExifTool is not found."""
        # Force exiftool to be unavailable
        import metadata_writer
        original_bin = metadata_writer.EXIFTOOL_BIN
        metadata_writer.EXIFTOOL_BIN = "nonexistent_exiftool_command"
        
        payload = build_wovely_payload(MOCK_RUN_DETAIL, MOCK_POINT)
        
        try:
            # Write with fallback active
            result_path = write_metadata_to_video(self.sample_video, self.output_video, payload)
            self.assertEqual(result_path, self.output_video)
            
            # Should have created sidecar json
            sidecar_path = self.output_video + ".wovely.json"
            self.assertTrue(os.path.exists(sidecar_path))
            
            # Read back should load the sidecar automatically
            read_back = read_metadata_from_video(self.output_video)
            self.assertIsNotNone(read_back)
            self.assertEqual(read_back["wovely"]["extraction"]["run_id"], 123)
        finally:
            # Restore original bin name
            metadata_writer.EXIFTOOL_BIN = original_bin

if __name__ == "__main__":
    unittest.main()
