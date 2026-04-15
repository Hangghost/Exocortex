# Exocortex

**A three-layer context infrastructure for AI agents — your AI second brain that actually knows you.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Stars](https://img.shields.io/github/stars/Hangghost/Exocortex?style=social)](https://github.com/Hangghost/Exocortex/stargazers)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/Hangghost/Exocortex/pulls)
&nbsp;&nbsp;[🇹🇼 中文版](README.zh-TW.md)

Exocortex is an open-core template for building a personalized AI agent system. It gives your AI (Claude, Cursor, etc.) persistent memory, structured context, and a self-evolving knowledge system — without locking you into any specific platform or vector database.

---

## Why This Exists

Every AI conversation starts from zero. The AI doesn't know your projects, your decision-making style, your past mistakes, or your ongoing work. You re-explain yourself endlessly.

Exocortex solves this by giving the AI a **structured, file-based memory system** that persists across sessions, evolves over time, and stays fully under your control.

---

## Who Is This For

**This is for you if:**
- You use AI tools daily (Claude, Cursor, ChatGPT) and re-explain your context every session
- You want your AI to know your projects, preferences, and decision-making style — persistently
- You care about **owning** your AI memory, not delegating it to a black box
- You're comfortable with Markdown files and basic git

**This is not** a plug-and-play app. It's a structured system you build once and own permanently. The more context you invest, the more capable your AI becomes.

---

## What You Get

**An AI that remembers everything about you**
Your active projects, ongoing work, and past decisions — without re-explaining every session. Open a conversation and your AI already knows where you left off.

**An AI that thinks like you**
Store your personal decision principles, communication style, and work philosophy. Your AI applies them automatically — giving advice that fits your mental model, not generic best practices.

**A memory that grows smarter over time**
The Observer-Reflector pipeline runs automatically: daily scans of your work logs extract patterns; weekly reflections distill them into durable insights. The longer you use the system, the more capable your AI becomes.

**Full ownership of your AI's knowledge**
Every fact your AI knows lives in plain Markdown files you control. Audit it, correct it, delete it. No black boxes, no vendor lock-in.

**One memory, any AI tool**
The same context layer works with Claude Code, Cursor, or any LLM that reads files. Switch tools without losing your AI's accumulated knowledge of you.

---

## The Three-Layer Memory Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  L3 — Rules Layer (rules/)                                       │
│  Permanent truths. Read every session. Slow to change.           │
│  → SOUL.md, USER.md, WORKSPACE.md, ARCHITECTURE.md, axioms/     │
├─────────────────────────────────────────────────────────────────┤
│  L1/L2 — Observations Layer (memory/OBSERVATIONS.md)            │
│  Medium-term signals. Distilled weekly by Reflector.             │
│  → Insights that survived a week of scrutiny                     │
├─────────────────────────────────────────────────────────────────┤
│  L0 — Raw Signals Layer (contexts/)                              │
│  Short-term records. Scanned daily by Observer.                  │
│  → Work logs, survey sessions, reflections, blog drafts          │
└─────────────────────────────────────────────────────────────────┘
```

**The flow:** Raw signals (L0) → Observer extracts observations (L1/L2) → Reflector promotes durable insights to rules (L3).

---

## System Workflow

```
Daily (19:00)   → AI Heartbeat Capture: collect signals from Calendar + Gmail
Daily (20:00)   → AI Heartbeat Observer: scan contexts/, write to OBSERVATIONS.md
Weekly (Sun)    → AI Heartbeat Reflector: distill observations, promote to rules/
```

You also interact with the system through structured slash commands:
- `/ctx:content` — commit today's work logs, notes, drafts
- `/ctx:project` — create, load, update, archive projects
- `/ctx:arch` — propose and track architecture changes (via OpenSpec workflow)
- `/opsx:propose|apply|archive` — OpenSpec workflow for structured changes

---

## Quick Start

### 1. Fork this repo as your personal instance

```bash
# Create your personal fork on GitHub, then:
git clone git@github.com:<your-username>/Exocortex.git exocortex-personal
cd exocortex-personal

# Add this public repo as upstream for future architecture updates
git remote add template git@github.com:Hangghost/Exocortex.git
```

### 2. Personalize the core files

Fill in the TODO fields in these files:

```
rules/USER.md         ← Your name, background, interests, communication style
rules/ENVIRONMENT.md  ← Your devices, accounts, tools
rules/SOUL.md         ← Your AI's personality and principles (optional)
rules/axioms/INDEX.md ← Your personal decision principles
```

### 3. Configure periodic jobs

```bash
# Copy environment template
cp .env.example .env
# Fill in your API keys (Anthropic, Google OAuth, etc.)

# Install dependencies
uv sync --all-groups

# Test the capture pipeline manually
python -m infra.periodic_jobs.ai_heartbeat.src.v1.capture
```

Set up cron jobs following `infra/periodic_jobs/CRONTAB.md`.

### 4. Install Claude Code commands

If you use Claude Code, the slash commands in `.claude/commands/` are automatically available when you open this repo.

---

## Repository Structure

```
Exocortex/
├── rules/                    # L3: Permanent rules layer
│   ├── SOUL.md               # AI identity and principles
│   ├── USER.md               # Your profile (personalize this)
│   ├── ENVIRONMENT.md        # Your devices and tools
│   ├── WORKSPACE.md          # Directory routing guide
│   ├── ARCHITECTURE.md       # System architecture reference
│   ├── CORE.md               # Shared agent protocol
│   ├── COMMUNICATION.md      # Interaction style guide
│   ├── axioms/               # Personal decision principles
│   └── skills/               # Reusable AI agent capabilities
├── contexts/                 # L0: Raw signals (your daily records)
│   ├── work_logs/            # Task execution and progress
│   ├── survey_sessions/      # Research and investigations
│   ├── thought_review/       # Reflections and retrospectives
│   └── blog/                 # Writing drafts
├── memory/
│   └── OBSERVATIONS.md       # L1/L2: Observer output (auto-written)
├── inbox/                    # Quick capture
│   ├── todos.md
│   ├── ideas.md
│   └── reading_list.md
├── registry/                 # Cross-system routing index
│   ├── dev.md                # Active repos and dev context
│   ├── career.md             # Career and skills
│   ├── life.md               # Goals and learning
│   ├── knowledge.md          # KnowledgeWiki pointer
│   └── library.md            # Personal library pointer
├── projects/                 # Active project contexts
│   └── INDEX.md              # Project registry
├── library/                  # Personal document index cards
├── openspec/                 # Architecture change workflow
│   ├── specs/                # Committed capability specs
│   └── changes/              # In-progress and archived changes
├── infra/
│   ├── periodic_jobs/
│   │   └── ai_heartbeat/     # Observer/Reflector/Capture pipeline
│   └── tools/                # Utility scripts
└── .claude/commands/         # Claude Code slash commands
```

---

## Design Philosophy

### Why files, not a database?

Markdown files on git are:
- **Transparent** — you can read, edit, and audit everything
- **Portable** — works with any AI tool, any editor, any platform
- **Version-controlled** — full history of how your second brain evolved
- **AI-friendly** — LLMs are heavily trained on Markdown; structured headings = structured thinking

### Why the three-layer design?

The layers map to cognitive science principles:
- **L3 (Rules)** → Long-term memory: stable facts about who you are
- **L1/L2 (Observations)** → Semantic memory: patterns extracted from experience
- **L0 (Contexts)** → Episodic memory: specific events and records

The Observer-Reflector pipeline is the consolidation mechanism — like sleep for human memory.

### Why not just use ChatGPT memory / built-in AI memory?

Built-in memory is a black box. You can't audit what's stored, can't fix incorrect memories, can't control what gets promoted. Exocortex gives you **full ownership** of your AI's memory.

---

## Creating Your Personal Instance

This repo is the **template** (public, upstream). Your personal instance is a **fork** (private, downstream).

```
Exocortex (this repo, public) ←── template remote
        │
        │  git fetch template && git merge template/main
        │  (sync architecture updates when milestones land)
        ↓
exocortex-personal (your fork, private)
   └── your personal data lives here, never pushed to public
```

Your personal files (`rules/USER.md`, `rules/ENVIRONMENT.md`, `contexts/`, `memory/`, `registry/`, `projects/`, `library/`, `inbox/`) stay in your private fork and never touch the public repo.

When this template gets architectural updates (new capabilities, improved pipeline, better commands), you pull them in with:

```bash
git fetch template
git merge template/main
```

---

## Acknowledgments

Heavily inspired by [grapeot/context-infrastructure](https://github.com/grapeot/context-infrastructure) — a pioneering exploration of structured AI context as a personal memory system.

---

## Contributing

Architecture improvements, new skills, and pipeline enhancements are welcome. Personal data, private integrations, and domain-specific content belong in your personal fork.

Before contributing, read `rules/ARCHITECTURE.md` for the system design principles.

---

## License

MIT
