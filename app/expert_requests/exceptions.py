"""
Custom exceptions for the expert requests module.
"""

from app.expert_requests.model import RequestStatus


class ExpertRequestError(Exception):
    """Base exception for expert request errors."""

    pass


class ExpertRequestNotFoundError(ExpertRequestError):
    """Raised when an expert request cannot be found."""

    def __init__(self):
        super().__init__("Expert request not found.")


class FarmerNotFoundError(ExpertRequestError):
    """Raised when the referenced farmer does not exist."""

    def __init__(self):
        super().__init__("Farmer not found.")


class InvalidStatusTransitionError(ExpertRequestError):
    """Raised when a status change is not allowed."""

    def __init__(
        self,
        current: RequestStatus,
        requested: RequestStatus,
    ):
        super().__init__(
            f"Cannot transition from {current.value} to {requested.value}."
        )


ALLOWED_STATUS_TRANSITIONS: dict[RequestStatus, set[RequestStatus]] = {
    RequestStatus.PENDING: {
        RequestStatus.ACCEPTED,
        RequestStatus.CANCELLED,
    },
    RequestStatus.ACCEPTED: {
        RequestStatus.COMPLETED,
        RequestStatus.CANCELLED,
    },
    RequestStatus.COMPLETED: set(),
    RequestStatus.CANCELLED: set(),
}
