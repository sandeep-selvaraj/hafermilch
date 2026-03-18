---
icon: lucide/home
---

<div class="hafermilch-hero" markdown="1">
<h1>hafermilch</h1>
<p>Multi-persona LLM agents that autonomously browse and critique your product's UI/UX — in their own voice.</p>

[Get Started](get-started.md){ .md-button .md-button--primary }
[View on GitHub](https://github.com/sandeep-selvaraj/hafermilch){ .md-button }
</div>

:material-language-python: **Python 3.11+** &nbsp;·&nbsp;
:material-robot: **100+ LLM providers via LiteLLM** &nbsp;·&nbsp;
:material-web: **Playwright · agent-browser** &nbsp;·&nbsp;
:material-package-variant: **uv · hatchling**

```bash
uv tool install hafermilch
playwright install chromium
hafermilch run myplan.yaml
```

---

## What is hafermilch?

hafermilch lets you define **personas** — characters with distinct backgrounds, goals, and expertise levels — and point them at any website. Each persona is backed by an LLM and a real browser. They navigate autonomously, form opinions in their own voice, and return structured scores and findings.

You define a persona once. You run it against any product by writing a plan.

---

## How it works

``` mermaid
flowchart LR
    P[Persona YAML\n🧑 background · goals · LLM] --> R
    L[Plan YAML\n🗺️ URL · tasks · steps] --> R
    R[EvaluationRunner] --> B[Browser Agent\nPlaywright or agent-browser]
    B -->|page context| LLM[LLM Provider\nOpenAI · Gemini · Ollama]
    LLM -->|BrowserAction| B
    R --> Rep[Report\nJSON · Markdown]
```

---

## Built-in personas

<div class="persona-grid">
  <div class="persona-card">
    <span class="persona-icon">🧑‍💻</span>
    <h3>Senior Engineer</h3>
    <p>High technical literacy. Notices API inconsistencies, error handling gaps, and developer-experience friction.</p>
  </div>
  <div class="persona-card">
    <span class="persona-icon">🗂️</span>
    <h3>Office Clerk</h3>
    <p>Non-technical. Confused by jargon, overwhelmed by dense layouts. Represents the median business user.</p>
  </div>
  <div class="persona-card">
    <span class="persona-icon">🚀</span>
    <h3>Startup Founder</h3>
    <p>Time-pressured. Cares about time-to-value, pricing clarity, and whether the product solves a real problem.</p>
  </div>
</div>

---

## Example output

```
──────────────── hafermilch v0.1.2 ────────────────
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

Reports are written to `reports/report.json`, `reports/report.md`, and `reports/report.html`.
