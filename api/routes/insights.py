"""Insight endpoints.

The route layer does nothing but resolve a window, call the engine, and
serialise. No thresholds, no arithmetic, no filtering rules live here — an
analytics decision made in a router is a decision that cannot be unit-tested
without a web server.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.analysis.models import InsightType
from app.api.deps import AnalysisServiceDep, CurrentUser
from app.schemas.insight import AnalysisResultRead, InsightRead

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get(
    "",
    response_model=AnalysisResultRead,
    summary="Run the analysis engine over a window",
)
def read_insights(
    user: CurrentUser,
    analysis: AnalysisServiceDep,
    start_date: Annotated[date | None, Query(description="Window start, inclusive")] = None,
    end_date: Annotated[date | None, Query(description="Window end, inclusive")] = None,
    days: Annotated[
        int | None, Query(ge=1, le=730, description="Trailing window length")
    ] = None,
) -> AnalysisResultRead:
    """Every insight the data supports, plus what it could not support.

    Defaults to the trailing 90 days — long enough for the ≥ 8 complete weeks
    that behavioural analysis requires, and two full calendar months for the
    monthly comparison.

    An empty ``insights`` list with a populated ``notices`` list is a normal,
    designed response, not an error.
    """
    result = analysis.run(user, start_date=start_date, end_date=end_date, days=days)
    return AnalysisResultRead.from_domain(result)


@router.get(
    "/types",
    response_model=list[str],
    summary="The closed set of insight types this engine can emit",
)
def read_insight_types() -> list[str]:
    """Useful to a renderer building a lookup table of ``title_key`` strings."""
    return [insight_type.value for insight_type in InsightType]


@router.get(
    "/{insight_type}",
    response_model=list[InsightRead],
    summary="Insights of one type",
)
def read_insights_of_type(
    insight_type: InsightType,
    user: CurrentUser,
    analysis: AnalysisServiceDep,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    days: Annotated[int | None, Query(ge=1, le=730)] = None,
) -> list[InsightRead]:
    """Filtered view of the same run. Returns ``[]`` when nothing qualifies."""
    result = analysis.run(user, start_date=start_date, end_date=end_date, days=days)
    matching = result.by_type(insight_type) + tuple(
        notice for notice in result.notices if notice.type is insight_type
    )
    return [InsightRead.from_domain(insight) for insight in matching]
