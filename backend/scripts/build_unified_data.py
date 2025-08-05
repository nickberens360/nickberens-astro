import json
import sys
from pathlib import Path

# Add the backend directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from core.data_source_config import config


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
    # Get configuration
    data_sources_config = config.data_sources
    base_path = Path(data_sources_config.get("base_path", "public"))
    output_path = base_path / data_sources_config.get("output_file", "unified_data.json")

    # Build unified data structure
    unified_data = {}

    # Process each configured source
    for source in data_sources_config.get("sources", []):
        source_name = source["name"]
        source_file = source["file"]
        source_path = base_path / source_file

        # Load the data
        if source.get("is_list_source", False):
            # Source is already a list (like illustrations)
            source_data = _load_json_or_default(source_path, [])
        else:
            # Source is an object (like resume, about)
            source_data = _load_json_or_default(source_path, {})

        # Add to unified data
        unified_data[source_name] = source_data
        print(f"📄 Loaded {source_name} data from {source_file}")

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
