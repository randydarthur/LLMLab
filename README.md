# LLMLab
Cross-platform set of utilities for managing local LLMs and routing agent traffic to local LLMs

LLMLab is an cross‑platform local LLM orchestration system.
It provides a unified environment for managing models, running a multi‑backend
router, benchmarking agents, and interacting with local LLMs through a curses‑based TUI.

LLMLab is designed for local LLM experimenters who want to deploy and maintain a local LLM
infrastructure across macOS, Linux, and Windows and who do not want to get into the details
of local LLM model lifecycle management.

---

## Features

### Cross-Platform Local LLM Manager
- Cross‑platform service management (systemd, launchd, Windows services)
- Model directory normalization and integrity checks
- Automated model pulls and catalog synchronization
- Tools for import auditing, sanity checks, and environment validation

### Multi‑Backend LLM Router
Located under `router/`, the router provides:
- Backend adapters for Ollama, OpenAI, Anthropic, DeepSeek, LM Studio
- YAML‑driven routing rules and task classification
- Configurable backend health checks
- A REPL client for interactive routing
- A preprocessor for merging, validating, and resolving routing configs

### Curses‑Based TUI
The TUI (`lab/ollama_lab/tui/`) includes:
- Model catalog browser
- Modal dialogs and widgets
- Terminal‑safe rendering layer

### Tools & Scripts
- Import auditing
- Scrapers for model catalogs
- Environment sanity checks
- Uninstall scripts for Ollama daemons
- llmfit integration helpers
- Cross‑platform terminal launcher

FUTURE CAPABILITIES

### Modular Agents
Under `agents/`, LLMLab will include a:
- Benchmark agent
- Evaluation agent
- Router assistant agent
Each agent has isolated configs, memory, prompts, tests, and tools.

---

## Repository Structure

...
LLMLab/
├── agents/          # Modular agents with configs, memory, prompts, tools
├── lab/             # Core LLMLab manager, TUI, services, utilities
├── router/          # Multi-backend routing engine
├── scripts/         # Helper scripts and utilities
├── services/        # Service definitions (future expansion)
├── tools/           # Shared tools
├── vscode/          # Editor configuration (extensions, settings, snippets)
├── notes/           # Operator notes and design docs
└── repos/           # External repos (placeholder)
...
