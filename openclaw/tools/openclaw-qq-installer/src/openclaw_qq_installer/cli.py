from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path

DEFAULT_REPO_ZIP_URL = "https://github.com/openclaw/openclaw/archive/refs/heads/main.zip"
DEFAULT_CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"
DEFAULT_PLUGIN_RELATIVE_PATH = Path("extensions") / "qq-natural"
DEFAULT_PLUGIN_ID = "qq-natural"
DEFAULT_STOCK_PLUGIN_ID = "qq"
DEFAULT_LISTEN_HOST = "127.0.0.1"
DEFAULT_LISTEN_PORT = 8080
DEFAULT_WS_PATH = "/onebot/v11/ws"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openclaw-qq-install",
        description="Install and configure the OpenClaw QQ plugin.",
    )
    parser.add_argument("--qq-self-id", help="QQ bot account id to write into channels.qq.selfId")
    parser.add_argument("--openclaw-bin", default="openclaw", help="Path to the openclaw binary")
    parser.add_argument("--config-path", default=str(DEFAULT_CONFIG_PATH), help="Path to openclaw.json")
    parser.add_argument(
        "--repo-zip-url",
        default=DEFAULT_REPO_ZIP_URL,
        help="Zip archive containing the OpenClaw repo with extensions/qq",
    )
    parser.add_argument("--listen-host", default=DEFAULT_LISTEN_HOST)
    parser.add_argument("--listen-port", type=int, default=DEFAULT_LISTEN_PORT)
    parser.add_argument("--websocket-path", default=DEFAULT_WS_PATH)
    parser.add_argument(
        "--qq-executable-path",
        help="Optional QQ executable path override, for example /Applications/QQ.app/Contents/MacOS/QQ",
    )
    parser.add_argument("--disable-auto-launch", action="store_true")
    parser.add_argument("--disable-idle-sleep", action="store_true")
    parser.add_argument("--disable-natural-chat", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without modifying anything")
    return parser


def ensure_openclaw_available(openclaw_bin: str) -> None:
    resolved = shutil.which(openclaw_bin)
    if resolved:
        return
    if Path(openclaw_bin).exists():
        return
    raise SystemExit(f"openclaw binary not found: {openclaw_bin}")


def run_command(args: list[str], dry_run: bool) -> None:
    print("$", " ".join(args))
    if dry_run:
        return
    subprocess.run(args, check=True)


def try_run_command(args: list[str], dry_run: bool) -> bool:
    print("$", " ".join(args))
    if dry_run:
        return True
    completed = subprocess.run(args, check=False, capture_output=True, text=True)
    if completed.returncode == 0:
        return True
    stderr = completed.stderr.strip()
    stdout = completed.stdout.strip()
    detail = stderr or stdout
    if detail:
        print(detail)
    return False


def download_repo_zip(url: str, dry_run: bool) -> Path:
    if dry_run:
        return Path("/tmp/openclaw-main.zip")
    tmp_dir = Path(tempfile.mkdtemp(prefix="openclaw-qq-installer-"))
    zip_path = tmp_dir / "openclaw.zip"
    with urllib.request.urlopen(url) as response, zip_path.open("wb") as fh:
        fh.write(response.read())
    return zip_path


def extract_plugin_dir(zip_path: Path, dry_run: bool) -> Path:
    if dry_run:
        return Path("/tmp/openclaw-main/extensions/qq")
    extract_root = zip_path.parent / "repo"
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(extract_root)
    candidates = list(extract_root.glob(f"*/{DEFAULT_PLUGIN_RELATIVE_PATH.as_posix()}"))
    if not candidates:
        raise SystemExit("Could not find extensions/qq in downloaded archive")
    return candidates[0]


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Failed to parse {config_path}: {exc}") from exc


def write_config(config_path: Path, cfg: dict, dry_run: bool) -> None:
    print(f"Updating config: {config_path}")
    if dry_run:
        print(json.dumps(cfg, indent=2, ensure_ascii=False))
        return
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def patch_config(cfg: dict, args: argparse.Namespace) -> dict:
    channels = cfg.setdefault("channels", {})
    qq = channels.setdefault("qq", {})

    qq["enabled"] = True
    qq.setdefault("listenHost", args.listen_host)
    qq.setdefault("listenPort", args.listen_port)
    qq.setdefault("websocketPath", args.websocket_path)
    qq["autoLaunch"] = not args.disable_auto_launch
    qq["preventIdleSleep"] = not args.disable_idle_sleep

    if args.qq_self_id:
        qq["selfId"] = str(args.qq_self_id)
    elif not qq.get("selfId"):
        raise SystemExit("--qq-self-id is required when channels.qq.selfId is not already configured")

    if args.qq_executable_path:
        qq["executablePath"] = args.qq_executable_path

    if not args.disable_natural_chat:
        qq["naturalChat"] = {
            "enabled": True,
            "applyToGroups": True,
            "applyToDirect": True,
            "splitMessages": True,
            "removeDecorativeEmoji": True,
            "hardBannedSymbols": ["☕"],
            "defaultPersona": "chino",
            "allowPersonaSwitch": True,
        }

    groups = qq.setdefault("groups", {})
    wildcard = groups.setdefault("*", {})
    wildcard.setdefault("requireMention", True)

    plugins = cfg.setdefault("plugins", {})
    entries = plugins.setdefault("entries", {})
    qq_entry = entries.setdefault(DEFAULT_PLUGIN_ID, {})
    qq_entry["enabled"] = True
    stock_entry = entries.setdefault(DEFAULT_STOCK_PLUGIN_ID, {})
    stock_entry["enabled"] = False

    return cfg


def print_next_steps(args: argparse.Namespace) -> None:
    ws_url = f"ws://{args.listen_host}:{args.listen_port}{args.websocket_path}"
    print("")
    print("Installed the OpenClaw QQ plugin.")
    print("Next step in NapCat / OneBot:")
    print(ws_url)
    print("")
    print("If OpenClaw is already running, restart it after installation.")


def ensure_plugin_enabled(args: argparse.Namespace, plugin_dir: Path) -> None:
    try_run_command([args.openclaw_bin, "plugins", "disable", DEFAULT_STOCK_PLUGIN_ID], args.dry_run)

    enabled = try_run_command([args.openclaw_bin, "plugins", "enable", DEFAULT_PLUGIN_ID], args.dry_run)
    if enabled:
        return
    run_command([args.openclaw_bin, "plugins", "install", str(plugin_dir)], args.dry_run)
    run_command([args.openclaw_bin, "plugins", "enable", DEFAULT_PLUGIN_ID], args.dry_run)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    ensure_openclaw_available(args.openclaw_bin)

    config_path = Path(args.config_path).expanduser()
    cfg = patch_config(load_config(config_path), args)

    zip_path = download_repo_zip(args.repo_zip_url, args.dry_run)
    plugin_dir = extract_plugin_dir(zip_path, args.dry_run)

    ensure_plugin_enabled(args, plugin_dir)
    write_config(config_path, cfg, args.dry_run)
    print_next_steps(args)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc
