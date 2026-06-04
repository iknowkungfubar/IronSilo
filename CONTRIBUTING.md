# Contributing

Thank you for considering contributing to this project. This document outlines the standards and processes we follow to maintain architectural robustness, security, and precision across every contribution.

## Code of Conduct

This project is committed to fostering a respectful, inclusive, and harassment-free environment. By participating, you agree to:

- **Be constructive** — Critique ideas, not people. Every review is an opportunity to improve.
- **Be precise** — Back claims with evidence. Provide logs, reproduction steps, or code references.
- **Be patient** — Maintainers review contributions in their available time. Reasonable follow-up is welcome; pinging is not.
- **Be secure** — Never commit secrets, credentials, or tokens. Never introduce vulnerabilities knowingly.

Violations may result in temporary or permanent exclusion from the project at the maintainers' discretion.

---

## Reporting Bugs

Before filing a bug report:

1. **Search existing issues** — Your bug may already be reported or fixed.
2. **Check the latest release** — The issue may have been addressed in a newer version.
3. **Minimize reproduction** — Strip the problem to its simplest reproducible form.

When reporting, include:

- **Environment**: OS, language version, dependency versions
- **Reproduction steps**: Exact commands, input, and configuration
- **Expected vs. actual behavior**: What you expected to happen vs. what actually happened
- **Logs and traces**: Error output, stack traces, debug logs — redact any sensitive data
- **Attempted fixes**: What you tried and the result

Security vulnerabilities should **not** be reported via public issues. See [Security Policy](SECURITY.md) for responsible disclosure.

---

## Feature Requests

Feature requests are welcome but must align with the project's scope:

- **Architectural consistency** — Does the feature fit the existing design philosophy?
- **Minimal surface area** — Can the feature be implemented without introducing unnecessary complexity?
- **Testability** — Can the feature be verified through automated tests?
- **Security posture** — Does the feature maintain or improve the security model?

Open an issue with the **Feature Request** template before writing code.

---

## Pull Request Process

### 1. Open a Discussion First

For significant changes (new features, architectural changes, breaking API changes), open an issue or discussion before writing code. This avoids wasted effort on changes that won't be accepted.

### 2. Branch Convention

```
feat/<short-description>
fix/<short-description>
docs/<short-description>
refactor/<short-description>
test/<short-description>
chore/<short-description>
security/<short-description>
```

Base your branch on `main` (or `master` where applicable).

### 3. Development Setup

Clone the repository and install dependencies:

```bash
git clone https://github.com/iknowkungfubar/IronSilo.git
cd IronSilo
pip install -e ".[dev]"
```

### 4. Make Changes

- Follow the project's coding standards (see below)
- Write or update tests to cover your changes
- Keep changes focused — one feature or fix per pull request
- Avoid mixing refactoring with feature work

### 5. Run All Checks

Before opening a PR, run the full verification suite:

```bash
pytest tests/ -v
ruff check src/ tests/
ruff format --check src/ tests/
```

All checks must pass. CI will enforce this.

### 6. Open the Pull Request

- Target the `main` branch (or `master` where the project uses it)
- Provide a clear description of what the PR does and why
- Reference any related issues: `Closes #123`
- Include testing instructions and edge cases considered
- Mark as **Draft** if the work is incomplete

### 7. Review Process

- Maintainers will review your PR within a reasonable timeframe
- Address review feedback with additional commits — do not squash until approved
- Once approved, your PR will be squash-merged with a conventional commit message
- After merge, the branch is deleted automatically

### 8. After Merge

- Monitor CI for the `main` branch to confirm the build passes
- Update any related documentation or dependent work

---

## Coding Standards

### General Principles

- **Precision over persuasion** — Code should be self-documenting. Comments explain *why*, not *what*.
- **Verifiability over velocity** — Every change must be testable. Untestable code is unmergeable.
- **Least privilege** — Grant minimal necessary access. Restrict scope, permissions, and surface area.
- **Fail closed** — On error, default to the safe state. Never silently swallow failures.
- **Deterministic by default** — Avoid global state, hidden side effects, and implicit configuration.

### Python

- Use `ruff` for linting and formatting — `ruff check src/ tests/ && ruff format --check src/ tests/`
- Use `mypy` for type checking — strict mode preferred
- All function signatures must include type annotations
- Use Pydantic models for all data boundaries (I/O, config, serialization)
- Prefer `pathlib` over `os.path` for filesystem operations
- Use `from __future__ import annotations` for deferred evaluation
- Document public modules, classes, and functions with docstrings

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <imperative description>

[optional body explaining motivation and context]

[optional footer with breaking changes or issue references]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `security`

Examples:
```
feat(api): add rate limiting to POST /organize endpoint
fix(memory): handle dangling references on session expiry
docs: clarify installation prerequisites for Windows
security(sandbox): escape shell metacharacters in user-supplied paths
```

---

## Testing

All new code must be accompanied by tests that validate both success and failure paths.

### Requirements

- **Unit tests** for all new functions and methods
- **Integration tests** for cross-module boundaries (API endpoints, data pipelines, CLI commands)
- **Edge cases** — empty input, maximum input, invalid input, concurrent access
- **Regression tests** for bug fixes — add a test that covers the fixed scenario
- **Security tests** for authentication, authorization, input validation, and sandbox boundaries

### Running Tests

```bash
pytest tests/ -v --cov=. --cov-fail-under=30
```

---

## Security Considerations

- All user-supplied input must be validated before processing
- File paths must be checked for traversal attacks (`../`, absolute paths)
- Shell commands must use parameterized execution — never string interpolation
- Secrets and tokens must never be logged, committed, or exposed in error messages
- Dependencies must be audited regularly — `cargo audit`, `pip-audit`, or equivalent
- If you discover a security vulnerability, follow the responsible disclosure process in `SECURITY.md`

---

## Documentation

- Update the `README.md` if your change affects installation, configuration, or usage
- Update or add docstrings for any new public API surface
- If your change adds a configuration option, document it with its default and effect
- PRs without documentation updates for user-facing changes will not be merged

---

## Questions?

Open a [Discussion](https://github.com/iknowkungfubar/IronSilo/discussions) or an [Issue](https://github.com/iknowkungfubar/IronSilo/issues) with a clear description of what you need help with.

---

*Thank you for helping maintain quality across this project.*
