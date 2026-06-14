# openclaw-qq-installer

`pip` installer for the OpenClaw QQ Natural plugin.

This package assumes the target machine already has:

- OpenClaw
- QQ
- NapCat / OneBot V11

It installs the `qq-natural` plugin into OpenClaw from the OpenClaw repository source,
then patches `~/.openclaw/openclaw.json` with a minimal QQ configuration.

## One-line usage

From a local checkout:

```bash
python3 -m pip install /path/to/openclaw/tools/openclaw-qq-installer && openclaw-qq-install --qq-self-id 123456789
```

If this package is published to PyPI later:

```bash
python3 -m pip install openclaw-qq-installer && openclaw-qq-install --qq-self-id 123456789
```

## Example

```bash
pip install openclaw-qq-installer
openclaw-qq-install --qq-self-id 123456789
```

After installation, configure NapCat reverse WebSocket to connect to:

```text
ws://127.0.0.1:8080/onebot/v11/ws
```
