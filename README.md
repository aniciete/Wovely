# Wovely

Wovely is a video-based clothing and hair attribute extraction system powered by Google Gemini multimodal models. The application uploads video files, extracts detailed clothing and physical attributes, saves the structured extraction results to a local database, generates semantic text embeddings, and visualizes similarity mappings inside an interactive 2D **Outfit Constellation**.

---

## Key Features

- **Multimodal Extraction**: Leverages Google Gemini multimodal capabilities (`gemini-3.1-flash-lite`, `gemini-2.5-flash`, etc.) to analyze video footage.
- **Granular Attribute Schema**: Identifies and categorizes:
  - **Hair**: Color, texture, length, style.
  - **Tops**: Type, color, fit, fabric, pattern, neckline, sleeve length, styling details.
  - **Bottoms**: Type, color, fit, fabric, pattern, garment length, styling details.
- **Intelligent Embeddings**: Generates and caches 768-dimensional text embeddings (`text-embedding-004`) for each attribute category to enable semantic similarity comparisons.
- **Interactive UI (SPA)**: A single-page dashboard featuring:
  - A modern, responsive **Glassmorphism** styling.
  - Drag-and-drop video upload queue with batch configuration.
  - **Outfit Constellation**: A 2D mapping visualizing outfit distribution and cluster proximity.
  - Interactive similarity lookup that calculates similarity scores with detailed category breakdowns (top vs. bottom vs. hair).
- **Safety Safeguards**: Built-in minor detection controls to abort processing of footage containing minors if not authorized.
- **Robust Storage**: Uses SQLite with self-managing schema migrations.

---

## Codebase Architecture

- **`app.py`**: The Flask application exposing the Web SPA and REST endpoints.
- **`extractor.py`**: Interacts with the Google GenAI SDK, implements the schema parsing, token estimation, cost calculation, and safety check boundaries.
- **`database.py`**: Handles connection pooling, SQLite transactions, DB schema initialization, and database migrations.
- **`embedder.py`**: Manages vector embedding retrieval, runs category weighting calculations for similarity scores, and computes 2D coordinates for the constellation layout.
- **`templates/` & `static/`**: Holds the frontend assets including styling (`style.css`), interactions (`app.js`), and layout templates (`index.html`).
- **`test_*.py`**: Test suites covering controllers, services, embedding logic, and extraction pipelines.

---

## Database Schema

```mermaid
erDiagram
    runs ||--o{ people : has
    runs ||--o{ outfit_embeddings : contains
    people ||--o| outfit_embeddings : "links to"
    
    runs {
        integer id PK
        text source_video
        text model
        text status
        real duration_sec
        integer input_tokens
        integer output_tokens
        real est_cost_usd
        integer chunks_total
        integer chunks_skipped
        text raw_json
        text created_at
    }

    people {
        integer id PK
        integer run_id FK
        integer chunk_index
        text person_label
        text hair_color
        text hair_texture
        text hair_length
        text hair_style
        text top_type
        text top_color
        text top_fit
        text top_fabric
        text top_pattern
        text top_neckline
        text top_sleeve_length
        text top_details
        text bottom_type
        text bottom_color
        text bottom_fit
        text bottom_fabric
        text bottom_pattern
        text bottom_garment_length
        text bottom_details
    }

    value_embeddings_cache {
        text field_name PK
        text value PK
        text embedding
        text created_at
    }

    outfit_embeddings {
        integer id PK
        integer person_id FK
        integer run_id FK
        text top_text
        text top_embedding
        text bottom_text
        text bottom_embedding
        text hair_text
        text hair_embedding
        text created_at
    }
```

---

## Getting Started

### Prerequisites
- Python 3.10+
- Google Gemini API Key
- **ExifTool** (Optional, required for embedding AI findings directly into video files):
  - macOS: `brew install exiftool`
  - Linux: `sudo apt-get install libimage-exiftool-perl` (or equivalent)
  - Windows: Download from [exiftool.org](https://exiftool.org/) and add to PATH.

### Installation

1. Clone or navigate to the repository directory:
   ```bash
   cd Wovely
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install project dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure your environment variables. Create a `.env` file in the root directory:
   ```env
   GEMINI_API_KEY=your_google_gemini_api_key
   ```

5. Run the web server:
   ```bash
   python3 app.py
   ```
   Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your web browser.

---

## Running Tests

To run the full suite of unit tests, use the Python interpreter in your virtual environment:

```bash
.venv/bin/python3 -m unittest
```
