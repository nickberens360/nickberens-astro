---
title: "Teaching an Embedded AI Agent What It Can Do"
description: "A page-scoped tool registry and context snapshot pattern for adding an AI agent to an existing Vue/Nuxt app without rewriting it."
pubDate: 2026-11-15
tags: ["ai", "agents", "vue", "nuxt", "architecture"]
author: "Nick Berens"
backgroundColor: "#eef6ff"
theme: "light"
---

I've spent over a year building an app that started as an exploration task and grew into something much bigger. Most of it was written with AI agents, and now I want to put an AI agent *inside* it, one that helps users get real tasks and workflows done.

The first hard question wasn't which model to use or how to write the prompts. It was this: **how does the agent know what it can actually do on the page the user is looking at?**

This post covers the pattern I landed on. It's a page-scoped tool registry paired with a live context snapshot, and it's designed to sit on top of an imperfect codebase instead of requiring a rewrite.

## The temptation to rewrite

When a codebase grows organically, especially one built quickly with AI help, the itch to start over is real. I felt it too. But a year of work carries a lot of hidden fixes and edge cases, and throwing that away to bolt on an agent is a bad trade.

The better move is to treat the agent layer as an **adapter**. Agent-facing definitions stay clean even when the code underneath is messy. You clean up the code gradually, one workflow at a time, as you expose it to the agent.

## The four pieces

The architecture comes down to four parts.

### 1. Tool definitions

Each capability the agent can use is a small object with:

- a **name**, written as a verb plus an object (`updateAddress`, `searchClaims`)
- a **description** the model reads to decide when to use the tool
- an **input schema**, as JSON Schema
- a **handler** that calls your existing store actions, services, or APIs, never the DOM
- a **confirmation flag** for destructive or committing actions, so the agent asks before it acts

### 2. A central registry

This is a Pinia store with a deliberately tiny API: `register`, `unregister`, and `list`. It holds whatever tools are active right now. Global tools like navigation and search are registered once at the app level, while page tools come and go.

### 3. A page composable

Pages call `useAgentTools()` with the tools they offer. The composable registers them on mount and removes them on unmount, so the agent's tool list always matches the screen. Pages only declare what they offer, and they never talk to the agent directly.

### 4. One execution path

Every tool call goes through a single function. It looks the tool up in the registry, validates the arguments against the schema, asks the user to confirm if the tool needs it, runs the handler, and returns a short result the model can use. Because every call passes through it, it's also the natural place for logging, permission checks, and auditing.

The key idea: **the registry is the source of truth.** The agent never guesses what's possible, and you never maintain a hard-coded tool list that drifts out of sync with the UI.

## Descriptions do the heavy lifting

Models choose tools mostly by reading their descriptions, so this is where agents tend to succeed or fail.

- **Say when to use the tool, not just what it does.** "Updates an address" is weak. "Use when the user wants to change the mailing address on the record currently open" is much better.
- **Say when *not* to use it**, especially when two tools are similar.
- **Describe every parameter**, including its format and where the value comes from. For example: "taken from page context, never ask the user."
- **Keep the active tool count low.** Accuracy drops once a page has more than about 15 to 20 tools, and page scoping helps keep that number down.

## The page snapshot: the agent's eyes

Tools tell the agent what it *can* do. The snapshot tells it what the user is *looking at*.

Each page registers a small context provider through the same composable, and the registry merges them into one snapshot that's sent fresh every turn. It includes the current route, the main open record (its ID plus a few key fields), selections and filters, and form state.

Keep it lean. Send summaries rather than store dumps, and aim for a few hundred tokens. Use readable labels instead of internal codes. Never cache the snapshot, because users click around between messages.

The payoff is that users can say "change this one" or "do the same for the next record," and the agent knows exactly what they mean.

<details data-copy>
<summary><strong>Full design doc: registry, execution layer, and snapshot rules</strong></summary>

**Guiding principles**

- Adapter, not rewrite: the registry wraps existing logic.
- The registry is the source of truth for what is possible.
- Page-scoped: register on mount, unregister on unmount.
- Refactor incrementally, only behind workflows you wrap.

**Registry API**

- `register(tools, scope)`
- `unregister(scope)`
- `list()` returns all currently active tools
- Context providers are held the same way.

**Composable:** `useAgentTools({ tools, context })`. Keep tool definitions in one file per feature (for example `agent/tools/policy.ts`) and import them into pages.

**Execution flow**

1. Look up the tool and reject it if it isn't active.
2. Validate the arguments against the schema.
3. If `requiresConfirmation` is set, pause and ask the user.
4. Run the handler.
5. Return a short, model-friendly result.

**Snapshot contents:** route and page name, the open record's ID and key fields, selections and filters, and form state with errors. Target a few hundred tokens and rebuild it every turn.

</details>

## Rolling it out without a rewrite

1. **Audit.** Have an agent map every route, what each page does, and where its logic lives. That map doubles as your list of candidate tools.
2. **Build the foundation**: the registry, the composable, the execution layer, and the snapshot merger.
3. **Pilot** three to five high-value workflows.
4. **Refactor along the path**, cleaning up only the code behind each wrapped workflow.
5. **Expand** feature by feature, keeping an eye on tool counts and description quality.

The audit is the step I'd skip if I weren't careful, and it's the one that makes everything else easier. Here's the prompt I'm using.

<details data-copy>
<summary><strong>Codebase audit prompt</strong></summary>

```text
You are auditing a Vue/Nuxt application to prepare it for an embedded AI agent that will call app functionality as tools. Do not change any code. Read only, then report.

Goal: build a capability map showing every user-facing feature, what it does, and where its logic actually lives.

Steps:
1. List every route/page (from the pages directory and any router config). For each, give the path, page name, and a one-line purpose.
2. For each page, list the user actions available (create, edit, delete, search, filter, submit, navigate, export, and so on).
3. For each action, trace where the real logic lives: Pinia store action, composable, service/API module, or inline in a component. Give file paths and function names.
4. Note the data each page depends on: main record type, key fields, selections, filters, and form state.
5. Flag problems: duplicated logic, business logic inside components, direct API calls from components, dead code, unclear naming, and inconsistent patterns between features.
6. Mark risky actions: anything destructive, committing, financial, or permission-gated.

Output:
- A table per page with columns: Action | Logic location (file + function) | Logic type (store/composable/service/component) | Inputs | Risky (yes/no) | Tool-ready (yes / needs extraction / unclear).
- A shared-logic section listing stores, composables, and services used across multiple pages.
- A problems list, ordered by how much each would hurt wrapping actions as agent tools.
- A shortlist of 5 to 10 candidate workflows for the first agent tools, chosen for user value and how cleanly their logic is already isolated.

Rules:
- Cite a file path for every claim. If you are unsure where something lives, write "unclear" rather than guessing.
- Do not propose a rewrite. Recommendations must be incremental and scoped to individual workflows.
```

</details>

## Wrapping up

The question "how does the agent know what it can do?" turns out to have a clean answer: let the UI tell it. Pages declare their tools and context, the registry keeps the current picture, and one execution path keeps everything safe and observable.

Best of all, you don't need a pristine codebase to start. You need an honest audit, a thin adapter layer, and the patience to clean up one workflow at a time.

I'll follow up once the pilot workflows are live and share what actually held up in practice.
