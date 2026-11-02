# Relay Documentation 📚

Welcome to the documentation for **Relay** — an environment-agnostic differential file synchronization engine combining the speed of `rsync` with the content-addressable model of `git`.

---

## 🧭 Documentation Navigation

| Document | Description |
| :--- | :--- |
| **[Architecture & Design](architecture.md)** | System layers, data flow, SQLite state ledger (`.relay.db`), and function-based SOLID architecture. |
| **[Diff Engine & Scenarios](diff-engine.md)** | Content-addressable diff logic, the 7 scenario classifications, and rollback / safety matrix. |
| **[Transport Adapters](transports.md)** | Transport abstraction contract, low-level operations matrix (Local vs. GCS vs. SSH), and zero-egress transfers. |
| **[Testing & Sandbox Guide](sandbox.md)** | Reproducible 5-scenario test harness, step-by-step CLI verification walkthrough, and developer QA workflows. |
| **[Project Context & Roadmap](../CONTEXT.md)** | High-level project state, completed milestones, and immediate development roadmap. |

---

## ⚡ Quick Start

```bash
# 1. Reset the test sandbox environment
make sandbox

# 2. Preview planned changes without modifying any files (dry-run)
uv run relay sync sandbox/source sandbox/dest --dry-run

# 3. Synchronize changes live
uv run relay sync sandbox/source sandbox/dest

# 4. Check status of any endpoint
uv run relay status sandbox/source
```
