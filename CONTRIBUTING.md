1|# Contributing
2|
3|Thank you for considering contributing to this project. This document outlines the standards and processes we follow to maintain architectural robustness, security, and precision across every contribution.
4|
5|## Code of Conduct
6|
7|This project is committed to fostering a respectful, inclusive, and harassment-free environment. By participating, you agree to:
8|
9|- **Be constructive** — Critique ideas, not people. Every review is an opportunity to improve.
10|- **Be precise** — Back claims with evidence. Provide logs, reproduction steps, or code references.
11|- **Be patient** — Maintainers review contributions in their available time. Reasonable follow-up is welcome; pinging is not.
12|- **Be secure** — Never commit secrets, credentials, or tokens. Never introduce vulnerabilities knowingly.
13|
14|Violations may result in temporary or permanent exclusion from the project at the maintainers' discretion.
15|
16|---
17|
18|## Reporting Bugs
19|
20|Before filing a bug report:
21|
22|1. **Search existing issues** — Your bug may already be reported or fixed.
23|2. **Check the latest release** — The issue may have been addressed in a newer version.
24|3. **Minimize reproduction** — Strip the problem to its simplest reproducible form.
25|
26|When reporting, include:
27|
28|- **Environment**: OS, language version, dependency versions (`pip list`, `cargo tree`, or equivalent)
29|- **Reproduction steps**: Exact commands, input, and configuration
30|- **Expected vs. actual behavior**: What you expected to happen vs. what actually happened
31|- **Logs and traces**: Error output, stack traces, debug logs — redact any sensitive data
32|- **Attempted fixes**: What you tried and the result
33|
34|Security vulnerabilities should **not** be reported via public issues. See [Security Policy](SECURITY.md) for responsible disclosure.
35|
36|---
37|
38|## Feature Requests
39|
40|Feature requests are welcome but must align with the project's scope:
41|
42|- **Architectural consistency** — Does the feature fit the existing design philosophy?
43|- **Minimal surface area** — Can the feature be implemented without introducing unnecessary complexity?
44|- **Testability** — Can the feature be verified through automated tests?
45|- **Security posture** — Does the feature maintain or improve the security model?
46|
47|Open an issue with the **Feature Request** template before writing code.
48|
49|---
50|
51|## Pull Request Process
52|
53|### 1. Open a Discussion First
54|
55|For significant changes (new features, architectural changes, breaking API changes), open an issue or discussion before writing code. This avoids wasted effort on changes that won't be accepted.
56|
57|### 2. Branch Convention
58|
59|```
60|feat/<short-description>
61|fix/<short-description>
62|docs/<short-description>
63|refactor/<short-description>
64|test/<short-description>
65|chore/<short-description>
66|security/<short-description>
67|```
68|
69|Base your branch on `main` (or `master` where applicable).
70|
71|### 3. Development Setup
72|
73|Clone the repository and install dependencies:
74|
75|```bash
76|git clone https://github.com/iknowkungfubar/IronSilo.git
77|cd IronSilo
78|# Install dependencies — see the project's README or setup documentation
79|```
80|
81|### 4. Make Changes
82|
83|- Follow the project's coding standards (see below)
84|- Write or update tests to cover your changes
85|- Keep changes focused — one feature or fix per pull request
86|- Avoid mixing refactoring with feature work
87|
88|### 5. Run All Checks
89|
90|Before opening a PR, run the full verification suite:
91|
92|```bash
93|# Run tests
94|# Run linters
95|# Run type checker
96|# Verify no new warnings
97|```
98|
99|All checks must pass. CI will enforce this.
100|
101|### 6. Open the Pull Request
102|
103|- Target the `main` branch (or `master` where the project uses it)
104|- Provide a clear description of what the PR does and why
105|- Reference any related issues: `Closes #123`
106|- Include testing instructions and edge cases considered
107|- Mark as **Draft** if the work is incomplete
108|
109|### 7. Review Process
110|
111|- Maintainers will review your PR within a reasonable timeframe
112|- Address review feedback with additional commits — do not squash until approved
113|- Once approved, your PR will be squash-merged with a conventional commit message
114|- After merge, the branch is deleted automatically
115|
116|### 8. After Merge
117|
118|- Monitor CI for the `main` branch to confirm the build passes
119|- Update any related documentation or dependent work
120|
121|---
122|
123|## Coding Standards
124|
125|### General Principles
126|
127|- **Precision over persuasion** — Code should be self-documenting. Comments explain *why*, not *what*.
128|- **Verifiability over velocity** — Every change must be testable. Untestable code is unmergeable.
129|- **Least privilege** — Grant minimal necessary access. Restrict scope, permissions, and surface area.
130|- **Fail closed** — On error, default to the safe state. Never silently swallow failures.
131|- **Deterministic by default** — Avoid global state, hidden side effects, and implicit configuration.
132|
133|### Rust Projects
134|
135|```
136|- Use `cargo clippy -- -D warnings` — no warnings tolerated
137|- Use `cargo fmt` — consistent formatting enforced in CI
138|- Never use `.unwrap()` or `.expect()` in production code
139|- Use `thiserror` or project-specific error types for all error paths
140|- Prefer owned types over references where lifetime complexity grows
141|- Mark all public APIs with `#[must_use]` where appropriate
142|- Document all public items with doc comments (`///`)
143|```
144|
145|### Python Projects
146|
147|```
148|- Use `ruff` for linting and formatting — `ruff check src/ tests/ && ruff format --check src/ tests/`
149|- Use `mypy` for type checking — strict mode preferred
150|- All function signatures must include type annotations
151|- Use Pydantic models for all data boundaries (I/O, config, serialization)
152|- Prefer `pathlib` over `os.path` for filesystem operations
153|- Use `from __future__ import annotations` for deferred evaluation
154|- Document public modules, classes, and functions with docstrings
155|```
156|
157|### JavaScript / TypeScript / Astro Projects
158|
159|```
160|- Use `prettier` or project-configured formatter
161|- Use `eslint` with recommended rules
162|- All exports must have JSDoc or TypeScript type annotations
163|- Avoid mutable global state
164|- Prefer `const` over `let` — `let` only for loop counters
165|- Use async/await over raw promises where possible
166|```
167|
168|### Commit Messages
169|
170|Follow [Conventional Commits](https://www.conventionalcommits.org/):
171|
172|```
173|<type>(<scope>): <imperative description>
174|
175|[optional body explaining motivation and context]
176|
177|[optional footer with breaking changes or issue references]
178|```
179|
180|Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `security`
181|
182|Examples:
183|```
184|feat(api): add rate limiting to POST /organize endpoint
185|fix(memory): handle dangling references on session expiry
186|docs: clarify installation prerequisites for Windows
187|security(sandbox): escape shell metacharacters in user-supplied paths
188|```
189|
190|---
191|
192|## Testing
193|
194|All new code must be accompanied by tests that validate both success and failure paths.
195|
196|### Requirements
197|
198|- **Unit tests** for all new functions and methods
199|- **Integration tests** for cross-module boundaries (API endpoints, data pipelines, CLI commands)
200|- **Edge cases** — empty input, maximum input, invalid input, concurrent access
201|- **Regression tests** for bug fixes — add a test that covers the fixed scenario
202|- **Security tests** for authentication, authorization, input validation, and sandbox boundaries
203|
204|### Running Tests
205|
206|```bash
207|# Run the full test suite
208|# Check test coverage — new code should maintain or improve coverage
209|```
210|
211|---
212|
213|## Security Considerations
214|
215|- All user-supplied input must be validated before processing
216|- File paths must be checked for traversal attacks (`../`, absolute paths)
217|- Shell commands must use parameterized execution — never string interpolation
218|- Secrets and tokens must never be logged, committed, or exposed in error messages
219|- Dependencies must be audited regularly — `cargo audit`, `pip-audit`, or equivalent
220|- If you discover a security vulnerability, follow the responsible disclosure process in `SECURITY.md`
221|
222|---
223|
224|## Documentation
225|
226|- Update the `README.md` if your change affects installation, configuration, or usage
227|- Update or add docstrings for any new public API surface
228|- If your change adds a configuration option, document it with its default and effect
229|- PRs without documentation updates for user-facing changes will not be merged
230|
231|---
232|
233|## Questions?
234|
235|Open a [Discussion](https://github.com/iknowkungfubar/IronSilo/discussions) or an [Issue](https://github.com/iknowkungfubar/IronSilo/issues) with a clear description of what you need help with.
236|
237|---
238|
239|*Thank you for helping maintain quality across this project.*
240|
