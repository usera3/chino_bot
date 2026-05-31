# Chino Bot

Chino Bot is an open-source agentic QQ assistant built with LangChain and
NoneBot2. It explores how a chat-native assistant can combine long-term
memory, tool calling, workflow automation, and QQ group interactions in one
maintainable Python codebase.

The project is maintained by [usera3](https://github.com/usera3). The current
public release line is `v4`.

## Why This Project Exists

Most chat bots stop at command routing. Chino Bot is designed as a practical
agent system:

- It keeps user-specific long-term memory with a dual-store design.
- It can choose tools from natural-language requests instead of fixed commands.
- It can orchestrate multi-step workflows such as reminders, document tasks,
  search, screenshots, and email.
- It exposes a modular tool layer so new capabilities can be added without
  rewriting the bot runtime.
- It keeps QQ and OneBot/NapCat integration separate from the agent core.

This makes the repository useful for maintainers who want to study or extend
real chat-agent infrastructure rather than a toy prompt wrapper.

## Project Status

Chino Bot is an active experimental open-source project. The v4 branch contains
the latest agent architecture, tool set, documentation, and test scaffolding.

Current strengths:

- LangChain-based agent runtime
- NoneBot2 and OneBot v11 integration
- 40+ tool implementations or prototypes
- Dual vector memory architecture
- Workflow planning and scheduled execution
- Code-analysis, document, web, image, mail, file, and QQ interaction tools
- Tests for the planning, code, command, and project-management layers

Known limitations:

- Some QQ features depend on NapCat/OneBot behavior and account permissions.
- Several provider-backed tools require user-supplied API keys.
- The project is not yet packaged as a one-command production deployment.
- Some historical Chinese notes are development logs rather than polished docs.

## Architecture

```text
QQ / OneBot / NapCat
        |
NoneBot2 plugins
        |
Butler agent core
        |
Tool registry and workflow executor
        |
Memory stores, document tools, web tools, code tools, system tools
```

Important directories:

- `core/` - agent runtime, memory stores, workflow executor, security helpers
- `tools/` - LangChain-compatible tools and utility integrations
- `plugins/` - NoneBot2 plugin entrypoints for QQ events
- `models/` - workflow and tool data models
- `tests/` - focused tests for core maintainability
- `docs/` - design notes, roadmap, and historical implementation notes

## Feature Overview

### Agent and Memory

- LangChain-based Butler agent
- Dual vector memory stores for conversation and knowledge retrieval
- Per-user memory isolation
- Context-aware tool selection
- Conversation summarization and retrieval experiments

### Workflow Automation

- Scheduled tasks
- Multi-step workflow execution
- Error handling and retry scaffolding
- Planning tools for code and project tasks

### Tooling

- Web search and link parsing
- HTML rendering and webpage screenshots
- Word, PDF, and Excel document helpers
- File transfer and file-management helpers
- Code reading, search, analysis, modification preview, and tests
- System diagnostics and log inspection
- QQ profile, group, poke, like, and group-file interactions

### Safety Boundaries

Chino Bot includes tools that can write files, run limited commands, and create
mock dialogue artifacts for testing. These features are guarded by explicit
security controls and should only be enabled for trusted administrators.

The mock-message utilities are intended for local testing, UI previews, and
development demos. They must not be used to deceive users, impersonate real
people, bypass platform rules, or publish misleading screenshots.

See [SECURITY.md](SECURITY.md) for the project security policy.

## Quick Start

### Requirements

- Python 3.10+
- A QQ account for bot testing
- NapCat or another OneBot v11-compatible adapter
- One supported LLM provider API key

### Install

```bash
git clone https://github.com/usera3/chino_bot.git
cd chino_bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
git clone https://github.com/usera3/chino_bot.git
cd chino_bot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
```

Edit `.env` and provide only the keys and account values you actually use.
Never commit `.env`, tokens, QQ account credentials, or private logs.

Important settings:

```dotenv
HOST=127.0.0.1
PORT=8080
BOT_QQ=your_bot_qq_number
SUPERUSERS=["your_admin_qq_number"]
CHINO_ADMIN_USERS=your_admin_qq_number
CHINO_PROJECT_ROOT=/absolute/path/to/chino_bot
```

Use one LLM provider:

```dotenv
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
```

or:

```dotenv
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

### Run

```bash
python bot.py
```

For QQ integration, configure the OneBot reverse WebSocket address in NapCat to
match the host and port from `.env`.

## Development

Run tests:

```bash
python -m pytest tests
```

Run quick smoke checks:

```bash
python quick_test_code_tools.py
python quick_test_system_tools.py
```

Format code:

```bash
black core tools plugins tests
```

## Maintainer Priorities

The project is being prepared for broader open-source collaboration. Current
maintenance priorities are:

- Replace environment-specific paths with configuration-driven defaults.
- Improve tests around file, command, workflow, and QQ tools.
- Reduce provider-specific coupling in the agent layer.
- Move historical notes into clearer docs.
- Add safer defaults for write and command execution tools.
- Improve Windows and Linux deployment docs.

## Contributing

Contributions are welcome. Good first areas include:

- Provider configuration cleanup
- Tests for individual tools
- Documentation translation and simplification
- Safer command and file-operation policies
- New LangChain tool adapters with clear tests

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## Responsible Use

This project is for personal automation, research, and open-source agent
development. Users are responsible for complying with QQ, NapCat, API provider,
and local laws or platform rules. Do not use this project for spam, harassment,
account abuse, impersonation, credential collection, or evading platform
controls.

## License

Chino Bot is released under the MIT License. See [LICENSE](LICENSE).

## Acknowledgements

Chino Bot builds on:

- [LangChain](https://github.com/langchain-ai/langchain)
- [NoneBot2](https://github.com/nonebot/nonebot2)
- [NapCat](https://github.com/NapNeko/NapCatQQ)
- [ChromaDB](https://github.com/chroma-core/chroma)
