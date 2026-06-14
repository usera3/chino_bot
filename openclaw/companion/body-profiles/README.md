# Body Profiles

This directory separates **who OpenClaw is** from **which visual body is currently attached**.

## Why

The personality should stay stable even when the shell body changes.

That means:

- `智乃` is the character identity
- body profiles are interchangeable visual shells

## Files

- `shizuku-sample.json`
  - current local sample body
- `quiet-clerk-target.json`
  - target body specification for a more fitting future model

## Workflow

### View current body config

```bash
node scripts/select-companion-body.mjs current
```

### Switch to an existing body profile

```bash
node scripts/select-companion-body.mjs apply --profile shizuku-sample
```

### Import a new Live2D body into the workspace

```bash
node scripts/import-live2d-body.mjs \
  --name "Chino Body" \
  --slug chino-body \
  --model-dir /absolute/path/to/model/folder \
  --model-file runtime/chino.model3.json \
  --avatar /absolute/path/to/avatar.png \
  --activate true
```

This will:

- copy the model into `companion-assets/live2d/<slug>/`
- copy the avatar into `companion-assets/avatars/`
- create a new body profile JSON
- optionally activate it in `companion/open-llm-vtuber-adapter.json`

