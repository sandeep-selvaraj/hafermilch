# hafermilch

Run LLM-powered personas against any website and get structured UX critiques, scores, and recommendations.

Each persona is a character — a senior engineer, a non-technical office clerk, a startup founder — backed by an LLM (any provider via [LiteLLM](https://docs.litellm.ai/)). They browse your product autonomously via a real browser and report back in their own voice.

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

For the agent-browser backend (optional), also install the CLI:

```bash
npm install -g agent-browser
```

---

## Concepts

**Persona** — who the agent is. Defines background, goals, expertise level, scoring dimensions, and which LLM to use. Reusable across any product. Stored in `examples/personas/`.

**Plan** — what to test. Defines the target URL, which personas to use, and the tasks/steps to execute. Stored in `examples/plans/`.

This separation means you define a persona once and point it at any product by swapping the plan.

---

## Browser backends

hafermilch supports two browser backends, selectable with `--browser`.

### Playwright (default)

Playwright runs a real Chromium browser as a Python-native library. It interacts with pages using **CSS selectors and ARIA roles**, which makes it precise and deterministic — great for products where you can predict the DOM structure or want strict control over what gets clicked.

Best for:
- Authenticated flows (login, forms, checkout) where selectors are stable
- Regression testing — comparing scores across deploys
- Environments where you do not want Node.js as a dependency

```bash
uv run hafermilch run examples/plans/saas_onboarding.yaml --browser playwright
```

### agent-browser

[agent-browser](https://github.com/vercel-labs/agent-browser) (Vercel Labs) is a Rust CLI purpose-built for AI agents. Its `snapshot` command returns an accessibility tree where every interactive element has a short **`@ref`** handle (e.g. `@e1`, `@e3`). The LLM picks refs directly from what it sees — no CSS selectors, no guessing at DOM structure.

Best for:
- Exploratory evaluations on unfamiliar products where selectors are unknown
- Semantic, human-like navigation ("click the button labelled Sign in") rather than implementation-level targeting
- Products that use heavy JS frameworks where CSS selectors are unstable or generated

```bash
uv run hafermilch run examples/plans/saas_onboarding.yaml --browser agent-browser
```

You can watch the agent navigate your site in real-time by starting the agent-browser dashboard before running an evaluation:

```bash
agent-browser dashboard start
```

This opens a live view of every action the agent takes — useful for debugging plans or just seeing what the persona actually does.

### Which one to pick?

| | Playwright | agent-browser |
| --- | --- | --- |
| Selector style | CSS / ARIA role | `@ref` from snapshot |
| LLM needs to know DOM? | Yes | No |
| Stability on JS-heavy apps | Can be brittle | More resilient |
| Extra install | `playwright install chromium` | `npm i -g @vercel-labs/agent-browser` |
| Vision support | Yes | Yes |
| Headless control | `--no-headless` flag | Managed by daemon |

In practice: start with **Playwright** for products you own and know. Switch to **agent-browser** when evaluating third-party products or when the LLM keeps choosing wrong selectors.

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

Reports are written to `reports/report.json`, `reports/report.md`, and `reports/report.html`.

---

## Credentials & authenticated flows

Plans can include credentials for testing login-protected products. Values support `${ENV_VAR}` interpolation so secrets stay out of YAML:

```yaml
# plans/myapp.yaml
credentials:
  username: ${APP_USERNAME}
  password: ${APP_PASSWORD}
  extra:
    account_id: "12345"
```

When credentials are present, the LLM receives them in its system prompt and can execute a single `login` action that auto-fills common form selectors — no multi-step selector guessing required.

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

hafermilch uses [LiteLLM](https://docs.litellm.ai/) as a unified gateway, giving you access to 100+ providers through a single configuration format. The most common providers:

| Provider | Config                          | API key env var    |
| -------- | ------------------------------- | ------------------ |
| OpenAI   | `provider: openai`, any GPT-4o model | `OPENAI_API_KEY`   |
| Azure OpenAI | `provider: openai` + `base_url` | `AZURE_OPENAI_API_KEY` |
| Gemini   | `provider: gemini`, e.g. `gemini-2.0-flash` | `GOOGLE_API_KEY`   |
| Ollama   | `provider: ollama`, e.g. `llava` | none (runs locally) |

Any provider supported by LiteLLM works — just set the appropriate `provider` and `model` values.

Vision-capable models (GPT-4o, Gemini 1.5+, LLaVA) also receive a screenshot of each page in addition to the accessibility tree.

To use a local Ollama instance at a non-default address:

```yaml
llm:
  provider: ollama
  model: llava
  base_url: "http://192.168.1.10:11434"
```

---

## Token usage & cost tracking

hafermilch tracks token counts and estimated costs at every level — per step, per persona, and for the full evaluation. Costs are calculated via LiteLLM's pricing data. Usage stats appear in the terminal output and in all three report formats.

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
| `--browser` / `-b` | `playwright` | Browser backend: `playwright` or `agent-browser` |
| `--headless / --no-headless` | headless | Show or hide the browser window (Playwright only) |
| `--record / --no-record` | off | Save a `.webm` recording of each session to the output directory (agent-browser only) |
| `--verbose` / `-v` | off | Enable debug logging |

Reports are written as three files: `report.json`, `report.md`, and `report.html`. The HTML report is a self-contained file you can open in any browser — no server needed.

**`validate` options:**

| Flag | Description |
| ---- | ----------- |
| `--personas-dir` / `-p` | Validate all personas in a directory |
| `--plan` | Validate a plan file |

---

## Example output

```
─────────────── hafermilch v0.1.2 ───────────────
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

Tokens: 12,450 (8,230 in / 4,220 out) · $0.042

Reports written to reports/
  report.json
  report.md
  report.html
```
