from uuid import UUID

from sqlalchemy.orm import Session

from app.expert_requests.exceptions import (
    ALLOWED_STATUS_TRANSITIONS,
    ExpertRequestNotFoundError,
    FarmerNotFoundError,
    InvalidStatusTransitionError,
)
from app.expert_requests.model import ExpertRequest, RequestStatus
from app.expert_requests.repository import ExpertRequestRepository
from app.expert_requests.schema import (
    ExpertRequestCreate,
    ExpertRequestResponse,
    ExpertRequestStatusUpdate,
)
from app.experts.exceptions import ExpertNotFoundError, ExpertUnavailableError
from app.experts.repository import ExpertRepository
from app.farmers.repository import FarmerRepository
from app.notifications.services.notification_service import NotificationService


class ExpertRequestService:
    """Business logic for expert request submission and status updates."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = ExpertRequestRepository(db)
        self.farmer_repository = FarmerRepository(db)
        self.expert_repository = ExpertRepository(db)
        self.notification_service = NotificationService(db)

    def create_request(
        self,
        data: ExpertRequestCreate,
    ) -> ExpertRequestResponse:
        """
        Create an expert request inside a single transaction.

        Validates farmer and expert existence and expert availability.
        """

        farmer = self.farmer_repository.get_by_id(data.farmer_id)
        if farmer is None:
            raise FarmerNotFoundError()

        expert = self.expert_repository.get_by_id(data.expert_id)
        if expert is None:
            raise ExpertNotFoundError()

        if not expert.is_available:
            raise ExpertUnavailableError()

        try:
            request = ExpertRequest(
                farmer_id=data.farmer_id,
                expert_id=data.expert_id,
                issue_type=data.issue_type,
                description=data.description,
                preferred_visit_date=data.preferred_visit_date,
                status=RequestStatus.PENDING,
            )

            created = self.repository.create(request)

            self.notification_service.create_expert_update_notification(
                farmer_id=data.farmer_id,
                title="Expert request submitted",
                message=(
                    f"Your request for {expert.full_name} "
                    f"({expert.expert_type.value}) has been submitted."
                ),
                commit=False,
            )

            self.db.commit()
            self.db.refresh(created)

            return ExpertRequestResponse.model_validate(created)

        except Exception:
            self.db.rollback()
            raise

    def update_status(
        self,
        data: ExpertRequestStatusUpdate,
    ) -> ExpertRequestResponse:
        """
        Update expert request status and notify the farmer.

        Uses a transaction so request update and notification stay in sync.
        """

        request = self.repository.get_by_id_for_update(data.request_id)
        if request is None:
            raise ExpertRequestNotFoundError()

        if request.status == data.status:
            return ExpertRequestResponse.model_validate(request)

        allowed = ALLOWED_STATUS_TRANSITIONS.get(request.status, set())
        if data.status not in allowed:
            raise InvalidStatusTransitionError(request.status, data.status)

        if (
            data.status == RequestStatus.ACCEPTED
            and not request.expert.is_available
        ):
            raise ExpertUnavailableError()

        previous_status = request.status
        request.status = data.status

        try:
            updated = self.repository.update(request)

            self.notification_service.create_expert_update_notification(
                farmer_id=request.farmer_id,
                title="Expert request status updated",
                message=(
                    f"Your expert request status changed from "
                    f"{previous_status.value} to {data.status.value}."
                ),
                commit=False,
            )

            self.db.commit()
            self.db.refresh(updated)

            return ExpertRequestResponse.model_validate(updated)

        except Exception:
            self.db.rollback()
            raise
