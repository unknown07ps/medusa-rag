from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.prompts.registry import PromptTemplate, prompt_registry

router = APIRouter()


class PromptVersionInfo(BaseModel):
    version: str
    description: str
    max_context_chunks: int
    temperature_override: Optional[float]


class PromptListResponse(BaseModel):
    versions: List[str]
    default: str


@router.get("", response_model=PromptListResponse)
async def list_prompt_versions():
    from app.core.config import settings
    return PromptListResponse(
        versions=prompt_registry.list_versions(),
        default=settings.DEFAULT_PROMPT_VERSION,
    )


@router.get("/{version}", response_model=PromptVersionInfo)
async def get_prompt_version(version: str):
    try:
        template = prompt_registry.get_prompt(version)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Prompt version '{version}' not found.")
    return PromptVersionInfo(
        version=template.version,
        description=template.description,
        max_context_chunks=template.max_context_chunks,
        temperature_override=template.temperature_override,
    )
