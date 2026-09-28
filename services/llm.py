import json
from typing import Any, Protocol
import requests
from requests.adapters import Retry

from exceptions.exception import InvalidLLMResponse


def build_prompt(team_id: str, metrics: dict[str, int | float]) -> str:
    metrics_json = json.dumps(metrics, sort_keys=True)
    promtp = (
        "You are assisting with team-level engineering productivity insights. "
        "Do not evaluate individuals, infer personal performance, or invent data. "
        "Use only the following aggregated metrics. Return JSON with exactly "
        "a string field named summary and an array of string recommendations.\n\n"
        f"Team: {team_id}\n"
        f"Aggregated metrics: {metrics_json}"
    )
    return promtp


def parse_llm_response(response: str) -> dict[str, Any]:
    try:
        parsed = json.loads(response)
    except json.JSONDecodeError as exc:
        raise InvalidLLMResponse("LLM response was not valid JSON") from exc

    if not isinstance(parsed, dict):
        raise InvalidLLMResponse("LLM response must be a JSON object")

    summary = parsed.get("summary")
    recommendations = parsed.get("recommendations")

    if not isinstance(summary, str):
        raise InvalidLLMResponse("summary must be a string")

    if not isinstance(recommendations, list) or not all(
        isinstance(item, str) for item in recommendations
    ):
        raise InvalidLLMResponse("recommendations must be a list of strings")

    return {
        "summary": summary,
        "recommendations": recommendations,
    }


class LLMClient(Protocol):
    api_url = "https://some.api.com"
    session = requests.session()
    # Desing Doc requires one retry
    retries = Retry(total=1, backoff_factor=1, status_forcelist=[502, 503, 504])

    def complete(self, prompt: str, timeout_seconds: float) -> str:
        # commented out because we dont want to hit an externar service for this code challenge
        # self.session.get(f"{self.api_url}/{prompt}", timeout=timeout_seconds)
        return f"{self.api_url}/{prompt}"
