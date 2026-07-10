class CropAlreadyExistsError(Exception):
    """
    Raised when a farmer registers the same crop twice.
    """

    pass


class FarmerCropNotFoundError(Exception):
    """
    Raised when a farmer crop does not exist.
    """

    pass