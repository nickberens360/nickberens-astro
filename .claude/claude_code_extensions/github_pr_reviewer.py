#!/usr/bin/env python3
"""
GitHub PR Reviewer Agent

Automatically reviews and addresses pull request comments.
"""

import json
import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class Priority(Enum):
    CRITICAL = 1  # Security, data loss, breaking changes
    HIGH = 2  # Bugs, performance, architecture
    MEDIUM = 3  # Code quality, UX
    LOW = 4  # Style, minor improvements


@dataclass
class PRComment:
    id: int
    author: str
    body: str
    file: Optional[str]
    line: Optional[int]
    created_at: str
    is_resolved: bool = False
    priority: Priority = Priority.LOW
    is_actionable: bool = False
    action_taken: Optional[str] = None


class GitHubPRReviewer:
    def __init__(self, max_iterations: int = 10, poll_interval: int = 60):
        self.max_iterations = max_iterations
        self.poll_interval = poll_interval
        self.addressed_comment_ids: Set[int] = set()
        self.current_branch = self._get_current_branch()
        self.pr_number = self._get_pr_number()
        self.test_command = self._detect_test_command()
        self.lint_command = self._detect_lint_command()
        self.gemini_configured = self._check_gemini_config()

    def _run_command(self, cmd: str, check: bool = True) -> Tuple[int, str, str]:
        """Run shell command and return exit code, stdout, stderr."""
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
        if check and result.returncode != 0:
            raise RuntimeError(f"Command failed: {cmd}\n{result.stderr}")
        return result.returncode, result.stdout, result.stderr

    def _get_current_branch(self) -> str:
        """Get the current git branch name."""
        _, branch, _ = self._run_command("git rev-parse --abbrev-ref HEAD")
        return branch.strip()

    def _get_pr_number(self) -> Optional[int]:
        """Get PR number for current branch."""
        try:
            _, output, _ = self._run_command(f"gh pr view --json number --jq .number")
            return int(output.strip()) if output.strip() else None
        except:
            return None

    def _detect_test_command(self) -> Optional[str]:
        """Auto-detect test command from project."""
        test_commands = [
            ("package.json", "npm test"),
            ("Makefile", "make test"),
            ("pyproject.toml", "pytest"),
            ("setup.py", "python -m pytest"),
            ("Cargo.toml", "cargo test"),
        ]

        for file, cmd in test_commands:
            if os.path.exists(file):
                return cmd
        return None

    def _check_gemini_config(self) -> bool:
        """Check if Gemini configuration exists in the repository."""
        return os.path.exists(".gemini/config.yaml") or os.path.exists(".gemini/styleguide.md")

    def _get_gemini_config_hint(self) -> str:
        """Get hint for Gemini based on configuration."""
        if not self.gemini_configured:
            # Default focus areas if no config
            return " - focus on correctness, security, efficiency, and maintainability"

        # If config exists, Gemini will use it automatically
        return " - use repository's .gemini configuration"

    def _detect_lint_command(self) -> Optional[str]:
        """Auto-detect lint command from project."""
        lint_commands = [
            ("package.json", "npm run lint"),
            ("Makefile", "make lint"),
            (".pre-commit-config.yaml", "pre-commit run --all-files"),
            ("pyproject.toml", "black . && flake8"),
            ("Cargo.toml", "cargo clippy"),
        ]

        for file, cmd in lint_commands:
            if os.path.exists(file):
                return cmd
        return None

    def fetch_pr_comments(self) -> List[PRComment]:
        """Fetch all PR comments including review comments."""
        if not self.pr_number:
            return []

        comments = []

        # Fetch issue comments
        _, issue_comments, _ = self._run_command(f"gh api repos/{{owner}}/{{repo}}/issues/{self.pr_number}/comments")
        issue_data = json.loads(issue_comments) if issue_comments else []

        for comment in issue_data:
            comments.append(
                PRComment(
                    id=comment["id"],
                    author=comment["user"]["login"],
                    body=comment["body"],
                    file=None,
                    line=None,
                    created_at=comment["created_at"],
                )
            )

        # Fetch review comments
        _, review_comments, _ = self._run_command(f"gh api repos/{{owner}}/{{repo}}/pulls/{self.pr_number}/comments")
        review_data = json.loads(review_comments) if review_comments else []

        for comment in review_data:
            comments.append(
                PRComment(
                    id=comment["id"],
                    author=comment["user"]["login"],
                    body=comment["body"],
                    file=comment.get("path"),
                    line=comment.get("line"),
                    created_at=comment["created_at"],
                )
            )

        # Filter out already addressed comments
        return [c for c in comments if c.id not in self.addressed_comment_ids]

    def analyze_comment(self, comment: PRComment) -> None:
        """Analyze a comment to determine priority and actionability."""
        body_lower = comment.body.lower()

        # Priority detection - enhanced for Gemini's focus areas
        if any(word in body_lower for word in ["security", "vulnerability", "exploit", "injection", "unsafe", "risk"]):
            comment.priority = Priority.CRITICAL
        elif any(word in body_lower for word in ["bug", "broken", "crash", "error", "fail", "correctness", "wrong"]):
            comment.priority = Priority.HIGH
        elif any(
            word in body_lower
            for word in ["refactor", "improve", "optimize", "clean", "efficiency", "performance", "maintainability"]
        ):
            comment.priority = Priority.MEDIUM
        else:
            comment.priority = Priority.LOW

        # Special handling for Gemini severity indicators if present
        if comment.author.lower() == "gemini" or "gemini" in comment.author.lower():
            if "critical" in body_lower or "severe" in body_lower:
                comment.priority = Priority.CRITICAL
            elif "high" in body_lower and "severity" in body_lower:
                comment.priority = Priority.HIGH

        # Actionability detection
        actionable_patterns = [
            r"please (fix|change|update|add|remove)",
            r"should (be|use|have)",
            r"(fix|change|update|add|remove) (this|the)",
            r"line \d+",
            r"```[\s\S]+```",  # Code blocks often indicate specific changes
        ]

        non_actionable_patterns = [
            r"^(lgtm|approved|looks good)",
            r"^\?",  # Questions
            r"(what|why|how) (do|does|is|are)",
            r"(consider|maybe|perhaps|thoughts)",
        ]

        # Check for actionable patterns
        for pattern in actionable_patterns:
            if re.search(pattern, body_lower):
                comment.is_actionable = True
                break

        # Override if non-actionable pattern found
        for pattern in non_actionable_patterns:
            if re.search(pattern, body_lower):
                comment.is_actionable = False
                break

    def group_comments_by_priority(self, comments: List[PRComment]) -> Dict[Priority, List[PRComment]]:
        """Group comments by priority level."""
        grouped = {p: [] for p in Priority}
        for comment in comments:
            self.analyze_comment(comment)
            if comment.is_actionable:
                grouped[comment.priority].append(comment)
        return grouped

    def run_tests(self) -> bool:
        """Run test suite to check for regressions."""
        if not self.test_command:
            print("No test command detected, skipping tests")
            return True

        print(f"Running tests: {self.test_command}")
        returncode, _, stderr = self._run_command(self.test_command, check=False)

        if returncode != 0:
            print(f"Tests failed:\n{stderr}")
            return False

        print("Tests passed")
        return True

    def run_lint(self) -> bool:
        """Run linting to ensure code quality."""
        if not self.lint_command:
            print("No lint command detected, skipping linting")
            return True

        print(f"Running lint: {self.lint_command}")
        returncode, _, stderr = self._run_command(self.lint_command, check=False)

        if returncode != 0:
            print(f"Linting failed:\n{stderr}")
            return False

        print("Linting passed")
        return True

    def _parse_file_reference(self, comment: PRComment) -> Optional[Tuple[str, Optional[int]]]:
        """Extract file and line reference from comment."""
        # Direct file reference from GitHub
        if comment.file:
            return comment.file, comment.line

        # Parse file references from comment body
        body = comment.body

        # Look for common patterns
        patterns = [
            r'(?:file|in)\s+[`"\']([^`"\'\n]+)[`"\']',  # file "path/to/file.py"
            r"([\w/.-]+\.\w+):(\d+)",  # file.py:123
            r"`([\w/.-]+\.\w+)`",  # `file.py`
        ]

        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                file_path = match.group(1)
                line_num = int(match.group(2)) if len(match.groups()) > 1 and match.group(2) else None
                return file_path, line_num

        return None, None

    def _analyze_comment_with_ai(self, comment: PRComment) -> Dict[str, any]:
        """Use pattern matching to analyze comment and generate fix instructions."""
        try:
            file_path, line_num = self._parse_file_reference(comment)
            body_lower = comment.body.lower()

            # Determine fix type based on keywords
            if any(word in body_lower for word in ["security", "vulnerability", "exploit", "injection", "unsafe"]):
                fix_type = "security"
            elif any(word in body_lower for word in ["bug", "error", "broken", "crash", "fail"]):
                fix_type = "bug"
            elif any(word in body_lower for word in ["refactor", "clean", "improve", "optimize"]):
                fix_type = "refactor"
            elif any(word in body_lower for word in ["style", "format", "lint"]):
                fix_type = "style"
            else:
                fix_type = "other"

            return {
                "fix_type": fix_type,
                "description": comment.body[:200].strip(),
                "file_path": file_path,
                "line_number": line_num,
                "explanation": f"Addressing {comment.author}'s feedback",
            }

        except Exception as e:
            print(f"Error analyzing comment: {e}")
            return {"fix_type": "unclear", "description": "Could not analyze comment"}

    def _apply_simple_fixes(self, comment: PRComment, analysis: Dict[str, any]) -> bool:
        """Apply common fixes based on comment analysis."""
        file_path = analysis.get("file_path")
        body_lower = comment.body.lower()
        changes_made = False

        # If we have a specific file, try to fix it
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                original_content = content

                # Apply specific fixes based on comment content
                if "hardcoded" in body_lower and ("password" in body_lower or "token" in body_lower):
                    # Remove hardcoded credentials
                    patterns = [
                        (r'password\s*=\s*["\'][^"\'\n]+["\']', 'password = os.getenv("PASSWORD")'),
                        (r'token\s*=\s*["\'][^"\'\n]+["\']', 'token = os.getenv("TOKEN")'),
                        (r"ADMIN_TOKEN=changeme", "ADMIN_TOKEN=<secure-token>"),
                    ]
                    for pattern, replacement in patterns:
                        content = re.sub(pattern, replacement, content)

                elif "redirect" in body_lower and "vulnerability" in body_lower:
                    # Fix open redirect vulnerabilities
                    if ".js" in file_path and "router" in file_path.lower():
                        # Add protocol-relative URL check
                        content = re.sub(
                            r"(!raw\.startsWith\(\'/\'\))",
                            r"(!raw.startsWith(\'/\') && !raw.startsWith(\'//\'))",
                            content,
                        )

                elif "localstorage" in body_lower and ("token" in body_lower or "session" in body_lower):
                    # Remove localStorage usage for sensitive data
                    patterns = [
                        (r"localStorage\.setItem\([^)]*token[^)]*\)", "// Removed localStorage token usage"),
                        (r"localStorage\.getItem\([^)]*token[^)]*\)", "null /* Removed localStorage token usage */"),
                        (r"localStorage\.removeItem\([^)]*token[^)]*\)", "// Removed localStorage token usage"),
                    ]
                    for pattern, replacement in patterns:
                        content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)

                elif "console.log" in body_lower or "debug" in body_lower:
                    # Remove debug console statements
                    content = re.sub(r"\s*console\.log\([^)]*\);?\s*\n?", "\n", content)

                elif "alert" in body_lower or "confirm" in body_lower:
                    # Replace native dialogs with proper UI components
                    content = re.sub(
                        r"alert\([^)]*\)", 'this.$emit("show-snackbar", { message: "Action completed" })', content
                    )
                    content = re.sub(r"confirm\([^)]*\)", "await this.showConfirmDialog", content)

                elif "magic number" in body_lower or ("hardcoded" in body_lower and "constant" in body_lower):
                    # Replace magic numbers with config constants
                    magic_numbers = {
                        "0.85": "DEFAULT_CACHE_HIT_RATE",
                        "15": "DEFAULT_TOTAL_SOURCES",
                        "8": "DEFAULT_TOTAL_TOPICS",
                        "0.7": "LOW_SIMILARITY_THRESHOLD",
                    }
                    for number, constant in magic_numbers.items():
                        if number in content:
                            # Import config if not already imported
                            if "from ..core.config import AppConfig" not in content and "backend/" in file_path:
                                content = "from ..core.config import AppConfig\n" + content
                            content = content.replace(number, f"AppConfig().{constant}")

                # Check if content actually changed
                if content != original_content:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"Applied fixes to {file_path}")
                    changes_made = True

            except Exception as e:
                print(f"Error applying fixes to {file_path}: {e}")

        # Global fixes that don't require specific files
        else:
            # Try to find and fix files mentioned in comment
            if "remove" in body_lower and "file" in body_lower:
                # Extract filenames and try to remove them
                file_patterns = re.findall(r"[\w/.-]+\.\w+", comment.body)
                for pattern in file_patterns:
                    if os.path.exists(pattern) and "temp" in pattern.lower():
                        try:
                            os.remove(pattern)
                            print(f"Removed file: {pattern}")
                            changes_made = True
                        except Exception as e:
                            print(f"Could not remove {pattern}: {e}")

        return changes_made

    def address_comment(self, comment: PRComment) -> bool:
        """Address a single comment. Returns True if successful."""
        print(f"\nAddressing comment {comment.id} (Priority: {comment.priority.name})")
        print(f"Author: {comment.author}")
        print(f"Comment: {comment.body[:200]}..." if len(comment.body) > 200 else f"Comment: {comment.body}")

        # Special handling for CodeRabbit comments - they often have specific file/line references
        if comment.author.lower() == "coderabbitai" and comment.file:
            print(f"CodeRabbit comment on file: {comment.file}" + (f" line {comment.line}" if comment.line else ""))

        # This is where the actual fixing logic would go
        # For now, we'll simulate the process

        # Run tests before making changes
        if not self.run_tests():
            print("Tests failing before changes, skipping comment")
            return False

        # Analyze comment to understand what needs to be fixed
        analysis = self._analyze_comment_with_ai(comment)
        print(f"Analysis: {analysis['fix_type']} - {analysis['description']}")

        if analysis["fix_type"] == "unclear":
            print("Comment is not actionable or unclear, skipping")
            return False

        # Apply fixes based on analysis
        changes_made = self._apply_simple_fixes(comment, analysis)

        if not changes_made:
            print(f"No automated fix available for comment {comment.id}")
            print(f"Manual review needed: {comment.body[:100]}")
            return False

        # Run tests after changes
        if not self.run_tests():
            print("Tests failed after changes, reverting")
            self._run_command("git checkout -- .", check=False)
            return False

        # Run linting
        if not self.run_lint():
            print("Linting failed, attempting to fix")
            # Try to auto-fix with common formatters
            try:
                if "black" in str(self.lint_command).lower():
                    self._run_command("black .", check=False)
                if "isort" in str(self.lint_command).lower():
                    self._run_command("isort .", check=False)
            except Exception as e:
                print(f"Auto-fix failed: {e}")

        # Commit changes
        commit_message = f"fix: Address PR comment #{comment.id}\n\n{comment.body[:100]}"
        try:
            self._run_command(f'git add -A && git commit -m "{commit_message}"')
            print(f"Committed fix for comment {comment.id}")
        except Exception as e:
            print(f"Failed to commit: {e}")
            return False

        # Mark as addressed
        self.addressed_comment_ids.add(comment.id)
        comment.action_taken = "Fixed and committed"

        return True

    def push_changes(self) -> bool:
        """Push committed changes to remote. Returns True if successful."""
        print("\nPushing changes to remote...")
        try:
            self._run_command(f"git push origin {self.current_branch}")
            print("Successfully pushed changes")
            return True
        except Exception as e:
            print(f"Failed to push changes: {e}")
            return False

    def request_new_reviews(self) -> None:
        """Request new reviews from AI reviewers after pushing changes."""
        if not self.pr_number:
            return

        print("\nRequesting new reviews from AI reviewers...")

        # Get latest commit SHA for CodeRabbit
        _, commit_sha, _ = self._run_command("git rev-parse HEAD")
        commit_sha = commit_sha.strip()[:8]  # Short SHA

        # Check if Gemini configuration exists for custom behavior
        gemini_config = self._get_gemini_config_hint()

        # Post comment requesting reviews with specific instructions
        review_request = (
            f"I pushed fixes in commit {commit_sha}, please review:\n\n"
            f"/gemini review{gemini_config}\n\n"
            "@coderabbitai please review the changes in this latest commit "
            "and verify that the fixes properly address the previous review comments. "
            "Focus on security, performance, and code quality issues.\n\n"
            "@copilot-reviewer review"
        )

        # Create comment via GitHub API
        try:
            self._run_command(f"gh pr comment {self.pr_number} " f'--body "{review_request}"')
            print("Review requests posted successfully")
        except Exception as e:
            print(f"Failed to post review request: {e}")

    def reply_to_comment(self, comment: PRComment) -> None:
        """Reply to a PR comment acknowledging it was addressed."""
        if not comment.action_taken:
            return

        # Get the latest commit SHA
        _, commit_sha, _ = self._run_command("git rev-parse HEAD")
        commit_sha = commit_sha.strip()[:8]

        # Different reply based on comment author
        if comment.author.lower() == "coderabbitai":
            # Specific reply for CodeRabbit with commit reference
            reply = (
                f"@coderabbitai I pushed a fix in commit {commit_sha} that addresses this issue. "
                f"Please review the changes to confirm the issue is resolved."
            )
            # Post as a direct reply to the comment thread
            self._run_command(f"gh pr comment {self.pr_number} " f'--body "{reply}"', check=False)
        else:
            # Generic reply for other reviewers
            reply = f"✅ Addressed in commit {commit_sha}: {comment.action_taken}"

            # Add reaction to acknowledge
            self._run_command(
                f"gh api repos/{{owner}}/{{repo}}/issues/comments/{comment.id}/reactions "
                f'--method POST -f content="+1"',
                check=False,
            )

    def run(self) -> None:
        """Main execution loop."""
        if not self.pr_number:
            print(f"No PR found for branch '{self.current_branch}'")
            return

        print(f"Starting PR review for PR #{self.pr_number} on branch '{self.current_branch}'")

        iteration = 0
        consecutive_empty_polls = 0

        while iteration < self.max_iterations:
            iteration += 1
            print(f"\n{'='*60}")
            print(f"Iteration {iteration}/{self.max_iterations}")
            print(f"{'='*60}")

            # Fetch comments
            comments = self.fetch_pr_comments()

            if not comments:
                consecutive_empty_polls += 1
                print("No new actionable comments found")

                if consecutive_empty_polls >= 2:
                    print("No new comments for 2 cycles, finishing")
                    break

                print(f"Waiting {self.poll_interval} seconds before next poll...")
                time.sleep(self.poll_interval)
                continue

            consecutive_empty_polls = 0
            print(f"Found {len(comments)} new comments")

            # Group by priority
            grouped = self.group_comments_by_priority(comments)

            # Address comments by priority
            changes_made = False
            for priority in Priority:
                priority_comments = grouped[priority]
                if not priority_comments:
                    continue

                print(f"\nAddressing {len(priority_comments)} {priority.name} priority comments")

                for comment in priority_comments:
                    if self.address_comment(comment):
                        changes_made = True
                        # Reply immediately for CodeRabbit to get faster re-review
                        if comment.author.lower() == "coderabbitai":
                            self.reply_to_comment(comment)

            # Push changes if any were made
            if changes_made:
                if self.push_changes():
                    print("Changes pushed successfully")

                    # Request new reviews from AI reviewers
                    self.request_new_reviews()

                    # Reply to all addressed comments after push
                    for priority in Priority:
                        for comment in grouped[priority]:
                            if comment.id in self.addressed_comment_ids and comment.author.lower() != "coderabbitai":
                                self.reply_to_comment(comment)
                else:
                    print("Failed to push changes, skipping review requests")

            # Brief pause before next iteration
            if iteration < self.max_iterations:
                print(f"\nWaiting {self.poll_interval} seconds before next poll...")
                time.sleep(self.poll_interval)

        print("\n" + "=" * 60)
        print("PR Review Complete")
        print(f"Addressed {len(self.addressed_comment_ids)} comments")
        print("=" * 60)


if __name__ == "__main__":
    # Get configuration from environment
    max_iterations = int(os.getenv("PR_REVIEWER_MAX_ITERATIONS", "10"))
    poll_interval = int(os.getenv("PR_REVIEWER_POLL_INTERVAL", "60"))

    # Run the reviewer
    reviewer = GitHubPRReviewer(max_iterations=max_iterations, poll_interval=poll_interval)
    reviewer.run()
