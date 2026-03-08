---
icon: lucide/rocket
---

# Get Started

## Prerequisites

- Python **3.11+**
- [uv](https://docs.astral.sh/uv/) — the package manager used by hafermilch
- Node.js (only if using the `agent-browser` backend)

---

## Installation

Clone the repository and sync dependencies:

```bash
git clone https://github.com/your-org/hafermilch.git
cd hafermilch
uv sync
```

Install the Playwright browser (required for the default backend):

```bash
uv run playwright install chromium
```

---

## Configure API keys

Copy the example environment file and add your keys:

```bash
cp .env.example .env
```

Then edit `.env`:

```bash title=".env"
# OpenAI
OPENAI_API_KEY=sk-...

# Gemini
GOOGLE_API_KEY=AIza...

# Ollama (optional — defaults to http://localhost:11434)
# OLLAMA_HOST=http://localhost:11434
```

!!! tip "Only add what you need"
    hafermilch only requires the key(s) for providers you actually use in your persona files. If all your personas use Ollama, you don't need any cloud API keys.

---

## Validate your setup

Before running a full evaluation, validate that your personas and plan files parse correctly:

```bash
uv run hafermilch validate \
  --personas-dir examples/personas \
  --plan examples/plans/saas_onboarding.yaml
```

You should see something like:

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
uv run hafermilch run examples/plans/saas_onboarding.yaml
```

hafermilch will:

1. Load the plan and resolve the referenced personas
2. Launch a browser for each persona
3. Navigate to each task URL and execute each step
4. Ask the LLM for a `BrowserAction` at every step
5. Compile findings into a final scored report

Results are printed to the terminal and written to `reports/`.

---

## Optional: agent-browser backend

If you want to use the [agent-browser](https://github.com/vercel-labs/agent-browser) backend instead of Playwright:

```bash
npm install -g agent-browser
```

Then pass `--browser agent-browser` to the `run` command:

```bash
uv run hafermilch run examples/plans/saas_onboarding.yaml --browser agent-browser
```

See [Browser Backends](browser-backends.md) for a detailed comparison.
