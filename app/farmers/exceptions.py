"""
Custom exceptions for the farmers module.

These exceptions represent business rule violations.
The router will convert them into HTTP responses.
"""


class FarmerError(Exception):
    
    #Base exception for farmer-related errors.
    

    pass


class FarmerNotFoundError(FarmerError):
    
    #Raised when a farmer cannot be found.
    

    def __init__(self):
        super().__init__("Farmer not found.")


class PhoneNumberAlreadyExistsError(FarmerError):
    
    #Raised when a phone number is already registered.
    

    def __init__(self):
        super().__init__("Phone number already exists.")


class NationalIDAlreadyExistsError(FarmerError):
    
    #Raised when a national ID is already registered.
    

    def __init__(self):
        super().__init__("National ID already exists.")


class InvalidPinError(FarmerError):
    
    #Raised when a PIN is incorrect.
    

    def __init__(self):
        super().__init__("Invalid PIN.")


class InactiveFarmerError(FarmerError):
    
    #Raised when the farmer account is inactive.
    

    def __init__(self):
        super().__init__("Farmer account is inactive.")