class USSDError(Exception):
    """Base exception for USSD-related errors."""


class UnregisteredPhoneError(USSDError):
    def __init__(self):
        super().__init__(
            "Phone number not registered. Please register with an extension officer."
        )


class InvalidPinError(USSDError):
    def __init__(self):
        super().__init__("Invalid PIN. Please try again later.")
