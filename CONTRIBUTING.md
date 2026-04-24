# Contributing to IronSilo

First off, thank you for considering contributing to IronSilo! It's people like you that make the open-source community such an incredible place to learn, inspire, and create.

Whether you're fixing a bug, adding a feature from the roadmap, or simply improving documentation, your help is welcome.

## 🛠️ How to Contribute

### 1. Reporting Bugs
Before creating bug reports, please check the existing issues to see if the problem has already been reported. When you are ready to create a bug report, please use the **Bug Report template** and include as many details as possible (OS, Docker version, and which local LLM you are running).

### 2. Suggesting Enhancements
Got an idea for the proxy, a new agent, or the web dashboard? Awesome. Check the `ROADMAP.md` to see if it's already planned. If not, open an issue using the **Feature Request template** to discuss it before you start writing code.

### 3. Pull Requests
1. Fork the repository and create your branch from `main`.
2. If you've added code that changes the proxy or docker configuration, please test it locally (`docker compose up --build`).
3. Ensure your code follows standard styling conventions.
4. **Write tests for new code** - we maintain 92%+ code coverage
5. Update the `README.md` or Manuals if your changes alter how a user interacts with the workspace.
6. Submit your Pull Request using the provided PR template.

### 4. Running Tests
```bash
# Install test dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/unit/test_proxy_proxy.py -v
```

**Coverage Requirements:**
- All new code must include tests
- Minimum coverage threshold: 80%
- Current coverage: 92.8%

## 💻 Local Development Setup
To test your changes locally:
1. Clone your fork: `git clone https://github.com/YOUR_USERNAME/IronSilo.git`
2. Make your changes (e.g., editing `proxy/proxy.py`).
3. Rebuild the environment: `docker compose build --no-cache`
4. Start the stack: `docker compose up -d`

Thank you for helping us build the ultimate offline AI fortress!