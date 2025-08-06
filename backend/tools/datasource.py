#!/usr/bin/env python3
"""
Data Source Management CLI Tool

This tool provides easy commands for managing RAG data sources,
including auto-discovery, configuration generation, and source listing.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import yaml

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

try:
    from core.auto_discovery import AutoDataSourceDiscovery
    from core.data_source_config import config
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)


def list_sources(show_details: bool = False):
    """List all available data sources."""
    print("📋 Data Sources Overview")
    print("=" * 50)

    # Manual sources
    manual_sources = config.data_sources.get("sources", [])
    print(f"📝 Manual Sources ({len(manual_sources)}):")

    for source in manual_sources:
        source_type = "List" if source.get("is_list_source") else "Object"
        print(f"  ✓ {source['name']} ({source['file']}) - {source_type}")

        if show_details:
            if source.get("is_list_source"):
                fields = source.get("item_fields", [])
                print(f"    Fields: {', '.join(fields)}")
            else:
                sections = source.get("sections", [])
                print(f"    Sections: {len(sections)} ({', '.join([s['name'] for s in sections])})")

    # Auto-discoverable sources
    try:
        discovery = AutoDataSourceDiscovery("public")
        auto_sources = discovery.discover_sources()
        manual_names = {s["name"] for s in manual_sources}
        new_auto_sources = [s for s in auto_sources if s["name"] not in manual_names]

        print(f"\n🔍 Auto-Discoverable Sources ({len(new_auto_sources)}):")

        if new_auto_sources:
            for source in new_auto_sources:
                source_type = "List" if source.get("is_list_source") else "Object"
                print(f"  🆕 {source['name']} ({source['file']}) - {source_type}")

                if show_details:
                    if source.get("is_list_source"):
                        fields = source.get("item_fields", [])
                        print(f"    Fields: {', '.join(fields)}")
                    else:
                        sections = source.get("sections", [])
                        print(f"    Sections: {len(sections)} ({', '.join([s['name'] for s in sections])})")
        else:
            print("  (All discoverable sources are already manually configured)")

    except Exception as e:
        print(f"  ⚠️ Auto-discovery failed: {e}")


def generate_config(source_name: str, output_file: Optional[str] = None):
    """Generate YAML configuration for a specific source."""
    try:
        discovery = AutoDataSourceDiscovery("public")
        auto_sources = discovery.discover_sources()

        # Find the requested source
        target_source = None
        for source in auto_sources:
            if source["name"] == source_name:
                target_source = source
                break

        if not target_source:
            print(f"❌ Source '{source_name}' not found")
            return

        # Generate templates and retriever config
        templates = discovery.generate_templates([target_source])

        # Load sample data for retriever config
        data_path = Path("public") / target_source["file"]
        with open(data_path, "r") as f:
            sample_data = json.load(f)

        retriever_config = discovery.generate_retriever_config(source_name, sample_data)

        # Create configuration structure
        config_data = {
            "data_sources": {"sources": [target_source]},
            "retrievers": {source_name: retriever_config},
            "templates": templates,
        }

        # Remove auto_discovered flag for clean output
        if "auto_discovered" in config_data["data_sources"]["sources"][0]:
            del config_data["data_sources"]["sources"][0]["auto_discovered"]

        # Output configuration
        yaml_output = yaml.dump(config_data, default_flow_style=False, sort_keys=False)

        if output_file:
            with open(output_file, "w") as f:
                f.write(yaml_output)
            print(f"✅ Configuration written to {output_file}")
        else:
            print(f"📄 Generated configuration for '{source_name}':")
            print("-" * 50)
            print(yaml_output)

    except Exception as e:
        print(f"❌ Failed to generate configuration: {e}")


def add_source(file_path: str, auto_configure: bool = True):
    """Add a new data source."""
    source_path = Path(file_path)

    if not source_path.exists():
        print(f"❌ File not found: {file_path}")
        return

    if not source_path.suffix.lower() == ".json":
        print("❌ Only JSON files are supported")
        return

    # Copy file to public directory if not already there
    public_dir = Path("public")
    if source_path.parent != public_dir:
        target_path = public_dir / source_path.name
        if target_path.exists():
            print(f"⚠️ File {source_path.name} already exists in public directory")
        else:
            import shutil

            shutil.copy2(source_path, target_path)
            print(f"📁 Copied {source_path.name} to public directory")

    if auto_configure:
        print(f"🔍 Auto-configuring {source_path.name}...")

        try:
            discovery = AutoDataSourceDiscovery("public")
            sources = discovery.discover_sources()

            source_name = source_path.stem
            target_source = None
            for source in sources:
                if source["name"] == source_name:
                    target_source = source
                    break

            if target_source:
                print(f"✅ Auto-configured data source: {source_name}")
                print(f"   Type: {'List' if target_source.get('is_list_source') else 'Object'}")
                if target_source.get("is_list_source"):
                    fields = target_source.get("item_fields", [])
                    print(f"   Fields: {', '.join(fields)}")
                else:
                    sections = target_source.get("sections", [])
                    print(f"   Sections: {len(sections)}")

                print("\n💡 To use this source, run:")
                print("   python3 backend/scripts/build_unified_data.py --auto-discover")
            else:
                print(f"❌ Failed to auto-configure {source_name}")

        except Exception as e:
            print(f"❌ Auto-configuration failed: {e}")
    else:
        print(f"✅ Added {source_path.name} to public directory")
        print("💡 Run with --auto-configure to generate configuration")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Data Source Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 -m backend.tools.datasource list                    # List all sources
  python3 -m backend.tools.datasource list --details          # List with details
  python3 -m backend.tools.datasource add projects.json       # Add new source
  python3 -m backend.tools.datasource generate projects       # Generate config
  python3 -m backend.tools.datasource generate projects -o config.yaml
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List all data sources")
    list_parser.add_argument("--details", "-d", action="store_true", help="Show detailed information about each source")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new data source")
    add_parser.add_argument("file", help="Path to JSON file to add")
    add_parser.add_argument("--no-auto-configure", action="store_true", help="Don't automatically configure the source")

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate configuration for a source")
    gen_parser.add_argument("source", help="Name of the source to generate config for")
    gen_parser.add_argument("--output", "-o", help="Output file for generated configuration")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "list":
        list_sources(show_details=args.details)
    elif args.command == "add":
        add_source(args.file, auto_configure=not args.no_auto_configure)
    elif args.command == "generate":
        generate_config(args.source, args.output)


if __name__ == "__main__":
    main()
