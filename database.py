import sqlite3
import json
from typing import List, Dict, Any, Optional

def get_db_connection(db_path: str) -> sqlite3.Connection:
    """Creates a connection to SQLite, enabling foreign keys and row factory."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def migrate_db(conn: sqlite3.Connection) -> None:
    """Idempotently adds columns to people table for Phase 2 styling metadata."""
    new_cols = [
        ("hair_texture", "TEXT"),
        ("hair_length", "TEXT"),
        ("hair_style", "TEXT"),
        ("top_fit", "TEXT"),
        ("top_fabric", "TEXT"),
        ("top_pattern", "TEXT"),
        ("top_neckline", "TEXT"),
        ("top_sleeve_length", "TEXT"),
        ("top_details", "TEXT"),
        ("bottom_fit", "TEXT"),
        ("bottom_fabric", "TEXT"),
        ("bottom_pattern", "TEXT"),
        ("bottom_garment_length", "TEXT"),
        ("bottom_details", "TEXT")
    ]
    
    # Check existing columns using PRAGMA table_info
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(people);")
    existing_cols = {row["name"] for row in cursor.fetchall()}
    
    for col_name, col_type in new_cols:
        if col_name not in existing_cols:
            try:
                conn.execute(f"ALTER TABLE people ADD COLUMN {col_name} {col_type};")
            except sqlite3.OperationalError as e:
                err_msg = str(e).lower()
                if "duplicate column" not in err_msg and "already exists" not in err_msg:
                    raise

def init_db(db_path: str) -> None:
    """Creates the tables for runs and people if they do not exist."""
    with get_db_connection(db_path) as conn:
        # Create runs table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                source_video  TEXT    NOT NULL,
                model         TEXT    NOT NULL,
                status        TEXT    NOT NULL,
                duration_sec  REAL,
                input_tokens  INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                est_cost_usd  REAL    DEFAULT 0.0,
                chunks_total  INTEGER DEFAULT 1,
                chunks_skipped INTEGER DEFAULT 0,
                raw_json      TEXT,
                created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
            );
        """)
        # Create people table with rich fields
        conn.execute("""
            CREATE TABLE IF NOT EXISTS people (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id                INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                chunk_index           INTEGER NOT NULL DEFAULT 0,
                person_label          TEXT    NOT NULL,
                hair_color            TEXT,
                hair_texture          TEXT,
                hair_length           TEXT,
                hair_style            TEXT,
                top_type              TEXT,
                top_color             TEXT,
                top_fit               TEXT,
                top_fabric            TEXT,
                top_pattern           TEXT,
                top_neckline          TEXT,
                top_sleeve_length     TEXT,
                top_details           TEXT,  -- stored as JSON array string
                bottom_type           TEXT,
                bottom_color          TEXT,
                bottom_fit            TEXT,
                bottom_fabric         TEXT,
                bottom_pattern        TEXT,
                bottom_garment_length TEXT,
                bottom_details        TEXT   -- stored as JSON array string
            );
        """)
        # Create value_embeddings_cache table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS value_embeddings_cache (
                field_name TEXT NOT NULL,
                value      TEXT NOT NULL,
                embedding  TEXT NOT NULL, -- JSON array of 768 floats
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (field_name, value)
            );
        """)
        # Create outfit_embeddings table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS outfit_embeddings (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id        INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
                run_id           INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                top_text         TEXT,
                top_embedding    TEXT,    -- JSON array of 768 floats, or NULL
                bottom_text      TEXT,
                bottom_embedding TEXT,    -- JSON array of 768 floats, or NULL
                hair_text        TEXT,
                hair_embedding   TEXT,    -- JSON array of 768 floats, or NULL
                created_at       TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        
        # Run migrations on existing db to keep it up to date
        migrate_db(conn)
        conn.commit()

def save_run(db_path: str, result: Dict[str, Any]) -> int:
    """Saves a run result to the database and returns the generated run_id."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        
        # Calculate summaries from chunks
        chunks = result.get("chunks", [])
        chunks_total = len(chunks)
        chunks_skipped = sum(1 for c in chunks if c.get("status") != "ok")
        
        # We can extract duration from the last chunk's range end, or set default
        duration_sec = 0.0
        if chunks:
            # e.g., [0.0, 120.0]
            time_range = chunks[-1].get("time_range_seconds", [0.0, 0.0])
            if len(time_range) == 2:
                duration_sec = time_range[1]

        metadata = result.get("run_metadata", {})
        input_tokens = metadata.get("total_input_tokens", 0)
        output_tokens = metadata.get("total_output_tokens", 0)
        est_cost_usd = metadata.get("estimated_cost_usd", 0.0)

        cursor.execute(
            """
            INSERT INTO runs (
                source_video, model, status, duration_sec, 
                input_tokens, output_tokens, est_cost_usd, 
                chunks_total, chunks_skipped, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.get("source_video", ""),
                result.get("model", ""),
                # overall status of first chunk or fallback
                chunks[0].get("status", "ok") if chunks else "ok",
                duration_sec,
                input_tokens,
                output_tokens,
                est_cost_usd,
                chunks_total,
                chunks_skipped,
                json.dumps(result)
            )
        )
        run_id = cursor.lastrowid
        if not run_id:
            raise RuntimeError("Failed to insert run and retrieve lastrowid.")

        # Save people from chunks
        for chunk in chunks:
            chunk_idx = chunk.get("chunk_index", 0)
            for person in chunk.get("people", []):
                hair = person.get("hair") or {}
                top = person.get("top") or {}
                bottom = person.get("bottom") or {}
                
                # Fallback for old mock structures in tests (e.g. hair_color as string)
                hair_color = hair.get("color") if isinstance(hair, dict) else person.get("hair_color")
                hair_texture = hair.get("texture") if isinstance(hair, dict) else None
                hair_length = hair.get("length") if isinstance(hair, dict) else None
                hair_style = hair.get("style") if isinstance(hair, dict) else None

                top_details_str = json.dumps(top.get("details", [])) if isinstance(top, dict) else "[]"
                bottom_details_str = json.dumps(bottom.get("details", [])) if isinstance(bottom, dict) else "[]"
                
                cursor.execute(
                    """
                    INSERT INTO people (
                        run_id, chunk_index, person_label, 
                        hair_color, hair_texture, hair_length, hair_style,
                        top_type, top_color, top_fit, top_fabric, top_pattern, top_neckline, top_sleeve_length, top_details,
                        bottom_type, bottom_color, bottom_fit, bottom_fabric, bottom_pattern, bottom_garment_length, bottom_details
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        chunk_idx,
                        person.get("person_label", ""),
                        hair_color,
                        hair_texture,
                        hair_length,
                        hair_style,
                        top.get("type") if isinstance(top, dict) else None,
                        top.get("color") if isinstance(top, dict) else None,
                        top.get("fit") if isinstance(top, dict) else None,
                        top.get("fabric") if isinstance(top, dict) else None,
                        top.get("pattern") if isinstance(top, dict) else None,
                        top.get("neckline") if isinstance(top, dict) else None,
                        top.get("sleeve_length") if isinstance(top, dict) else None,
                        top_details_str,
                        bottom.get("type") if isinstance(bottom, dict) else None,
                        bottom.get("color") if isinstance(bottom, dict) else None,
                        bottom.get("fit") if isinstance(bottom, dict) else None,
                        bottom.get("fabric") if isinstance(bottom, dict) else None,
                        bottom.get("pattern") if isinstance(bottom, dict) else None,
                        bottom.get("garment_length") if isinstance(bottom, dict) else None,
                        bottom_details_str
                    )
                )

        conn.commit()
        return run_id

def get_all_runs(db_path: str) -> List[Dict[str, Any]]:
    """Returns a list of all runs, ordered by most recent first."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, source_video, model, status, duration_sec, 
                   input_tokens, output_tokens, est_cost_usd, 
                   chunks_total, chunks_skipped, created_at,
                   (SELECT count(*) FROM people WHERE people.run_id = runs.id) AS people_count
            FROM runs
            ORDER BY created_at DESC, id DESC
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_run_detail(db_path: str, run_id: int) -> Optional[Dict[str, Any]]:
    """Returns detailed information for a single run, including all detected people."""
    with get_db_connection(db_path) as conn:
        # Get run info
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
        run_row = cursor.fetchone()
        if not run_row:
            return None
        
        run_data = dict(run_row)
        
        # Get people info
        cursor.execute("SELECT * FROM people WHERE run_id = ?", (run_id,))
        people_rows = cursor.fetchall()
        
        people_list = []
        for p in people_rows:
            # Parse details lists
            top_details = []
            if "top_details" in p.keys() and p["top_details"]:
                try:
                    top_details = json.loads(p["top_details"])
                except Exception:
                    pass
            bottom_details = []
            if "bottom_details" in p.keys() and p["bottom_details"]:
                try:
                    bottom_details = json.loads(p["bottom_details"])
                except Exception:
                    pass

            people_list.append({
                "chunk_index": p["chunk_index"],
                "person_label": p["person_label"],
                "hair": {
                    "color": p["hair_color"],
                    "texture": p["hair_texture"] if "hair_texture" in p.keys() else None,
                    "length": p["hair_length"] if "hair_length" in p.keys() else None,
                    "style": p["hair_style"] if "hair_style" in p.keys() else None
                },
                "top": {
                    "type": p["top_type"],
                    "color": p["top_color"],
                    "fit": p["top_fit"] if "top_fit" in p.keys() else None,
                    "fabric": p["top_fabric"] if "top_fabric" in p.keys() else None,
                    "pattern": p["top_pattern"] if "top_pattern" in p.keys() else None,
                    "neckline": p["top_neckline"] if "top_neckline" in p.keys() else None,
                    "sleeve_length": p["top_sleeve_length"] if "top_sleeve_length" in p.keys() else None,
                    "details": top_details
                },
                "bottom": {
                    "type": p["bottom_type"],
                    "color": p["bottom_color"],
                    "fit": p["bottom_fit"] if "bottom_fit" in p.keys() else None,
                    "fabric": p["bottom_fabric"] if "bottom_fabric" in p.keys() else None,
                    "pattern": p["bottom_pattern"] if "bottom_pattern" in p.keys() else None,
                    "garment_length": p["bottom_garment_length"] if "bottom_garment_length" in p.keys() else None,
                    "details": bottom_details
                }
            })
            
        run_data["people"] = people_list
        return run_data

def delete_run(db_path: str, run_id: int) -> bool:
    """Deletes a run (and all associated people via CASCADE). Returns True if deleted."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM runs WHERE id = ?", (run_id,))
        conn.commit()
        return cursor.rowcount > 0

def save_cached_embedding(db_path: str, field_name: str, value: str, embedding_vector: List[float]) -> None:
    """Saves a semantic value's embedding vector to cache."""
    with get_db_connection(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO value_embeddings_cache (field_name, value, embedding)
            VALUES (?, ?, ?)
            """,
            (field_name, value.lower().strip(), json.dumps(embedding_vector))
        )
        conn.commit()

def get_cached_embedding(db_path: str, field_name: str, value: str) -> Optional[List[float]]:
    """Retrieves a semantic value's embedding vector from cache if available."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT embedding FROM value_embeddings_cache WHERE field_name = ? AND value = ?",
            (field_name, value.lower().strip())
        )
        row = cursor.fetchone()
        if row:
            return json.loads(row["embedding"])
        return None

def get_all_people_with_attributes(db_path: str) -> List[Dict[str, Any]]:
    """Returns a list of all people across all runs with associated run details and styling fields."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, r.source_video, r.model, r.created_at
            FROM people p
            JOIN runs r ON p.run_id = r.id
            ORDER BY r.created_at DESC, p.id DESC
        """)
        rows = cursor.fetchall()
        
        people_list = []
        for p in rows:
            top_details = []
            if "top_details" in p.keys() and p["top_details"]:
                try:
                    top_details = json.loads(p["top_details"])
                except Exception:
                    pass
            bottom_details = []
            if "bottom_details" in p.keys() and p["bottom_details"]:
                try:
                    bottom_details = json.loads(p["bottom_details"])
                except Exception:
                    pass
                    
            people_list.append({
                "person_id": p["id"],
                "run_id": p["run_id"],
                "source_video": p["source_video"],
                "model": p["model"],
                "created_at": p["created_at"],
                "chunk_index": p["chunk_index"],
                "person_label": p["person_label"],
                "hair": {
                    "color": p["hair_color"],
                    "texture": p["hair_texture"] if "hair_texture" in p.keys() else None,
                    "length": p["hair_length"] if "hair_length" in p.keys() else None,
                    "style": p["hair_style"] if "hair_style" in p.keys() else None
                },
                "top": {
                    "type": p["top_type"],
                    "color": p["top_color"],
                    "fit": p["top_fit"] if "top_fit" in p.keys() else None,
                    "fabric": p["top_fabric"] if "top_fabric" in p.keys() else None,
                    "pattern": p["top_pattern"] if "top_pattern" in p.keys() else None,
                    "neckline": p["top_neckline"] if "top_neckline" in p.keys() else None,
                    "sleeve_length": p["top_sleeve_length"] if "top_sleeve_length" in p.keys() else None,
                    "details": top_details
                },
                "bottom": {
                    "type": p["bottom_type"],
                    "color": p["bottom_color"],
                    "fit": p["bottom_fit"] if "bottom_fit" in p.keys() else None,
                    "fabric": p["bottom_fabric"] if "bottom_fabric" in p.keys() else None,
                    "pattern": p["bottom_pattern"] if "bottom_pattern" in p.keys() else None,
                    "garment_length": p["bottom_garment_length"] if "bottom_garment_length" in p.keys() else None,
                    "details": bottom_details
                }
            })
        return people_list

def save_outfit_embedding(db_path: str, person_id: int, run_id: int, 
                           top_text: Optional[str], top_emb: Optional[List[float]],
                           bottom_text: Optional[str], bottom_emb: Optional[List[float]],
                           hair_text: Optional[str], hair_emb: Optional[List[float]]) -> None:
    """Saves the individual outfit and hair text/vector embeddings for a person."""
    with get_db_connection(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO outfit_embeddings (
                person_id, run_id, 
                top_text, top_embedding, 
                bottom_text, bottom_embedding, 
                hair_text, hair_embedding
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                person_id,
                run_id,
                top_text,
                json.dumps(top_emb) if top_emb else None,
                bottom_text,
                json.dumps(bottom_emb) if bottom_emb else None,
                hair_text,
                json.dumps(hair_emb) if hair_emb else None
            )
        )
        conn.commit()

def get_all_outfit_embeddings(db_path: str) -> List[Dict[str, Any]]:
    """Retrieves all outfit embeddings from the database."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM outfit_embeddings")
        rows = cursor.fetchall()
        results = []
        for r in rows:
            results.append({
                "person_id": r["person_id"],
                "run_id": r["run_id"],
                "top_text": r["top_text"],
                "top_embedding": json.loads(r["top_embedding"]) if r["top_embedding"] else None,
                "bottom_text": r["bottom_text"],
                "bottom_embedding": json.loads(r["bottom_embedding"]) if r["bottom_embedding"] else None,
                "hair_text": r["hair_text"],
                "hair_embedding": json.loads(r["hair_embedding"]) if r["hair_embedding"] else None
            })
        return results

def has_outfit_embedding(db_path: str, person_id: int) -> bool:
    """Checks if a person already has processed embeddings."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM outfit_embeddings WHERE person_id = ?", (person_id,))
        return cursor.fetchone() is not None
