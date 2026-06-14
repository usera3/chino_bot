# Chino Bot v5

`v5` is the OpenClaw-based QQ fusion release of this project.

Compared with `v4`, this branch does not just tweak reply style. It packages the
actual local fusion layout:

- `openclaw/` as the chat brain, context owner, and QQ orchestration layer
- `bridge/openclaw_tool_bridge.py` as the Python bridge exposing `chino_bot`
  capabilities back into OpenClaw
- `core/openclaw_style.py` plus the updated Butler / plugin wiring on the
  `chino_bot` side
- `voice/qwen3-tts-apple-silicon/` with the current voice assets, scripts, and
  an exact model manifest for the `akari2` voice setup

This branch is a public-safe release. Live credentials, private runtime state,
and machine-specific absolute paths were removed or converted to examples.
Large Qwen TTS weight files are not committed because GitHub rejects them in a
normal Git branch; the exact upstream model source and checksums are included
instead.

## Layout

- `openclaw/`: OpenClaw source, QQ plugins, skills, and companion assets
- `bridge/`: the Python bridge used by the `chinobot-bridge` OpenClaw plugin
- `core/`, `plugins/`, `tools/`: the original `chino_bot` runtime with the
  local fusion changes applied
- `voice/qwen3-tts-apple-silicon/`: TTS runtime scripts, voice reference audio,
  sample outputs, and model download metadata
- `config/openclaw-config.v5.example.json`: sanitized OpenClaw config template
- `config/napcat-onebot11.windows.example.json`: reverse WebSocket sample for
  NapCat on Windows

## What Changed In v5

- OpenClaw is now the intended top-level conversation brain.
- `chino_bot` remains the QQ tool / execution layer and is bridged back into
  OpenClaw.
- QQ natural-chat and bridge defaults were rewritten so the repo can be moved to
  a different machine without editing source code first.
- Voice assets are included, while model weights are restored through
  `voice/qwen3-tts-apple-silicon/download-model.sh`.

See [V5_RELEASE_NOTES.md](V5_RELEASE_NOTES.md) and
[docs/openclaw-zhinai-融合设计.md](docs/openclaw-zhinai-融合设计.md).

## Quick Start

### 1. Python side

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. OpenClaw side

```bash
cd openclaw
corepack enable
corepack prepare pnpm@10.23.0 --activate
pnpm install
pnpm build
```

`openclaw/dist/` is intentionally not committed in this public branch. Build it
locally before running the gateway.

### 3. Voice model restore

```bash
cd voice/qwen3-tts-apple-silicon
./download-model.sh
```

This fetches `mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit` into the repo layout
used by the bridge and verifies the two large `.safetensors` files against the
recorded SHA-256 values.

### 4. Environment

```bash
cp .env.example .env
```

Fill only the keys you use. Important values for the fusion layout:

```dotenv
HOST=127.0.0.1
PORT=8080
BOT_QQ=your_bot_qq_number
SUPERUSERS=["your_admin_qq_number"]
CHINO_ADMIN_USERS=your_admin_qq_number
CHINO_PROJECT_ROOT=/absolute/path/to/chino_bot
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENCLAW_GATEWAY_TOKEN=
```

### 5. OpenClaw config

Copy [config/openclaw-config.v5.example.json](config/openclaw-config.v5.example.json)
to `~/.openclaw/openclaw.json` and replace the placeholder paths and QQ account
values.

### 6. Run

Start the Python / NoneBot side when needed:

```bash
python bot.py
```

Start OpenClaw from the `openclaw/` directory:

```bash
cd openclaw
node openclaw.mjs gateway --verbose
```

Then point NapCat reverse WebSocket to the address configured in the OpenClaw
QQ channel config.

## Notes

- `v4` remains the cleaner standalone `chino_bot` line.
- `v5` is intentionally closer to a real handoff package than to a minimal
  library release.
- Private group-specific social state was removed from the public config
  templates, but the QQ fusion code path itself is preserved.
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
