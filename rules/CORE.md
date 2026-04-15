# CORE.md - Shared Agent Protocol

This file is the single source of truth for all shared agent behaviors. Read it at the start of every session before anything else.

## Session Start Protocol

Before doing anything else, read these files in order:

1. `rules/SOUL.md` — who you are
2. `rules/USER.md` — who you're helping
3. `rules/ENVIRONMENT.md` — your devices, accounts, and tool setup
4. `rules/WORKSPACE.md` — file routing index (check here before searching)
5. `rules/COMMUNICATION.md` — how to think and write
6. `rules/skills/INDEX.md` — system skills (reusable workflows, best practices, tool guides); complement with agent global skills (`~/.claude/skills/`) and agent project skills (`.claude/skills/`) to form the complete capability map for this session

**For cross-system tasks** (e.g., "update my resume", "continue project X", "plan learning"): after reading the above, also read the relevant domain file from `registry/` — `registry/career.md`, `registry/dev.md`, `registry/life.md`, or `registry/knowledge.md` — to find the right information sources before proceeding.

**To understand current progress**: read `projects/INDEX.md` for an overview of active projects. Use `/ctx:project load <name>` to bring a specific project's full context (goals, status, next steps, decisions, materials) into the session. Use this when the user asks to "continue" something or when you need to know what's active right now.

## File Routing

**Always check `rules/WORKSPACE.md` before globbing or grepping.** It maps content categories to directories. If you find a new directory not in WORKSPACE.md, add it.

## Skills System

When asked "how to do X", check skills before reaching for system tools:

1. Quick-reference table in `AGENTS.md`
2. `rules/skills/INDEX.md`
3. System tools

## Memory System

Three-layer architecture:

- **L3 (Global constraints)**: Everything in `rules/` — loaded passively each session
- **L1/L2 (Dynamic memory)**: `memory/OBSERVATIONS.md` — pull actively when you need past context
- **Auto-accumulation**: `infra/periodic_jobs/ai_heartbeat/src/v0/observer.py` (daily) and `reflector.py` (weekly)

Observation priority in OBSERVATIONS.md: 🔴 High (principles), 🟡 Medium (active projects), 🟢 Low (daily tasks).

## Sub-agent Model Routing

Configured in `~/.config/opencode/oh-my-opencode.json`:

| Task type | Model | Category |
|---|---|---|
| Creative, brainstorm | Gemini 2.5 Pro | `artistry` |
| Execution, research, code | Sonnet 4.6 | `deep` / `unspecified-high` |
| Lightweight tasks | Haiku 4.5 | `quick` |
| Hard logic/architecture | Opus 4.6 | `ultrabrain` |

For creative work, default to spawning a Gemini (`artistry`) subagent in background in parallel with your own thinking.

## If Running as Opus

Context window is precious. Your two jobs: (1) **design** — decompose problems, plan, assign subagent tasks; (2) **write and QA** — final text and result verification are yours, never delegated. Research, scripts, data processing → delegate. Writing and quality → never delegate. Default to `run_in_background=true` when designing task splits.

## Safety

- Don't exfiltrate private data.
- Don't run destructive commands without asking.
- When in doubt, ask.
