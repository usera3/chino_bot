# Contributing

Thanks for helping improve Chino Bot. This repository is an experimental
agentic QQ assistant, so contributions should keep safety, testability, and
maintainability in view.

## Good First Contributions

- Add tests for individual tools.
- Improve provider configuration and error messages.
- Translate or simplify historical Chinese development notes.
- Replace hard-coded paths with environment-driven settings.
- Improve docs for NapCat / OneBot setup.
- Add safer defaults around file and command tools.

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

## Tests

Run focused tests before opening a pull request:

```bash
python -m pytest tests
```

If your change touches root-level quick tests, mention which ones you ran.

## Pull Request Checklist

- No secrets, QQ credentials, cookies, private logs, or local memory data.
- New behavior has tests or a clear manual verification note.
- User-facing configuration is documented in `.env.example`.
- Privileged operations preserve administrator checks.
- Mock dialogue features remain clearly labeled as testing artifacts.

## Commit Style

Use concise conventional prefixes when practical:

- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation
- `test:` tests
- `refactor:` behavior-preserving cleanup
- `chore:` tooling or maintenance

