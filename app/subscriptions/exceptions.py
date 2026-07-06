"""
Custom exceptions for the subscriptions module.
"""


class SubscriptionError(Exception):
    """Base exception for subscription-related errors."""

    pass


class SubscriptionNotFoundError(SubscriptionError):
    """Raised when a farmer has no subscription record."""

    def __init__(self):
        super().__init__("Subscription not found.")


class FarmerNotFoundError(SubscriptionError):
    """Raised when the referenced farmer does not exist."""

    def __init__(self):
        super().__init__("Farmer not found.")
