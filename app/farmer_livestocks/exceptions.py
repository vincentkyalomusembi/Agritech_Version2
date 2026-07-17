class LivestockAlreadyExistsError(Exception):
    """
    Raised when a farmer registers the same livestock twice.
    """

    pass


class FarmerLivestockNotFoundError(Exception):
    """
    Raised when farmer livestock does not exist.
    """

    pass