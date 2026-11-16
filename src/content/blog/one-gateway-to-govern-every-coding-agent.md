---
title: "One Gateway to Govern Every Coding Agent"
description: "How I log and limit what Claude Code, Codex and other coding agents write to our CMS, without depending on any one tool's hooks."
pubDate: 2026-11-16
tags: ["ai", "agents", "governance", "cms", "architecture"]
author: "Nick Berens"
backgroundColor: "#fff1e6"
theme: "light"
---

I use several coding agents every day: Claude Code, Codex, and whatever new tool shows up that week. More and more, they don't just edit code. They create and update content in our headless CMS, and they push changes to our repos.

That raised a question I couldn't answer: **if an agent changed something in the CMS yesterday, how would I know which agent did it, and how would I undo it?**

This post covers the pattern I settled on. It's a small local gateway that every agent write has to pass through, and it works no matter which harness the agent runs in.

## Where does governance belong?

My first instinct was hooks. Claude Code has pre- and post-tool hooks, and other harnesses have their own versions. But that approach falls apart fast:

- Every harness does hooks differently, and some have none.
- An agent with a real API token can skip the hook with a plain HTTP call.
- I'd be maintaining the same logic in several places.

The only thing every harness has in common is that, in the end, it sends HTTP to the CMS API. So that's where governance goes: **at the network and credential layer.**

## The pattern

The gateway is a small proxy running on my machine. Agents talk to `localhost` instead of the CMS API, using a stand-in token. The gateway checks each request against a policy, swaps in the real token, forwards the request, and logs it.

The key move is that **the gateway is the only thing holding the real token.** If an agent tries to skip it, its request simply fails. Governance you can't bypass is the only kind worth having.

On top of that:

- **An MCP server** gives every harness one shared interface to the CMS, and it points at the gateway, never straight at the CMS.
- **Harness hooks** are still useful, but only for adding context to the log, never for enforcement.
- **The CMS's own audit log** works as a cross-check.

## Rollback without building rollback

I originally wanted a rollback UI. Then I realized I already had most of it:

- **The CMS keeps version history for each entry.** If each log line records the entry ID and the new version number, undoing a change is just restoring the previous version.
- **Git is already rollback for code.** Agents work on branches and open PRs, and branch protection stops them pushing to main. Undo means closing or reverting the PR.

What's genuinely hard to undo is deletes, schema changes and publishes. So in v1, the gateway just blocks them. Blocking a dangerous operation is much easier to maintain than building an undo for it.

## Don't forget the old tokens

If your agents already had API tokens, assume those tokens are no longer secret. They could be sitting in configs, logs or chat history. Rotate them, keep the new ones only in your OS keychain where the gateway reads them, and revoke the old ones.

## Keep it dumb

The gateway stays maintainable as long as it stays simple. It logs requests as raw JSON and doesn't model every CMS endpoint, so API changes don't break it. It also fails closed: if the gateway isn't running, agents can't write. That's annoying for about a day, and then it's reassuring.

## The artifacts

Here's the design doc I wrote for this, plus the prompts I hand a coding agent to build the gateway and the MCP server. Adapt them to your own setup.

<details data-copy>
<summary><strong>Design doc: local v1 agent governance gateway</strong></summary>

**Goals**

- Log every non-read request an agent makes to the CMS, tied to the harness and session that made it.
- Keep real management tokens away from agents completely.
- Block destructive operations (deletes, schema changes, publishes) in v1.
- Make rollback a lookup: every log line points to the CMS entry version or the PR that undoes it.
- Work the same across every harness.

**Non-goals for v1**

- A custom rollback UI.
- Hosting the gateway as a shared service.
- Covering humans editing in the CMS web UI, or app code writing at runtime.

**Token handling**

- Real tokens live only in the OS keychain, read by the gateway at startup.
- Agents get a stand-in token, one per harness, that only the gateway accepts.
- Rotate any token an agent has seen before.

**Policy**

- **Allow and log:** creating and updating entries and assets.
- **Block:** deletes, content type and schema changes, publish and unpublish, bulk operations.
- **Fail closed:** no gateway, no writes.
- Blocked requests return an error naming the rule, so the agent reports it instead of retrying.

**What gets logged (local SQLite)**

- **Who:** harness, session ID (`X-Agent-Session` header), human operator.
- **What:** timestamp, method, path, stack, content type, entry UID, locale, raw request body.
- **Result:** status, new entry version, policy decision and rule.

**Build order**

1. Local logging gateway (FastAPI) with keychain token and SQLite log.
2. Policy layer that blocks destructive operations.
3. Rotate tokens and point every harness at the gateway.
4. PR-only agent workflow with branch protection.
5. MCP server pointed at the gateway.
6. Hooks for extra context, then more upstreams (project management, repos).

</details>

<details data-copy>
<summary><strong>Build prompt: the gateway</strong></summary>

```text
Build a local governance gateway in Python with FastAPI. It sits between coding agents and the Contentstack Management API, so every agent write is checked, logged and forwarded.

Requirements:

1. Proxy: listen on localhost:8787. Forward everything under /v3/ to the Contentstack Management API base URL (configurable, for other regions). Pass path, query and body through unchanged.

2. Tokens: agents send a stand-in token in the authorization header. Map each stand-in token to a harness name (claude-code, codex, cursor) in a local config file. Reject unknown tokens with 401. Read the real management token from the OS keychain with the keyring library, never from .env files. Swap in the real token before forwarding.

3. Policy: allow reads. Allow creating and updating entries and assets. Block with 403 and a JSON error naming the rule: any DELETE, any write to content types or global fields, publish and unpublish, and bulk operations. Keep the rules in one config file.

4. Logging: write every non-read request to a local SQLite file. Columns: timestamp, harness, X-Agent-Session header, operator, method, path, stack API key, content type UID, entry UID, locale, raw request body, response status, new entry version from the response, policy decision, rule name.

5. Fail closed: refuse to start if the keychain token is missing.

6. CLI: `gateway logs --since 1d` prints recent writes as a table.

7. Tests: pytest with a mocked upstream (respx), covering the token swap, each block rule, and the contents of a log row.

Keep it simple: don't model endpoints beyond what the policy needs. Include a README with setup steps, including how to rotate any tokens agents saw before.
```

</details>

<details data-copy>
<summary><strong>Build prompt: the MCP server</strong></summary>

```text
Build an MCP server in Python with the official MCP Python SDK (stdio transport). It gives coding agents a small set of Contentstack tools. It never calls Contentstack directly: every request goes to the local governance gateway.

Config (env vars):
- GATEWAY_URL, default http://localhost:8787
- AGENT_TOKEN, the stand-in token for this harness
- STACK_API_KEY, and an optional BRANCH

On startup, generate a session ID (UUID). Send it as X-Agent-Session on every request, with AGENT_TOKEN in the authorization header and the stack key in the api_key header.

Tools, each mapped to one Management API call through the gateway:
- list_content_types()
- get_content_type(uid)
- list_entries(content_type, query?, locale?, limit?)
- get_entry(content_type, uid, locale?)
- create_entry(content_type, fields, locale?)
- update_entry(content_type, uid, fields, locale?)
- list_assets(query?) and get_asset(uid)

Do not add delete, publish, schema or bulk tools.

Behavior:
- Tool descriptions say that writes are logged and destructive operations are blocked.
- Writes return the entry UID and the new version number.
- On a 403 from the gateway, return the rule name in the tool error and tell the agent to report it, not to retry another way.
- If the gateway is not running, return "Gateway not running: CMS writes are disabled."
- Set request timeouts and return readable errors.

Tests: pytest with a mocked gateway (respx), checking headers, paths, request bodies and 403 handling.

README: config snippets for Claude Code (.mcp.json) and Codex (config.toml), each with its own stand-in token.
```

</details>

## Wrapping up

You don't need to bet on one agent tool to govern all of them. Put the control where they all meet, which is the API, hold the only real key there, and let existing version history do the undo work.

Next I'll build the gateway itself and share what actually held up once real agents start hitting it.
