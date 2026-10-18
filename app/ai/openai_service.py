import json

from app.ai.gemini_service import build_text_prompt
from app.ai.prompts import SYSTEM_PROMPT
from app.core.config import settings

# Same fields as the Gemini schema; strict JSON-schema mode needs every key
# listed as required, with nullability expressed in the type.
STRUCTURED_SCHEMA = {
    "type": "object",
    "properties": {
        "primary_id": {"type": "string"},
        "alternative_ids": {"type": "array", "items": {"type": "string"}},
        "why_fit": {"type": "string"},
        "planting_window": {"type": ["string", "null"]},
        "spacing": {"type": ["string", "null"]},
        "actions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["primary_id", "alternative_ids", "why_fit", "planting_window", "spacing", "actions"],
    "additionalProperties": False,
}


class OpenAIService:
    """OpenAI counterpart of GeminiService with the same two methods."""

    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OpenAI API is not configured.")
        from app.recommendations.ai_services.provider import _openai_client

        self.client = _openai_client()

    def generate_recommendation(self, context: dict) -> str:
        response = self.client.responses.create(
            model=settings.OPENAI_MODEL,
            input=build_text_prompt(context),
        )
        return (response.output_text or "").strip()[:1200]

    def generate_structured_recommendation(self, context: dict) -> dict:
        """Select catalogue IDs from the supplied context and return JSON."""
        response = self.client.responses.create(
            model=settings.OPENAI_MODEL,
            input=f"{SYSTEM_PROMPT}\n\nDATA:\n{json.dumps(context, ensure_ascii=False, default=str)}",
            text={"format": {"type": "json_schema", "name": "recommendation", "schema": STRUCTURED_SCHEMA, "strict": True}},
        )
        if not response.output_text:
            raise RuntimeError("OpenAI returned an empty structured response.")
        return json.loads(response.output_text)
