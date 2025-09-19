from __future__ import annotations

import os
import sys
from pathlib import Path


def _print(msg: str) -> None:
    sys.stdout.write(msg + "\n")


def perms() -> int:
    """Check permissions for /data and UNIFIED_PERSIST_DIR."""
    targets: list[tuple[str, Path]] = []
    data = Path("/data")
    targets.append(("/data", data))

    persist_dir = os.getenv("UNIFIED_PERSIST_DIR", "backend/.unified_chroma")
    targets.append((f"UNIFIED_PERSIST_DIR={persist_dir}", Path(persist_dir)))

    code = 0
    for label, p in targets:
        try:
            exists = p.exists()
            writable = False
            readable = False
            if not exists:
                # Try to create the directory non-destructively
                p.mkdir(parents=True, exist_ok=True)
                exists = p.exists()
            readable = os.access(p, os.R_OK)
            writable = os.access(p, os.W_OK)
            _print(f"[perms] {label}: exists={exists} readable={readable} writable={writable}")
            # Try a write test inside the directory
            if exists and writable and p.is_dir():
                test_file = p / ".diag_write_test"
                try:
                    test_file.write_text("ok", encoding="utf-8")
                    test_file.unlink(missing_ok=True)  # py>=3.8
                    _print(f"[perms] {label}: write test passed")
                except Exception as e:
                    _print(f"[perms] {label}: write test FAILED: {e}")
                    code = 2
        except Exception as e:
            _print(f"[perms] {label}: error: {e}")
            code = 2
    return code


def db_paths() -> int:
    """Print resolved database paths using shared helper."""
    try:
        from ...core.database_utils import get_database_path
    except Exception as e:
        _print(f"[db-paths] failed to import helper: {e}")
        return 2

    names = [
        "admin_monitoring.db",
        "rag_monitoring.db",
        "knowledge_index.db",
    ]
    for name in names:
        try:
            p = get_database_path(name)
            _print(f"[db-paths] {name}: {p}")
        except Exception as e:
            _print(f"[db-paths] {name}: error: {e}")
    return 0


def volume() -> int:
    """Verify /data mount and writability; suggest env if missing."""
    p = Path("/data")
    if not p.exists():
        _print("[volume] /data does not exist. Ensure Railway persistent volume is mounted at /data.")
        return 1
    if not p.is_dir():
        _print("[volume] /data exists but is not a directory.")
        return 1
    try:
        test = p / ".diag_volume_test"
        test.write_text("ok", encoding="utf-8")
        test.unlink(missing_ok=True)
        _print("[volume] /data is writable. Good.")
        return 0
    except Exception as e:
        _print(f"[volume] write test FAILED: {e}")
        return 2


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in {"-h", "--help", "help"}:
        _print("Usage: python -m backend.tools.diagnostics <command>\n" "  commands: perms | db-paths | volume\n")
        return 0
    cmd = argv[1]
    if cmd == "perms":
        return perms()
    if cmd == "db-paths":
        return db_paths()
    if cmd == "volume":
        return volume()
    _print(f"Unknown command: {cmd}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
