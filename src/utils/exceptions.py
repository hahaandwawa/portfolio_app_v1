class AppError(Exception):
    """Base exception for application errors."""

    def __init__(self, message: str, code: str = "APP_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)

class ValidationError(AppError):
    """Raised when input validation fails."""

    def __init__(self, message: str):
        super().__init__(message, code="VALIDATION_ERROR")


class NotFoundError(AppError):
    """Raised when a requested resource is not found."""

    def __init__(self, resource: str, identifier: str):
        super().__init__(f"{resource} not found: {identifier}", code="NOT_FOUND")