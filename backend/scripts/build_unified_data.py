import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv

# Load environment variables from backend/.env file
load_dotenv(Path(__file__).parent.parent / ".env")


def should_rebuild_unified_data() -> bool:
    """Check if unified_data.json needs rebuilding based on source file changes."""
    base_path = Path("public")
    output_path = base_path / "unified_data.json"

    # If output doesn't exist, always rebuild
    if not output_path.exists():
        print("📝 unified_data.json doesn't exist. Building...")
        return True

    output_mtime = output_path.stat().st_mtime

    # Check local JSON source files
    source_files = [
        base_path / "resume.json",
        base_path / "about.json",
        base_path / "illustrations.json"
    ]

    for source_file in source_files:
        if source_file.exists() and source_file.stat().st_mtime > output_mtime:
            print(f"📝 Source file {source_file.name} has been modified. Rebuilding...")
            return True

    # For GitHub data, check if it's been more than 24 hours since last build
    current_time = datetime.now().timestamp()
    hours_since_last_build = (current_time - output_mtime) / 3600

    if hours_since_last_build > 24:
        print(f"📝 GitHub data is stale ({hours_since_last_build:.1f} hours old). Rebuilding...")
        return True

    print("✅ unified_data.json is up to date. Skipping rebuild.")
    return False


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
        repos_data: List[Dict[str, Any]] = response.json()
        print(f"✅ Successfully fetched {len(repos_data)} GitHub repositories.")
        return repos_data
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch GitHub repositories: {e}")
        return []


def fetch_github_commits(username: str, repo: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Fetches recent commits from a GitHub repository."""
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Authorization": f"token {token}"} if token else {}
    url = f"https://api.github.com/repos/{username}/{repo}/commits?per_page={limit}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        commits = response.json()

        # Format commits for vector storage
        formatted_commits = []
        for commit in commits:
            formatted_commits.append({
                "sha": commit["sha"][:7],
                "message": commit["commit"]["message"].split('\n')[0],
                "author": commit["commit"]["author"]["name"],
                "date": commit["commit"]["author"]["date"],
                "url": commit["html_url"],
                "full_message": commit["commit"]["message"]
            })

        print(f"✅ Successfully fetched {len(formatted_commits)} commits from {repo}.")
        return formatted_commits
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch commits from {repo}: {e}")
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

    # --- Fetch GitHub Commits ---
    username = os.getenv("PUBLIC_GITHUB_USERNAME")
    github_commits = []
    if username:
        github_commits = fetch_github_commits(username, "nickberens-astro", 10)

    # --- Build unified structure ---
    unified_data = {
        "resume": resume_data,
        "about": about_data,
        "illustrations": illustrations_data,
        "github_repositories": github_repos,
        "github_commits": github_commits,
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
