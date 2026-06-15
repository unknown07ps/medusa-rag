"""
Prompt version registry.

Loads prompt templates from YAML files under app/prompts/versions/.
Each version file must define: system_template, user_template, version, and description.

Hot-reloading is supported: calling get_prompt() always reads from disk so you
can A/B test prompts without restarting the service.
"""
import os
from pathlib import Path
from typing import Dict, Optional

import yaml
from pydantic import BaseModel

import structlog

from app.core.config import settings
from app.monitoring.metrics import ACTIVE_PROMPT_VERSION

logger = structlog.get_logger(__name__)


class PromptTemplate(BaseModel):
    version: str
    description: str
    system_template: str
    user_template: str
    max_context_chunks: int = 5
    temperature_override: Optional[float] = None


class PromptRegistry:
    def __init__(self, store_path: str):
        self.store_path = Path(store_path)
        self._cache: Dict[str, PromptTemplate] = {}

    def _load_from_disk(self, version: str) -> PromptTemplate:
        filepath = self.store_path / f"{version}.yaml"
        if not filepath.exists():
            raise FileNotFoundError(f"Prompt version '{version}' not found at {filepath}")
        with open(filepath) as f:
            data = yaml.safe_load(f)
        return PromptTemplate(**data)

    def get_prompt(self, version: Optional[str] = None) -> PromptTemplate:
        v = version or settings.DEFAULT_PROMPT_VERSION
        try:
            template = self._load_from_disk(v)
            ACTIVE_PROMPT_VERSION.labels(version=v).set(1)
            return template
        except FileNotFoundError:
            logger.warning(
                "Prompt version not found, falling back to default",
                requested=v,
                default=settings.DEFAULT_PROMPT_VERSION,
            )
            return self._load_from_disk(settings.DEFAULT_PROMPT_VERSION)

    def list_versions(self) -> list[str]:
        return [p.stem for p in self.store_path.glob("*.yaml")]

    def format_prompt(
        self,
        template: PromptTemplate,
        context: str,
        query: str,
    ) -> tuple[str, str]:
        system = template.system_template
        user = template.user_template.format(context=context, query=query)
        return system, user


prompt_registry = PromptRegistry(settings.PROMPT_STORE_PATH)
