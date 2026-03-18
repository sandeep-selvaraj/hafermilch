---
icon: lucide/cpu
---

# LLM Providers

Each persona declares which LLM it uses in its `llm:` block. hafermilch uses [LiteLLM](https://docs.litellm.ai/) as a unified gateway, giving you access to **100+ LLM providers** through a single configuration format. The most common providers are documented below.

---

## OpenAI

```yaml
llm:
  provider: openai
  model: gpt-4o
  temperature: 0.4
```

The API key is read from `OPENAI_API_KEY` in your environment or `.env` file. You can also set it directly in the persona YAML (not recommended for shared repos):

```yaml
llm:
  provider: openai
  model: gpt-4o
  api_key: sk-...
```

### Vision support

GPT-4o and other vision-capable models automatically receive a screenshot of each page alongside the accessibility tree. Set `temperature` lower (0.2–0.4) for more deterministic browser actions.

---

## Azure OpenAI

Azure deployments are detected automatically when `base_url` is set:

```yaml
llm:
  provider: openai
  model: gpt-4o
  base_url: "https://your-resource.openai.azure.com/"
  api_version: "2024-02-01"
```

The Azure API key is read from `AZURE_OPENAI_API_KEY`.

| Setting | Azure env var |
|---|---|
| API key | `AZURE_OPENAI_API_KEY` |
| Endpoint | `base_url` in the persona YAML |
| API version | `api_version` in the persona YAML |

---

## Gemini

```yaml
llm:
  provider: gemini
  model: gemini-2.0-flash
  temperature: 0.5
```

The API key is read from `GOOGLE_API_KEY`.

### Recommended models

| Model | Notes |
|---|---|
| `gemini-2.0-flash` | Fast, cheap, vision-capable — recommended |
| `gemini-1.5-pro` | More capable reasoning, higher cost |
| `gemini-2.0-flash-lite` | Cheapest option for non-critical personas |

---

## Ollama

Run models locally — no API key required.

```yaml
llm:
  provider: ollama
  model: llava
```

By default, hafermilch connects to `http://localhost:11434`. Override with `OLLAMA_HOST` in your environment:

```bash
OLLAMA_HOST=http://192.168.1.10:11434
```

Or per-persona:

```yaml
llm:
  provider: ollama
  model: llava
  base_url: "http://192.168.1.10:11434"
```

The per-persona `base_url` takes precedence over `OLLAMA_HOST`.

### Vision support

Use a multimodal model like `llava` or `bakllava` to enable screenshot-based context:

```yaml
llm:
  provider: ollama
  model: llava
```

Text-only models (e.g. `llama3`, `mistral`) only receive the accessibility tree.

---

## Other providers

Since hafermilch uses LiteLLM under the hood, any provider LiteLLM supports will work. Set the appropriate `provider` and `model` values:

```yaml
llm:
  provider: anthropic
  model: claude-3-5-sonnet-20241022
  temperature: 0.4
```

Refer to the [LiteLLM provider list](https://docs.litellm.ai/docs/providers) for the full set of supported providers and their configuration.

---

## Provider summary

| Provider | `provider:` value | API key env var | Vision |
|---|---|---|---|
| OpenAI | `openai` | `OPENAI_API_KEY` | GPT-4o, GPT-4-turbo |
| Azure OpenAI | `openai` | `AZURE_OPENAI_API_KEY` | Same as OpenAI |
| Gemini | `gemini` | `GOOGLE_API_KEY` | All Gemini 1.5+ models |
| Ollama | `ollama` | — (local) | `llava`, `bakllava` |
| Any LiteLLM provider | see [docs](https://docs.litellm.ai/docs/providers) | varies | varies |

---

## Mixing providers across personas

You can use different providers for different personas in the same plan. This is useful for cost optimisation — run the nuanced personas on a powerful model and the simpler ones on a fast/cheap one:

```yaml
# examples/personas/tech_expert.yaml
llm:
  provider: openai
  model: gpt-4o
  temperature: 0.3

# examples/personas/office_clerk.yaml
llm:
  provider: gemini
  model: gemini-2.0-flash
  temperature: 0.7

# examples/personas/startup_founder.yaml
llm:
  provider: ollama
  model: llava
```
