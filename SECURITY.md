# Security Policy

Chino Bot connects a language-model agent to messaging, file, command, and
workflow tools. Treat every deployment as security-sensitive.

## Supported Versions

Security fixes are handled on the active `v4` branch.

## Secrets

Do not commit:

- `.env` files
- API keys
- QQ credentials
- OneBot access tokens
- cookies or session files
- private logs
- local memory/vector-store data

Use `.env.example` as the only committed configuration template.

## Administrator Controls

File writes, command execution, and other privileged operations should only be
available to trusted administrators configured through:

```dotenv
CHINO_ADMIN_USERS=your_admin_qq_number
```

Keep `CHINO_PROJECT_ROOT` pointed at the repository root or another deliberate
sandbox path.

## Responsible Use

Do not use this project for spam, harassment, account abuse, impersonation,
credential collection, evasion of platform rules, or publication of misleading
mock conversations. Mock dialogue tools are intended for local testing and UI
preview artifacts only.

## Reporting a Vulnerability

Please open a private report through GitHub security advisories if available,
or open an issue with minimal reproduction steps and no secrets. If a report
contains credentials, revoke those credentials before posting.

