"""
Import follow-up categories and questions from a JSON file into the admin DB.

Usage:
  python backend/scripts/import_followup_from_json.py path/to/followup_export.json
  # or read from stdin
  cat followup_export.json | python backend/scripts/import_followup_from_json.py -

Behavior:
- Upserts categories by unique `name` (create if missing, otherwise update fields).
- Upserts questions by (`category_id`, `question_text`).
- Idempotent: safe to run multiple times.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List

from backend.core.admin_database import get_admin_db_manager


def _load_payload(path: str) -> Dict[str, Any]:
    if path == "-":
        raw = sys.stdin.read()
    else:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    data = json.loads(raw)
    if not isinstance(data, dict) or "categories" not in data:
        raise ValueError("Invalid payload: expected object with 'categories' key")
    return data


def upsert_followup(data: Dict[str, Any]) -> Dict[str, Any]:
    db = get_admin_db_manager()

    cats: List[Dict[str, Any]] = data.get("categories", [])
    created_cats = 0
    updated_cats = 0
    created_qs = 0
    updated_qs = 0

    for cat in cats:
        name = cat["name"].strip()
        display_name = cat.get("display_name")
        description = cat.get("description")
        icon = cat.get("icon")
        sort_order = int(cat.get("sort_order", 0))
        is_active = bool(cat.get("is_active", True))

        existing = db.get_followup_category_by_name(name)
        if existing is None:
            cat_id = db.create_followup_category(
                name=name,
                display_name=display_name or name.title(),
                description=description or "",
                icon=icon or "help-circle",
                sort_order=sort_order,
            )
            created_cats += 1
            # Ensure desired active state on newly-created categories
            if is_active is not None:
                db.update_followup_category(category_id=cat_id, is_active=is_active)
            current = db.get_followup_category(cat_id) or {"id": cat_id}
        else:
            # Update category fields to match
            db.update_followup_category(
                category_id=existing["id"],
                display_name=display_name or existing.get("display_name"),
                description=description or existing.get("description"),
                icon=icon or existing.get("icon"),
                sort_order=sort_order,
                is_active=is_active,
            )
            updated_cats += 1
            current = db.get_followup_category(existing["id"]) or existing

        cat_id = current["id"]

        # Fetch fresh list of questions for this category to ensure up-to-date data
        existing_questions = db.get_followup_questions(category_id=cat_id, active_only=False)

        # Build index of existing questions by text for this category
        existing_q_index = {q["question_text"].strip(): q for q in existing_questions}

        for q in cat.get("questions", []):
            q_text = q["question_text"].strip()
            q_order = int(q.get("sort_order", 0))
            q_active = bool(q.get("is_active", True))

            existing_q = existing_q_index.get(q_text)
            if existing_q is None:
                question_id = db.create_followup_question(
                    category_id=cat_id, question_text=q_text, sort_order=q_order, is_active=q_active
                )
                created_qs += 1
                # Update index to avoid duplicates within the same category block
                existing_q_index[q_text] = {"id": question_id}
            else:
                db.update_followup_question(
                    question_id=existing_q["id"], question_text=q_text, sort_order=q_order, is_active=q_active
                )
                updated_qs += 1

    return {
        "categories_created": created_cats,
        "categories_updated": updated_cats,
        "questions_created": created_qs,
        "questions_updated": updated_qs,
        "total_categories": len(cats),
    }


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Import follow-up categories/questions from JSON")
    parser.add_argument("path", help="Path to JSON file, or '-' to read from stdin")
    args = parser.parse_args(argv)

    data = _load_payload(args.path)
    summary = upsert_followup(data)
    print(json.dumps({"status": "ok", **summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
