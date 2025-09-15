"""
Export follow-up categories and questions from the local admin database to JSON.

Usage:
  python backend/scripts/export_followup_to_json.py --output followup_export.json

The script reads from the database path determined by get_database_path(),
which in development resolves to backend/logs/admin_monitoring.db.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from backend.core.admin_database import get_admin_db_manager


def export_followup() -> Dict[str, Any]:
    db = get_admin_db_manager()
    # Include inactive to fully sync prod to local
    categories = db.get_followup_categories(active_only=False)

    result: Dict[str, Any] = {"categories": []}
    for cat in categories:
        cat_id = cat["id"]
        questions = db.get_followup_questions(category_id=cat_id, active_only=False)
        result["categories"].append(
            {
                "name": cat["name"],
                "display_name": cat.get("display_name"),
                "description": cat.get("description"),
                "icon": cat.get("icon"),
                "sort_order": cat.get("sort_order", 0),
                "is_active": bool(cat.get("is_active", 1)),
                "questions": [
                    {
                        "question_text": q["question_text"],
                        "sort_order": q.get("sort_order", 0),
                        "is_active": bool(q.get("is_active", 1)),
                    }
                    for q in questions
                ],
            }
        )
    return result


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Export follow-up categories and questions to JSON")
    parser.add_argument("--output", "-o", type=Path, required=True, help="Output JSON file path")
    args = parser.parse_args(argv)

    data = export_followup()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Exported {len(data['categories'])} categories to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
