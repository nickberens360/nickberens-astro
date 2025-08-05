import json
import sys
from pathlib import Path
from typing import Any, Dict, List, cast

# Ensure the backend directory is in the Python path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from core.data_source_config import config  # noqa: E402


def _get_file_registry_path() -> Path:
    """Get the path to the file registry."""
    return backend_dir / ".rag_cache" / "file_registry.json"


def _load_file_registry() -> Dict[str, Any]:
    """Load the file registry or return empty dict if not found."""
    registry_path = _get_file_registry_path()
    if not registry_path.exists():
        return {}

    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            return cast(Dict[str, Any], json.load(f))
    except (json.JSONDecodeError, IOError, OSError):
        return {}


def _get_source_file_paths() -> List[Path]:
    """Get all source file paths that should be checked for modifications."""
    source_paths = []
    data_sources_config = config.data_sources

    for source in data_sources_config.get("sources", []):
        source_path = config.get_source_file_path(source["name"])
        if source_path:
            source_paths.append(source_path)

    return source_paths


def _files_modified_since_last_build() -> bool:
    """
    Check if any source files have been modified since the last build.

    Returns:
        bool: True if files have been modified or registry is missing, False otherwise
    """
    registry = _load_file_registry()
    if not registry:
        print("📝 File registry not found, rebuild required")
        return True

    source_paths = _get_source_file_paths()

    for source_path in source_paths:
        if not source_path.exists():
            print(f"⚠️ Source file not found: {source_path}")
            continue

        # Get current file stats
        current_mtime = source_path.stat().st_mtime
        current_size = source_path.stat().st_size

        # Get registry entry for this file
        file_key = source_path.name
        registry_entry = registry.get(file_key)

        if not registry_entry:
            print(f"📝 File {file_key} not in registry, rebuild required")
            return True

        # Compare modification time and size
        registry_mtime = registry_entry.get("modified", 0)
        registry_size = registry_entry.get("size", 0)

        if current_mtime != registry_mtime or current_size != registry_size:
            print(f"📝 File {file_key} has been modified, rebuild required")
            return True

    print("✅ No source files have been modified since last build")
    return False


def _update_file_registry() -> None:
    """Update the file registry with current file information."""
    registry_path = _get_file_registry_path()
    registry_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing registry
    registry = _load_file_registry()

    # Update entries for source files
    source_paths = _get_source_file_paths()

    for source_path in source_paths:
        if source_path.exists():
            stat = source_path.stat()
            registry[source_path.name] = {"size": stat.st_size, "modified": stat.st_mtime, "type": "application/json"}

    # Write updated registry
    try:
        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)
        print(f"📝 Updated file registry at {registry_path}")
    except (IOError, OSError) as e:
        print(f"⚠️ Failed to update file registry: {e}")


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


def build_unified_data(force_rebuild: bool = False):
    """
    Builds a single, structured JSON data file from various sources.
    This file acts as the "source of truth" for the RAG system, enabling
    logical chunking and rich metadata embedding.

    Args:
        force_rebuild: If True, rebuild regardless of file modification status
    """
    # Check if rebuild is needed (unless forced)
    if not force_rebuild and not _files_modified_since_last_build():
        print("⏭️ Skipping build - no source files have been modified")
        return

    print("🔨 Building unified data file...")

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

        # Update file registry after successful build
        _update_file_registry()

    except (IOError, OSError) as e:
        print(f"❌ Failed to write unified data file: {e}")
        raise


if __name__ == "__main__":
    build_unified_data()
