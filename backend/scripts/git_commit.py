import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple


def _run_git_command(command: List[str]) -> Tuple[bool, str]:
    """
    Runs a git command and returns success status and output.

    Args:
        command: List of command arguments to pass to git

    Returns:
        Tuple of (success: bool, output: str)
    """
    try:
        result = subprocess.run(["git"] + command, capture_output=True, text=True, check=False, cwd=Path.cwd())
        return result.returncode == 0, result.stdout.strip() or result.stderr.strip()
    except (subprocess.SubprocessError, OSError) as e:
        return False, f"Failed to run git command: {e}"


def _check_git_repository() -> bool:
    """
    Checks if the current directory is a git repository.

    Returns:
        True if in a git repository, False otherwise
    """
    success, _ = _run_git_command(["rev-parse", "--git-dir"])
    return success


def get_git_status() -> Tuple[bool, str]:
    """
    Gets the current git status.

    Returns:
        Tuple of (success: bool, status_output: str)
    """
    if not _check_git_repository():
        return False, "Not in a git repository"

    return _run_git_command(["status", "--porcelain"])


def stage_files(files: Optional[List[str]] = None) -> Tuple[bool, str]:
    """
    Stages files for commit.

    Args:
        files: List of file paths to stage. If None, stages all changes.

    Returns:
        Tuple of (success: bool, output: str)
    """
    if not _check_git_repository():
        return False, "Not in a git repository"

    if files is None:
        # Stage all changes
        command = ["add", "."]
    else:
        # Stage specific files
        command = ["add"] + files

    success, output = _run_git_command(command)
    if success:
        file_list = "all changes" if files is None else ", ".join(files)
        return True, f"✅ Successfully staged {file_list}"
    else:
        return False, f"❌ Failed to stage files: {output}"


def commit_changes(message: str, stage_all: bool = True) -> Tuple[bool, str]:
    """
    Commits staged changes with the provided message.

    Args:
        message: Commit message
        stage_all: Whether to stage all changes before committing

    Returns:
        Tuple of (success: bool, output: str)
    """
    if not _check_git_repository():
        return False, "Not in a git repository"

    if not message.strip():
        return False, "❌ Commit message cannot be empty"

    # Check if there are any changes to commit
    status_success, status_output = get_git_status()
    if not status_success:
        return False, f"❌ Failed to check git status: {status_output}"

    if not status_output.strip():
        return False, "⚠️ No changes to commit"

    # Stage files if requested
    if stage_all:
        stage_success, stage_output = stage_files()
        if not stage_success:
            return False, stage_output
        print(stage_output)

    # Commit the changes
    success, output = _run_git_command(["commit", "-m", message])
    if success:
        return True, f"✅ Successfully committed changes: {message}"
    else:
        return False, f"❌ Failed to commit changes: {output}"


def commit_with_auto_message(prefix: str = "Auto-commit") -> Tuple[bool, str]:
    """
    Commits changes with an automatically generated message based on git status.

    Args:
        prefix: Prefix for the auto-generated commit message

    Returns:
        Tuple of (success: bool, output: str)
    """
    if not _check_git_repository():
        return False, "Not in a git repository"

    # Get current status to generate message
    status_success, status_output = get_git_status()
    if not status_success:
        return False, f"❌ Failed to check git status: {status_output}"

    if not status_output.strip():
        return False, "⚠️ No changes to commit"

    # Count changes
    lines = status_output.strip().split("\n")
    modified_count = len([line for line in lines if line.startswith(" M") or line.startswith("M")])
    added_count = len([line for line in lines if line.startswith("A") or line.startswith("??")])
    deleted_count = len([line for line in lines if line.startswith(" D") or line.startswith("D")])

    # Generate message
    changes = []
    if modified_count > 0:
        changes.append(f"{modified_count} modified")
    if added_count > 0:
        changes.append(f"{added_count} added")
    if deleted_count > 0:
        changes.append(f"{deleted_count} deleted")

    if changes:
        auto_message = f"{prefix}: {', '.join(changes)} files"
    else:
        auto_message = f"{prefix}: Update files"

    return commit_changes(auto_message, stage_all=True)


def main():
    """Main function for command-line usage."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python git_commit.py <commit_message>")
        print("  python git_commit.py --auto [prefix]")
        print("  python git_commit.py --status")
        sys.exit(1)

    if sys.argv[1] == "--status":
        success, output = get_git_status()
        if success:
            if output:
                print("📋 Git Status:")
                print(output)
            else:
                print("✅ Working directory clean")
        else:
            print(f"❌ {output}")
        sys.exit(0 if success else 1)

    elif sys.argv[1] == "--auto":
        prefix = sys.argv[2] if len(sys.argv) > 2 else "Auto-commit"
        success, output = commit_with_auto_message(prefix)
        print(output)
        sys.exit(0 if success else 1)

    else:
        # Regular commit with provided message
        message = " ".join(sys.argv[1:])
        success, output = commit_changes(message)
        print(output)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
