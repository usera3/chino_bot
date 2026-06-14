# V5 Release Notes

## Included

- OpenClaw QQ fusion source under `openclaw/`
- Local Python bridge under `bridge/`
- `chino_bot` runtime changes for OpenClaw-style QQ replies
- Voice reference clips, prompt text, and sample outputs under
  `voice/qwen3-tts-apple-silicon/`
- Qwen3-TTS model manifest and download script for the exact
  `Qwen3-TTS-12Hz-1.7B-Base-8bit` checkpoint
- Sanitized OpenClaw and NapCat config templates

## Deliberately Removed Or Replaced

- Live `.env` values
- Gateway tokens, provider keys, mail credentials, and private logs
- Current machine absolute paths in runtime defaults
- Public branch copies of the large TTS `.safetensors` files
- Private group-specific OpenClaw config entries
- Prebuilt `openclaw/dist/` artifacts that had environment-specific content

## Expected Setup Flow

1. Install Python dependencies in the repo root.
2. Install and build OpenClaw inside `openclaw/`.
3. Download the Qwen3-TTS model weights with
   `voice/qwen3-tts-apple-silicon/download-model.sh`.
4. Copy `.env.example` to `.env`.
5. Copy `config/openclaw-config.v5.example.json` to `~/.openclaw/openclaw.json`
   and edit the placeholder paths.
6. Connect NapCat to the OpenClaw QQ reverse WebSocket endpoint.
