# Bota Recorder

OpenClaw plugin that lets the agent control a local Bota recording pen over BLE.

It reuses the existing Python BLE gateway in:

- `/Users/mozi100/PycharmProjects/PythonProject6/firmware/host_tools/bota_web/server.py`

Capabilities exposed to the agent via the `bota_recorder` tool:

- connect/disconnect
- start recording
- stop recording
- list recordings
- download a recording to the local machine
- inspect current gateway/device state

Typical config lives under:

- `plugins.entries.bota-recorder.config`

Allow the tool by adding either:

- `bota-recorder` to a tool allowlist
- or the specific tool name `bota_recorder`

This plugin is designed for local use on the same machine as the BLE adapter.
