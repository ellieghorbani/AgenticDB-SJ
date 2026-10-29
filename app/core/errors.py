"""Domain-specific errors exposed through API exception handlers."""


class ResourceNotFoundError(LookupError):
    """Raised when a requested database entity does not exist."""
