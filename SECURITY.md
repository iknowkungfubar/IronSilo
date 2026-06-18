# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| >= 2.1  | :white_check_mark: |
| < 2.1   | :x:                |

## Reporting a Vulnerability

Please report security vulnerabilities via the GitHub Security Advisory tab.
Do not open public issues for security bugs.

## Security Measures

- API keys should be set via environment variables, not stored in config files
- PostgreSQL passwords must be set via runtime secrets
- All dependencies are audited via pip-audit in CI
