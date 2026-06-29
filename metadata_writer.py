import json
import subprocess
import shutil
import os
import sys
from typing import Dict, Any, Optional

EXIFTOOL_BIN = os.environ.get("EXIFTOOL_BIN", "exiftool")

# Get path of exiftool.config relative to this file
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exiftool.config")

def build_wovely_payload(run_detail: Dict[str, Any], constellation_point: Optional[Dict] = None) -> Dict[str, Any]:
    """Assemble the wovely metadata payload from a run_detail dict."""
    from embedder import compose_top_text, compose_bottom_text

    people_clean = []
    people_summaries = []
    
    for p in run_detail.get("people", []):
        top = p.get("top", {})
        bottom = p.get("bottom", {})
        hair = p.get("hair", {})
        
        people_clean.append({
            "person_label": p.get("person_label", "unknown"),
            "hair": {
                "color": hair.get("color"),
                "texture": hair.get("texture"),
                "length": hair.get("length"),
                "style": hair.get("style"),
            },
            "top": {
                "type": top.get("type"),
                "color": top.get("color"),
                "fit": top.get("fit"),
                "fabric": top.get("fabric"),
                "pattern": top.get("pattern"),
                "neckline": top.get("neckline"),
                "sleeve_length": top.get("sleeve_length"),
                "details": top.get("details", []),
            },
            "bottom": {
                "type": bottom.get("type"),
                "color": bottom.get("color"),
                "fit": bottom.get("fit"),
                "fabric": bottom.get("fabric"),
                "pattern": bottom.get("pattern"),
                "garment_length": bottom.get("garment_length"),
                "details": bottom.get("details", []),
            }
        })
        
        # Build individual summary
        top_desc = compose_top_text(top)
        bot_desc = compose_bottom_text(bottom)
        summary = ""
        if top_desc and bot_desc:
            summary = f"{top_desc} & {bot_desc}"
        elif top_desc:
            summary = top_desc
        elif bot_desc:
            summary = bot_desc
        if summary:
            people_summaries.append(summary)

    # Join multiple summaries if there are multiple people
    semantic_summary = " | ".join(people_summaries) if people_summaries else "No visible clothing detected"

    return {
        "wovely": {
            "schema_version": "1.0",
            "extraction": {
                "run_id":            run_detail.get("id"),
                "model":             run_detail.get("model"),
                "extracted_at":      run_detail.get("created_at"),
                "duration_seconds":  run_detail.get("duration_sec"),
                "status":            run_detail.get("status"),
                "input_tokens":      run_detail.get("input_tokens", 0),
                "output_tokens":     run_detail.get("output_tokens", 0),
                "estimated_cost_usd":run_detail.get("est_cost_usd", 0.0),
                "gemini_file_uri":   None
            },
            "platform_metadata": {
                "platform": run_detail.get("platform_name"),
                "handle":   run_detail.get("platform_handle"),
            },
            "people": people_clean,
            "semantic_summary": semantic_summary,
            "constellation": {
                "x":    constellation_point["x"] if constellation_point else None,
                "y":    constellation_point["y"] if constellation_point else None,
                "mode": constellation_point.get("mode", "full") if constellation_point else "full",
            } if constellation_point else None,
        }
    }


def write_sidecar_metadata(video_path: str, payload: Dict[str, Any]) -> str:
    """Fallback sidecar writer when exiftool is missing or fails."""
    sidecar_path = video_path + ".wovely.json"
    with open(sidecar_path, "w") as f:
        json.dump(payload, f, indent=2)
    return sidecar_path


def write_metadata_to_video(
    source_video_path: str,
    output_path: str,
    payload: Dict[str, Any]
) -> str:
    """
    Embeds the wovely JSON payload into the video file using ExifTool.
    Falls back to writing a sidecar JSON file if ExifTool is not available or fails.
    """
    # Copy first so we never mutate the original storage copy unexpectedly
    if source_video_path != output_path:
        shutil.copy2(source_video_path, output_path)

    # 1. Check if exiftool binary is available
    if not shutil.which(EXIFTOOL_BIN) and not os.path.exists(EXIFTOOL_BIN):
        print(f"Warning: exiftool binary not found. Falling back to sidecar metadata.", file=sys.stderr)
        write_sidecar_metadata(output_path, payload)
        return output_path

    payload_json = json.dumps(payload, separators=(",", ":"))
    
    # 2. Call exiftool
    args = [
        EXIFTOOL_BIN,
        "-config", CONFIG_PATH,
        "-m",  # ignore minor warnings/errors
        "-overwrite_original",
        "-overwrite_original_in_place",
        f"-XMP-wovely:JSONPayload={payload_json}",
        f"-XMP-wovely:SchemaVersion={payload['wovely']['schema_version']}",
        f"-XMP-wovely:RunID={payload['wovely']['extraction']['run_id']}",
        f"-XMP-wovely:Model={payload['wovely']['extraction']['model']}",
        f"-XMP-wovely:ExtractedAt={payload['wovely']['extraction']['extracted_at']}",
        output_path,
    ]
    
    try:
        result = subprocess.run(args, capture_output=True, text=True, check=True)
        return output_path
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Warning: ExifTool write failed: {e}. Falling back to sidecar metadata.", file=sys.stderr)
        write_sidecar_metadata(output_path, payload)
        return output_path


def read_metadata_from_video(video_path: str) -> Optional[Dict[str, Any]]:
    """Round-trip reader for verification. Checks embedded tags first, then falls back to sidecar."""
    if not os.path.exists(video_path):
        return None

    # Check sidecar first if it exists
    sidecar_path = video_path + ".wovely.json"
    if os.path.exists(sidecar_path):
        try:
            with open(sidecar_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to read sidecar file: {e}", file=sys.stderr)

    # Otherwise read using ExifTool
    if not shutil.which(EXIFTOOL_BIN) and not os.path.exists(EXIFTOOL_BIN):
        return None

    args = [
        EXIFTOOL_BIN,
        "-config", CONFIG_PATH,
        "-m",
        "-j",
        "-XMP-wovely:JSONPayload",
        video_path
    ]
    
    try:
        result = subprocess.run(args, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        if data and "JSONPayload" in data[0]:
            return json.loads(data[0]["JSONPayload"])
    except Exception as e:
        print(f"Warning: ExifTool read failed: {e}", file=sys.stderr)
        return None
        
    return None
