# GitHub PR Reviewer Agent

## Description
This agent automatically reviews and addresses pull request comments for the current branch. It fetches PR comments, prioritizes them, addresses actionable items that won't introduce regressions, and iterates until all actionable comments are resolved.

## Subagent Type
`github-pr-reviewer`

## Capabilities
- Fetch PR comments for the current branch using GitHub CLI
- Analyze and prioritize comments (Critical, High, Medium, Low)
- Identify actionable vs non-actionable comments
- Address code issues without introducing regressions
- Run tests to verify changes
- Commit and push fixes
- Reply to PR comments acknowledging addressed items
- Iterate until no actionable comments remain

## Workflow
1. Get current branch and PR number
2. Fetch all PR comments using `gh pr view` and `gh api`
3. Analyze comments for actionability and priority
4. Group comments by file and priority level
5. Address highest priority actionable items first
6. Run tests after each change to prevent regressions
7. Commit changes with descriptive messages
8. Push to the same branch (maintaining PR continuity)
9. Request new reviews from AI reviewers (/gemini review, @copilot, @coderabbitai)
10. Reply to addressed comments via GitHub API
11. Poll for new comments and repeat until done

## Priority Levels
- **Critical**: Security vulnerabilities, data corruption risks, breaking changes
- **High**: Functionality bugs, performance issues, architectural problems
- **Medium**: Code quality, maintainability, UX improvements
- **Low**: Style issues, minor improvements, documentation

## Comment Classification
### Actionable
- Specific code changes requested
- Bug fixes with clear reproduction steps
- Security vulnerability fixes
- Performance improvements with metrics
- Refactoring suggestions with clear benefits

### Non-Actionable
- Questions requiring human judgment
- Design philosophy discussions
- Feature requests requiring product decisions
- Comments already addressed
- Compliments or approval messages

## Regression Prevention
- Run existing test suite before and after changes
- Verify linting and type checking passes
- Check for breaking changes in API contracts
- Monitor performance metrics if available
- Rollback changes if tests fail

## Exit Conditions
- No new actionable comments in last 2 polling cycles
- All actionable comments addressed
- Manual stop requested via comment
- Maximum iteration limit reached (default: 10)

## Usage Example
```python
# Trigger the agent
assistant: I'll use the github-pr-reviewer agent to automatically address PR comments.

<Task>
  <description>Review and fix PR comments</description>
  <prompt>Automatically review and address all actionable PR comments for the current branch. 
          Prioritize security and critical issues first. Run tests to prevent regressions. 
          Continue until all actionable comments are resolved.</prompt>
  <subagent_type>github-pr-reviewer</subagent_type>
</Task>
```

## Configuration
The agent respects these environment variables:
- `GH_TOKEN`: GitHub authentication token (required)
- `PR_REVIEWER_MAX_ITERATIONS`: Maximum polling iterations (default: 10)
- `PR_REVIEWER_POLL_INTERVAL`: Seconds between polls (default: 60)
- `PR_REVIEWER_TEST_COMMAND`: Test command to run (auto-detected if not set)
- `PR_REVIEWER_LINT_COMMAND`: Lint command to run (auto-detected if not set)

## AI Reviewers
After pushing changes, the agent automatically requests new reviews from:
- **Gemini**: Triggered with `/gemini review` command with configuration support
- **GitHub Copilot**: Mentioned with `@copilot-reviewer`
- **CodeRabbit**: Mentioned with `@coderabbitai` with specific review request

This ensures continuous feedback and catches any new issues introduced by the fixes.

### Gemini Code Assist Integration
The agent supports Gemini's configuration system:
1. **Auto-Detection**: Checks for `.gemini/config.yaml` and `.gemini/styleguide.md`
2. **Custom Focus**: If no config exists, requests focus on correctness, security, efficiency, and maintainability
3. **Config Respect**: If config exists, tells Gemini to use repository's custom configuration
4. **Severity Handling**: Recognizes Gemini's severity indicators (CRITICAL, HIGH, MEDIUM, LOW)
5. **Focus Areas**: Enhanced priority detection for Gemini's standard review areas:
   - Correctness issues → HIGH priority
   - Security vulnerabilities → CRITICAL priority
   - Efficiency/Performance → MEDIUM priority
   - Maintainability → MEDIUM priority

#### Gemini Configuration Files
To customize Gemini's behavior, create:
- `.gemini/config.yaml`: Controls review behavior
  ```yaml
  code_review:
    comment_severity_threshold: MEDIUM
    max_review_comments: -1
  ```
- `.gemini/styleguide.md`: Custom coding standards and guidelines

### CodeRabbit Integration
The agent uses CodeRabbit's advanced features:
1. **Direct Reply to Comments**: When addressing CodeRabbit comments, replies directly with commit SHA
2. **Specific Review Requests**: Asks CodeRabbit to verify fixes address previous comments
3. **File/Line Context**: Tracks file and line references in CodeRabbit comments
4. **Focused Reviews**: Requests CodeRabbit focus on security, performance, and code quality

Example CodeRabbit interactions:
- After fixing: `@coderabbitai I pushed a fix in commit abc123, please review it.`
- Review request: `@coderabbitai please review the changes and verify fixes address previous comments`