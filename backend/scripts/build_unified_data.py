import json
from pathlib import Path


def _load_json_or_default(path, default_value):
    """Loads a JSON file or returns a default value if not found or corrupt."""
    if not path.exists():
        print(f"⚠️ Data file not found at {path}")
        return default_value
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error decoding JSON from {path}: {e}")
        return default_value
    except (IOError, OSError) as e:
        print(f"❌ Error reading file {path}: {e}")
        return default_value


def build_unified_data():
    """
    Builds a single, structured JSON data file from various sources.
    This file acts as the "source of truth" for the RAG system, enabling
    logical chunking and rich metadata embedding.
    """
    base_path = Path("public")
    output_path = base_path / "unified_data.json"

    # --- Illustrations JSON (already structured) ---
    illustrations_path = base_path / "illustrations.json"
    if illustrations_path.exists():
        with open(illustrations_path, "r", encoding="utf-8") as f:
            illustrations_data = json.load(f)
    else:
        illustrations_data = []
        print(f"⚠️ Illustrations file not found at {illustrations_path}")

    # --- Resume Data (loaded from JSON) ---
    resume_path = base_path / "resume.json"
    if resume_path.exists():
        with open(resume_path, "r", encoding="utf-8") as f:
            resume_data = json.load(f)
    else:
        resume_data = {}
        print(f"⚠️ Resume file not found at {resume_path}")

    # --- About Data (loaded from JSON) ---
    about_path = base_path / "about.json"
    if about_path.exists():
        with open(about_path, "r", encoding="utf-8") as f:
            about_data = json.load(f)
    else:
        about_data = {}
        print(f"⚠️ About file not found at {about_path}")

    # --- Build unified structure ---
    unified_data = {
        "resume": resume_data,
        "about": about_data,
        "illustrations": illustrations_data,
    }

    # --- Write output ---
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(unified_data, f, indent=2)
        print(f"✅ Structured unified data file created at {output_path}")
    except (IOError, OSError) as e:
        print(f"❌ Failed to write unified data file: {e}")
        raise


if __name__ == "__main__":
    build_unified_data()
