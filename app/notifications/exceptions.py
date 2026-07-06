"""
Custom exceptions for the notifications module.
"""


class NotificationError(Exception):
    """Base exception for notification-related errors."""

    pass


class FarmerIdRequiredError(NotificationError):
    """Raised when a farmer_id filter is required but missing."""

    def __init__(self):
        super().__init__("farmer_id is required.")


class NotificationNotFoundError(NotificationError):
    """Raised when a notification cannot be found."""

    def __init__(self):
        super().__init__("Notification not found.")
