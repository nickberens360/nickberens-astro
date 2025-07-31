# backend/scripts/build_unified_data.py

import json
from pathlib import Path
from typing import Any, Dict, List, Union

from backend.core.config import AppConfig


class DataSourceError(Exception):
    """Custom exception for data source related errors."""
    pass


def _validate_source_config(source: Dict[str, Any]) -> None:
    """Validates that a data source configuration has required fields."""
    required_fields = ["name", "path"]
    for field in required_fields:
        if field not in source:
            raise DataSourceError(f"Data source missing required field: {field}")


def _get_default_structure(source: Dict[str, Any]) -> Union[Dict[str, Any], List[Any]]:
    """
    Determines the default structure for a data source.
    Checks for explicit default_structure config, then falls back to
    source-specific defaults based on naming conventions.
    """
    # Check for explicit configuration
    if "default_structure" in source:
        structure_type = source["default_structure"]
        if structure_type == "dict":
            return {}
        elif structure_type == "list":
            return []
        else:
            print(f"⚠️ Unknown default_structure '{structure_type}' for {source['name']}, using dict")
            return {}

    # Fall back to naming convention defaults
    source_name = source["name"].lower()
    list_sources = {"products", "illustrations", "items", "entries", "records"}

    if source_name in list_sources or source_name.endswith(("s", "es")):
        return []
    else:
        return {}


def _load_json_with_validation(path: Path, source: Dict[str, Any]) -> Union[Dict[str, Any], List[Any]]:
    """
    Loads and validates a JSON file with proper error handling and structure validation.
    """
    source_name = source["name"]

    if not path.exists():
        print(f"⚠️ Data file not found: {path}")
        default = _get_default_structure(source)
        print(f"📝 Using default structure for '{source_name}': {type(default).__name__}")
        return default

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate that loaded data matches expected structure type
        expected_default = _get_default_structure(source)
        if not isinstance(data, type(expected_default)):
            print(
                f"⚠️ Warning: '{source_name}' loaded as {type(data).__name__} but expected {type(expected_default).__name__}"
            )

        # Ensure we return the correct type for mypy
        if isinstance(data, (dict, list)):
            print(f"✅ Successfully loaded '{source_name}' ({len(data)} items)")
            return data
        else:
            # If data is not dict or list, fall back to default structure
            print(f"⚠️ Warning: '{source_name}' contains invalid data type, using default structure")
            return _get_default_structure(source)

    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {path}: {e}")
        default = _get_default_structure(source)
        print(f"📝 Using default structure for '{source_name}': {type(default).__name__}")
        return default

    except (IOError, OSError) as e:
        print(f"❌ Error reading file {path}: {e}")
        raise DataSourceError(f"Failed to read data source '{source_name}': {e}")


def _validate_unified_data(unified_data: Dict[str, Any]) -> None:
    """Validates the final unified data structure."""
    if not unified_data:
        raise DataSourceError("No data sources were successfully loaded")

    print("\n📊 Unified data summary:")
    for source_name, data in unified_data.items():
        data_type = type(data).__name__
        size = len(data) if hasattr(data, '__len__') else "unknown"
        print(f"  • {source_name}: {data_type} with {size} items")


def build_unified_data() -> None:
    """
    Builds a single, structured JSON data file from various sources.
    This file acts as the "source of truth" for the RAG system, enabling
    logical chunking and rich metadata embedding.
    """
    print("🔨 Building unified data file...")

    base_path = Path("public")
    output_path = base_path / "unified_data.json"

    # Ensure output directory exists
    base_path.mkdir(parents=True, exist_ok=True)

    unified_data: Dict[str, Any] = {}
    errors = []

    # Process each data source
    for i, source in enumerate(AppConfig.DATA_SOURCES, 1):
        print(f"\n[{i}/{len(AppConfig.DATA_SOURCES)}] Processing data source...")

        try:
            _validate_source_config(source)
            source_name = source["name"]
            source_path = Path(source["path"])

            print(f"📂 Loading '{source_name}' from {source_path}")
            unified_data[source_name] = _load_json_with_validation(source_path, source)

        except DataSourceError as e:
            error_msg = f"Failed to process source {source.get('name', 'unknown')}: {e}"
            print(f"❌ {error_msg}")
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error processing source {source.get('name', 'unknown')}: {e}"
            print(f"💥 {error_msg}")
            errors.append(error_msg)

    # Validate final result
    try:
        _validate_unified_data(unified_data)
    except DataSourceError as e:
        print(f"\n❌ Validation failed: {e}")
        if errors:
            print("Errors encountered:")
            for error in errors:
                print(f"  • {error}")
        raise

    # Write output in the format expected by data_loader.py
    # Your data_loader expects the data directly, not wrapped in a 'data' key
    output_data = unified_data

    # Add metadata as a separate key if you want to track it
    if errors:
        output_data["_metadata"] = {
            "sources_processed": len(AppConfig.DATA_SOURCES),
            "sources_loaded": len(unified_data),
            "errors": errors
        }

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print("\n✅ Unified data file created successfully!")
        print(f"📁 Location: {output_path}")
        print(f"📊 Sources: {len(unified_data)}/{len(AppConfig.DATA_SOURCES)}")

        if errors:
            print(f"⚠️ {len(errors)} errors encountered (see metadata for details)")

    except (IOError, OSError) as e:
        error_msg = f"Failed to write unified data file to {output_path}: {e}"
        print(f"❌ {error_msg}")
        raise DataSourceError(error_msg)


if __name__ == "__main__":
    try:
        build_unified_data()
    except DataSourceError as e:
        print(f"\n💥 Build failed: {e}")
        exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Build interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        exit(1)
