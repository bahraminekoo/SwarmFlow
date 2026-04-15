"""YAML template system for defining team archetypes."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class WorkerTemplate(BaseModel):
    name: str
    system_prompt: str


class TeamTemplate(BaseModel):
    name: str
    description: str = ""
    workers: list[WorkerTemplate] = Field(default_factory=list)
    default_goal: str = ""

    def get_worker_configs(self) -> dict[str, str]:
        """Convert worker templates to {name: system_prompt} dict."""
        return {w.name: w.system_prompt for w in self.workers}


def load_template(template_path: str | Path) -> TeamTemplate:
    """Load a team template from a YAML file."""
    path = Path(template_path)
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    return TeamTemplate(**data)


def load_template_by_name(name: str, templates_dir: str | Path | None = None) -> TeamTemplate:
    """Load a built-in or custom template by name."""
    if templates_dir:
        custom_path = Path(templates_dir) / f"{name}.yaml"
        if custom_path.exists():
            return load_template(custom_path)

    # Check built-in templates
    builtin_dir = Path(__file__).parent.parent / "templates"
    builtin_path = builtin_dir / f"{name}.yaml"
    if builtin_path.exists():
        return load_template(builtin_path)

    raise FileNotFoundError(
        f"Template '{name}' not found. Available: {', '.join(list_templates(templates_dir))}"
    )


def list_templates(templates_dir: str | Path | None = None) -> list[str]:
    """List all available template names."""
    templates: set[str] = set()

    # Built-in templates
    builtin_dir = Path(__file__).parent.parent / "templates"
    if builtin_dir.exists():
        for f in builtin_dir.glob("*.yaml"):
            templates.add(f.stem)

    # Custom templates
    if templates_dir:
        custom_dir = Path(templates_dir)
        if custom_dir.exists():
            for f in custom_dir.glob("*.yaml"):
                templates.add(f.stem)

    return sorted(templates)
