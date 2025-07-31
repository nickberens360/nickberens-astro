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


def _get_default_structure_from_config(source: Dict[str, Any]) -> Union[Dict[str, Any], List[Any]]:
    """
    Determines the default structure for a data source based on configuration.
    Uses explicit config first, then falls back to intelligent detection.
    """
    # Check for explicit configuration first
    if "default_structure" in source:
        structure_type = source["default_structure"]
        if structure_type == "dict":
            return {}
        elif structure_type == "list":
            return []
        else:
            print(f"⚠️ Unknown default_structure '{structure_type}' for {source['name']}, using intelligent detection")

    # Fall back to intelligent detection using config rules
    source_name = source["name"].lower()
    rules = AppConfig.DEFAULT_STRUCTURE_RULES

    # Check exact name matches
    list_indicators = rules["list_indicators"]
    if isinstance(list_indicators, dict) and "exact_names" in list_indicators:
        exact_names = list_indicators["exact_names"]
        if isinstance(exact_names, list) and source_name in exact_names:
            return []

    # Check suffix matches
    if isinstance(list_indicators, dict) and "suffixes" in list_indicators:
        suffixes = list_indicators["suffixes"]
        if isinstance(suffixes, list):
            for suffix in suffixes:
                if isinstance(suffix, str) and source_name.endswith(suffix):
                    return []

    # Use fallback (dict by default)
    dict_fallback = rules.get("dict_fallback", True)
    if dict_fallback:
        return {}
    else:
        return []


def _load_json_with_validation(path: Path, source: Dict[str, Any]) -> Union[Dict[str, Any], List[Any]]:
    """
    Loads and validates a JSON file with proper error handling and structure validation.
    """
    source_name = source["name"]

    if not path.exists():
        print(f"⚠️ Data file not found: {path}")
        default = _get_default_structure_from_config(source)
        print(f"📝 Using default structure for '{source_name}': {type(default).__name__}")
        return default

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate that loaded data matches expected structure type
        expected_default = _get_default_structure_from_config(source)
        if not isinstance(data, type(expected_default)):
            print(
                f"⚠️ Warning: '{source_name}' loaded as {type(data).__name__} "
                f"but expected {type(expected_default).__name__} based on config"
            )

        # Ensure we return the correct type for mypy
        if isinstance(data, (dict, list)):
            print(f"✅ Successfully loaded '{source_name}' ({len(data)} items)")
            return data
        else:
            # If data is not dict or list, fall back to default structure
            print(f"⚠️ Warning: '{source_name}' contains invalid data type, using default structure")
            return _get_default_structure_from_config(source)

    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {path}: {e}")
        default = _get_default_structure_from_config(source)
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
        if source_name.startswith("_"):  # Skip metadata
            continue
        data_type = type(data).__name__
        size = len(data) if hasattr(data, '__len__') else "unknown"
        print(f"  • {source_name}: {data_type} with {size} items")


def _validate_processing_config(source: Dict[str, Any]) -> None:
    """Validates processing configuration for a data source."""
    processing_config = source.get("processing_config")
    if not processing_config:
        print(f"⚠️ No processing config found for {source['name']} - will be skipped during processing")
        return

    chunk_strategy = processing_config.get("chunk_strategy")
    if not chunk_strategy:
        print(f"⚠️ No chunk_strategy defined for {source['name']}")
        return

    if chunk_strategy == "by_sections":
        sections = processing_config.get("sections")
        if not sections:
            print(f"⚠️ by_sections strategy requires 'sections' config for {source['name']}")
        else:
            print(f"✅ Processing config validated for {source['name']} ({len(sections)} sections)")

    elif chunk_strategy == "by_items":
        if "content_template" not in processing_config:
            print(f"⚠️ by_items strategy requires 'content_template' for {source['name']}")
        else:
            print(f"✅ Processing config validated for {source['name']} (by_items strategy)")

    else:
        print(f"⚠️ Unknown chunk_strategy '{chunk_strategy}' for {source['name']}")


def build_unified_data() -> None:
    """
    Builds a single, structured JSON data file from various sources.
    This file acts as the "source of truth" for the RAG system, enabling
    logical chunking and rich metadata embedding based on configuration.
    """
    print("🔨 Building unified data file using config-driven approach...")

    base_path = Path("public")
    output_path = base_path / "unified_data.json"

    # Ensure output directory exists
    base_path.mkdir(parents=True, exist_ok=True)

    unified_data: Dict[str, Any] = {}
    errors = []
    processing_warnings = []

    # Process each data source from configuration
    for i, source in enumerate(AppConfig.DATA_SOURCES, 1):
        print(f"\n[{i}/{len(AppConfig.DATA_SOURCES)}] Processing data source...")

        try:
            _validate_source_config(source)
            source_name = source["name"]
            source_path = Path(source["path"])

            print(f"📂 Loading '{source_name}' from {source_path}")
            unified_data[source_name] = _load_json_with_validation(source_path, source)

            # Validate processing configuration
            try:
                _validate_processing_config(source)
            except Exception as e:
                warning_msg = f"Processing config validation warning for {source_name}: {e}"
                print(f"⚠️ {warning_msg}")
                processing_warnings.append(warning_msg)

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

    # Prepare output data with metadata
    output_data = unified_data.copy()

    # Add comprehensive metadata
    metadata = {
        "sources_processed": len(AppConfig.DATA_SOURCES),
        "sources_loaded": len([k for k in unified_data.keys() if not k.startswith("_")]),
        "config_version": AppConfig.APP_VERSION,
        "default_structure_rules": AppConfig.DEFAULT_STRUCTURE_RULES
    }

    if errors:
        metadata["errors"] = errors

    if processing_warnings:
        metadata["processing_warnings"] = processing_warnings

    output_data["_metadata"] = metadata

    # Write the unified data file
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print("\n✅ Unified data file created successfully!")
        print(f"📁 Location: {output_path}")
        print(f"📊 Sources: {metadata['sources_loaded']}/{metadata['sources_processed']}")

        # Report configuration summary
        print("\n📋 Configuration Summary:")
        for source in AppConfig.DATA_SOURCES:
            processing_config = source.get("processing_config", {})
            strategy = processing_config.get("chunk_strategy", "none")
            structure = source.get("default_structure", "auto-detected")
            print(f"  • {source['name']}: {strategy} strategy, {structure} structure")

        if errors:
            print(f"\n⚠️ {len(errors)} errors encountered (see metadata for details)")

        if processing_warnings:
            print(f"⚠️ {len(processing_warnings)} processing warnings (see metadata for details)")

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
