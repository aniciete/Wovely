#!/usr/bin/env python3
import os
import sys
import argparse
import datetime
import json
import time
from typing import Optional, List, Tuple
from pydantic import BaseModel, Field

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Exceptions
class SafetyError(ValueError):
    """Raised when safety constraints are violated (e.g. minors in footage)."""
    pass

# Schema definitions
class GarmentAttribute(BaseModel):
    type: Optional[str] = Field(
        default=None, 
        description="The specific sub-type of the garment (e.g., 'halter top', 'leather jacket', 'skinny jeans', 'oversized hoodie', 'denim shorts', 'maxi dress'). Set to null if not visible/present."
    )
    color: Optional[str] = Field(
        default=None, 
        description="The color name of the garment (e.g., 'red', 'navy', 'cream', 'mustard'). Set to null if not visible/present."
    )
    fit: Optional[str] = Field(
        default=None,
        description="The visual fit category (e.g., 'fitted', 'relaxed', 'oversized', 'cropped', 'slim', 'loose'). Set to null if not visible."
    )
    fabric: Optional[str] = Field(
        default=None,
        description="The fabric material type (e.g., 'denim', 'cotton', 'satin', 'silk', 'leather', 'knit', 'velvet', 'mesh'). Set to null if not visible."
    )
    pattern: Optional[str] = Field(
        default=None,
        description="The surface pattern (e.g., 'solid', 'striped', 'floral', 'plaid', 'tie-dye', 'graphic print'). Set to null if not visible."
    )
    neckline: Optional[str] = Field(
        default=None,
        description="Neckline style (Applies to TOPS/DRESSES only; e.g., 'v-neck', 'halter', 'crew neck', 'strapless', 'off-shoulder', 'sweetheart'). Set to null if bottomwear or not visible."
    )
    sleeve_length: Optional[str] = Field(
        default=None,
        description="Sleeve length type (Applies to TOPS/DRESSES only; e.g., 'sleeveless', 'short sleeve', 'long sleeve', '3/4 sleeve', 'cap sleeve'). Set to null if bottomwear or not visible."
    )
    garment_length: Optional[str] = Field(
        default=None,
        description="The length scale (Applies to BOTTOMS/DRESSES only; e.g., 'mini', 'midi', 'maxi', 'knee-length', 'ankle', 'cropped'). Set to null if topwear or not visible."
    )
    details: List[str] = Field(
        default_factory=list,
        description="List of specific styling details or embellishments present on this garment (e.g., ['ruched', 'spaghetti straps', 'gold hardware', 'distressed', 'high-waisted', 'button-down', 'fringe', 'lace trim']). Return empty list if none."
    )

class HairAttribute(BaseModel):
    color: Optional[str] = Field(
        default=None,
        description="Hair color (e.g., 'blonde', 'brunette', 'black', 'platinum', 'auburn', 'ginger'). Set to null if not visible/present."
    )
    texture: Optional[str] = Field(
        default=None,
        description="Hair texture (e.g., 'straight', 'wavy', 'curly', 'coily'). Set to null if not visible."
    )
    length: Optional[str] = Field(
        default=None,
        description="Hair length (e.g., 'short', 'shoulder-length', 'long', 'buzzed'). Set to null if not visible."
    )
    style: Optional[str] = Field(
        default=None,
        description="Hair style (e.g., 'down', 'ponytail', 'bun', 'braids', 'half-up'). Set to null if not visible."
    )

class PersonAttributes(BaseModel):
    person_label: str = Field(
        description="A stable label assigned to the person, e.g., 'person_1', 'person_2'. Must be reused consistently for the same person throughout this chunk."
    )
    hair: HairAttribute = Field(
        description="Attributes of the person's hair."
    )
    top: GarmentAttribute = Field(
        description="Attributes of the top garment."
    )
    bottom: GarmentAttribute = Field(
        description="Attributes of the bottom garment."
    )

class ChunkResult(BaseModel):
    people: List[PersonAttributes] = Field(
        default_factory=list,
        description="List of detected people and their clothing/hair attributes."
    )

# Constants
DEFAULT_MODEL = "gemini-3.1-flash-lite"
TOKENS_PER_SECOND_ESTIMATE = 300
PAID_INPUT_COST_PER_1M = 0.10
PAID_OUTPUT_COST_PER_1M = 0.40

PROMPT_TEXT = (
    "You are analyzing a video to identify clothing and hair attributes for "
    "fashion cataloging and outfit similarity matching.\n\n"
    "For each visually distinct person who appears in this video segment, extract the following:\n\n"
    "1. HAIR:\n"
    "   - color: exact color (e.g., 'blonde', 'brunette', 'black', 'platinum', 'ginger')\n"
    "   - texture: texture pattern (e.g., 'straight', 'wavy', 'curly', 'coily')\n"
    "   - length: estimated length (e.g., 'short', 'shoulder-length', 'long', 'buzzed')\n"
    "   - style: arrangement style (e.g., 'down', 'ponytail', 'bun', 'braids', 'half-up')\n\n"
    "2. TOPWEAR (or DRESS):\n"
    "   - type: specific sub-type (e.g., 'halter top', 'leather jacket', 'crop top', 'oversized hoodie', 'slip dress')\n"
    "   - color: color name (e.g., 'red', 'navy', 'cream', 'mustard', 'charcoal')\n"
    "   - fit: visual fit (e.g., 'fitted', 'relaxed', 'oversized', 'cropped', 'slim')\n"
    "   - fabric: material category (e.g., 'denim', 'cotton', 'satin', 'silk', 'leather', 'knit', 'mesh', 'corduroy')\n"
    "   - pattern: fabric pattern (e.g., 'solid', 'striped', 'floral', 'plaid', 'tie-dye')\n"
    "   - neckline: neckline style (e.g., 'v-neck', 'halter', 'crew neck', 'strapless', 'off-shoulder')\n"
    "   - sleeve_length: sleeve length (e.g., 'sleeveless', 'short sleeve', 'long sleeve')\n"
    "   - details: list of details or construction features (e.g., ['ruched', 'spaghetti straps', 'gold hardware', 'lace trim', 'fringe', 'button-down'])\n\n"
    "3. BOTTOMWEAR:\n"
    "   - type: specific sub-type (e.g., 'skinny jeans', 'cargo pants', 'denim shorts', 'maxi skirt', 'leggings')\n"
    "   - color: color name (e.g., 'black', 'blue', 'light wash', 'white', 'olive')\n"
    "   - fit: visual fit (e.g., 'slim', 'baggy', 'high-waisted', 'relaxed')\n"
    "   - fabric: material category (e.g., 'denim', 'leather', 'cotton', 'satin')\n"
    "   - pattern: fabric pattern (e.g., 'solid', 'striped', 'plaid')\n"
    "   - garment_length: length scale (e.g., 'mini', 'midi', 'maxi', 'ankle', 'cropped')\n"
    "   - details: list of details (e.g., ['distressed', 'high-waisted', 'cargo pockets', 'pleated'])\n\n"
    "Constraints:\n"
    "- If a garment/attribute is not visible (out of frame, occluded, or not worn), set it to null. DO NOT guess.\n"
    "- Do not describe or comment on bare skin, body shape, or nudity. Only report garments that are actually present. "
    "If a person is not wearing topwear or bottomwear, report that garment object fields as null; never describe bare skin.\n"
    "- Assign each person a stable label (e.g., 'person_1') consistently throughout this segment.\n\n"
    "Respond using the provided JSON schema only."
)

def check_minor_safety(minor_possible: bool) -> None:
    """Abort immediately if the operator flags the presence of minors."""
    if minor_possible:
        raise SafetyError("Footage contains or may contain minors. Refusing to process for safety.")

def log_free_tier_warning() -> None:
    """Logs a warning about data-usage policy when running under the free tier."""
    print("WARNING: Running under the Google Gemini Free Tier. Submitted content "
          "may be used by Google to improve products. For complete data privacy compliance "
          "and to prevent content training, use a paid billing tier key.", file=sys.stderr)

def get_video_duration(video_path: str) -> float:
    """Gets duration in seconds of a video file using OpenCV, falling back if unavailable."""
    if not os.path.exists(video_path):
        return 0.0
    try:
        import cv2
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            if fps > 0:
                duration = frame_count / fps
                cap.release()
                return float(duration)
            cap.release()
    except Exception:
        pass
    return 0.0

def calculate_estimated_cost(duration_seconds: float) -> Tuple[int, float]:
    """Calculates estimated tokens and USD cost (based on paid tier rates)."""
    estimated_tokens = int(duration_seconds * TOKENS_PER_SECOND_ESTIMATE)
    estimated_cost = (estimated_tokens / 1_000_000) * PAID_INPUT_COST_PER_1M
    return estimated_tokens, estimated_cost

def run_extraction(
    video_path: str,
    model_name: str,
    dry_run: bool = False,
    minor_possible: bool = False
) -> dict:
    # 1. Check safety constraint
    check_minor_safety(minor_possible)

    # 2. Check file existence
    if not dry_run and not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # 3. Log free tier warning (defaulting to warning behavior for single-user run)
    log_free_tier_warning()

    # 4. Compute size & duration estimation
    duration = get_video_duration(video_path)
    est_tokens, est_cost = calculate_estimated_cost(duration)

    if dry_run:
        print("\n--- DRY RUN ESTIMATE ---")
        print(f"Video file: {video_path}")
        print(f"Model: {model_name}")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Estimated Input Tokens: {est_tokens}")
        print(f"Estimated Cost (Paid Tier Rates): ${est_cost:.4f}")
        print("\nPrompt that would be sent:")
        print(PROMPT_TEXT)
        print("------------------------\n")
        return {
            "source_video": os.path.basename(video_path),
            "model": model_name,
            "status": "dry_run",
            "duration_seconds": duration,
            "estimated_tokens": est_tokens,
            "estimated_cost_usd": est_cost
        }

    # 5. Initialize client & safety settings
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    safety_settings = [
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
        )
    ]

    print(f"Uploading {video_path} via File API...")
    try:
        uploaded_file = client.files.upload(file=video_path)
    except Exception as e:
        print(f"ERROR: Failed to upload file via File API: {e}", file=sys.stderr)
        return {
            "source_video": os.path.basename(video_path),
            "model": model_name,
            "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
            "chunks": [
                {
                    "chunk_index": 0,
                    "time_range_seconds": [0, duration],
                    "status": "upload_failure",
                    "people": []
                }
            ],
            "run_metadata": {
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "estimated_cost_usd": 0.0,
                "chunks_skipped": 1
            }
        }

    print(f"File uploaded. Name: {uploaded_file.name}. Waiting for processing...")
    try:
        state = getattr(uploaded_file, "state", None)
        while state and getattr(state, "name", str(state)) == "PROCESSING":
            time.sleep(5)
            uploaded_file = client.files.get(name=uploaded_file.name)
            state = getattr(uploaded_file, "state", None)

        state_name = getattr(state, "name", str(state)) if state else "ACTIVE"
        if state_name == "FAILED":
            raise ValueError("File state transitioned to FAILED on Gemini server.")
    except Exception as e:
        print(f"ERROR: Video processing failed on server: {e}", file=sys.stderr)
        # Cleanup uploaded file record
        try:
            client.files.delete(name=uploaded_file.name)
        except Exception:
            pass
        return {
            "source_video": os.path.basename(video_path),
            "model": model_name,
            "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
            "chunks": [
                {
                    "chunk_index": 0,
                    "time_range_seconds": [0, duration],
                    "status": "processing_failure",
                    "people": []
                }
            ],
            "run_metadata": {
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "estimated_cost_usd": 0.0,
                "chunks_skipped": 1
            }
        }

    # 6. Call model
    print(f"Querying model {model_name}...")
    chunk_status = "ok"
    people_data = []
    input_tokens = 0
    output_tokens = 0
    actual_cost = 0.0

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=[uploaded_file, PROMPT_TEXT],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ChunkResult,
                safety_settings=safety_settings,
            )
        )

        # Extract tokens
        if response.usage_metadata:
            input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0)
            output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0)
            actual_cost = (input_tokens / 1_000_000) * PAID_INPUT_COST_PER_1M + \
                          (output_tokens / 1_000_000) * PAID_OUTPUT_COST_PER_1M

        # Check safety/errors
        block_reason = None
        if response.prompt_feedback and response.prompt_feedback.block_reason:
            block_reason = response.prompt_feedback.block_reason
            chunk_status = "blocked_input"
            print(f"WARNING: Request safety blocked (input). Reason: {block_reason}", file=sys.stderr)
        
        elif response.candidates:
            cand = response.candidates[0]
            finish_reason = getattr(cand, "finish_reason", None)
            finish_reason_str = str(finish_reason).upper() if finish_reason else ""
            if "SAFETY" in finish_reason_str:
                chunk_status = "blocked_output"
                print("WARNING: Request safety blocked (output).", file=sys.stderr)
            elif "RECITATION" in finish_reason_str:
                chunk_status = "blocked_output"
                print("WARNING: Request blocked due to recitation check.", file=sys.stderr)

        if chunk_status == "ok":
            # Successful parse
            if response.parsed:
                people_data = response.parsed.people
            else:
                chunk_status = "parse_error"
                print("WARNING: Response failed parsing to defined schema.", file=sys.stderr)

    except APIError as e:
        print(f"WARNING: API Error occurred: {e}", file=sys.stderr)
        if e.code == 429:
            chunk_status = "rate_limited"
        else:
            chunk_status = "api_error"
    except Exception as e:
        print(f"WARNING: Unexpected error during execution: {e}", file=sys.stderr)
        chunk_status = "execution_error"
    finally:
        # Cleanup uploaded file
        try:
            print("Cleaning up file from Gemini File API storage...")
            client.files.delete(name=uploaded_file.name)
        except Exception as e:
            print(f"Warning: Failed to delete remote file: {e}", file=sys.stderr)

    # Format result structure
    people_list = []
    for p in people_data:
        people_list.append(p.model_dump() if hasattr(p, "model_dump") else p.dict())

    return {
        "source_video": os.path.basename(video_path),
        "model": model_name,
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "chunks": [
            {
                "chunk_index": 0,
                "time_range_seconds": [0.0, duration],
                "status": chunk_status,
                "people": people_list
            }
        ],
        "run_metadata": {
            "total_input_tokens": input_tokens,
            "total_output_tokens": output_tokens,
            "estimated_cost_usd": float(f"{actual_cost:.6f}"),
            "chunks_skipped": 1 if chunk_status != "ok" else 0
        }
    }

def main():
    parser = argparse.ArgumentParser(description="Clothing & Hair Attribute Extraction - Phase 1 Prototype")
    parser.add_argument("--video", type=str, required=True, help="Path to local video file")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help=f"Gemini model identifier (default: {DEFAULT_MODEL})")
    parser.add_argument("--dry-run", action="store_true", help="Print dry-run details and token estimations without calling the API")
    parser.add_argument("--minor-possible", action="store_true", help="Set this flag if the video may contain minors (will abort execution for safety)")
    parser.add_argument("--output", type=str, help="Path to write the output JSON result")

    args = parser.parse_args()

    try:
        result = run_extraction(
            video_path=args.video,
            model_name=args.model,
            dry_run=args.dry_run,
            minor_possible=args.minor_possible
        )
    except SafetyError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Output to stdout/file
    json_output = json.dumps(result, indent=2)
    if args.output:
        with open(args.output, "w") as f:
            f.write(json_output)
        print(f"Results written to {args.output}")
    else:
        print(json_output)

if __name__ == "__main__":
    main()
