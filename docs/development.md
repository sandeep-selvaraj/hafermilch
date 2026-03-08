---
icon: lucide/wrench
---

# Development

---

## Setup

```bash
git clone https://github.com/your-org/hafermilch.git
cd hafermilch
uv sync
```

Install pre-commit hooks:

```bash
uv run pre-commit install
```

---

## Running tests

```bash
uv run pytest
```

Pass extra arguments after `--`:

```bash
# Run a specific test file
uv run pytest tests/test_runner.py -v

# Run tests matching a keyword
uv run pytest -k test_llm -v
```

---

## Nox sessions

[Nox](https://nox.thea.codes/) orchestrates lint and tests in isolated virtual environments.

```bash
# Run all sessions (lint + tests)
uv run nox

# Run only the test session
uv run nox -s tests

# Run only the lint session
uv run nox -s lint

# Pass extra pytest args
uv run nox -s tests -- -k test_runner -v
```

### Sessions

| Session | What it does |
|---|---|
| `lint` | Runs `pre-commit run --all-files` (ruff lint + ruff format) |
| `tests` | Runs `pytest tests/` with `pytest-asyncio` |

---

## Code style

hafermilch uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting, enforced via pre-commit.

```bash
# Auto-fix lint issues
uv run ruff check --fix src/ tests/

# Format code
uv run ruff format src/ tests/
```

Ruff is configured in `pyproject.toml` under `[tool.ruff]`.

---

## Project structure

```
hafermilch/
├── src/hafermilch/
│   ├── browser/
│   │   ├── base.py             # Abstract BaseBrowserAgent
│   │   ├── playwright_agent.py # Playwright backend
│   │   ├── agent_browser.py    # agent-browser subprocess backend
│   │   ├── context.py          # PageContext dataclass
│   │   └── factory.py          # create_browser_agent()
│   ├── core/
│   │   ├── models.py           # All Pydantic models
│   │   ├── settings.py         # pydantic-settings (env vars)
│   │   └── exceptions.py       # Custom exception hierarchy
│   ├── evaluation/
│   │   ├── runner.py           # EvaluationRunner orchestrator
│   │   └── prompter.py         # Prompt construction
│   ├── llm/
│   │   ├── base.py             # Abstract LLMProvider
│   │   ├── openai_provider.py  # OpenAI + Azure
│   │   ├── gemini_provider.py  # Google Gemini
│   │   ├── ollama_provider.py  # Ollama (local)
│   │   └── factory.py          # LLMProviderFactory
│   ├── personas/
│   │   └── loader.py           # YAML loading + validation
│   ├── reporting/
│   │   └── reporter.py         # JSON + Markdown output
│   └── cli.py                  # Typer CLI entrypoint
├── tests/
│   ├── conftest.py             # Shared fixtures
│   ├── test_llm_base.py
│   ├── test_persona_loader.py
│   ├── test_prompter.py
│   ├── test_agent_browser.py
│   └── test_runner.py
├── examples/
│   ├── personas/               # Built-in persona YAMLs
│   └── plans/                  # Built-in plan YAMLs
├── pyproject.toml
├── noxfile.py
└── .pre-commit-config.yaml
```

---

## Adding a new LLM provider

1. Create `src/hafermilch/llm/myprovider.py` subclassing `LLMProvider`
2. Implement `async def complete(self, messages)` and `supports_vision`
3. Add a branch in `src/hafermilch/llm/factory.py`
4. Add the new provider name to the `provider` field validation in `core/models.py`

---

## Adding a new browser backend

1. Create `src/hafermilch/browser/mybackend.py` subclassing `BaseBrowserAgent`
2. Implement `start()`, `stop()`, `navigate()`, `capture()`, `execute()`, and the `selector_hint` property
3. Add the backend to `BrowserBackend` in `browser/factory.py`
4. Update `create_browser_agent()` with a new branch

---

## CI

GitHub Actions runs on every push and pull request to `master`/`main`:

- **Lint** — `nox -s lint` on ubuntu-latest
- **Tests** — `nox -s tests` across Python 3.11, 3.12, and 3.13
