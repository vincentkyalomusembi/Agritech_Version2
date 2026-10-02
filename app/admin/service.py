from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.advisory.model import Advisory
from app.audit.model import AuditLog
from app.audit.service import write_audit
from app.core.africas_talking import AfricasTalkingClient
from app.core.config import settings
from app.expert_requests.exceptions import InvalidStatusTransitionError
from app.expert_requests.model import ExpertRequest, RequestStatus
from app.expert_requests.services.expert_request_service import ExpertRequestService
from app.expert_requests.schema import ExpertRequestStatusUpdate
from app.counties.repository import CountyRepository
from app.experts.model import Expert
from app.experts.schema import ExpertResponse
from app.farmers.model import Farmer
from app.farmers.utils import normalize_phone_number
from app.market_prices.model import MarketPrice
from app.pricing.engine import format_quote_sms, normalize_plan_name
from app.pricing.model import PricingRule, QuoteStatus, SubscriptionQuote
from app.pricing.schema import PricingRuleCreate, QuoteResponse
from app.pricing.service import FarmerSizeService, QuoteService
from app.sms_sessions.model import SMSSession, SessionStatus
from app.staff.model import StaffRole, StaffUser
from app.staff.repository import StaffRepository
from app.staff.schema import StaffResponse
from app.staff.security import hash_password
from app.subscriptions.model import Subscription
from app.admin.schema import (
    AdminExpertCreate,
    AdminExpertUpdate,
    AdminFarmerDetail,
    AdminFarmerListItem,
    AdminFieldOfficerCreate,
    AdminFieldOfficerResponse,
    AdminOverview,
    AdminRequestItem,
    AdminRequestPatch,
    QuotePreviewResponse,
)


def _mask_national_id(value: str) -> str:
    if not value:
        return "****"
    return f"****{value[-4:]}"


class AdminService:
    def __init__(self, db: Session):
        self.db = db
        self.size = FarmerSizeService(db)
        self.quotes = QuoteService(db)

    def overview(self) -> AdminOverview:
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        aging_cutoff = now - timedelta(hours=48)

        farmers_total = self.db.query(func.count(Farmer.id)).scalar() or 0
        farmers_7d = (
            self.db.query(func.count(Farmer.id))
            .filter(Farmer.created_at >= week_ago)
            .scalar()
            or 0
        )

        class_rows = (
            self.db.query(Subscription.size_class, func.count(Subscription.id))
            .group_by(Subscription.size_class)
            .all()
        )
        by_size_class = {name: 0 for name in ("Micro", "Small", "Medium", "Large")}
        for name, count in class_rows:
            key = normalize_plan_name(name)
            by_size_class[key] = by_size_class.get(key, 0) + int(count)

        active_paid = (
            self.db.query(func.count(Subscription.id))
            .filter(
                Subscription.is_active.is_(True),
                Subscription.amount_kes.isnot(None),
                Subscription.amount_kes > 0,
            )
            .scalar()
            or 0
        )
        failed_payments_7d = (
            self.db.query(func.count(SMSSession.id))
            .filter(
                SMSSession.session_status == SessionStatus.FAILED,
                SMSSession.updated_at >= week_ago,
            )
            .scalar()
            or 0
        )

        request_rows = (
            self.db.query(ExpertRequest.status, func.count(ExpertRequest.id))
            .group_by(ExpertRequest.status)
            .all()
        )
        requests_by_status = {status.value: 0 for status in RequestStatus}
        for request_status, count in request_rows:
            requests_by_status[request_status.value] = int(count)

        requests_aging = (
            self.db.query(func.count(ExpertRequest.id))
            .filter(
                ExpertRequest.status == RequestStatus.PENDING,
                ExpertRequest.created_at <= aging_cutoff,
            )
            .scalar()
            or 0
        )
        advisories_active = (
            self.db.query(func.count(Advisory.id))
            .filter(Advisory.is_active.is_(True))
            .scalar()
            or 0
        )
        last_price = (
            self.db.query(func.max(MarketPrice.created_at)).scalar()
        )
        sms_open = (
            self.db.query(func.count(SMSSession.id))
            .filter(
                SMSSession.is_active.is_(True),
                SMSSession.session_status.in_([SessionStatus.ACTIVE, SessionStatus.PROCESSING]),
            )
            .scalar()
            or 0
        )

        db_status = "ok"
        try:
            from sqlalchemy import text
            self.db.execute(text("SELECT 1"))
        except Exception:
            db_status = "error"

        return AdminOverview(
            farmers_total=farmers_total,
            farmers_7d=farmers_7d,
            by_size_class=by_size_class,
            active_paid_subscriptions=active_paid,
            failed_payments_7d=failed_payments_7d,
            requests_by_status=requests_by_status,
            requests_aging_48h=requests_aging,
            advisories_active=advisories_active,
            market_prices_last_scraped_at=last_price,
            sms_sessions_open=sms_open,
            health={
                "status": "ok" if db_status == "ok" else "degraded",
                "database": db_status,
                "africas_talking_configured": AfricasTalkingClient().is_configured,
                "secret_key_set": bool(settings.SECRET_KEY),
            },
        )

    def list_farmers(
        self,
        *,
        search: str | None,
        county_id: UUID | None,
        size_class: str | None,
        is_active: bool | None,
        limit: int,
        offset: int,
    ) -> tuple[list[AdminFarmerListItem], int]:
        query = self.db.query(Farmer).options(
            joinedload(Farmer.county),
            joinedload(Farmer.subscriptions),
            joinedload(Farmer.crops),
        )
        if search:
            like = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Farmer.full_name.ilike(like),
                    Farmer.phone_number.ilike(like),
                )
            )
        if county_id:
            query = query.filter(Farmer.county_id == county_id)
        if is_active is not None:
            query = query.filter(Farmer.is_active.is_(is_active))
        if size_class:
            query = query.join(Subscription, Subscription.farmer_id == Farmer.id, isouter=True).filter(
                or_(
                    Subscription.size_class == size_class,
                    Subscription.plan_name == size_class,
                )
            )

        total = query.count()
        rows = query.order_by(Farmer.created_at.desc()).offset(offset).limit(limit).all()
        items = [self._farmer_list_item(row) for row in rows]
        return items, total

    def farmer_detail(self, farmer_id: UUID, *, show_full_id: bool) -> AdminFarmerDetail:
        farmer = (
            self.db.query(Farmer)
            .options(
                joinedload(Farmer.county),
                joinedload(Farmer.crops),
                joinedload(Farmer.livestock),
                joinedload(Farmer.subscriptions),
                joinedload(Farmer.expert_requests),
            )
            .filter(Farmer.id == farmer_id)
            .first()
        )
        if farmer is None:
            raise HTTPException(status_code=404, detail="Farmer not found.")

        computation = self.size.compute(farmer.id)
        latest_quote = (
            self.db.query(SubscriptionQuote)
            .filter(SubscriptionQuote.farmer_id == farmer.id)
            .order_by(SubscriptionQuote.created_at.desc())
            .first()
        )
        base = self._farmer_list_item(farmer)
        return AdminFarmerDetail(
            **base.model_dump(),
            national_id=farmer.national_id if show_full_id else None,
            crops=[
                {
                    "id": str(row.id),
                    "name": row.crop.name if row.crop else None,
                    "farm_size": row.farm_size,
                }
                for row in farmer.crops
            ],
            livestock=[
                {
                    "id": str(row.id),
                    "name": row.livestock.name if row.livestock else None,
                    "herd_size": row.herd_size,
                }
                for row in farmer.livestock
            ],
            tlu_total=computation.tlu_total,
            current_quote=self.quotes._to_response(latest_quote) if latest_quote else None,
            requests=[
                {
                    "id": str(row.id),
                    "status": row.status.value,
                    "issue_type": row.issue_type,
                    "expert_id": str(row.expert_id),
                }
                for row in farmer.expert_requests
            ],
        )

    def set_farmer_active(self, farmer_id: UUID, is_active: bool, actor: StaffUser | None) -> AdminFarmerListItem:
        farmer = self.db.query(Farmer).filter(Farmer.id == farmer_id).first()
        if farmer is None:
            raise HTTPException(status_code=404, detail="Farmer not found.")
        farmer.is_active = is_active
        self.db.commit()
        self.db.refresh(farmer)
        write_audit(
            self.db,
            action="farmer.activate" if is_active else "farmer.deactivate",
            entity="farmer",
            entity_id=farmer.id,
            actor_id=actor.id if actor else None,
            metadata={"is_active": is_active},
            commit=True,
        )
        return self._farmer_list_item(farmer)

    def list_requests(
        self,
        *,
        status_filter: RequestStatus | None,
        county_id: UUID | None,
        expert_id: UUID | None,
        assigned_only_expert_id: UUID | None,
        limit: int,
        offset: int,
    ) -> tuple[list[AdminRequestItem], int]:
        query = self.db.query(ExpertRequest).options(
            joinedload(ExpertRequest.farmer).joinedload(Farmer.county),
            joinedload(ExpertRequest.expert),
        )
        if status_filter:
            query = query.filter(ExpertRequest.status == status_filter)
        if expert_id:
            query = query.filter(ExpertRequest.expert_id == expert_id)
        if assigned_only_expert_id:
            query = query.filter(ExpertRequest.expert_id == assigned_only_expert_id)
        if county_id:
            query = query.join(Farmer, Farmer.id == ExpertRequest.farmer_id).filter(Farmer.county_id == county_id)

        total = query.count()
        rows = query.order_by(ExpertRequest.created_at.desc()).offset(offset).limit(limit).all()
        return [self._request_item(row) for row in rows], total

    def get_request(self, request_id: UUID, assigned_only_expert_id: UUID | None = None) -> AdminRequestItem:
        request = (
            self.db.query(ExpertRequest)
            .options(
                joinedload(ExpertRequest.farmer).joinedload(Farmer.county),
                joinedload(ExpertRequest.expert),
            )
            .filter(ExpertRequest.id == request_id)
            .first()
        )
        if request is None:
            raise HTTPException(status_code=404, detail="Request not found.")
        if assigned_only_expert_id and request.expert_id != assigned_only_expert_id:
            raise HTTPException(status_code=403, detail="This request is not assigned to you.")
        return self._request_item(request)

    def patch_request(
        self,
        request_id: UUID,
        payload: AdminRequestPatch,
        *,
        actor: StaffUser,
        officer_expert_id: UUID | None,
    ) -> AdminRequestItem:
        request = self.db.query(ExpertRequest).filter(ExpertRequest.id == request_id).first()
        if request is None:
            raise HTTPException(status_code=404, detail="Request not found.")
        if officer_expert_id is not None:
            if request.expert_id != officer_expert_id:
                raise HTTPException(status_code=403, detail="This request is not assigned to you.")
            if payload.expert_id is not None and payload.expert_id != request.expert_id:
                raise HTTPException(status_code=403, detail="Officers cannot reassign requests.")

        if payload.expert_id is not None and officer_expert_id is None:
            expert = self.db.query(Expert).filter(Expert.id == payload.expert_id).first()
            if expert is None:
                raise HTTPException(status_code=404, detail="Expert not found.")
            request.expert_id = payload.expert_id
            self.db.commit()
            write_audit(
                self.db,
                action="request.assign",
                entity="expert_request",
                entity_id=request.id,
                actor_id=actor.id,
                metadata={"expert_id": str(payload.expert_id)},
                commit=True,
            )

        if payload.status is not None:
            try:
                ExpertRequestService(self.db).update_status(
                    ExpertRequestStatusUpdate(request_id=request_id, status=payload.status)
                )
            except InvalidStatusTransitionError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            write_audit(
                self.db,
                action="request.status",
                entity="expert_request",
                entity_id=request_id,
                actor_id=actor.id,
                metadata={"status": payload.status.value},
                commit=True,
            )

        return self.get_request(request_id)

    def create_expert(self, payload: AdminExpertCreate, actor: StaffUser) -> ExpertResponse:
        expert = Expert(
            full_name=payload.full_name,
            phone_number=normalize_phone_number(payload.phone_number),
            expert_type=payload.expert_type,
            county_id=payload.county_id,
            organization=payload.organization,
            is_available=payload.is_available,
        )
        self.db.add(expert)
        self.db.commit()
        self.db.refresh(expert)
        write_audit(
            self.db,
            action="expert.create",
            entity="expert",
            entity_id=expert.id,
            actor_id=actor.id,
            commit=True,
        )
        return ExpertResponse.model_validate(expert)

    def create_field_officer(
        self,
        payload: AdminFieldOfficerCreate,
        actor: StaffUser,
    ) -> AdminFieldOfficerResponse:
        phone = normalize_phone_number(payload.phone_number)
        county = CountyRepository(self.db).get_by_id(payload.county_id)
        if county is None:
            raise HTTPException(status_code=404, detail="County not found.")

        if self.db.query(Expert).filter(Expert.phone_number == phone).first():
            raise HTTPException(status_code=409, detail="An expert with this phone number already exists.")
        if StaffRepository(self.db).get_by_phone(phone):
            raise HTTPException(status_code=409, detail="A staff user with this phone number already exists.")

        expert = Expert(
            full_name=payload.full_name.strip(),
            phone_number=phone,
            expert_type=payload.expert_type,
            county_id=payload.county_id,
            organization=payload.organization.strip(),
            is_available=payload.is_available,
        )
        staff = StaffUser(
            full_name=payload.full_name.strip(),
            phone_number=phone,
            email=payload.email,
            password_hash=hash_password(payload.password),
            role=StaffRole.OFFICER,
            county_id=payload.county_id,
            expert_id=None,
        )
        try:
            self.db.add(expert)
            self.db.flush()
            staff.expert_id = expert.id
            self.db.add(staff)
            self.db.commit()
            self.db.refresh(expert)
            self.db.refresh(staff)
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Could not create field officer. Phone number may already be in use.",
            ) from None

        write_audit(
            self.db,
            action="field_officer.create",
            entity="expert",
            entity_id=expert.id,
            actor_id=actor.id,
            metadata={"staff_id": str(staff.id), "expert_id": str(expert.id)},
            commit=True,
        )
        return AdminFieldOfficerResponse(
            expert=ExpertResponse.model_validate(expert),
            staff=StaffResponse.model_validate(staff),
        )

    def update_expert(self, expert_id: UUID, payload: AdminExpertUpdate, actor: StaffUser | None) -> ExpertResponse:
        expert = self.db.query(Expert).filter(Expert.id == expert_id).first()
        if expert is None:
            raise HTTPException(status_code=404, detail="Expert not found.")
        data = payload.model_dump(exclude_unset=True)
        if "phone_number" in data and data["phone_number"]:
            data["phone_number"] = normalize_phone_number(data["phone_number"])
        for field, value in data.items():
            setattr(expert, field, value)
        self.db.commit()
        self.db.refresh(expert)
        write_audit(
            self.db,
            action="expert.update",
            entity="expert",
            entity_id=expert.id,
            actor_id=actor.id if actor else None,
            metadata=data,
            commit=True,
        )
        return ExpertResponse.model_validate(expert)

    def list_quotes(self, limit: int, offset: int) -> tuple[list[QuoteResponse], int]:
        total = self.db.query(func.count(SubscriptionQuote.id)).scalar() or 0
        rows = (
            self.db.query(SubscriptionQuote)
            .order_by(SubscriptionQuote.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [self.quotes._to_response(row) for row in rows], total

    def requote(self, farmer_id: UUID, reason: str, actor: StaffUser) -> QuoteResponse:
        quote = self.quotes.create_quote(farmer_id)
        write_audit(
            self.db,
            action="quote.create",
            entity="subscription_quote",
            entity_id=quote.id,
            actor_id=actor.id,
            metadata={"reason": reason, "farmer_id": str(farmer_id)},
            commit=True,
        )
        return quote

    def preview_quote(self, acres: float, cattle: int, goats: int, sheep: int, poultry: int) -> QuotePreviewResponse:
        computation = self.size.preview(acres, cattle, goats, sheep, poultry)
        return QuotePreviewResponse(
            **computation.model_dump(),
            sms_text=format_quote_sms(
                computation.size_class,
                computation.acres,
                {"Cattle": cattle, "Goats": goats, "Sheep": sheep, "Chicken": poultry},
                computation.monthly_kes,
            ),
        )

    def list_pricing_rules(self) -> list[PricingRule]:
        return self.db.query(PricingRule).order_by(PricingRule.version.desc()).all()

    def create_pricing_rule(self, payload: PricingRuleCreate, actor: StaffUser) -> PricingRule:
        current = self.db.query(func.max(PricingRule.version)).scalar() or 0
        if payload.is_active:
            self.db.query(PricingRule).update({PricingRule.is_active: False})
        rule = PricingRule(
            version=int(current) + 1,
            tlu_weights=payload.tlu_weights,
            bands=payload.bands,
            entitlements=payload.entitlements,
            is_active=payload.is_active,
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        write_audit(
            self.db,
            action="pricing.create",
            entity="pricing_rule",
            entity_id=rule.id,
            actor_id=actor.id,
            metadata={"version": rule.version},
            commit=True,
        )
        return rule

    def list_subscriptions(self, limit: int, offset: int) -> tuple[list[dict], int]:
        total = self.db.query(func.count(Subscription.id)).scalar() or 0
        rows = (
            self.db.query(Subscription)
            .options(joinedload(Subscription.farmer))
            .order_by(Subscription.updated_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        items = [
            {
                "id": str(row.id),
                "farmer_id": str(row.farmer_id),
                "farmer_name": row.farmer.full_name if row.farmer else None,
                "is_active": row.is_active,
                "plan_name": row.plan_name,
                "size_class": getattr(row, "size_class", None) or normalize_plan_name(row.plan_name),
                "amount_kes": getattr(row, "amount_kes", None),
                "start_date": str(row.start_date) if row.start_date else None,
                "end_date": str(row.end_date) if row.end_date else None,
            }
            for row in rows
        ]
        return items, total

    def list_sms_sessions(self, limit: int, offset: int) -> tuple[list[dict], int]:
        total = self.db.query(func.count(SMSSession.id)).scalar() or 0
        rows = (
            self.db.query(SMSSession)
            .options(joinedload(SMSSession.farmer))
            .order_by(SMSSession.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        items = [
            {
                "id": str(row.id),
                "farmer_id": str(row.farmer_id),
                "farmer_name": row.farmer.full_name if row.farmer else None,
                "session_type": row.session_type.value,
                "session_status": row.session_status.value,
                "is_active": row.is_active,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            }
            for row in rows
        ]
        return items, total

    def list_audit(self, limit: int, offset: int) -> tuple[list[dict], int]:
        total = self.db.query(func.count(AuditLog.id)).scalar() or 0
        rows = (
            self.db.query(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        items = [
            {
                "id": str(row.id),
                "actor_id": str(row.actor_id) if row.actor_id else None,
                "actor_kind": row.actor_kind,
                "action": row.action,
                "entity": row.entity,
                "entity_id": row.entity_id,
                "metadata": row.metadata_json,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
        return items, total

    def _farmer_list_item(self, farmer: Farmer) -> AdminFarmerListItem:
        sub = farmer.subscriptions[0] if farmer.subscriptions else None
        acres = sum(float(row.farm_size or 0) for row in farmer.crops) if farmer.crops else 0.0
        return AdminFarmerListItem(
            id=farmer.id,
            full_name=farmer.full_name,
            phone_number=farmer.phone_number,
            national_id_masked=_mask_national_id(farmer.national_id),
            county_id=farmer.county_id,
            county_name=farmer.county.name if farmer.county else None,
            is_active=farmer.is_active,
            acres=acres,
            size_class=(
                getattr(sub, "size_class", None) or normalize_plan_name(sub.plan_name)
                if sub
                else None
            ),
            amount_kes=getattr(sub, "amount_kes", None) if sub else None,
            created_at=farmer.created_at,
        )

    def _request_item(self, request: ExpertRequest) -> AdminRequestItem:
        farmer = request.farmer
        return AdminRequestItem(
            id=request.id,
            farmer_id=request.farmer_id,
            farmer_name=farmer.full_name if farmer else None,
            farmer_phone=farmer.phone_number if farmer else None,
            county_id=farmer.county_id if farmer else None,
            county_name=farmer.county.name if farmer and farmer.county else None,
            expert_id=request.expert_id,
            expert_name=request.expert.full_name if request.expert else None,
            issue_type=request.issue_type,
            description=request.description,
            status=request.status,
            preferred_visit_date=request.preferred_visit_date,
            created_at=request.created_at,
            updated_at=request.updated_at,
        )
