import os
import sys
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from database import (
    get_cached_embedding,
    save_cached_embedding,
    get_all_people_with_attributes,
    save_outfit_embedding,
    has_outfit_embedding
)

# Layer 1 weights (Full Mode)
DEFAULT_TOP_WEIGHT = 0.40
DEFAULT_BOTTOM_WEIGHT = 0.35
DEFAULT_HAIR_WEIGHT = 0.25

# Layer 2 weights (Garment level)
GARMENT_WEIGHTS = {
    "type": 0.30,
    "color": 0.25,
    "fabric": 0.15,
    "pattern": 0.10,
    "fit": 0.08,
    "sub": 0.07,  # neckline/sleeve for top, garment_length for bottom
    "details": 0.05
}

HAIR_WEIGHTS = {
    "color": 0.50,
    "length": 0.20,
    "texture": 0.15,
    "style": 0.15
}

def get_genai_client():
    """Initializes Google GenAI client if API key is present."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except Exception:
        return None

def embed_text(text: str, client) -> Optional[List[float]]:
    """Calls the Google GenAI embedding API to generate vector embedding, trying multiple model fallbacks."""
    if not client or not text:
        return None
        
    models_to_try = ["text-embedding-004", "gemini-embedding-2"]
    errors = []
    
    for model_name in models_to_try:
        try:
            response = client.models.embed_content(
                model=model_name,
                contents=text.strip()
            )
            if response.embeddings and len(response.embeddings) > 0:
                return response.embeddings[0].values
        except Exception as e:
            errors.append(f"Model '{model_name}': {e}")
            
    # Only print warning if all models in the fallback queue failed
    print(f"Warning: All attempts to generate embedding failed. Details:\n" + "\n".join(errors), file=sys.stderr)
    return None

def get_or_embed_value(field_name: str, value: str, client, db_path: str) -> Optional[List[float]]:
    """Gets embedding from SQLite cache, or generates and stores it on miss."""
    if not value or not value.strip():
        return None
    val_clean = value.lower().strip()
    
    # 1. Try cache
    cached = get_cached_embedding(db_path, field_name, val_clean)
    if cached:
        return cached
        
    # 2. Try API call if client is available
    if client:
        emb = embed_text(val_clean, client)
        if emb:
            save_cached_embedding(db_path, field_name, val_clean, emb)
            return emb
            
    return None

def get_cosine_similarity(vec_a: Optional[List[float]], vec_b: Optional[List[float]]) -> float:
    """Computes cosine similarity between two numeric vectors."""
    if not vec_a or not vec_b:
        return 0.0
    a = np.array(vec_a)
    b = np.array(vec_b)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)

def compute_garment_similarity(g_a: dict, g_b: dict, db_path: str) -> float:
    """Layer 2: Attribute-weighted similarity for two garments with proportional weight redistribution."""
    scores = {}
    
    # 1. Type (Semantic)
    val_a = g_a.get("type")
    val_b = g_b.get("type")
    if val_a and val_b:
        emb_a = get_cached_embedding(db_path, "type", val_a)
        emb_b = get_cached_embedding(db_path, "type", val_b)
        if emb_a and emb_b:
            scores["type"] = get_cosine_similarity(emb_a, emb_b)
        else:
            scores["type"] = 1.0 if val_a.lower().strip() == val_b.lower().strip() else 0.0
    elif not val_a and not val_b:
        pass  # skip if both are missing
    else:
        scores["type"] = 0.0
        
    # 2. Color (Semantic)
    val_a = g_a.get("color")
    val_b = g_b.get("color")
    if val_a and val_b:
        emb_a = get_cached_embedding(db_path, "color", val_a)
        emb_b = get_cached_embedding(db_path, "color", val_b)
        if emb_a and emb_b:
            scores["color"] = get_cosine_similarity(emb_a, emb_b)
        else:
            scores["color"] = 1.0 if val_a.lower().strip() == val_b.lower().strip() else 0.0
    elif not val_a and not val_b:
        pass
    else:
        scores["color"] = 0.0
        
    # 3. Fabric (Exact)
    val_a = g_a.get("fabric")
    val_b = g_b.get("fabric")
    if val_a and val_b:
        scores["fabric"] = 1.0 if val_a.lower().strip() == val_b.lower().strip() else 0.0
    elif not val_a and not val_b:
        pass
    else:
        scores["fabric"] = 0.0
        
    # 4. Pattern (Exact)
    val_a = g_a.get("pattern")
    val_b = g_b.get("pattern")
    if val_a and val_b:
        scores["pattern"] = 1.0 if val_a.lower().strip() == val_b.lower().strip() else 0.0
    elif not val_a and not val_b:
        pass
    else:
        scores["pattern"] = 0.0
        
    # 5. Fit (Exact)
    val_a = g_a.get("fit")
    val_b = g_b.get("fit")
    if val_a and val_b:
        scores["fit"] = 1.0 if val_a.lower().strip() == val_b.lower().strip() else 0.0
    elif not val_a and not val_b:
        pass
    else:
        scores["fit"] = 0.0
        
    # 6. Sub-attribute: Neckline/Sleeves (Tops) or Garment Length (Bottoms)
    is_top = "neckline" in g_a or "sleeve_length" in g_a or "neckline" in g_b or "sleeve_length" in g_b
    if is_top:
        sub_scores = []
        for field in ["neckline", "sleeve_length"]:
            va = g_a.get(field)
            vb = g_b.get(field)
            if va and vb:
                sub_scores.append(1.0 if va.lower().strip() == vb.lower().strip() else 0.0)
            elif not va and not vb:
                pass
            else:
                sub_scores.append(0.0)
        if sub_scores:
            scores["sub"] = sum(sub_scores) / len(sub_scores)
    else:
        va = g_a.get("garment_length")
        vb = g_b.get("garment_length")
        if va and vb:
            scores["sub"] = 1.0 if va.lower().strip() == vb.lower().strip() else 0.0
        elif not va and not vb:
            pass
        else:
            scores["sub"] = 0.0
            
    # 7. Details (Jaccard overlapping list)
    det_a = g_a.get("details") or []
    det_b = g_b.get("details") or []
    set_a = {str(d).lower().strip() for d in det_a if d}
    set_b = {str(d).lower().strip() for d in det_b if d}
    if set_a or set_b:
        if set_a and set_b:
            intersect = len(set_a.intersection(set_b))
            union = len(set_a.union(set_b))
            scores["details"] = intersect / union if union > 0 else 0.0
        else:
            scores["details"] = 0.0

    # Null weight redistribution
    active_weights = {k: GARMENT_WEIGHTS[k] for k in scores.keys()}
    total_weight = sum(active_weights.values())
    if total_weight == 0:
        return 1.0  # Both garments blank -> perfect match
        
    weighted_sum = sum(scores[k] * active_weights[k] for k in scores.keys())
    return weighted_sum / total_weight

def compute_hair_similarity(h_a: dict, h_b: dict, db_path: str) -> float:
    """Layer 2: Attribute-weighted similarity for hair with proportional weight redistribution."""
    scores = {}
    
    # 1. Color (Semantic)
    val_a = h_a.get("color")
    val_b = h_b.get("color")
    if val_a and val_b:
        emb_a = get_cached_embedding(db_path, "color", val_a)
        emb_b = get_cached_embedding(db_path, "color", val_b)
        if emb_a and emb_b:
            scores["color"] = get_cosine_similarity(emb_a, emb_b)
        else:
            scores["color"] = 1.0 if val_a.lower().strip() == val_b.lower().strip() else 0.0
    elif not val_a and not val_b:
        pass
    else:
        scores["color"] = 0.0
        
    # 2. Length, Texture, Style (Exact)
    for field in ["length", "texture", "style"]:
        va = h_a.get(field)
        vb = h_b.get(field)
        if va and vb:
            scores[field] = 1.0 if va.lower().strip() == vb.lower().strip() else 0.0
        elif not va and not vb:
            pass
        else:
            scores[field] = 0.0
            
    active_weights = {k: HAIR_WEIGHTS[k] for k in scores.keys()}
    total_weight = sum(active_weights.values())
    if total_weight == 0:
        return 1.0
        
    weighted_sum = sum(scores[k] * active_weights[k] for k in scores.keys())
    return weighted_sum / total_weight

def compute_person_similarity(p_a: dict, p_b: dict, db_path: str, mode: str = "full") -> dict:
    """Layer 1: Weighted composite person-to-person similarity with weight redistribution."""
    # Topwear similarity check
    top_sim = None
    has_top_a = p_a.get("top") and p_a["top"].get("type")
    has_top_b = p_b.get("top") and p_b["top"].get("type")
    if has_top_a and has_top_b:
        top_sim = compute_garment_similarity(p_a["top"], p_b["top"], db_path)
        
    # Bottomwear similarity check
    bottom_sim = None
    has_bot_a = p_a.get("bottom") and p_a["bottom"].get("type")
    has_bot_b = p_b.get("bottom") and p_b["bottom"].get("type")
    if has_bot_a and has_bot_b:
        bottom_sim = compute_garment_similarity(p_a["bottom"], p_b["bottom"], db_path)
        
    # Hair similarity check
    hair_sim = None
    has_hair_a = p_a.get("hair") and p_a["hair"].get("color")
    has_hair_b = p_b.get("hair") and p_b["hair"].get("color")
    if has_hair_a and has_hair_b:
        hair_sim = compute_hair_similarity(p_a["hair"], p_b["hair"], db_path)

    # Layer 1 Mode Weights
    if mode == "top":
        comp_weights = {"top": 1.0, "bottom": 0.0, "hair": 0.0}
    elif mode == "bottom":
        comp_weights = {"top": 0.0, "bottom": 1.0, "hair": 0.0}
    elif mode == "clothing":
        comp_weights = {"top": 0.53, "bottom": 0.47, "hair": 0.0}
    else:  # full
        comp_weights = {"top": DEFAULT_TOP_WEIGHT, "bottom": DEFAULT_BOTTOM_WEIGHT, "hair": DEFAULT_HAIR_WEIGHT}

    scores = {}
    if top_sim is not None and comp_weights["top"] > 0:
        scores["top"] = top_sim
    if bottom_sim is not None and comp_weights["bottom"] > 0:
        scores["bottom"] = bottom_sim
    if hair_sim is not None and comp_weights["hair"] > 0:
        scores["hair"] = hair_sim

    active_weights = {k: comp_weights[k] for k in scores.keys()}
    total_weight = sum(active_weights.values())
    
    if total_weight == 0:
        total_score = 1.0
    else:
        weighted_sum = sum(scores[k] * active_weights[k] for k in scores.keys())
        total_score = weighted_sum / total_weight

    return {
        "total": total_score,
        "top": top_sim if top_sim is not None else 0.0,
        "bottom": bottom_sim if bottom_sim is not None else 0.0,
        "hair": hair_sim if hair_sim is not None else 0.0,
        "breakdown": scores
    }

def compose_top_text(top: dict) -> Optional[str]:
    """Helper to assemble a readable prompt sentence describing topwear."""
    if not top or not top.get("type"):
        return None
    parts = []
    if top.get("color"): parts.append(top["color"])
    if top.get("fit"): parts.append(top["fit"])
    if top.get("fabric"): parts.append(top["fabric"])
    parts.append(top["type"])
    desc = " ".join(parts)
    
    details = []
    if top.get("neckline"): details.append(f"{top['neckline']} neckline")
    if top.get("sleeve_length"): details.append(top['sleeve_length'])
    if top.get("pattern") and top["pattern"] != "solid": details.append(f"{top['pattern']} pattern")
    if top.get("details"): details.extend(top["details"])
    if details:
        desc += f" with {', '.join(details)}"
    return desc.strip()

def compose_bottom_text(bottom: dict) -> Optional[str]:
    """Helper to assemble a readable prompt sentence describing bottomwear."""
    if not bottom or not bottom.get("type"):
        return None
    parts = []
    if bottom.get("color"): parts.append(bottom["color"])
    if bottom.get("fit"): parts.append(bottom["fit"])
    if bottom.get("fabric"): parts.append(bottom["fabric"])
    parts.append(bottom["type"])
    desc = " ".join(parts)
    
    details = []
    if bottom.get("garment_length"): details.append(f"{bottom['garment_length']} length")
    if bottom.get("pattern") and bottom["pattern"] != "solid": details.append(f"{bottom['pattern']} pattern")
    if bottom.get("details"): details.extend(bottom["details"])
    if details:
        desc += f" with {', '.join(details)}"
    return desc.strip()

def compose_hair_text(hair: dict) -> Optional[str]:
    """Helper to assemble a readable prompt sentence describing hair."""
    if not hair or not hair.get("color"):
        return None
    parts = []
    if hair.get("color"): parts.append(hair["color"])
    if hair.get("texture"): parts.append(hair["texture"])
    if hair.get("length"): parts.append(hair["length"])
    parts.append("hair")
    if hair.get("style"): parts.append(f"worn {hair['style']}")
    return " ".join(parts).strip()

def embed_run_values(run_id: int, db_path: str) -> None:
    """Pre-generates and caches vector embeddings for any new garment types or colors in a run."""
    client = get_genai_client()
    from database import get_run_detail
    run = get_run_detail(db_path, run_id)
    if not run:
        return
        
    for person in run.get("people", []):
        # 1. Embed and cache values (type, color)
        top = person.get("top") or {}
        bottom = person.get("bottom") or {}
        hair = person.get("hair") or {}
        
        # Top type / color
        if top.get("type"):
            get_or_embed_value("type", top["type"], client, db_path)
        if top.get("color"):
            get_or_embed_value("color", top["color"], client, db_path)
            
        # Bottom type / color
        if bottom.get("type"):
            get_or_embed_value("type", bottom["type"], client, db_path)
        if bottom.get("color"):
            get_or_embed_value("color", bottom["color"], client, db_path)
            
        # Hair color
        if hair.get("color"):
            get_or_embed_value("color", hair["color"], client, db_path)

        # 2. Embed full sentences for outfit_embeddings table mapping if client is available
        if client and not has_outfit_embedding(db_path, person.get("id", 0)):
            top_txt = compose_top_text(top)
            bottom_txt = compose_bottom_text(bottom)
            hair_txt = compose_hair_text(hair)
            
            top_emb = embed_text(top_txt, client) if top_txt else None
            bottom_emb = embed_text(bottom_txt, client) if bottom_txt else None
            hair_emb = embed_text(hair_txt, client) if hair_txt else None
            
            from database import get_db_connection
            with get_db_connection(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id FROM people WHERE run_id = ? AND person_label = ?",
                    (run_id, person.get("person_label"))
                )
                row = cursor.fetchone()
                if row:
                    person_db_id = row["id"]
                    save_outfit_embedding(
                        db_path, person_db_id, run_id,
                        top_txt, top_emb,
                        bottom_txt, bottom_emb,
                        hair_txt, hair_emb
                    )

def classical_mds(D: np.ndarray, dimensions: int = 2) -> np.ndarray:
    """Classical multidimensional scaling (MDS) implementation in NumPy."""
    n = D.shape[0]
    if n == 0:
        return np.zeros((0, dimensions))
    if n == 1:
        return np.zeros((1, dimensions))
    if n == 2:
        dist = D[0, 1]
        return np.array([[0.0, 0.0], [dist, 0.0]])
        
    A = -0.5 * (D ** 2)
    r_mean = np.mean(A, axis=1, keepdims=True)
    c_mean = np.mean(A, axis=0, keepdims=True)
    g_mean = np.mean(A)
    B = A - r_mean - c_mean + g_mean
    
    evals, evecs = np.linalg.eigh(B)
    idx = np.argsort(evals)[::-1]
    evals = evals[idx]
    evecs = evecs[:, idx]
    
    top_evals = evals[:dimensions]
    top_evals = np.maximum(top_evals, 0)
    
    coords = evecs[:, :dimensions] * np.sqrt(top_evals)
    return coords

def compute_constellation_coords(db_path: str, mode: str = "full") -> List[Dict[str, Any]]:
    """Calculates coordinates for the 2D outfit constellation map via classical MDS, using cache if valid."""
    from database import get_db_connection
    
    # 1. Get total people count and verify cache validity
    people = get_all_people_with_attributes(db_path)
    n = len(people)
    if n == 0:
        return []

    # Check cache count
    cached_count = 0
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) as cnt 
                FROM constellation_cache 
                WHERE mode = ? 
                  AND person_id IN (SELECT id FROM people)
                """,
                (mode,)
            )
            row = cursor.fetchone()
            if row:
                cached_count = row["cnt"]
    except Exception as e:
        print(f"Warning: Failed to check constellation cache validity: {e}", file=sys.stderr)

    if cached_count == n:
        # Cache is valid! Fetch directly from cache joining with metadata
        try:
            with get_db_connection(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT 
                        p.id as person_id,
                        p.run_id,
                        r.source_video,
                        p.person_label,
                        r.created_at,
                        c.x,
                        c.y,
                        p.top_type, p.top_color, p.top_fit, p.top_fabric, p.top_pattern, p.top_neckline, p.top_sleeve_length, p.top_details,
                        p.bottom_type, p.bottom_color, p.bottom_fit, p.bottom_fabric, p.bottom_pattern, p.bottom_garment_length, p.bottom_details,
                        p.hair_color, p.hair_texture, p.hair_length, p.hair_style
                    FROM constellation_cache c
                    JOIN people p ON c.person_id = p.id
                    JOIN runs r ON p.run_id = r.id
                    WHERE c.mode = ?
                    """,
                    (mode,)
                )
                rows = cursor.fetchall()
                
                points = []
                for row in rows:
                    p = dict(row)
                    
                    # Reconstruct models for helpers
                    top = {
                        "type": p["top_type"],
                        "color": p["top_color"],
                        "fit": p["top_fit"],
                        "fabric": p["top_fabric"],
                        "pattern": p["top_pattern"],
                        "neckline": p["top_neckline"],
                        "sleeve_length": p["top_sleeve_length"],
                        "details": json.loads(p["top_details"]) if p["top_details"] else []
                    }
                    bottom = {
                        "type": p["bottom_type"],
                        "color": p["bottom_color"],
                        "fit": p["bottom_fit"],
                        "fabric": p["bottom_fabric"],
                        "pattern": p["bottom_pattern"],
                        "garment_length": p["bottom_garment_length"],
                        "details": json.loads(p["bottom_details"]) if p["bottom_details"] else []
                    }
                    hair = {
                        "color": p["hair_color"],
                        "texture": p["hair_texture"],
                        "length": p["hair_length"],
                        "style": p["hair_style"]
                    }
                    
                    top_desc = compose_top_text(top)
                    bot_desc = compose_bottom_text(bottom)
                    summary = ""
                    if top_desc and bot_desc:
                        summary = f"{top_desc} & {bot_desc}"
                    elif top_desc:
                        summary = top_desc
                    elif bot_desc:
                        summary = bot_desc
                    else:
                        summary = "No visible clothing detected"
                        
                    points.append({
                        "person_id": p["person_id"],
                        "run_id": p["run_id"],
                        "source_video": p["source_video"],
                        "person_label": p["person_label"],
                        "created_at": p["created_at"],
                        "x": p["x"],
                        "y": p["y"],
                        "summary": summary,
                        "dominant_color": p["top_color"] or p["bottom_color"] or "gray",
                        "hair_summary": compose_hair_text(hair) or "hair not visible"
                    })
                return points
        except Exception as e:
            print(f"Warning: Failed to load from constellation cache, falling back to calculation: {e}", file=sys.stderr)

    # 2. Cache is invalid/missing: Compute pairwise distances
    D = np.zeros((n, n))
    for i in range(n):
        for j in range(i, n):
            if i == j:
                D[i, j] = 0.0
            else:
                sim = compute_person_similarity(people[i], people[j], db_path, mode=mode)["total"]
                dist = 1.0 - sim
                D[i, j] = dist
                D[j, i] = dist
                
    # 3. Project to 2D via MDS
    coords = classical_mds(D, dimensions=2)
    
    # 4. Save to cache
    try:
        with get_db_connection(db_path) as conn:
            conn.execute("DELETE FROM constellation_cache WHERE mode = ?", (mode,))
            for i, p in enumerate(people):
                conn.execute(
                    """
                    INSERT INTO constellation_cache (mode, person_id, x, y)
                    VALUES (?, ?, ?, ?)
                    """,
                    (mode, p["person_id"], float(coords[i, 0]), float(coords[i, 1]))
                )
            conn.commit()
    except Exception as e:
        print(f"Warning: Failed to save to constellation cache: {e}", file=sys.stderr)

    # 5. Format results
    points = []
    for i, p in enumerate(people):
        top_color = p.get("top", {}).get("color")
        bot_color = p.get("bottom", {}).get("color")
        dom_color = top_color or bot_color or "gray"
        
        top_desc = compose_top_text(p.get("top", {}))
        bot_desc = compose_bottom_text(p.get("bottom", {}))
        summary = ""
        if top_desc and bot_desc:
            summary = f"{top_desc} & {bot_desc}"
        elif top_desc:
            summary = top_desc
        elif bot_desc:
            summary = bot_desc
        else:
            summary = "No visible clothing detected"
            
        points.append({
            "person_id": p["person_id"],
            "run_id": p["run_id"],
            "source_video": p["source_video"],
            "person_label": p["person_label"],
            "created_at": p["created_at"],
            "x": float(coords[i, 0]),
            "y": float(coords[i, 1]),
            "summary": summary,
            "dominant_color": dom_color,
            "hair_summary": compose_hair_text(p.get("hair", {})) or "hair not visible"
        })
        
    return points

def warm_constellation_cache_async(db_path: str) -> None:
    """Spawns a daemon thread to compute and cache coordinates for all modes in the background."""
    import threading
    def task():
        for mode in ["full", "clothing", "top", "bottom"]:
            try:
                compute_constellation_coords(db_path, mode=mode)
            except Exception as e:
                print(f"Error warming constellation cache for mode '{mode}': {e}", file=sys.stderr)
                
    thread = threading.Thread(target=task)
    thread.daemon = True
    thread.start()
