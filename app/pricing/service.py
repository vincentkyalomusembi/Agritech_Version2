from uuid import UUID

from sqlalchemy.orm import Session

from app.expert_requests.model import ExpertRequest, RequestStatus
from app.farmer_crops.repository import FarmerCropRepository
from app.farmer_livestocks.repository import FarmerLivestockRepository
from app.pricing.engine import (
    DEFAULT_BANDS,
    DEFAULT_ENTITLEMENTS,
    DEFAULT_TLU_WEIGHTS,
    PAID_SERVICES,
    compute_from_inputs,
    format_quote_sms,
    normalize_plan_name,
)
from app.subscriptions.model import Subscription
from app.pricing.model import PricingRule, QuoteStatus, SubscriptionQuote
from app.pricing.schema import QuoteResponse, SizeComputation


class FarmerSizeService:
    def __init__(self, db: Session):
        self.db = db
        self.crops = FarmerCropRepository(db)
        self.livestock = FarmerLivestockRepository(db)

    def active_rule(self) -> PricingRule | None:
        return (
            self.db.query(PricingRule)
            .filter(PricingRule.is_active.is_(True))
            .order_by(PricingRule.version.desc())
            .first()
        )

    def rule_payload(self) -> tuple[int, dict, list, dict]:
        rule = self.active_rule()
        if rule is None:
            return 1, DEFAULT_TLU_WEIGHTS, list(DEFAULT_BANDS), DEFAULT_ENTITLEMENTS
        return rule.version, rule.tlu_weights, rule.bands, rule.entitlements

    def herd_counts(self, farmer_id: UUID) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in self.livestock.get_farmer_livestock(farmer_id):
            name = row.livestock.name if row.livestock else "Other"
            counts[name] = counts.get(name, 0) + int(row.herd_size or 0)
        return counts

    def total_acres(self, farmer_id: UUID) -> float:
        return sum(float(row.farm_size or 0) for row in self.crops.get_farmer_crops(farmer_id))

    def compute(self, farmer_id: UUID) -> SizeComputation:
        version, weights, bands, _ = self.rule_payload()
        raw = compute_from_inputs(
            self.total_acres(farmer_id),
            self.herd_counts(farmer_id),
            weights=weights,
            bands=bands,
        )
        raw["rule_version"] = version
        return SizeComputation.model_validate(raw)

    def preview(
        self,
        acres: float,
        cattle: int = 0,
        goats: int = 0,
        sheep: int = 0,
        poultry: int = 0,
    ) -> SizeComputation:
        version, weights, bands, _ = self.rule_payload()
        raw = compute_from_inputs(
            acres,
            {"Cattle": cattle, "Goats": goats, "Sheep": sheep, "Chicken": poultry},
            weights=weights,
            bands=bands,
        )
        raw["rule_version"] = version
        return SizeComputation.model_validate(raw)

    def entitlements_for(self, size_class: str) -> list[str]:
        _, _, _, entitlements = self.rule_payload()
        return list(entitlements.get(normalize_plan_name(size_class), entitlements.get("Micro", [])))

    def current_size_class(self, farmer_id: UUID) -> str:
        sub = self.db.query(Subscription).filter(Subscription.farmer_id == farmer_id).first()
        if sub is None:
            return "Micro"
        return normalize_plan_name(sub.size_class or sub.plan_name)

    def can_use_service(self, farmer_id: UUID, service_key: str) -> bool:
        if service_key not in PAID_SERVICES:
            return True
        size_class = self.current_size_class(farmer_id)
        allowed = self.entitlements_for(size_class)
        if service_key == "expert_request" and size_class == "Micro":
            pending = (
                self.db.query(ExpertRequest)
                .filter(
                    ExpertRequest.farmer_id == farmer_id,
                    ExpertRequest.status == RequestStatus.PENDING,
                )
                .count()
            )
            return pending < 1
        return service_key in allowed


class QuoteService:
    def __init__(self, db: Session):
        self.db = db
        self.size = FarmerSizeService(db)

    def create_quote(self, farmer_id: UUID, *, commit: bool = True) -> QuoteResponse:
        computation = self.size.compute(farmer_id)
        herd = self.size.herd_counts(farmer_id)
        rule = self.size.active_rule()
        quote = SubscriptionQuote(
            farmer_id=farmer_id,
            acres_used=computation.acres,
            tlu_used=computation.tlu_total,
            herd_snapshot=herd,
            size_class=computation.size_class,
            amount_kes=computation.monthly_kes,
            rule_version=computation.rule_version,
            rule_id=rule.id if rule else None,
            status=QuoteStatus.PENDING,
        )
        self.db.add(quote)
        if commit:
            self.db.commit()
        else:
            self.db.flush()
        self.db.refresh(quote)
        return self._to_response(quote, herd)

    def get_by_id(self, quote_id: UUID) -> SubscriptionQuote | None:
        return self.db.query(SubscriptionQuote).filter(SubscriptionQuote.id == quote_id).first()

    def mark_paid(self, quote: SubscriptionQuote, *, commit: bool = True) -> SubscriptionQuote:
        if quote.status == QuoteStatus.PAID:
            return quote
        quote.status = QuoteStatus.PAID
        if commit:
            self.db.commit()
            self.db.refresh(quote)
        return quote

    def mark_cancelled(self, quote: SubscriptionQuote, *, commit: bool = True) -> SubscriptionQuote:
        if quote.status == QuoteStatus.PAID:
            return quote
        quote.status = QuoteStatus.CANCELLED
        if commit:
            self.db.commit()
            self.db.refresh(quote)
        return quote

    def _to_response(self, quote: SubscriptionQuote, herd: dict | None = None) -> QuoteResponse:
        snapshot = herd if herd is not None else (quote.herd_snapshot or {})
        return QuoteResponse(
            id=quote.id,
            farmer_id=quote.farmer_id,
            acres_used=quote.acres_used,
            tlu_used=quote.tlu_used,
            herd_snapshot=snapshot,
            size_class=quote.size_class,
            amount_kes=quote.amount_kes,
            rule_version=quote.rule_version,
            status=quote.status,
            created_at=quote.created_at,
            sms_text=format_quote_sms(
                quote.size_class,
                quote.acres_used,
                {k: int(v) for k, v in snapshot.items()},
                quote.amount_kes,
            ),
        )
