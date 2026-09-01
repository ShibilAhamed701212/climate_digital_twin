from __future__ import annotations


class DisasterError(Exception):
    def __init__(self, message: str, code: str = "INTERNAL_ERROR") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ValidationError(DisasterError):
    def __init__(self, message: str, code: str = "BAD_REQUEST") -> None:
        super().__init__(message, code)


class NotFoundError(DisasterError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "NOT_FOUND")


class ConflictError(DisasterError):
    def __init__(self, message: str, code: str = "CONFLICT") -> None:
        super().__init__(message, code)


class TaskNotEnabledError(DisasterError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "TASK_NOT_ENABLED")
