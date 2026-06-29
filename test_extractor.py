import unittest
import sys
import io
from pydantic import ValidationError
from extractor import (
    GarmentAttribute,
    PersonAttributes,
    ChunkResult,
    PROMPT_TEXT,
    check_minor_safety,
    log_free_tier_warning,
    calculate_estimated_cost,
    get_video_duration
)

class TestExtractor(unittest.TestCase):

    def test_prompt_never_requests_nudity_description(self):
        """Verify prompt explicitly prohibits describing nudity/bare skin and requests nulls."""
        self.assertIn("Do not describe or comment on bare skin, body shape, or nudity", PROMPT_TEXT)
        self.assertIn("If a person is not wearing topwear or bottomwear, report that garment object fields as null; never describe bare skin", PROMPT_TEXT)
        self.assertIn("If a garment/attribute or platform metadata is not visible (out of frame, occluded, or not worn/present), set it to null. DO NOT guess", PROMPT_TEXT)
        # Verify no instructions ask for describing nudity or bare skin
        self.assertNotIn("describe nudity", PROMPT_TEXT.lower())
        self.assertNotIn("describe skin", PROMPT_TEXT.lower())

    def test_run_aborts_if_operator_flags_possible_minor(self):
        """Verify that passing minor_possible=True raises SafetyError."""
        from extractor import SafetyError
        with self.assertRaises(SafetyError):
            check_minor_safety(minor_possible=True)

        # Confirm it does not abort if false
        try:
            check_minor_safety(minor_possible=False)
        except SafetyError:
            self.fail("check_minor_safety raised SafetyError unexpectedly when minor_possible=False")

    def test_response_schema_validates_pydantic_model(self):
        """Test pydantic schema validation for valid and invalid mock outputs."""
        # 1. Valid data
        valid_data = {
            "people": [
                {
                    "person_label": "person_1",
                    "hair": {"color": "brown", "texture": "straight", "length": "long", "style": "down"},
                    "top": {"type": "hoodie", "color": "gray", "fit": "oversized", "fabric": "cotton", "pattern": "solid", "details": []},
                    "bottom": {"type": "jeans", "color": "blue", "fit": "slim", "fabric": "denim", "pattern": "solid", "details": []}
                },
                {
                    "person_label": "person_2",
                    "hair": {"color": None, "texture": None, "length": None, "style": None},
                    "top": {"type": None, "color": None, "fit": None, "fabric": None, "pattern": None, "details": []},
                    "bottom": {"type": "shorts", "color": "black", "fit": "relaxed", "fabric": "cotton", "pattern": "solid", "details": []}
                }
            ]
        }
        chunk = ChunkResult(**valid_data)
        self.assertEqual(len(chunk.people), 2)
        self.assertEqual(chunk.people[0].person_label, "person_1")
        self.assertEqual(chunk.people[0].top.type, "hoodie")
        self.assertIsNone(chunk.people[1].hair.color)
        self.assertIsNone(chunk.people[1].top.type)

        # 2. Invalid data - missing required field 'person_label'
        invalid_data = {
            "people": [
                {
                    # "person_label" is missing
                    "hair": {"color": "blonde"},
                    "top": {"type": "t-shirt", "color": "white"},
                    "bottom": {"type": "skirt", "color": "red"}
                }
            ]
        }
        with self.assertRaises(ValidationError):
            ChunkResult(**invalid_data)

    def test_cost_estimator_matches_worked_example(self):
        """Verify cost estimation formula matches worked examples (1 hour = $0.108)."""
        # 1 hour of video = 3600 seconds
        tokens, cost = calculate_estimated_cost(3600.0)
        self.assertEqual(tokens, 1080000)
        self.assertAlmostEqual(cost, 0.108, places=4)

        # 0 seconds of video
        tokens, cost = calculate_estimated_cost(0.0)
        self.assertEqual(tokens, 0)
        self.assertEqual(cost, 0.0)

    def test_free_tier_warning_triggered(self):
        """Verify free tier warning is logged to stderr."""
        captured_stderr = io.StringIO()
        sys.stderr = captured_stderr
        try:
            log_free_tier_warning()
        finally:
            sys.stderr = sys.__stderr__

        warning_output = captured_stderr.getvalue()
        self.assertIn("WARNING: Running under the Google Gemini Free Tier", warning_output)
        self.assertIn("data privacy compliance", warning_output)

    def test_gemini_api_retry_backoff(self):
        """Verify call_gemini_with_retry performs backoff retries on transient errors and succeeds."""
        from unittest.mock import patch, MagicMock
        from google.genai.errors import APIError
        from extractor import call_gemini_with_retry

        # Create mock client and response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "success"

        # Create a transient APIError
        transient_error = APIError(code=503, response_json={"error": {"message": "Unavailable due to high demand"}})

        # Set side effect: 2 failures followed by 1 success
        mock_client.models.generate_content.side_effect = [
            transient_error,
            transient_error,
            mock_response
        ]

        with patch("time.sleep", return_value=None) as mock_sleep:
            result = call_gemini_with_retry(
                client=mock_client,
                model_name="gemini-3-flash-preview",
                uploaded_file=MagicMock(),
                safety_settings=None,
                initial_backoff=0.01
            )

        self.assertEqual(result, mock_response)
        self.assertEqual(mock_client.models.generate_content.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

if __name__ == "__main__":
    unittest.main()
