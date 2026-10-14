from datetime import datetime, timedelta, timezone
from math import atan2, cos, radians, sin, sqrt
from uuid import UUID

from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.core.africas_talking import AfricasTalkingClient
from app.expert_requests.exceptions import ALLOWED_STATUS_TRANSITIONS, ExpertRequestNotFoundError, FarmerNotFoundError, InvalidStatusTransitionError
from app.expert_requests.model import ExpertOffer, ExpertRequest, RequestStatus
from app.expert_requests.repository import ExpertRequestRepository
from app.expert_requests.schema import ExpertRequestCreate, ExpertRequestResponse, ExpertRequestStatusUpdate
from app.experts.model import Expert, ExpertType
from app.farmers.repository import FarmerRepository

OFFER_TIMEOUT_MINUTES = 30


class ExpertRequestService:
    """Shared request assignment, offer-response and resolution workflow."""

    def __init__(self, db: Session, sms=None):
        self.db = db
        self.repository = ExpertRequestRepository(db)
        self.farmers = FarmerRepository(db)
        self.sms = sms or AfricasTalkingClient()

    def create_request(self, data: ExpertRequestCreate, source_session_id: UUID | None = None) -> ExpertRequestResponse:
        if source_session_id is not None:
            existing = self.db.query(ExpertRequest).filter_by(source_session_id=source_session_id).first()
            if existing is not None:
                return ExpertRequestResponse.model_validate(existing)
        farmer = self.farmers.get_by_id(data.farmer_id)
        if farmer is None:
            raise FarmerNotFoundError()
        request = ExpertRequest(
            farmer_id=farmer.id,
            expert_id=None,
            issue_type=data.issue_type,
            description=data.description,
            preferred_visit_date=data.preferred_visit_date,
            status=RequestStatus.UNASSIGNED,
            source_session_id=source_session_id,
        )
        self.db.add(request)
        self.db.flush()
        request.request_code = f"ER-{str(request.id).replace('-', '')[:8].upper()}"
        self.db.commit()
        self.db.refresh(request)
        self.offer_next(request.id)
        self.db.refresh(request)
        return ExpertRequestResponse.model_validate(request)

    def _score(self, expert: Expert, request: ExpertRequest, farmer) -> float:
        from app.expert_requests.model import ExpertOffer

        active = self.db.query(ExpertRequest).filter(
            ExpertRequest.expert_id == expert.id,
            ExpertRequest.status.in_([RequestStatus.PENDING, RequestStatus.OFFERED, RequestStatus.ACCEPTED]),
        ).count()
        offers = self.db.query(ExpertOffer).filter_by(expert_id=expert.id).all()
        responded = [offer for offer in offers if offer.status in {"accepted", "declined"}]
        response_rate = len(responded) / len(offers) if offers else 0.5
        last_assignment = self.db.query(ExpertRequest.updated_at).filter(
            ExpertRequest.expert_id == expert.id,
            ExpertRequest.status.in_([RequestStatus.ACCEPTED, RequestStatus.COMPLETED]),
        ).order_by(ExpertRequest.updated_at.desc()).first()
        last_assignment = last_assignment[0] if last_assignment else None
        idle_days = min(30.0, (datetime.now(timezone.utc) - last_assignment).total_seconds() / 86400) if last_assignment else 30.0
        score = 8.0 * response_rate + min(idle_days / 10, 3.0) - 4.0 * active
        if expert.county_id == farmer.county_id:
            score += 5.0
        if all(value is not None for value in (farmer.latitude, farmer.longitude, expert.latitude, expert.longitude)):
            dlat = radians(expert.latitude - farmer.latitude)
            dlon = radians(expert.longitude - farmer.longitude)
            a = sin(dlat / 2) ** 2 + cos(radians(farmer.latitude)) * cos(radians(expert.latitude)) * sin(dlon / 2) ** 2
            distance = 6371 * 2 * atan2(sqrt(a), sqrt(1 - a))
            score += max(-10.0, 10.0 - distance / 20.0)
        return score

    def offer_next(self, request_id: UUID) -> ExpertRequest:
        request = self.repository.get_by_id_for_update(request_id)
        if request is None:
            raise ExpertRequestNotFoundError()
        if request.status in {RequestStatus.ACCEPTED, RequestStatus.COMPLETED, RequestStatus.CANCELLED}:
            return request
        farmer = self.farmers.get_by_id(request.farmer_id)
        required_type = ExpertType.VETERINARY if request.issue_type.lower().startswith(("livestock", "veterinary", "animal")) else ExpertType.AGRICULTURE
        candidates = self.db.query(Expert).filter(
            Expert.is_available.is_(True), Expert.contact_verified.is_(True), Expert.expert_type == required_type
        ).all()
        already_offered = {offer.expert_id for offer in self.db.query(ExpertOffer).filter_by(request_id=request.id).all()}
        candidates = [expert for expert in candidates if expert.id not in already_offered]
        candidates.sort(key=lambda expert: self._score(expert, request, farmer), reverse=True)
        if not candidates:
            request.expert_id = None
            request.status = RequestStatus.ESCALATED
            self.db.commit()
            self.sms.send_sms(farmer.phone_number, f"Request {request.request_code}: no expert has accepted yet. Your request is escalated to our support team.")
            return request

        expert = candidates[0]
        offer = ExpertOffer(
            request_id=request.id,
            expert_id=expert.id,
            score=self._score(expert, request, farmer),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=OFFER_TIMEOUT_MINUTES),
        )
        request.expert_id = expert.id
        request.status = RequestStatus.OFFERED
        self.db.add(offer)
        self.db.commit()
        self.sms.send_sms(expert.phone_number,
            f"Expert request {request.request_code}: {request.issue_type}. Reply YES {request.request_code} to accept or NO {request.request_code} to pass. Expires in {OFFER_TIMEOUT_MINUTES} min.")
        self.sms.send_sms(farmer.phone_number, f"Request {request.request_code} received. Finding an available expert; we will text you when one accepts.")
        return request

    def handle_expert_reply(self, phone: str, text: str) -> bool:
        parts = text.strip().upper().split()
        if len(parts) != 2 or parts[0] not in {"YES", "NO", "DONE"} or not parts[1].startswith("ER-"):
            return False
        expert = self.db.query(Expert).filter(Expert.phone_number == phone).first()
        if expert is None:
            return False
        request = self.db.query(ExpertRequest).filter_by(request_code=parts[1]).with_for_update().first()
        if request is None:
            self.sms.send_sms(phone, "Request code not found.")
            return True
        if parts[0] == "DONE":
            if request.expert_id != expert.id or request.status != RequestStatus.ACCEPTED:
                self.sms.send_sms(phone, "This request is not assigned to you.")
                return True
            self._complete_request(request)
            return True
        offer = self.db.query(ExpertOffer).filter_by(request_id=request.id, expert_id=expert.id, status="offered").with_for_update().first()
        if offer is None or request.status != RequestStatus.OFFERED:
            self.sms.send_sms(phone, "No open offer for that request code.")
            return True
        now = datetime.now(timezone.utc)
        if offer.expires_at <= now:
            offer.status = "expired"
            offer.responded_at = now
            self.db.commit()
            self.offer_next(request.id)
            return True
        offer.responded_at = now
        offer.response_seconds = max(0, int((now - offer.offered_at).total_seconds()))
        if parts[0] == "YES":
            offer.status = "accepted"
            request.expert_id = expert.id
            request.status = RequestStatus.ACCEPTED
            self.db.commit()
            farmer = self.farmers.get_by_id(request.farmer_id)
            self.sms.send_sms(farmer.phone_number, f"{expert.full_name} accepted request {request.request_code}. Contact: {expert.phone_number}. Reply MENU for services.")
            self.sms.send_sms(expert.phone_number, f"You are assigned request {request.request_code}. Farmer: {farmer.full_name}, {farmer.phone_number}. Reply DONE {request.request_code} when finished.")
        else:
            offer.status = "declined"
            offer.response_note = "declined by expert"
            request.expert_id = None
            request.status = RequestStatus.UNASSIGNED
            self.db.commit()
            self.offer_next(request.id)
        return True

    def handle_farmer_resolution(self, farmer, text: str) -> bool:
        parts = text.strip().upper().split()
        if len(parts) != 2 or parts[0] not in {"SOLVED", "UNSOLVED"} or not parts[1].startswith("ER-"):
            return False
        request = self.db.query(ExpertRequest).filter_by(request_code=parts[1], farmer_id=farmer.id).with_for_update().first()
        if request is None or request.status != RequestStatus.COMPLETED:
            return False
        request.farmer_resolution = parts[0].lower()
        if parts[0] == "UNSOLVED":
            request.status = RequestStatus.ESCALATED
        self.db.commit()
        self.sms.send_sms(farmer.phone_number, "Thanks for the feedback. Our support team will follow up." if parts[0] == "UNSOLVED" else "Thanks for confirming the issue was solved.")
        return True

    def _complete_request(self, request: ExpertRequest) -> None:
        request.status = RequestStatus.COMPLETED
        self.db.commit()
        farmer = self.farmers.get_by_id(request.farmer_id)
        self.sms.send_sms(farmer.phone_number, f"Your expert request {request.request_code} is marked complete. Reply SOLVED {request.request_code} or UNSOLVED {request.request_code}.")

    def expire_offers(self) -> int:
        now = datetime.now(timezone.utc)
        expired = self.db.query(ExpertOffer).filter(ExpertOffer.status == "offered", ExpertOffer.expires_at <= now).all()
        request_ids = set()
        for offer in expired:
            offer.status = "expired"
            offer.responded_at = now
            request_ids.add(offer.request_id)
        self.db.commit()
        for request_id in request_ids:
            self.offer_next(request_id)
        return len(expired)

    def update_status(self, data: ExpertRequestStatusUpdate) -> ExpertRequestResponse:
        request = self.repository.get_by_id_for_update(data.request_id)
        if request is None:
            raise ExpertRequestNotFoundError()
        if data.status != request.status and data.status not in ALLOWED_STATUS_TRANSITIONS.get(request.status, set()):
            raise InvalidStatusTransitionError(request.status, data.status)
        request.status = data.status
        if data.status == RequestStatus.COMPLETED:
            self.db.commit()
            farmer = self.farmers.get_by_id(request.farmer_id)
            self.sms.send_sms(farmer.phone_number, f"Your expert request {request.request_code} is marked complete. Reply SOLVED {request.request_code} or UNSOLVED {request.request_code}.")
        elif data.status == RequestStatus.UNASSIGNED:
            self.db.commit()
            self.offer_next(request.id)
        else:
            self.db.commit()
        self.db.refresh(request)
        return ExpertRequestResponse.model_validate(request)
