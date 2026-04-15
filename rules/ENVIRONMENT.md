# ENVIRONMENT.md - 你的環境基底 / Your Environment Baseline

_由 Reflector 自動維護。紀錄設備、帳號、工具類環境事實。_
_Auto-maintained by Reflector. Records device, account, and tool facts._
_更新方式：merge（同類別舊事實被新事實覆蓋），非 append-only。_

---

<!-- TODO: Fill in your actual environment details.
     This file gives the AI accurate context about your setup,
     so it doesn't have to guess or make wrong assumptions. -->

## 設備 / Devices

<!-- TODO: List your primary machines and their roles.
     Example:
     - MacBook Pro: work machine, main development environment
     - Mac mini: home machine, personal projects, always-on for remote access -->
- **[Device 1]:** [Role / description]
- **[Device 2]:** [Role / description]

## 帳號架構 / Account Architecture

<!-- TODO: Describe your account setup — especially if you have work/personal separation.
     Example: separate Claude Code accounts per machine, one for work one for personal. -->
- **[Tool] 帳號隔離:** [Description of how accounts are separated across machines]

## 工具與連線 / Tools & Connectivity

<!-- TODO: List your primary tools and how machines connect.
     Example: Cursor (VS Code-based IDE), Tailscale (VPN for cross-machine SSH) -->
- **主工作介面 / Primary Interface:** [Your IDE / editor setup]
- **遠端連線 / Remote Access:** [How you access other machines, if applicable]

## 工作流限制 / Workflow Constraints

<!-- TODO: Document any constraints the AI should know about.
     Example: "Don't suggest switching accounts on the same machine — use SSH instead"
              "Home machine is always on — safe to suggest remote operations" -->
- [Constraint 1]
- [Constraint 2]

## Git Repo 架構 / Git Repo Architecture

<!-- TODO: Document your repo setup.
     Example:
     - exocortex-personal (private): your production instance with personal data
     - Exocortex (public): open-core template, upstream for exocortex-personal
     Sync: git fetch template && git merge template/main (milestone-driven) -->
- **[repo-name]（本 repo）:** [Description — private/public, what it contains]
- **[other-repo]:** [Description]
- **Sync 機制:** [How repos stay in sync, if applicable]
