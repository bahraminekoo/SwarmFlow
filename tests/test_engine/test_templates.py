"""Tests for the YAML template system."""

from __future__ import annotations

from pathlib import Path

import pytest

from swarmflow.engine.templates import (
    TeamTemplate,
    WorkerTemplate,
    list_templates,
    load_template,
    load_template_by_name,
)

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "src" / "swarmflow" / "templates"


class TestTemplates:
    def test_load_hedge_fund_template(self):
        tmpl = load_template(TEMPLATES_DIR / "hedge-fund.yaml")
        assert tmpl.name == "hedge-fund"
        assert len(tmpl.workers) == 6
        assert tmpl.default_goal
        configs = tmpl.get_worker_configs()
        assert "buffett-analyst" in configs
        assert "risk-manager" in configs

    def test_load_research_lab_template(self):
        tmpl = load_template(TEMPLATES_DIR / "research-lab.yaml")
        assert tmpl.name == "research-lab"
        assert len(tmpl.workers) == 5
        assert "survey-lead" in tmpl.get_worker_configs()

    def test_load_startup_pitch_template(self):
        tmpl = load_template(TEMPLATES_DIR / "startup-pitch.yaml")
        assert tmpl.name == "startup-pitch"
        assert len(tmpl.workers) == 4
        assert "market-strategist" in tmpl.get_worker_configs()

    def test_load_template_by_name(self):
        tmpl = load_template_by_name("hedge-fund")
        assert tmpl.name == "hedge-fund"

    def test_load_nonexistent_template(self):
        with pytest.raises(FileNotFoundError):
            load_template_by_name("nonexistent-template")

    def test_list_templates(self):
        names = list_templates()
        assert "hedge-fund" in names
        assert "research-lab" in names
        assert "startup-pitch" in names
        assert len(names) >= 3

    def test_worker_configs_dict(self):
        tmpl = TeamTemplate(
            name="test",
            workers=[
                WorkerTemplate(name="w1", system_prompt="Prompt 1"),
                WorkerTemplate(name="w2", system_prompt="Prompt 2"),
            ],
        )
        configs = tmpl.get_worker_configs()
        assert configs == {"w1": "Prompt 1", "w2": "Prompt 2"}
