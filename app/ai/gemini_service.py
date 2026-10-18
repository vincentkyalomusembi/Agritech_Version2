from functools import lru_cache

from google import genai

from app.ai.prompts import LEGACY_SYSTEM_PROMPT, SYSTEM_PROMPT
from app.core.config import settings
import json


def build_text_prompt(context: dict) -> str:
    """Bounded advice prompt shared by every text provider."""
    return f"""
{LEGACY_SYSTEM_PROMPT}

Farmer Data

{context}

Return at most six short bullet points covering crop varieties, livestock,
disease risks, fertilizer/feed, farming action, and market opportunity. Omit
categories not supported by the supplied data.
"""


@lru_cache(maxsize=1)
def _gemini_client() -> genai.Client:
    # One SDK client per process keeps its HTTP connections warm.
    return genai.Client(api_key=settings.GEMINI_API_KEY)


class GeminiService:
    """
    Handles communication with Gemini.
    """

    def __init__(self):
        # ---- Copilot Improvement ----
        # Fail before constructing an SDK client with an empty credential so
        # configuration faults are clear and do not trigger avoidable retries.
        # ---- End Improvement ----
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("Gemini API is not configured.")
        self.client = _gemini_client()

    def generate_recommendation(
        self,
        context: dict,
    ) -> str:
        """
        Generate an agricultural recommendation.
        """

        # ---- Copilot Improvement ----
        # Ask for a bounded, structured answer and trim overlong provider text
        # so USSD/SMS follow-up messages remain concise and predictable.
        # ---- End Improvement ----
        prompt = build_text_prompt(context)

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        return (response.text or "").strip()[:1200]

    def generate_structured_recommendation(self, context: dict) -> dict:
        """Ask Gemini to select IDs from the supplied catalogue and return JSON."""
        schema = {
            "type": "OBJECT",
            "properties": {
                "primary_id": {"type": "STRING"},
                "alternative_ids": {"type": "ARRAY", "items": {"type": "STRING"}},
                "why_fit": {"type": "STRING"},
                "planting_window": {"type": "STRING", "nullable": True},
                "spacing": {"type": "STRING", "nullable": True},
                "actions": {"type": "ARRAY", "items": {"type": "STRING"}},
            },
            "required": ["primary_id", "alternative_ids", "why_fit", "planting_window", "spacing", "actions"],
        }
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{SYSTEM_PROMPT}\n\nDATA:\n{json.dumps(context, ensure_ascii=False, default=str)}",
            config={"response_mime_type": "application/json", "response_schema": schema},
        )
        if not response.text:
            raise RuntimeError("Gemini returned an empty structured response.")
        return json.loads(response.text)
