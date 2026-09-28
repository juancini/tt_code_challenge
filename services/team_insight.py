from datetime import datetime
from typing import Any

from exceptions.exception import InvalidEvent, InvalidLLMResponse
from services.llm import build_prompt, parse_llm_response


SUPPORTED_TYPES = {
    "pr_opened",
    "pr_merged",
    "deployment",
    "incident",
}


def parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise InvalidEvent("timestamp must be a string")

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidEvent(f"invalid timestamp: {value}") from exc

    if parsed.tzinfo is None:
        raise InvalidEvent("timestamp must include a timezone")

    return parsed.astimezone(timezone.utc)


def validate_event(event: Any) -> tuple[str, datetime, str | None]:
    if not isinstance(event, dict):
        raise InvalidEvent("each event must be an object")

    event_type = event.get("type")
    if event_type not in SUPPORTED_TYPES:
        raise InvalidEvent(f"unsupported event type: {event_type}")

    timestamp = parse_timestamp(event.get("timestamp"))

    event_id = event.get("id")
    requires_id = event_type in {"pr_opened", "pr_merged"}

    if requires_id and not isinstance(event_id, str):
        raise InvalidEvent(f"{event_type} requires a string id")

    if event_id is not None and not isinstance(event_id, str):
        raise InvalidEvent("id must be a string when provided")

    return event_type, timestamp, event_id


def calculate_metrics(events: list[dict[str, Any]]) -> dict[str, int | float | None]:
    opened: dict[str, datetime] = {}
    merged: dict[str, datetime] = {}
    deployments = 0
    incidents = 0

    for event in events:
        event_type, timestamp, event_id = validate_event(event)
        if event_id is None:
            continue

        if event_type == "pr_opened":
            opened[event_id] = timestamp
        elif event_type == "pr_merged":
            merged[event_id] = timestamp
        elif event_type == "deployment":
            deployments += 1
        elif event_type == "incident":
            incidents += 1

    cycle_times = []

    for pr_id, merged_at in merged.items():
        opened_at = opened.get(pr_id)
        if opened_at is not None and merged_at >= opened_at:
            cycle_times.append((merged_at - opened_at).total_seconds() / 3600)

    average_cycle_time = (
        round(sum(cycle_times) / len(cycle_times), 2) if cycle_times else None
    )

    return {
        "merged_prs": len(merged),
        "average_pr_cycle_time_hours": average_cycle_time,
        "deployments": deployments,
        "incidents": incidents,
    }


def generate_team_insight(
    team_id: str,
    events: list[dict[str, Any]],
    llm_client: LLMClient,
) -> dict[str, Any]:
    if not isinstance(team_id, str) or not team_id.strip():
        raise ValueError("team_id must be a non-empty string")

    if not isinstance(events, list):
        raise ValueError("events must be a list")

    metrics = calculate_metrics(events)
    prompt = build_prompt(team_id, metrics)

    last_error: Exception | None = None

    for attempt in range(2):
        try:
            raw_response = llm_client.complete(
                prompt,
                timeout_seconds=5.0,
            )
            insight = parse_llm_response(raw_response)
            break
        except (TimeoutError, ConnectionError) as exc:
            last_error = exc
            if attempt == 1:
                raise RuntimeError("LLM request failed after retry") from exc
        except InvalidLLMResponse:
            raise
    else:
        raise RuntimeError("LLM request failed") from last_error

    return {
        "team_id": team_id,
        "metrics": metrics,
        "insight": insight,
    }
