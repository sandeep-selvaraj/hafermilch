---
icon: lucide/rocket
---

# Get Started

## Prerequisites

- Python **3.11+**
- [uv](https://docs.astral.sh/uv/) — recommended package manager
- Node.js (only if using the `agent-browser` backend)

---

## Installation

=== "From PyPI (recommended)"

    Install hafermilch as a **global tool** with uv — no virtualenv management needed:

    ```bash
    uv tool install hafermilch
    ```

    Then run it directly from anywhere:

    ```bash
    hafermilch run myplan.yaml
    ```

    To install with Playwright support:

    ```bash
    uv tool install hafermilch
    hafermilch run myplan.yaml  # playwright is a declared dependency, installed automatically
    playwright install chromium
    ```

    To upgrade to the latest release:

    ```bash
    uv tool upgrade hafermilch
    ```

=== "Try without installing (uvx)"

    Run hafermilch once without permanently installing it:

    ```bash
    uvx hafermilch --version
    uvx hafermilch run myplan.yaml
    ```

    !!! tip
        `uvx` is ideal for CI pipelines or one-off evaluations.

=== "Add to a project (uv add)"

    Add hafermilch as a dependency in an existing uv project:

    ```bash
    uv add hafermilch
    uv run hafermilch run myplan.yaml
    ```

=== "pip"

    ```bash
    pip install hafermilch
    hafermilch run myplan.yaml
    ```

---

## Install the Playwright browser

Regardless of how you installed hafermilch, run this once to download the Chromium binary:

=== "uv tool install"

    ```bash
    playwright install chromium
    ```

=== "uvx / uv add / pip"

    ```bash
    uv run playwright install chromium
    # or
    python -m playwright install chromium
    ```

---

## Get the example files

The built-in example personas and plans are [available on GitHub](https://github.com/sandeep-selvaraj/hafermilch/tree/main/examples). Download them to get started quickly:

```bash
# Clone just the examples directory (sparse checkout)
git clone --filter=blob:none --sparse https://github.com/sandeep-selvaraj/hafermilch.git
cd hafermilch
git sparse-checkout set examples
```

Or grab a single plan file directly:

```bash
curl -O https://raw.githubusercontent.com/sandeep-selvaraj/hafermilch/main/examples/plans/saas_onboarding.yaml
mkdir -p personas
curl -o personas/tech_expert.yaml \
  https://raw.githubusercontent.com/sandeep-selvaraj/hafermilch/main/examples/personas/tech_expert.yaml
```

---

## Configure API keys

Set your LLM API keys as environment variables, or create a `.env` file in your working directory:

```bash title=".env"
# OpenAI
OPENAI_API_KEY=sk-...

# Gemini
GOOGLE_API_KEY=AIza...

# Ollama (optional — defaults to http://localhost:11434)
# OLLAMA_HOST=http://localhost:11434
```

!!! tip "Only add what you need"
    hafermilch only requires keys for providers used in your persona files. If all your personas use Ollama, no cloud API keys are needed. hafermilch uses [LiteLLM](https://docs.litellm.ai/) under the hood, so any provider LiteLLM supports will work — just set the appropriate environment variables.

---

## Validate your setup

Before running a full evaluation, confirm your personas and plan files parse correctly:

```bash
hafermilch validate \
  --personas-dir examples/personas \
  --plan examples/plans/saas_onboarding.yaml
```

You should see:

```
3 persona(s) valid:
  tech_expert — Senior Engineer (ollama/gpt-oss:20b)
  office_clerk — Office Clerk (ollama/gpt-oss:20b)
  startup_founder — Startup Founder (ollama/gpt-oss:20b)
Plan valid: saas_onboarding
  Target: https://automationexercise.com/
  Personas: tech_expert, office_clerk, startup_founder
  Tasks: 2
```

---

## Run your first evaluation

```bash
hafermilch run examples/plans/saas_onboarding.yaml
```

hafermilch will:

1. Load the plan and resolve the referenced personas
2. Launch a browser for each persona
3. Navigate to each task URL and execute each step
4. Ask the LLM for a `BrowserAction` at every step
5. Compile findings into a final scored report

Results are printed to the terminal (including token usage and cost) and written to `reports/` as JSON, Markdown, and HTML.

---

## Optional: agent-browser backend

If you want to use the [agent-browser](https://github.com/vercel-labs/agent-browser) backend instead of Playwright:

```bash
npm install -g agent-browser
```

Then pass `--browser agent-browser`:

```bash
hafermilch run examples/plans/saas_onboarding.yaml --browser agent-browser
```

See [Browser Backends](browser-backends.md) for a detailed comparison.

---

## Development install

To contribute or run from source:

```bash
git clone https://github.com/sandeep-selvaraj/hafermilch.git
cd hafermilch
uv sync
uv run playwright install chromium
uv run hafermilch run examples/plans/saas_onboarding.yaml
```

See [Development](development.md) for the full contributor guide.
