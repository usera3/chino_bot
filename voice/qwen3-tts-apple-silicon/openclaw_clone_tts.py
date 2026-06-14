#!/usr/bin/env python3
import argparse
import os
import sys
import warnings
from pathlib import Path

os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

try:
    from mlx_audio.tts.generate import generate_audio
    from mlx_audio.tts.utils import load_model
except ImportError as exc:
    raise SystemExit(f"mlx_audio not available: {exc}") from exc


def get_smart_path(path_str: str) -> Path:
    base = Path(path_str).expanduser().resolve()
    snapshots_dir = base / "snapshots"
    if snapshots_dir.is_dir():
        subfolders = sorted([entry for entry in snapshots_dir.iterdir() if entry.is_dir()])
        if subfolders:
            return subfolders[0]
    return base


def read_saved_voice(repo_root: Path, voice_name: str) -> tuple[Path, str]:
    wav_path = repo_root / "voices" / f"{voice_name}.wav"
    txt_path = repo_root / "voices" / f"{voice_name}.txt"
    if not wav_path.is_file():
        raise SystemExit(f"saved voice wav not found: {wav_path}")
    if not txt_path.is_file():
        raise SystemExit(f"saved voice transcript not found: {txt_path}")
    ref_text = txt_path.read_text(encoding="utf-8").strip()
    if not ref_text:
        raise SystemExit(f"saved voice transcript is empty: {txt_path}")
    return wav_path, ref_text


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenClaw helper for local Qwen3-MLX voice cloning.")
    parser.add_argument("--text", required=True, help="Text to synthesize")
    parser.add_argument("--output-path", required=True, help="Where to write the generated wav")
    parser.add_argument(
        "--voice-name",
        default="akari2",
        help="Saved voice name under voices/<name>.wav and voices/<name>.txt",
    )
    parser.add_argument(
        "--model-path",
        default=None,
        help="Model folder path. Defaults to models/Qwen3-TTS-12Hz-1.7B-Base-8bit",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent
    model_path = (
        Path(args.model_path).expanduser().resolve()
        if args.model_path
        else repo_root / "models" / "Qwen3-TTS-12Hz-1.7B-Base-8bit"
    )
    output_path = Path(args.output_path).expanduser().resolve()
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    ref_audio, ref_text = read_saved_voice(repo_root, args.voice_name)
    model = load_model(str(get_smart_path(str(model_path))))
    generate_audio(
        model=model,
        text=args.text.strip(),
        ref_audio=str(ref_audio),
        ref_text=ref_text,
        output_path=str(output_dir),
    )

    generated_path = output_dir / "audio_000.wav"
    if not generated_path.is_file():
        raise SystemExit(f"generated file missing: {generated_path}")
    if generated_path != output_path:
        generated_path.replace(output_path)

    print(str(output_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
