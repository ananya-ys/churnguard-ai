class AppBaseException(Exception):
    """Base for all application exceptions."""
    status_code: int = 500
    error: str = "internal_error"

    def __init__(self, message: str = "An unexpected error occurred") -> None:
        self.message = message
        super().__init__(message)


class NotFoundException(AppBaseException):
    status_code = 404
    error = "not_found"


class ConflictException(AppBaseException):
    status_code = 409
    error = "conflict"


class UnauthorizedException(AppBaseException):
    status_code = 401
    error = "unauthorized"


class ForbiddenException(AppBaseException):
    status_code = 403
    error = "forbidden"


class ValidationException(AppBaseException):
    status_code = 422
    error = "validation_error"


class PipelineNotLoadedException(AppBaseException):
    status_code = 503
    error = "model_unavailable"

    def __init__(self) -> None:
        super().__init__("ML pipeline is not loaded. Contact administrator.")


class JobFailedException(AppBaseException):
    status_code = 500
    error = "job_failed"


class AUCGateException(AppBaseException):
    status_code = 422
    error = "auc_gate_failed"

    def __init__(self, auc: float, threshold: float) -> None:
        super().__init__(
            f"Model AUC {auc:.4f} is below minimum threshold {threshold:.4f}"
        )


class FileTooLargeException(AppBaseException):
    status_code = 413
    error = "file_too_large"


class InvalidFileException(AppBaseException):
    status_code = 400
    error = "invalid_file"
