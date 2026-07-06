"""
Custom exceptions for the experts module.
"""


class ExpertError(Exception):
    """Base exception for expert-related errors."""

    pass


class ExpertNotFoundError(ExpertError):
    """Raised when an expert cannot be found."""

    def __init__(self):
        super().__init__("Expert not found.")


class ExpertUnavailableError(ExpertError):
    """Raised when an expert is not available for requests."""

    def __init__(self):
        super().__init__("Expert is not available.")
