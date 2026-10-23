import json
import logging
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.ai.llm import LLMRouter
from app.catalogue.model import CropVariety, LivestockBreed
from app.farmers.repository import FarmerRepository
from app.recommendations.context_service import RecommendationContextService
from app.recommendations.model import Recommendation, RecommendationType
from app.recommendations.repository import RecommendationRepository
from app.recommendations.vendor_matching import VendorMatchingService


logger = logging.getLogger(__name__)


class StructuredRecommendationService:
    def __init__(self, db: Session, ai=None, vendor_search=None):
        self.db = db
        self.ai = ai
        self.vendor_search = vendor_search
        self.farmers = FarmerRepository(db)
        self.context_service = RecommendationContextService(db)

    def recommend(self, farmer_id: UUID, kind: str, session_inputs: dict | None = None) -> dict:
        farmer = self.farmers.get_by_id(farmer_id)
        if farmer is None:
            raise ValueError("Farmer not found")
        environment_context = self.context_service.environmental_context(farmer)
        latitude, longitude = environment_context["latitude"], environment_context["longitude"]
        weather, environment = environment_context["weather_forecast"], environment_context["observations"]

        livestock = kind == "livestock"
        model = LivestockBreed if livestock else CropVariety
        parent = model.livestock if livestock else model.crop
        rows = self.db.query(model).options(joinedload(parent)).order_by(model.name.asc()).all()
        candidates = []
        for row in rows:
            item = {
                "id": str(row.id), "name": row.name,
                "altitude_min_m": row.altitude_min_m, "altitude_max_m": row.altitude_max_m,
                "rainfall_min_mm": row.rainfall_min_mm, "rainfall_max_mm": row.rainfall_max_mm,
                "maturity_days_min": row.maturity_days_min, "maturity_days_max": row.maturity_days_max,
                "risk_attributes": row.risk_attributes, "adapted_regions": row.adapted_regions,
            }
            if livestock:
                item["livestock"] = row.livestock.name
            else:
                item["crop"] = row.crop.name
            candidates.append(item)
        if not candidates:
            raise ValueError("No sourced catalogue entries are available")
        requested = self._requested_name(kind, session_inputs or {})
        matching = [item for item in candidates if self._same_name(requested, item.get("livestock" if livestock else "crop"))] if requested else []
        # Honour the farmer's own choice; only widen to the full catalogue when
        # we hold no sourced varieties for what they asked for.
        requested_unavailable = bool(requested) and not matching
        if matching:
            candidates = matching
        eligible_primary_ids = {item["id"] for item in candidates}

        context = {
            "kind": kind,
            "farmer": {"name": farmer.full_name, "county": farmer.county.name,
                       "latitude": latitude, "longitude": longitude,
                       "sub_county": farmer.sub_county, "ward": farmer.ward},
            "session_inputs": session_inputs or {},
            "weather_forecast": weather,
            "rainfall_and_ndvi_observations": environment,
            "catalogue_only_choices": candidates,
            "farmer_requested": requested,
            "farmer_requested_is_not_in_catalogue": requested_unavailable,
        }
        try:
            provider_client = self.ai or LLMRouter()
            selection = provider_client.generate_structured_recommendation(context)
            result = self._validate_selection(selection, candidates, eligible_primary_ids)
            provider = getattr(provider_client, "last_provider", None) or "gemini"
        except Exception:
            result = self._fallback(candidates, farmer.county.name, weather, environment, eligible_primary_ids)
            provider = "catalogue_fallback"

        by_id = {item["id"]: item for item in candidates}
        primary = by_id[result["primary_id"]]
        alternatives = [by_id[item_id] for item_id in result["alternative_ids"]]
        vendors, vendor_source = self._find_vendors(primary, farmer, livestock)
        card = {
            "kind": kind,
            "primary": primary,
            "why_fit": result["why_fit"],
            "evidence": {"weather_forecast": weather, "rainfall_and_ndvi": environment},
            "alternatives": alternatives,
            "planting_window": result.get("planting_window"),
            "spacing": result.get("spacing"),
            "actions": result.get("actions", [])[:4],
            "requested": requested,
            "requested_unavailable": requested_unavailable,
            "vendors": vendors,
            "vendor_note": (
                "Found by web search; call to confirm availability, price and distance."
                if vendor_source == "web_search"
                else "Vendor location is not verified; call to confirm distance, price, and stock."
                if vendors and vendors[0].get("distance_km") is None
                else None if vendors else "No seller found yet; ask your nearest agrovet."
            ),
        }
        recommendation = Recommendation(
            farmer_id=farmer.id,
            crop_variety_id=UUID(primary["id"]) if not livestock else None,
            livestock_breed_id=UUID(primary["id"]) if livestock else None,
            vendor_product_id=UUID(vendors[0]["product_id"]) if vendors and vendors[0].get("product_id") else None,
            recommendation_type=RecommendationType.LIVESTOCK if livestock else RecommendationType.CROP,
            title=f"{primary.get('crop') or primary.get('livestock')}: {primary['name']}"[:200],
            recommendation_text=json.dumps(card, ensure_ascii=False),
            recommendation_data=card,
            ai_provider=provider,
            is_sent=False,
        )
        RecommendationRepository(self.db).create(recommendation)
        return {"id": str(recommendation.id), **card}

    @staticmethod
    def _requested_name(kind: str, inputs: dict) -> str | None:
        keys = ("livestock_type", "livestock") if kind == "livestock" else ("crop_name", "crop")
        value = next((str(inputs[k]).strip() for k in keys if inputs.get(k)), "")
        return None if value.lower() in {"", "other", "n/a"} else value

    @staticmethod
    def _same_name(requested: str, name: str | None) -> bool:
        def norm(text):
            return " ".join(w[:-1] if w.endswith("s") and len(w) > 3 else w for w in str(text or "").lower().split())
        a, b = norm(requested), norm(name)
        return bool(a and b and (a == b or a in b or b in a))

    def _find_vendors(self, primary: dict, farmer, livestock: bool) -> tuple[list[dict], str | None]:
        """Seeded vendor listings first; otherwise ask Gemini with Google Search."""
        if not livestock:
            matched = VendorMatchingService(self.db).match_variety(UUID(primary["id"]), farmer)
            if matched:
                return matched, "database"
        try:
            finder = self.vendor_search or LLMRouter().find_vendors
            found = finder(
                item=f"{primary.get('crop') or primary.get('livestock')} {primary['name']}",
                kind="livestock" if livestock else "crop",
                county=farmer.county.name, sub_county=farmer.sub_county, ward=farmer.ward,
            )
        except Exception:
            logger.exception("Vendor web search failed for farmer_id=%s", farmer.id)
            return [], None
        return found, ("web_search" if found else None)

    @staticmethod
    def _validate_selection(selection: dict, candidates: list[dict], eligible_primary_ids: set[str]) -> dict:
        ids = {item["id"] for item in candidates}
        primary = str(selection["primary_id"])
        if primary not in ids or primary not in eligible_primary_ids:
            raise ValueError("AI selected an item outside the catalogue choices")
        alternatives = []
        for value in selection.get("alternative_ids", []):
            candidate_id = str(value)
            if candidate_id in ids and candidate_id != primary and candidate_id not in alternatives:
                alternatives.append(candidate_id)
            if len(alternatives) == 2:
                break
        if len(alternatives) < 2:
            primary_item = next(item for item in candidates if item["id"] == primary)
            ordered = [item for item in candidates if item["id"] != primary]
            ordered.sort(key=lambda item: item.get("crop", item.get("livestock")) == primary_item.get("crop", primary_item.get("livestock")))
            for item in ordered:
                if item["id"] == primary or item["id"] in alternatives:
                    continue
                alternatives.append(item["id"])
                if len(alternatives) == 2:
                    break
        # Catalogue facts do not currently include planting windows or spacing.
        # Keep those fields empty rather than trusting unsupported generated text.
        return {"primary_id": primary, "alternative_ids": alternatives,
                "why_fit": str(selection.get("why_fit") or "Selected from the verified local catalogue.")[:300],
                "planting_window": None, "spacing": None,
                "actions": [str(v)[:200] for v in selection.get("actions", [])[:4]]}

    @staticmethod
    def _fallback(candidates: list[dict], county: str, weather, environment, eligible_primary_ids: set[str]) -> dict:
        def score(item):
            regions = (item.get("adapted_regions") or "").lower()
            value = 5 if county.lower() in regions else 0
            dry = str((environment or {}).get("rainfall", "")).lower()
            forecast = str((weather or {}).get("forecast", "")).lower()
            if any(term in dry + forecast for term in ("low", "dry", "drought")) and "drought" in (item.get("risk_attributes") or "").lower():
                value += 3
            return value
        ranked = sorted((item for item in candidates if item["id"] in eligible_primary_ids), key=score, reverse=True)
        primary = ranked[0]
        alternatives = [candidate for candidate in ranked[1:] if candidate.get("crop", candidate.get("livestock")) != primary.get("crop", primary.get("livestock"))]
        alternatives.extend(candidate for candidate in ranked[1:] if candidate not in alternatives)
        alt_ids = [candidate["id"] for candidate in alternatives[:2]]
        return {"primary_id": primary["id"], "alternative_ids": alt_ids,
                "why_fit": f"{primary['name']} is in the sourced catalogue for Kenya. Confirm local rainfall and seed availability before planting.",
                "planting_window": None, "spacing": None,
                "actions": ["Use the package label and local extension advice for planting date and spacing."]}


def _sentence(text, limit: int) -> str:
    """First sentence of text, trimmed to limit characters on a word boundary."""
    text = " ".join(str(text or "").split())
    first = text.split(". ")[0].rstrip(".")
    if len(first) > limit:
        first = first[:limit].rsplit(" ", 1)[0].rstrip(",;: ")
    return first


def format_recommendation_sms(card: dict, max_chars: int = 300) -> list[str]:
    """One short, line-per-fact SMS (about two SMS parts); the website shows the full card.

    Lines are dropped whole, least important first, so a message never ends mid-word.
    """
    primary = card["primary"]
    label = primary.get("crop") or primary.get("livestock")
    head = f"AgriTech pick: {label} - {primary['name']}"
    if card.get("requested_unavailable") and card.get("requested"):
        head = f"No verified {card['requested']} variety yet. Closest match: {label} - {primary['name']}"
    days = (primary.get("maturity_days_min"), primary.get("maturity_days_max"))
    grows = f"Ready in {days[0]}-{days[1]} days" if all(days) and days[0] != days[1] else f"Ready in {days[0] or days[1]} days" if any(days) else ""
    why = _sentence(card.get("why_fit"), 110)
    tip = _sentence((card.get("actions") or [""])[0], 90)
    others = [entry["name"] for entry in card.get("alternatives", []) if entry.get("name")]
    vendors = card.get("vendors") or []
    buy = "Buy: ask your nearest agrovet (no seller found yet)"
    if vendors:
        vendor = vendors[0]
        price = f", KES {vendor['price_kes']:g}/{vendor.get('unit') or 'unit'}" if vendor.get("price_kes") is not None else ""
        phone = f", {vendor['phone']}" if vendor.get("phone") else ""
        buy = f"Buy: {vendor['name']}{price}{phone}"
    # (line, droppable-after-position): lowest priority listed last.
    lines = [head, f"{why}." if why else "", f"{grows}." if grows else "", buy,
             f"Next: {tip}." if tip else "", f"Also: {', '.join(others)}" if others else "", "Call first to confirm stock."]
    lines = [line for line in lines if line]
    for drop in ("Also:", "Next:", "Ready in", "Call first"):
        if len("\n".join(lines)) <= max_chars:
            break
        lines = [line for line in lines if not line.startswith(drop)]
    text = "\n".join(lines)
    if len(text) > max_chars:
        text = "\n".join(lines[:2] + [lines[-1]] if len(lines) > 2 else lines)[:max_chars].rsplit(" ", 1)[0]
    return [text]
