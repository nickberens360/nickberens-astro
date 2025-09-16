.PHONY: lint lint-check lint-fix lint-fast type-check test-unit test-integration

lint-fix:
	black .
	isort .
	autoflake --in-place --remove-all-unused-imports --remove-unused-variables --recursive .

lint-check:
	black --check .
	isort --check-only .
	flake8 .

type-check:
	mypy backend/core --ignore-missing-imports

lint: lint-fix lint-check type-check

# Faster local lint (no mypy)
lint-fast:
	black .
	isort .
	autoflake --in-place --remove-all-unused-imports --remove-unused-variables --recursive .
	black --check .
	isort --check-only .
	flake8 .

# Test targets for faster dev cycles
test-unit:
	pytest -m "not integration and not slow" -q

test-integration:
	pytest -m "integration" -q

# Run indexing on a directory and print metrics JSON
index-report:
	python -m backend.scripts.indexing_report --dir "$(DIR)" $(if $(FORCE),--force,) $(if $(HETERO),--hetero,) $(if $(PERSIST_DIR),--persist-dir "$(PERSIST_DIR)",)

# -----------------------------
# Follow-up data sync via Railway
# -----------------------------
.PHONY: followup-export followup-import followup-sync followup-verify railway-check-followup-scripts

# Optional: set SERVICE to target a specific Railway service
RAILWAY_RUN=railway run $(if $(SERVICE),--service $(SERVICE),)

followup-export:
	python -m backend.scripts.export_followup_to_json -o followup_export.json
	@echo "Exported local follow-up data to followup_export.json"

railway-check-followup-scripts:
	$(RAILWAY_RUN) bash -lc 'pwd; ls -la /app/backend/scripts || true; ls -la /app/backend/scripts/export_followup_to_json.py /app/backend/scripts/import_followup_from_json.py || true'

# Import using inline Python so no redeploy is required
followup-import:
	@test -f followup_export.json || (echo "followup_export.json not found. Run 'make followup-export' first." && exit 1)
	cat followup_export.json | $(RAILWAY_RUN) bash -lc 'python - <<'"'"'PY'"'"'
import sys, json
from backend.core.admin_database import get_admin_db_manager

j = json.load(sys.stdin)
db = get_admin_db_manager()
created_cats = updated_cats = created_qs = updated_qs = 0

for cat in j.get("categories", []):
    name = cat["name"].strip()
    display = cat.get("display_name") or name.title()
    desc = cat.get("description") or ""
    icon = cat.get("icon") or "help-circle"
    sort = int(cat.get("sort_order", 0))
    active = bool(cat.get("is_active", True))

    existing = db.get_followup_category_by_name(name)
    if existing is None:
        cid = db.create_followup_category(name=name, display_name=display, description=desc, icon=icon, sort_order=sort)
        created_cats += 1
        current = db.get_followup_category(cid)
    else:
        db.update_followup_category(category_id=existing["id"], display_name=display, description=desc, icon=icon, sort_order=sort, is_active=active)
        updated_cats += 1
        current = db.get_followup_category(existing["id"]) 

    cid = current["id"]
    existing_q = {q["question_text"].strip(): q for q in db.get_followup_questions(category_id=cid, active_only=False)}
    for q in cat.get("questions", []):
        qt = q["question_text"].strip()
        qo = int(q.get("sort_order", 0))
        qa = bool(q.get("is_active", True))
        prior = existing_q.get(qt)
        if prior is None:
            db.create_followup_question(category_id=cid, question_text=qt, sort_order=qo, is_active=qa)
            created_qs += 1
        else:
            db.update_followup_question(question_id=prior["id"], question_text=qt, sort_order=qo, is_active=qa)
            updated_qs += 1

print(json.dumps({"status":"ok","categories_created":created_cats,"categories_updated":updated_cats,"questions_created":created_qs,"questions_updated":updated_qs}))
PY'

# Convenience target: export locally then import to Railway
followup-sync: followup-export followup-import
	@echo "Follow-up data synchronized to Railway."

followup-verify:
	$(RAILWAY_RUN) bash -lc 'python - <<'"'"'PY'"'"'
from backend.core.admin_database import get_admin_db_manager
db = get_admin_db_manager()
cats = db.get_followup_categories(active_only=False)
print({"category_count": len(cats)})
for c in cats:
    qs = db.get_followup_questions(category_id=c["id"], active_only=False)
    print(f"- {c['name']} ({len(qs)} questions)")
PY'

