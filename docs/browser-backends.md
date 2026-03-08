---
icon: lucide/globe
---

# Browser Backends

hafermilch supports two browser backends. Select one with the `--browser` flag.

---

## Playwright (default)

Playwright runs a real Chromium browser as a Python-native library. It captures the page's **accessibility tree** via `aria_snapshot()` and interacts using **CSS selectors and ARIA roles**.

```bash
uv run hafermilch run examples/plans/saas_onboarding.yaml --browser playwright
```

### How it works

1. Playwright launches a Chromium instance (headless by default)
2. `aria_snapshot()` on the `body` element produces a YAML-like accessibility tree
3. The LLM reads the tree and returns a `BrowserAction` with a **CSS selector**
4. Playwright executes the action (`click`, `fill`, `navigate`, …)

### Strengths

- No extra dependencies beyond `playwright install chromium`
- Precise, deterministic selector targeting
- Full vision support — screenshots are sent to vision-capable models
- `--no-headless` flag lets you watch the browser live

### Best for

- Products you own and whose DOM structure you know
- Authenticated flows (login, checkout) where selectors are stable
- Regression testing — comparing scores across deploys
- Environments where you cannot install Node.js

---

## agent-browser

[agent-browser](https://github.com/vercel-labs/agent-browser) (by Vercel Labs) is a Rust CLI purpose-built for LLM-driven browsing. Its `snapshot` command returns an accessibility tree where every interactive element carries a short **`@ref` handle** (e.g. `@e1`, `@e7`). The LLM picks refs directly — no CSS knowledge required.

```bash
npm install -g agent-browser

uv run hafermilch run examples/plans/saas_onboarding.yaml --browser agent-browser
```

### How it works

1. hafermilch calls the `agent-browser` CLI via subprocess for each action
2. The `snapshot` command returns a tree like:
   ```
   - heading "Sign up" [ref=@e1]
   - textbox "Email" [ref=@e3]
   - button "Create account" [ref=@e7]
   ```
3. The LLM reads the tree and returns a `BrowserAction` with a **`@ref` selector**
4. hafermilch calls `agent-browser click @e7`

### Strengths

- LLM never needs to guess CSS selectors
- More resilient on JS-heavy apps where selectors are generated or unstable
- Semantic, human-like navigation ("the button labelled 'Create account'")
- Session-isolated — each run starts fresh

### Best for

- Exploratory evaluations of unfamiliar third-party products
- Products using heavy React/Vue/Angular frameworks with unstable selectors
- When the LLM keeps choosing wrong selectors with Playwright

---

## Comparison

| | Playwright | agent-browser |
|---|---|---|
| Selector style | CSS / ARIA role | `@ref` from snapshot |
| LLM needs DOM knowledge | Yes | No |
| Stability on JS-heavy apps | Can be brittle | More resilient |
| Extra install | `playwright install chromium` | `npm i -g agent-browser` |
| Vision support | :material-check: | :material-check: |
| Headless control | `--no-headless` flag | Managed by daemon |
| Language | Python (native) | Rust CLI (subprocess) |

---

## Which should I pick?

!!! tip "Start with Playwright"
    If you're evaluating a product you own or build, start with Playwright. It's zero-extra-setup and gives you full control.

!!! tip "Switch to agent-browser when Playwright struggles"
    If your LLM keeps selecting wrong elements, or you're evaluating a third-party product with an unfamiliar DOM, switch to `--browser agent-browser`. The `@ref` approach is much more forgiving.
