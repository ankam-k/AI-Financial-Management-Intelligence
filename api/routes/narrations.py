"""Narration endpoints."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import AnalysisServiceDep, CurrentUser, LLMClientDep, NarrationServiceDep
from app.domain.errors import NotFoundError
from app.narration.payload import allowed_numbers, build_payload
from app.narration.prompts import OUTPUT_SCHEMA, build_prompt
from app.schemas.narration import (
    LLMStatusRead,
    NarratedAnalysisRead,
    PromptPreviewRead,
)

router = APIRouter(prefix="/api/narrations", tags=["narrations"])


@router.get(
    "",
    response_model=NarratedAnalysisRead,
    summary="Analyse a window and explain every insight",
)
def read_narrations(
    user: CurrentUser,
    narration: NarrationServiceDep,
    start_date: Annotated[date | None, Query(description="Window start, inclusive")] = None,
    end_date: Annotated[date | None, Query(description="Window end, inclusive")] = None,
    days: Annotated[int | None, Query(ge=1, le=730)] = None,
    generate: Annotated[
        bool, Query(description="Set false to force template narration")
    ] = True,
) -> NarratedAnalysisRead:
    """Every insight, explained in five sections.

    Works with no model installed: narration falls back to hand-written
    templates, and `narration.provider` reports which you got. Nothing factual
    differs between the two — only fluency.

    Data-sufficiency notices are explained too. A new user's most likely
    response is a plain account of what is missing, which is the designed
    behaviour rather than an empty result.
    """
    return NarratedAnalysisRead.from_domain(
        narration.run(
            user,
            start_date=start_date,
            end_date=end_date,
            days=days,
            allow_generation=generate,
        )
    )


@router.get(
    "/status",
    response_model=LLMStatusRead,
    summary="Whether a model is configured and reachable",
)
def read_status(client: LLMClientDep) -> LLMStatusRead:
    """Reports without raising, so a missing model is never an error here."""
    return LLMStatusRead.from_domain(client.health())


@router.get(
    "/prompt/{insight_id}",
    response_model=PromptPreviewRead,
    summary="The exact prompt one insight would produce",
)
def read_prompt(
    insight_id: str,
    user: CurrentUser,
    analysis: AnalysisServiceDep,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    days: Annotated[int | None, Query(ge=1, le=730)] = None,
) -> PromptPreviewRead:
    """Inspect what the model is given, and what it will be held to.

    Insight ids are content-addressed, so an id from `GET /api/insights` over
    the same window resolves here.
    """
    result = analysis.run(user, start_date=start_date, end_date=end_date, days=days)

    for insight in result.insights + result.notices:
        if insight.id == insight_id:
            payload = build_payload(insight)
            system, user_prompt = build_prompt(
                payload, insight.tier, display_name=user.display_name
            )
            return PromptPreviewRead(
                insight_id=insight.id,
                insight_type=insight.type.value,
                tier=insight.tier.value,
                system_prompt=system,
                user_prompt=user_prompt,
                output_schema=OUTPUT_SCHEMA,
                allowed_numbers=sorted(allowed_numbers(payload)),
            )

    raise NotFoundError(
        f"No insight '{insight_id}' in this window. Insight ids are derived from "
        "the window, so the same window must be requested here."
    )
