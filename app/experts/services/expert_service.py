from uuid import UUID

from sqlalchemy.orm import Session

from app.experts.exceptions import ExpertNotFoundError
from app.experts.model import Expert, ExpertType
from app.experts.repository import DEFAULT_LIST_LIMIT, ExpertRepository
from app.experts.schema import ExpertListResponse, ExpertResponse


class ExpertService:
    """Business logic for expert lookup and listing."""

    def __init__(self, db: Session):
        self.repository = ExpertRepository(db)

    def get_expert(self, expert_id: UUID) -> Expert:
        """Return a single expert or raise if not found."""

        expert = self.repository.get_by_id(expert_id)

        if expert is None:
            raise ExpertNotFoundError()

        return expert

    def list_experts(
        self,
        county_id: UUID | None = None,
        expert_type: ExpertType | None = None,
        is_available: bool | None = None,
        limit: int | None = DEFAULT_LIST_LIMIT,
        offset: int = 0,
    ) -> ExpertListResponse:
        """
        List experts with optional filters.

        Results are capped by DEFAULT_LIST_LIMIT unless limit is explicitly set.
        """

        effective_limit = limit if limit is not None else DEFAULT_LIST_LIMIT
        if effective_limit > DEFAULT_LIST_LIMIT:
            effective_limit = DEFAULT_LIST_LIMIT

        experts = self.repository.list_filtered(
            county_id=county_id,
            expert_type=expert_type,
            is_available=is_available,
            limit=effective_limit,
            offset=offset,
        )

        total = self.repository.count_filtered(
            county_id=county_id,
            expert_type=expert_type,
            is_available=is_available,
        )

        return ExpertListResponse(
            items=[ExpertResponse.model_validate(expert) for expert in experts],
            total=total,
            limit=effective_limit,
            offset=offset,
        )
