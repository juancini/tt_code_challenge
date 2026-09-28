from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from exceptions.exception import InvalidEvent
from services.team_insight import generate_team_insight

router = APIRouter(prefix="/teams", tags=["teams"])


class TeamInsightRequest(BaseModel):
    events: list[dict[str, Any]]


@router.post("/{team_id}/insights")
def create_team_insight(team_id: str, request: TeamInsightRequest):
    try:
        return generate_team_insight(
            team_id=team_id, events=request.events, llm_client=get_llm_client()
        )
    except InvalidEvent as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
