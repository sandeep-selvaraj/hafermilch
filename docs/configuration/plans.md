---
icon: lucide/map
---

# Plans

A plan tells hafermilch *what* to test and *where*. Plans are YAML files you pass as the first argument to `hafermilch run`.

---

## Full schema

```yaml
name: myapp_evaluation               # (1)!
description: >                       # (2)!
  Evaluate the onboarding and core feature flow for MyApp.

target_url: "https://myapp.com"      # (3)!

personas:                            # (4)!
  - tech_expert
  - office_clerk

tasks:                               # (5)!
  - name: sign_up                    # (6)!
    description: Registration flow   # (7)!
    start_url: "https://myapp.com/signup"  # (8)!
    steps:                           # (9)!
      - instruction: >               # (10)!
          Find the sign-up form and register using realistic test data.
          Note any friction or confusing fields.
        max_actions: 12              # (11)!

  - name: core_feature
    description: Use the main feature
    steps:
      - instruction: >
          Navigate to the main feature and try to use it as a first-time user.
          Describe what works well and what is confusing.
        max_actions: 8
      - instruction: >
          Try to find the pricing or upgrade page. Note how clearly
          the value proposition and cost are communicated.
        max_actions: 6
```

1. **`name`** — identifier for the plan. Used in report filenames and CLI output.
2. **`description`** — human-readable summary. Not sent to the LLM.
3. **`target_url`** — the base URL of the product being evaluated. Used as the navigation start if a task doesn't define its own `start_url`.
4. **`personas`** — list of persona `name` values to run. Each must correspond to a YAML file in `--personas-dir`.
5. **`tasks`** — ordered list of task objects. Tasks run sequentially, in order.
6. **`name`** — unique task identifier. Appears in findings and the report.
7. **`description`** — short human label for the task.
8. **`start_url`** — optional. If provided, the browser navigates here before the first step. Falls back to `target_url`.
9. **`steps`** — list of step objects within the task.
10. **`instruction`** — natural language prompt injected into the LLM's action prompt. Write it from the persona's perspective.
11. **`max_actions`** — maximum LLM turns for this step. Prevents infinite loops. Typical range: 5–15.

---

## Tips for writing good instructions

**Be goal-oriented, not prescriptive.** Let the LLM navigate naturally:

```yaml
# Good — describes the goal
instruction: >
  Find the sign-up button and create an account using test data.
  Note any confusing fields or error messages.

# Too prescriptive — breaks if the page changes
instruction: >
  Click the button with id="signup-btn", then fill the email field
  with "test@example.com" and the password field with "Password123".
```

**Mention what to observe.** The observation is what goes into the finding:

```yaml
instruction: >
  Navigate to the pricing page. Note whether plans and pricing are
  clearly explained and whether the differences between tiers are obvious.
```

**Keep max_actions proportional to complexity.** A single-field login needs 4–5 actions. A multi-step checkout might need 15+.

---

## Multi-step tasks

Each task can have multiple steps. Steps run in order and share the same browser session, so the browser state carries over:

```yaml
tasks:
  - name: full_onboarding
    steps:
      # Step 1: Land on the homepage
      - instruction: >
          You just arrived at the homepage. Observe what the product does
          and whether the value proposition is immediately clear.
        max_actions: 3

      # Step 2: Sign up (browser is still on homepage)
      - instruction: >
          Find the sign-up flow and register as a new user.
        max_actions: 10

      # Step 3: First use (browser is now logged in)
      - instruction: >
          You are now logged in. Find and use the product's core feature.
        max_actions: 8
```

---

## Using start_url

If different tasks start at different URLs (e.g., you want to test the dashboard directly without going through signup), use `start_url`:

```yaml
tasks:
  - name: dashboard_cold
    start_url: "https://myapp.com/dashboard"
    steps:
      - instruction: >
          You have been given direct access to the dashboard. Without prior
          context, assess how quickly you understand what's going on.
        max_actions: 6
```
