from __future__ import annotations

import logging
import os
import re
from pathlib import Path

import yaml
from pydantic import ValidationError

from hafermilch.core.exceptions import PersonaLoadError
from hafermilch.core.models import EvaluationPlan, Persona

logger = logging.getLogger(__name__)


def _interpolate_env_vars(text: str) -> str:
    """Replace ``${VAR}`` placeholders with their environment variable values.

    Unresolved variables are left as-is and a warning is logged.
    """

    def _replace(m: re.Match) -> str:
        name = m.group(1)
        value = os.environ.get(name)
        if value is None:
            logger.warning("Environment variable '%s' is not set — placeholder left as-is", name)
            return m.group(0)
        logger.debug("Resolved ${%s} → %s", name, value[:3] + "***" if len(value) > 3 else "***")
        return value

    return re.sub(r"\$\{(\w+)\}", _replace, text)


def load_persona(path: Path) -> Persona:
    """Load and validate a single persona YAML file.

    ``${ENV_VAR}`` placeholders anywhere in the file are substituted with the
    corresponding environment variable before parsing.
    """
    try:
        raw = yaml.safe_load(_interpolate_env_vars(path.read_text()))
        return Persona.model_validate(raw)
    except FileNotFoundError as exc:
        raise PersonaLoadError(f"Persona file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise PersonaLoadError(f"YAML parse error in {path}: {exc}") from exc
    except ValidationError as exc:
        raise PersonaLoadError(f"Invalid persona in {path}:\n{exc}") from exc


def load_personas_from_dir(directory: Path) -> dict[str, Persona]:
    """Load all *.yaml / *.yml files in a directory and index them by name."""
    paths = sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml"))
    if not paths:
        raise PersonaLoadError(f"No persona YAML files found in: {directory}")
    personas: dict[str, Persona] = {}
    for p in paths:
        persona = load_persona(p)
        personas[persona.name] = persona
    return personas


def load_plan(path: Path) -> EvaluationPlan:
    """Load and validate an evaluation plan YAML file.

    ``${ENV_VAR}`` placeholders anywhere in the file are substituted with the
    corresponding environment variable before parsing.
    """
    try:
        raw = yaml.safe_load(_interpolate_env_vars(path.read_text()))
        return EvaluationPlan.model_validate(raw)
    except FileNotFoundError as exc:
        raise PersonaLoadError(f"Plan file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise PersonaLoadError(f"YAML parse error in {path}: {exc}") from exc
    except ValidationError as exc:
        raise PersonaLoadError(f"Invalid plan in {path}:\n{exc}") from exc


def resolve_plan_personas(plan: EvaluationPlan, personas: dict[str, Persona]) -> list[Persona]:
    """Resolve the persona names in a plan to loaded Persona objects."""
    resolved: list[Persona] = []
    for name in plan.personas:
        if name not in personas:
            available = ", ".join(personas.keys()) or "none"
            raise PersonaLoadError(
                f"Plan references unknown persona '{name}'. Available: {available}"
            )
        resolved.append(personas[name])
    return resolved
