"""
Exceptions for Xoose Builder Engine.
"""


class BuilderError(Exception):
    """Base error for all builder exceptions."""

    def __init__(self, message: str, code: str = "BUILDER_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code

    def to_dict(self) -> dict:
        return {
            "success": False,
            "error": self.message,
            "code": self.code,
        }


class ValidationError(BuilderError):
    """Raised when manifest or input validation fails."""

    def __init__(self, message: str, code: str = "VALIDATION_ERROR"):
        super().__init__(message, code=code)


class SecurityError(BuilderError):
    """Raised when security boundaries are violated."""

    def __init__(self, message: str, code: str = "SECURITY_VIOLATION"):
        super().__init__(message, code=code)


class PathTraversalError(SecurityError):
    """Raised when a path tries to escape its allowed root."""

    def __init__(self, message: str = "Path traversal detected"):
        super().__init__(message, code="PATH_TRAVERSAL")


class InvalidSlugError(ValidationError):
    """Raised when application slug has invalid format."""

    def __init__(self, message: str = "Invalid slug format"):
        super().__init__(message, code="INVALID_SLUG")


class WorkspaceCollisionError(BuilderError):
    """Raised when target workspace already exists without force flag."""

    def __init__(self, message: str = "Target workspace already exists"):
        super().__init__(message, code="WORKSPACE_COLLISION")


class TemplateNotFoundError(BuilderError):
    """Raised when the specified template directory or entry point does not exist."""

    def __init__(self, message: str = "Template source not found"):
        super().__init__(message, code="TEMPLATE_NOT_FOUND")
