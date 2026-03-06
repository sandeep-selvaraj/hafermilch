class HafermilchError(Exception):
    """Base error for all hafermilch exceptions."""


class PersonaLoadError(HafermilchError):
    """Raised when a persona YAML fails to load or validate."""


class LLMProviderError(HafermilchError):
    """Raised when an LLM provider call fails."""


class BrowserError(HafermilchError):
    """Raised when a browser action fails."""


class EvaluationError(HafermilchError):
    """Raised when the evaluation pipeline encounters a fatal error."""
