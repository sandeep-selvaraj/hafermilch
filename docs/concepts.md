---
icon: lucide/layers
---

# Concepts

hafermilch is built around two orthogonal ideas: **who** is evaluating and **what** to evaluate. Keeping them separate means you define a persona once and reuse it across every product you test.

---

## Persona

A persona is a *character* — a synthetic user with a defined background, goals, technical ability, and voice. It has no knowledge of any specific product until you point it at one via a plan.

```yaml title="examples/personas/office_clerk.yaml"
name: office_clerk
display_name: "Office Clerk"
description: Non-technical business user who needs everything self-explanatory.

background: >
  Administrative assistant at a mid-sized company. Uses Excel and Outlook daily.
  Frustrated by software that assumes technical knowledge.

goals:
  - Complete basic tasks without reading documentation
  - Understand what each button does from its label alone
  - Not feel lost or overwhelmed

expertise_level: beginner
technical: false

llm:
  provider: ollama
  model: gpt-oss:20b
  temperature: 0.7

scoring_dimensions:
  - name: Clarity
    description: Are labels, instructions, and flows self-explanatory?
    weight: 2.0
  - name: Onboarding
    description: How easy is it to get started without help?
    weight: 1.5
```

Personas are stored in a directory (default: `examples/personas/`) and are referenced by `name` in plans.

---

## Plan

A plan defines *what* to test and *against which URL*. It lists which persona names to load and describes the tasks to execute as a sequence of natural-language instructions.

```yaml title="examples/plans/saas_onboarding.yaml"
name: saas_onboarding
description: Evaluate the onboarding and core feature flow
target_url: "https://example.com"

personas:
  - tech_expert
  - office_clerk
  - startup_founder

tasks:
  - name: sign_up
    description: Registration flow
    steps:
      - instruction: >
          Find the sign-up or register button and complete the registration
          using realistic test data. Note any confusing fields or friction.
        max_actions: 12

  - name: explore_product
    description: First use of the main feature
    steps:
      - instruction: >
          After signing up, locate and try the core feature of the product.
          Describe what you find and how intuitive it feels.
        max_actions: 10
```

---

## EvaluationRunner

The `EvaluationRunner` wires everything together:

1. For each persona in the plan, it creates an LLM provider and a browser agent
2. For each task, it navigates to the `start_url` (or falls back to `target_url`)
3. For each step, it captures a `PageContext` (accessibility tree + optional screenshot) and asks the LLM what to do next as a structured `BrowserAction`
4. After all tasks are complete, it asks the LLM to produce a `PersonaReport` with a score, dimension breakdown, and recommendations

---

## BrowserAction

Each LLM turn returns a `BrowserAction` — a structured JSON object:

```json
{
  "action_type": "click",
  "selector": "#signup-button",
  "observation": "I can see a prominent 'Get Started' button in the hero section.",
  "reasoning": "This is the most obvious entry point for registration."
}
```

| Field | Description |
|---|---|
| `action_type` | `navigate`, `click`, `type`, `scroll`, `wait`, `login`, `done` |
| `selector` | CSS selector (Playwright) or `@ref` handle (agent-browser) |
| `url` | Target URL — only for `navigate` actions |
| `text` | Text to type — only for `type` actions |
| `observation` | What the persona sees on the page right now |
| `reasoning` | Why this action is the right next step |

When `action_type` is `login`, the browser agent auto-fills common login form selectors (email, username, password) and submits the form in a single atomic step — reducing the number of LLM calls needed for authenticated flows.

When `action_type` is `done`, the step is considered complete and the runner moves to the next step.

---

## Report structure

After all personas have run, the runner produces an `EvaluationReport`:

```
EvaluationReport
  ├── total_usage             (TokenUsage — aggregated across all personas)
  └── PersonaReport × N
        ├── overall_score       (0–10)
        ├── summary             (LLM prose)
        ├── recommendations     (list of strings)
        ├── total_usage         (TokenUsage — aggregated for this persona)
        ├── dimension_scores    (DimensionScore × M)
        │     ├── dimension     (name from persona YAML)
        │     ├── score         (0–10)
        │     └── rationale     (LLM prose)
        └── findings            (Finding × K)
              ├── task_name
              ├── step_instruction
              ├── url
              ├── observation
              ├── reasoning
              ├── action_taken
              ├── usage           (TokenUsage for this step)
              └── screenshot      (base64 PNG, if vision model)
```

### Output formats

Reports are generated in three formats:

- **JSON** (`report.json`) — complete data dump with all fields, ideal for programmatic consumption
- **Markdown** (`report.md`) — human-readable table format with findings
- **HTML** (`report.html`) — interactive, styled report with embedded screenshots, score visualizations, color-coded action badges, and token usage breakdowns. Built with Jinja2

Reports are written to `reports/report.json`, `reports/report.md`, and `reports/report.html`.

---

## Token usage & cost tracking

hafermilch tracks token consumption at every level:

- **Per step** — each LLM call records prompt tokens, completion tokens, and estimated cost
- **Per persona** — all step usages are aggregated into a `total_usage` on the `PersonaReport`
- **Per evaluation** — all persona usages are summed into an `EvaluationReport.total_usage`

Costs are calculated using LiteLLM's built-in pricing data. Token stats appear in the terminal output, and in all three report formats (JSON, Markdown, HTML).

```
TokenUsage
  ├── prompt_tokens       (input tokens sent to the LLM)
  ├── completion_tokens   (output tokens from the LLM)
  ├── total_tokens        (sum)
  └── cost_usd            (estimated cost in USD)
```
