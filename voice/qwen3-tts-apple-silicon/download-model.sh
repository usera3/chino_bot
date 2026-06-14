#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_DIR="${ROOT_DIR}/models/Qwen3-TTS-12Hz-1.7B-Base-8bit"
HF_REPO="${HF_REPO:-mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit}"

EXPECTED_MAIN_SHA="b965c581ccf6aa852a4124feeb7a8a111542ee7b213139368b4cc7ba7fd4728b"
EXPECTED_SPEECH_SHA="836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258"

if ! command -v huggingface-cli >/dev/null 2>&1; then
  echo "huggingface-cli not found."
  echo "Install it with: python3 -m pip install huggingface_hub"
  exit 1
fi

mkdir -p "${MODEL_DIR}"

echo "Downloading ${HF_REPO} into ${MODEL_DIR}"
huggingface-cli download \
  "${HF_REPO}" \
  --local-dir "${MODEL_DIR}" \
  --local-dir-use-symlinks False

main_sha="$(shasum -a 256 "${MODEL_DIR}/model.safetensors" | awk '{print $1}')"
speech_sha="$(shasum -a 256 "${MODEL_DIR}/speech_tokenizer/model.safetensors" | awk '{print $1}')"

if [[ "${main_sha}" != "${EXPECTED_MAIN_SHA}" ]]; then
  echo "Main model checksum mismatch: ${main_sha}"
  exit 1
fi

if [[ "${speech_sha}" != "${EXPECTED_SPEECH_SHA}" ]]; then
  echo "Speech tokenizer checksum mismatch: ${speech_sha}"
  exit 1
fi

echo "Model download verified."
