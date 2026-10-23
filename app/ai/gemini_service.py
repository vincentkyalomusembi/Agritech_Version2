from functools import lru_cache

from google import genai

from app.ai.prompts import LEGACY_SYSTEM_PROMPT, SYSTEM_PROMPT
from app.core.config import settings
import json
import re


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

    def find_vendors(self, item: str, kind: str, county: str, sub_county: str | None = None,
                     ward: str | None = None, limit: int = 3) -> list[dict]:
        """Find real sellers near the farmer using Gemini with Google Search grounding.

        Search grounding cannot be combined with JSON-mode output, so the model
        is asked for a JSON array in plain text and the result is validated here.
        """
        from google.genai import types

        place = ", ".join(part for part in (ward, sub_county, county + " County", "Kenya") if part)
        product = "seed or seedlings" if kind == "crop" else "animals or breeding stock"
        prompt = (
            f"Find up to {limit} real agrovets, seed companies or breeders in or near {place} that sell "
            f"{product} for: {item}. Use only what you find in search results. Never invent a business, "
            "phone number or price; use null for anything you did not find. Return ONLY a JSON array of "
            'objects with keys: name (string), phone (string|null), address (string|null), '
            'price_kes (number|null), unit (string|null), source_url (string|null).'
        )
        response = self.client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]),
        )
        match = re.search(r"\[.*\]", response.text or "", re.S)
        if not match:
            return []
        vendors = []
        for row in json.loads(match.group(0)):
            name = str(row.get("name") or "").strip()
            if not name:
                continue
            phone = re.sub(r"[^\d+]", "", str(row.get("phone") or "")) or None
            price = row.get("price_kes")
            vendors.append({
                "name": name[:120], "phone": phone if phone and len(phone) >= 9 else None,
                "address": (str(row["address"])[:200] if row.get("address") else None),
                "county": county,
                "price_kes": float(price) if isinstance(price, (int, float)) and price > 0 else None,
                "unit": (str(row["unit"])[:40] if row.get("unit") else None),
                "source_url": row.get("source_url"), "distance_km": None, "stock_quantity": None,
            })
        return vendors[:limit]
