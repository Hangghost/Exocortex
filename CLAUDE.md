# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Session Start — MANDATORY

**DO NOT respond to any user message until you have read all of the following files in order:**

1. `rules/SOUL.md`
2. `rules/USER.md`
3. `rules/ENVIRONMENT.md`
4. `rules/WORKSPACE.md`
5. `rules/COMMUNICATION.md`
6. `rules/skills/INDEX.md`

These files are defined in `rules/CORE.md`. Reading CORE.md alone is not sufficient — you must read each file listed above. Only after completing all 6 reads should you proceed.

## What This Repo Is

A reference implementation of a three-layer context infrastructure for AI agents. It is not a traditional software project — there is no build system, no test suite, and no compilation step. The "product" is the structured knowledge system itself.

## Periodic Jobs

Scripts require environment variables from `.env` (copy from `.env.example`):

```bash
# Run v1 capture manually (date argument optional, defaults to today)
python -m infra.periodic_jobs.ai_heartbeat.src.v1.capture 2024-01-15

# Run v1 observer manually
python -m infra.periodic_jobs.ai_heartbeat.src.v1.observe 2024-01-15

# Run reflector manually
python infra/periodic_jobs/ai_heartbeat/src/v0/reflector.py
```

Cron schedule reference: `infra/periodic_jobs/CRONTAB.md`

Dependencies:
```bash
uv sync --all-groups
```

Dependency groups are defined in `pyproject.toml`. Each skill with scripts has its own group. To add a skill's dependencies, add a new group to `pyproject.toml` and run `uv sync --all-groups`.
