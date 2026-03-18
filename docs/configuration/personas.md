---
icon: lucide/user-round
---

# Personas

Personas are defined in YAML files inside a directory you pass with `--personas-dir`. Each file maps to one persona and is referenced by its `name` field in plan files.

---

## Full schema

```yaml
# Required
name: qa_engineer                    # (1)!
display_name: "QA Engineer"          # (2)!
description: >                       # (3)!
  Methodical tester who hunts for edge cases and broken states.

# Character definition
background: >                        # (4)!
  5 years in QA at a fintech company. Instinctively tries to break things —
  submits empty forms, clicks back mid-flow, resizes the window.

goals:                               # (5)!
  - Find broken states and edge cases
  - Check form validation and error messages
  - Verify navigation is consistent

expertise_level: intermediate        # (6)!
technical: true                      # (7)!

# LLM backend
llm:                                 # (8)!
  provider: openai                   # (9)!
  model: gpt-4o                      # (10)!
  temperature: 0.3                   # (11)!
  api_key: sk-...                    # (12)!
  base_url: https://...              # (13)!
  api_version: "2024-02-01"          # (14)!

# Scoring
scoring_dimensions:                  # (15)!
  - name: Robustness
    description: How well does the UI handle unexpected input and edge cases?
    weight: 2.0
  - name: Error Handling
    description: Are error messages clear and recoverable?
    weight: 1.5
```

1. **`name`** — unique identifier. Referenced in plan `personas:` lists. Use snake_case.
2. **`display_name`** — shown in CLI output and reports. Can include spaces.
3. **`description`** — one-line summary used in system prompts.
4. **`background`** — rich prose paragraph describing the persona's professional history and instincts. Injected verbatim into the LLM system prompt.
5. **`goals`** — bullet list of what this persona is trying to accomplish. Guides the LLM toward persona-appropriate behavior.
6. **`expertise_level`** — `beginner`, `intermediate`, or `expert`. Influences tone and depth of critique.
7. **`technical`** — `true` / `false`. Technical personas receive more detail in prompts (e.g., accessibility tree structure explanation).
8. **`llm`** — LLM configuration block. See [LLM Providers](llm-providers.md) for details.
9. **`provider`** — any LiteLLM-supported provider: `openai`, `gemini`, `ollama`, `anthropic`, etc.
10. **`model`** — model name as the provider expects it.
11. **`temperature`** — float 0.0–2.0. Lower = more deterministic actions.
12. **`api_key`** — optional. Falls back to the `OPENAI_API_KEY` / `GOOGLE_API_KEY` environment variable.
13. **`base_url`** — optional. Overrides the default API endpoint. Useful for Azure OpenAI or custom Ollama hosts.
14. **`api_version`** — Azure OpenAI only.
15. **`scoring_dimensions`** — list of dimensions the LLM will score this persona's experience on. Each dimension gets a 0–10 score and a rationale in the report.

---

## Fields reference

### `expertise_level`

| Value | Effect |
|---|---|
| `beginner` | Prompts ask the LLM to behave naively, avoid jargon, and express confusion freely |
| `intermediate` | Balanced — notices UX patterns but not deeply technical |
| `expert` | Prompts push for technical critique: API consistency, error handling, performance signals |

### `scoring_dimensions`

Each dimension in `scoring_dimensions` contributes to the persona's final report. The LLM is asked to score each dimension independently and provide a rationale. The `weight` field is metadata for your own weighting logic — hafermilch currently includes it in the report as-is.

---

## Example personas

=== "Senior Engineer"

    ```yaml
    name: tech_expert
    display_name: "Senior Engineer"
    description: Experienced developer with high standards for API consistency and DX.

    background: >
      10 years building B2B SaaS. Immediately notices inconsistent error messages,
      missing loading states, and accessibility violations.

    goals:
      - Evaluate technical quality of the interface
      - Identify accessibility and semantic HTML issues
      - Check error handling and edge case behavior

    expertise_level: expert
    technical: true

    llm:
      provider: ollama
      model: gpt-oss:20b
      temperature: 0.4

    scoring_dimensions:
      - name: Technical Quality
        description: API consistency, error messages, and developer-facing signals.
        weight: 2.0
      - name: Accessibility
        description: Semantic structure, ARIA labels, keyboard navigation.
        weight: 1.5
    ```

=== "Office Clerk"

    ```yaml
    name: office_clerk
    display_name: "Office Clerk"
    description: Non-technical user who needs everything self-explanatory.

    background: >
      Administrative assistant. Uses Excel and email daily.
      Gets confused by technical jargon and multi-step flows.

    goals:
      - Complete tasks without reading documentation
      - Understand buttons from their labels
      - Not feel overwhelmed or lost

    expertise_level: beginner
    technical: false

    llm:
      provider: ollama
      model: gpt-oss:20b
      temperature: 0.7

    scoring_dimensions:
      - name: Clarity
        description: Are labels and flows self-explanatory?
        weight: 2.0
      - name: Onboarding
        description: How easy is it to start without help?
        weight: 1.5
    ```

=== "Startup Founder"

    ```yaml
    name: startup_founder
    display_name: "Startup Founder"
    description: Time-pressured decision-maker who cares about value, not features.

    background: >
      Running a 10-person startup. Evaluating tools quickly. Cares deeply about
      time-to-value, pricing transparency, and whether the product solves a real problem.

    goals:
      - Understand the value proposition immediately
      - Get to the "aha moment" as fast as possible
      - Assess whether pricing is fair and transparent

    expertise_level: intermediate
    technical: false

    llm:
      provider: ollama
      model: gpt-oss:20b
      temperature: 0.6

    scoring_dimensions:
      - name: Value Clarity
        description: Is the value proposition immediately obvious?
        weight: 2.0
      - name: Time to Value
        description: How fast can a new user get something meaningful done?
        weight: 2.0
    ```
