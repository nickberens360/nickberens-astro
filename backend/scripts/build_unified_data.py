import json
import os
from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv

# Load environment variables from backend/.env file
load_dotenv(Path(__file__).parent.parent / ".env")


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


def fetch_github_repos() -> List[Dict[str, Any]]:
    """Fetches public repositories from GitHub."""
    username = os.getenv("PUBLIC_GITHUB_USERNAME")
    if not username:
        print("⚠️ PUBLIC_GITHUB_USERNAME environment variable not set. Skipping GitHub fetch.")
        return []

    token = os.getenv("GITHUB_TOKEN")
    headers = {"Authorization": f"token {token}"} if token else {}
    url = f"https://api.github.com/users/{username}/repos"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print(f"✅ Successfully fetched {len(response.json())} GitHub repositories.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch GitHub repositories: {e}")
        return []


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
    illustrations_data = _load_json_or_default(illustrations_path, [])

    # --- Resume Data (loaded from JSON) ---
    resume_path = base_path / "resume.json"
    resume_data = _load_json_or_default(resume_path, {})

    # --- About Data (loaded from JSON) ---
    about_path = base_path / "about.json"
    about_data = _load_json_or_default(about_path, {})

    # --- Fetch GitHub Repositories ---
    github_repos = fetch_github_repos()

    # --- Build unified structure ---
    unified_data = {
        "resume": resume_data,
        "about": about_data,
        "illustrations": illustrations_data,
        "github_repositories": github_repos,
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
