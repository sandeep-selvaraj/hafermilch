---
icon: lucide/terminal
---

# CLI Reference

hafermilch is invoked via `uv run hafermilch`. All commands support `--help`.

---

## `run`

Run an evaluation plan against a live product URL.

```
uv run hafermilch run <plan> [OPTIONS]
```

### Arguments

| Argument | Description |
|---|---|
| `plan` | Path to the evaluation plan YAML file (**required**) |

### Options

| Flag | Default | Description |
|---|---|---|
| `--personas-dir` / `-p` | `examples/personas` | Directory containing persona YAML files |
| `--output` / `-o` | `reports` | Directory to write `report.json` and `report.md` |
| `--browser` / `-b` | `playwright` | Browser backend: `playwright` or `agent-browser` |
| `--headless` / `--no-headless` | headless | Show or hide the browser window (Playwright only) |
| `--verbose` / `-v` | off | Enable debug logging |

### Examples

```bash
# Basic run with defaults
uv run hafermilch run examples/plans/saas_onboarding.yaml

# Custom personas dir and output location
uv run hafermilch run plans/myapp.yaml \
  --personas-dir personas/ \
  --output results/myapp/

# Watch the browser in action
uv run hafermilch run plans/myapp.yaml --no-headless

# Use agent-browser backend with verbose logging
uv run hafermilch run plans/myapp.yaml \
  --browser agent-browser \
  --verbose
```

---

## `validate`

Validate persona and/or plan YAML files without running an evaluation.

```
uv run hafermilch validate [OPTIONS]
```

### Options

| Flag | Description |
|---|---|
| `--personas-dir` / `-p` | Validate all persona YAML files in the given directory |
| `--plan` | Validate a single plan YAML file |

You can pass one or both flags. At least one is required.

### Examples

```bash
# Validate personas only
uv run hafermilch validate --personas-dir examples/personas

# Validate a plan only
uv run hafermilch validate --plan examples/plans/saas_onboarding.yaml

# Validate both
uv run hafermilch validate \
  --personas-dir examples/personas \
  --plan examples/plans/saas_onboarding.yaml
```

### Example output

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

## `--version`

Print the current version and exit.

```bash
uv run hafermilch --version
# hafermilch 0.1.0
```

---

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Configuration error (invalid YAML, missing persona, etc.) or evaluation error |
