import os
import sys
import uuid
import werkzeug
from flask import Flask, request, jsonify, render_template, send_from_directory
from database import init_db, save_run, get_all_runs, get_run_detail, delete_run, get_all_people_with_attributes
from extractor import run_extraction, SafetyError
from embedder import embed_run_values, compute_constellation_coords, compute_person_similarity

app = Flask(__name__, static_folder="static", template_folder="templates")

# Configuration
DB_PATH = "wovely.db"
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # Max 500MB upload

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
init_db(DB_PATH)

@app.route("/")
def index():
    """Serves the main single-page application (SPA)."""
    return render_template("index.html")

@app.route("/api/extract", methods=["POST"])
def api_extract():
    """Endpoint to upload a video, run attribute extraction, and save to DB."""
    # 1. Check if file is uploaded
    if "video" not in request.files:
        return jsonify({"error": "No video file provided"}), 400
    
    video_file = request.files["video"]
    if video_file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    
    # 2. Get other options
    model_name = request.form.get("model", "gemini-3.1-flash-lite")
    dry_run = request.form.get("dry_run") == "true"
    minor_possible = request.form.get("minor_possible") == "true"

    # 3. Save file temporarily
    filename = werkzeug.utils.secure_filename(video_file.filename)
    # prepend unique uuid to avoid file collisions
    unique_filename = f"{uuid.uuid4()}_{filename}"
    temp_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
    
    try:
        video_file.save(temp_path)
    except Exception as e:
        return jsonify({"error": f"Failed to save uploaded file: {str(e)}"}), 500

    # 4. Perform extraction
    try:
        result = run_extraction(
            video_path=temp_path,
            model_name=model_name,
            dry_run=dry_run,
            minor_possible=minor_possible
        )
        
        # 5. Save to database if not a dry-run
        db_id = None
        if not dry_run:
            db_id = save_run(DB_PATH, result)
            result["db_id"] = db_id
            
            # Cache semantic values and populate embeddings for Phase 2 similarity constellation
            try:
                embed_run_values(db_id, DB_PATH)
            except Exception as e:
                print(f"Warning: Embedding generation failed for run {db_id}: {e}", file=sys.stderr)
 
        return jsonify(result)
        
    except SafetyError as e:
        return jsonify({"error": str(e)}), 400
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Internal extraction error: {str(e)}"}), 500
    finally:
        # Always clean up the temporary file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e:
                print(f"Warning: Failed to clean up temp file {temp_path}: {e}", file=sys.stderr)

@app.route("/api/runs", methods=["GET"])
def api_get_runs():
    """Retrieve history of all extraction runs."""
    try:
        runs = get_all_runs(DB_PATH)
        return jsonify(runs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/runs/<int:run_id>", methods=["GET"])
def api_get_run_detail(run_id):
    """Retrieve detailed data for a specific run including detected people."""
    try:
        run_detail = get_run_detail(DB_PATH, run_id)
        if not run_detail:
            return jsonify({"error": "Run not found"}), 404
        return jsonify(run_detail)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/runs/<int:run_id>", methods=["DELETE"])
def api_delete_run(run_id):
    """Delete a run from the history database."""
    try:
        deleted = delete_run(DB_PATH, run_id)
        if not deleted:
            return jsonify({"error": "Run not found"}), 404
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/constellation", methods=["GET"])
def api_get_constellation():
    """Retrieve points coordinates for the outfit constellation map."""
    mode = request.args.get("mode", "full")
    if mode not in ["full", "clothing", "top", "bottom"]:
        return jsonify({"error": "Invalid similarity mode"}), 400
    try:
        points = compute_constellation_coords(DB_PATH, mode=mode)
        return jsonify(points)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/runs/<int:run_id>/similar", methods=["GET"])
def api_get_similar(run_id):
    """Retrieve runs similar to the target run with detailed scores breakdown."""
    mode = request.args.get("mode", "full")
    n_str = request.args.get("n", "10")
    try:
        n = int(n_str)
    except ValueError:
        n = 10
        
    if mode not in ["full", "clothing", "top", "bottom"]:
        return jsonify({"error": "Invalid similarity mode"}), 400
        
    try:
        # Get all people with attributes
        all_people = get_all_people_with_attributes(DB_PATH)
        
        # Find target run's people
        target_people = [p for p in all_people if p["run_id"] == run_id]
        if not target_people:
            return jsonify([]) # no people in this run, or run doesn't exist
            
        target_person = target_people[0] # compare using the first person in target run
        
        similarities = []
        for p in all_people:
            if p["run_id"] == run_id:
                continue # exclude target run itself
                
            sim_res = compute_person_similarity(target_person, p, DB_PATH, mode=mode)
            similarities.append({
                "person_id": p["person_id"],
                "run_id": p["run_id"],
                "source_video": p["source_video"],
                "person_label": p["person_label"],
                "created_at": p["created_at"],
                "score": sim_res["total"],
                "top_score": sim_res["top"],
                "bottom_score": sim_res["bottom"],
                "hair_score": sim_res["hair"],
                "outfit_summary": ((p.get("top", {}).get("color") or "") + " " + (p.get("top", {}).get("type") or "")).strip() + " / " + ((p.get("bottom", {}).get("color") or "") + " " + (p.get("bottom", {}).get("type") or "")).strip()
            })
            
        # Sort by total score descending
        similarities.sort(key=lambda x: x["score"], reverse=True)
        return jsonify(similarities[:n])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/runs/<int:run_id>/embed", methods=["POST"])
def api_embed_run(run_id):
    """Triggers or regenerates the embedding cache and vectors for a run."""
    try:
        embed_run_values(run_id, DB_PATH)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
