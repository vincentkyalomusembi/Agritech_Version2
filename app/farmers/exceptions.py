"""
Custom exceptions for the Farmer module.

Services raise these exceptions when business rules are violated.
FastAPI exception handlers convert them into HTTP responses.
"""


class FarmerNotFoundError(Exception):
    """Raised when a farmer does not exist."""

    def __init__(self):
        super().__init__("Farmer not found.")


class PhoneNumberAlreadyExistsError(Exception):
    """Raised when a phone number is already registered."""

    def __init__(self):
        super().__init__("Phone number is already registered.")


class NationalIDAlreadyExistsError(Exception):
    """Raised when a national ID already exists."""

    def __init__(self):
        super().__init__("National ID is already registered.")


class InvalidPinError(Exception):
    """Raised when the provided PIN is incorrect."""

    def __init__(self):
        super().__init__("Invalid PIN.")


class InactiveFarmerError(Exception):
    """Raised when an inactive farmer attempts to log in."""

    def __init__(self):
        super().__init__("Farmer account is inactive.")


class CountyNotFoundError(Exception):
    """Raised when the selected county does not exist."""

    def __init__(self):
        super().__init__("County not found.")


class InvalidPhoneNumberError(Exception):
    """Raised when a phone number format is invalid."""

    def __init__(self):
        super().__init__("Invalid phone number.")


class WeakPinError(Exception):
    """Raised when a PIN does not meet security requirements."""

    def __init__(self):
        super().__init__("PIN does not meet security requirements.")


class SamePinError(Exception):
    """Raised when the new PIN matches the current PIN."""

    def __init__(self):
        super().__init__("New PIN must be different from the current PIN.")


class UnauthorizedError(Exception):
    """Raised when authentication fails."""

    def __init__(self):
        super().__init__("Authentication required.")


class InvalidTokenError(Exception):
    """Raised when a JWT token is invalid or expired."""

    def __init__(self):
        super().__init__("Invalid or expired access token.")