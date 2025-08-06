import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, cast

# Ensure the backend directory is in the Python path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from core.data_source_config import config  # noqa: E402

# Import auto-discovery functionality
try:
    from core.auto_discovery import AutoDataSourceDiscovery  # noqa: E402
except ImportError as e:
    print(f"Warning: Auto-discovery functionality not available: {e}")
    AutoDataSourceDiscovery = None


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


def _get_source_file_paths(auto_discover: bool = False) -> List[Path]:
    """Get all source file paths that should be checked for modifications.

    Args:
        auto_discover: If True, include auto-discoverable JSON files

    Returns:
        List of source file paths to check for modifications
    """
    source_paths = []
    data_sources_config = config.data_sources

    # Add manually configured sources
    for source in data_sources_config.get("sources", []):
        source_path = config.get_source_file_path(source["name"])
        if source_path:
            source_paths.append(source_path)

    # Add auto-discoverable sources if requested
    if auto_discover and AutoDataSourceDiscovery is not None:
        try:
            base_path = Path(data_sources_config.get("base_path", "public"))
            discovery = AutoDataSourceDiscovery(base_path)
            auto_sources = discovery.discover_sources()

            # Get manual source names to avoid duplicates
            manual_names = {
                p.name
                for s in data_sources_config.get("sources", [])
                if (p := config.get_source_file_path(s["name"])) is not None
            }

            # Add paths for auto-discovered sources that aren't manually configured
            for auto_source in auto_sources:
                auto_file_path = base_path / auto_source["file"]
                if auto_file_path.name not in manual_names and auto_file_path.exists():
                    source_paths.append(auto_file_path)

        except Exception as e:
            print(f"⚠️ Error during auto-discovery path lookup: {e}")

    return source_paths


def _files_modified_since_last_build(auto_discover: bool = False) -> bool:
    """
    Check if any source files have been modified since the last build.

    Args:
        auto_discover: If True, also check for new auto-discoverable JSON files

    Returns:
        bool: True if files have been modified or registry is missing, False otherwise
    """
    registry = _load_file_registry()
    if not registry:
        print("📝 File registry not found, rebuild required")
        return True

    source_paths = _get_source_file_paths(auto_discover=auto_discover)

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


def _update_file_registry(auto_discover: bool = False) -> None:
    """Update the file registry with current file information.

    Args:
        auto_discover: If True, include auto-discoverable files in registry
    """
    registry_path = _get_file_registry_path()
    registry_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing registry
    registry = _load_file_registry()

    # Update entries for source files
    source_paths = _get_source_file_paths(auto_discover=auto_discover)

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


def _merge_auto_discovered_sources(
    manual_sources: List[Dict[str, Any]], auto_sources: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Merge manually configured sources with auto-discovered sources.

    Args:
        manual_sources: Sources from manual configuration
        auto_sources: Sources from auto-discovery

    Returns:
        Merged list of sources, with manual sources taking precedence
    """
    # Create a set of manually configured source names
    manual_names = {source["name"] for source in manual_sources}

    # Add auto-discovered sources that aren't manually configured
    merged_sources = list(manual_sources)
    for auto_source in auto_sources:
        if auto_source["name"] not in manual_names:
            merged_sources.append(auto_source)
            print(f"🔍 Added auto-discovered source: {auto_source['name']}")
        else:
            print(f"⏭️ Skipping auto-discovered source '{auto_source['name']}' (manually configured)")

    return merged_sources


def build_unified_data(force_rebuild: bool = False, auto_discover: bool = False):
    """
    Builds a single, structured JSON data file from various sources.
    This file acts as the "source of truth" for the RAG system, enabling
    logical chunking and rich metadata embedding.

    Args:
        force_rebuild: If True, rebuild regardless of file modification status
        auto_discover: If True, automatically discover and include JSON files
    """
    # Check if rebuild is needed (unless forced)
    if not force_rebuild and not _files_modified_since_last_build(auto_discover=auto_discover):
        print("⏭️ Skipping build - no source files have been modified")
        return

    print("🔨 Building unified data file...")

    # Get configuration
    data_sources_config = config.data_sources
    base_path = Path(data_sources_config.get("base_path", "public"))
    output_path = base_path / data_sources_config.get("output_file", "unified_data.json")

    # Get sources list (manual + auto-discovered if enabled)
    manual_sources = data_sources_config.get("sources", [])
    sources_to_process = manual_sources

    if auto_discover and AutoDataSourceDiscovery is not None:
        print("🔍 Auto-discovering JSON sources...")
        try:
            discovery = AutoDataSourceDiscovery(base_path)
            auto_sources = discovery.discover_sources()
            sources_to_process = _merge_auto_discovered_sources(manual_sources, auto_sources)

            if auto_sources:
                print(f"✅ Auto-discovery found {len(auto_sources)} sources")
            else:
                print("ℹ️ No additional sources found via auto-discovery")
        except Exception as e:
            print(f"⚠️ Auto-discovery failed: {e}")
            print("📝 Continuing with manual configuration only")
    elif auto_discover:
        print("⚠️ Auto-discovery requested but not available")

    # Build unified data structure
    unified_data = {}

    # Process each source
    for source in sources_to_process:
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
        _update_file_registry(auto_discover=auto_discover)

    except (IOError, OSError) as e:
        print(f"❌ Failed to write unified data file: {e}")
        raise


def watch_mode(auto_discover: bool = False):
    """Watch for file changes and auto-rebuild.

    Args:
        auto_discover: Whether to use auto-discovery mode
    """
    print("👀 Starting watch mode...")
    print("Press Ctrl+C to stop watching")

    try:
        last_build_time = 0.0
        while True:
            try:
                # Check if files have been modified
                if _files_modified_since_last_build(auto_discover=auto_discover):
                    current_time = time.time()
                    # Debounce rapid file changes (wait at least 2 seconds)
                    if current_time - last_build_time > 2:
                        print("\n📝 File changes detected, rebuilding...")
                        build_unified_data(force_rebuild=True, auto_discover=auto_discover)
                        last_build_time = current_time
                        print("✅ Rebuild complete. Watching for changes...")

                time.sleep(1)  # Check every second
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"⚠️ Error during watch: {e}")
                time.sleep(5)  # Wait longer on error

    except KeyboardInterrupt:
        print("\n👋 Stopping watch mode")


def main():
    """Main entry point with command-line argument parsing."""
    parser = argparse.ArgumentParser(
        description="Build unified data file for RAG system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 build_unified_data.py                    # Standard build
  python3 build_unified_data.py --force            # Force rebuild
  python3 build_unified_data.py --auto-discover    # Auto-discover JSON files
  python3 build_unified_data.py --watch            # Watch mode
  python3 build_unified_data.py --watch --auto-discover  # Watch with auto-discovery
        """,
    )

    parser.add_argument(
        "--force", "-f", action="store_true", help="Force rebuild regardless of file modification status"
    )

    parser.add_argument(
        "--auto-discover",
        "-a",
        action="store_true",
        help="Automatically discover and include JSON files from public directory",
    )

    parser.add_argument("--watch", "-w", action="store_true", help="Watch for file changes and automatically rebuild")

    parser.add_argument(
        "--list-sources", action="store_true", help="List all available sources (manual + auto-discovered) and exit"
    )

    args = parser.parse_args()

    # Handle list sources command
    if args.list_sources:
        print("📋 Available Data Sources:")
        print("=" * 40)

        # Manual sources
        manual_sources = config.data_sources.get("sources", [])
        print(f"📝 Manual sources ({len(manual_sources)}):")
        for source in manual_sources:
            print(f"  - {source['name']} ({source['file']})")

        # Auto-discovered sources
        if AutoDataSourceDiscovery is not None:
            try:
                discovery = AutoDataSourceDiscovery(Path(config.data_sources.get("base_path", "public")))
                auto_sources = discovery.discover_sources()
                manual_names = {s["name"] for s in manual_sources}
                new_auto_sources = [s for s in auto_sources if s["name"] not in manual_names]

                print(f"\n🔍 Auto-discoverable sources ({len(new_auto_sources)}):")
                for source in new_auto_sources:
                    source_type = "List" if source.get("is_list_source") else "Object"
                    print(f"  - {source['name']} ({source['file']}) - {source_type}")

                if not new_auto_sources:
                    print("  (All discoverable sources are already manually configured)")

            except Exception as e:
                print(f"  ⚠️ Auto-discovery failed: {e}")
        else:
            print("\n🔍 Auto-discovery not available")

        return

    # Handle watch mode
    if args.watch:
        watch_mode(auto_discover=args.auto_discover)
        return

    # Standard build
    build_unified_data(force_rebuild=args.force, auto_discover=args.auto_discover)


if __name__ == "__main__":
    main()
