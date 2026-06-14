# Model Manifest

The public `v5` branch does not commit the two large Qwen3-TTS weight files
because GitHub rejects them in a normal Git branch.

Use `download-model.sh` to fetch the exact checkpoint into this directory:

- upstream repo: `mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit`
- local target:
  `voice/qwen3-tts-apple-silicon/models/Qwen3-TTS-12Hz-1.7B-Base-8bit`

Expected large files:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `model.safetensors` | `2417320525` | `b965c581ccf6aa852a4124feeb7a8a111542ee7b213139368b4cc7ba7fd4728b` |
| `speech_tokenizer/model.safetensors` | `682293092` | `836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258` |

All smaller config / tokenizer files already live in Git.
