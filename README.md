# hafermilch

Run LLM-powered personas against any website and get structured UX critiques, scores, and recommendations.

Each persona is a character — a senior engineer, a non-technical office clerk, a startup founder — backed by an LLM (OpenAI, Gemini, or Ollama). They browse your product autonomously via a real browser and report back in their own voice.

---

## Installation

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run playwright install chromium
```

Copy the environment file and add your API keys:

```bash
cp .env.example .env
```

---

## Concepts

**Persona** — who the agent is. Defines background, goals, expertise level, scoring dimensions, and which LLM to use. Reusable across any product. Stored in `examples/personas/`.

**Plan** — what to test. Defines the target URL, which personas to use, and the tasks/steps to execute. Stored in `examples/plans/`.

This separation means you define a persona once and point it at any product by swapping the plan.

---

## Quick start

Validate your configs first:

```bash
uv run hafermilch validate --personas-dir examples/personas --plan examples/plans/saas_onboarding.yaml
```

Run an evaluation:

```bash
uv run hafermilch run examples/plans/saas_onboarding.yaml
```

Reports are written to `reports/report.md` and `reports/report.json`.

---

## Writing a plan

Create a YAML file anywhere and pass it as the first argument to `run`:

```yaml
# plans/myapp.yaml
name: myapp_evaluation
description: Evaluate the onboarding flow for MyApp
target_url: "https://myapp.com"

personas:
  - tech_expert
  - office_clerk

tasks:
  - name: sign_up
    description: Registration flow
    steps:
      - instruction: >
          Find the sign-up button and register using realistic test data.
          Note any friction or confusing fields.
        max_actions: 10

  - name: core_feature
    description: Use the main feature
    steps:
      - instruction: >
          Navigate to the main feature and try to use it as a first-time user.
        max_actions: 8
```

Run it:

```bash
uv run hafermilch run plans/myapp.yaml --personas-dir examples/personas
```

---

## Writing a persona

Create a YAML file in your personas directory:

```yaml
# personas/qa_engineer.yaml
name: qa_engineer
display_name: "QA Engineer"
description: Methodical tester who hunts for edge cases and broken states.
background: >
  5 years in QA at a fintech company. Instinctively tries to break things —
  submits empty forms, clicks back mid-flow, resizes the window.
goals:
  - Find broken states and edge cases
  - Check form validation and error messages
  - Verify that navigation is consistent
expertise_level: intermediate
technical: true

llm:
  provider: openai
  model: gpt-4o
  temperature: 0.3

scoring_dimensions:
  - name: Robustness
    description: How well does the UI handle unexpected input and edge cases?
    weight: 2.0
  - name: Error Handling
    description: Are error messages clear and recoverable?
    weight: 1.5
```

Then reference it by `name` in any plan.

---

## Supported LLM providers

| Provider | Config                          | API key env var    |
| -------- | ------------------------------- | ------------------ |
| OpenAI   | `provider: openai`, any GPT-4o model | `OPENAI_API_KEY`   |
| Gemini   | `provider: gemini`, e.g. `gemini-1.5-pro` | `GOOGLE_API_KEY`   |
| Ollama   | `provider: ollama`, e.g. `llava` | none (runs locally) |

Vision-capable models (GPT-4o, Gemini 1.5+, LLaVA) also receive a screenshot of each page in addition to the accessibility tree.

To use a local Ollama instance at a non-default address:

```yaml
llm:
  provider: ollama
  model: llava
  base_url: "http://192.168.1.10:11434"
```

---

## CLI reference

```
uv run hafermilch run <plan>         Run an evaluation plan
uv run hafermilch validate           Validate persona/plan YAML files
uv run hafermilch --version          Show version
```

**`run` options:**

| Flag | Default | Description |
| ---- | ------- | ----------- |
| `--personas-dir` / `-p` | `examples/personas` | Directory of persona YAML files |
| `--output` / `-o` | `reports` | Directory to write reports into |
| `--headless / --no-headless` | headless | Show or hide the browser window |
| `--verbose` / `-v` | off | Enable debug logging |

**`validate` options:**

| Flag | Description |
| ---- | ----------- |
| `--personas-dir` / `-p` | Validate all personas in a directory |
| `--plan` | Validate a plan file |

---

## Example output

```
─────────────── hafermilch v0.1.0 ───────────────
Plan:     saas_onboarding
Target:   https://example.com
Personas: Senior Engineer, Office Clerk, Startup Founder

         Results
┌──────────────────┬───────────┬──────────┐
│ Persona          │   Score   │ Findings │
├──────────────────┼───────────┼──────────┤
│ Senior Engineer  │ 7.2 / 10  │       18 │
│ Office Clerk     │ 5.8 / 10  │       14 │
│ Startup Founder  │ 6.4 / 10  │       16 │
└──────────────────┴───────────┴──────────┘

Reports written to reports/
```
