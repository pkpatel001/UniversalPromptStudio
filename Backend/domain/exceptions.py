"""Application-domain exceptions for provider execution boundaries."""

from __future__ import annotations


class AIProviderExecutionError(RuntimeError):
    """A safe structured provider failure translated for application callers."""

    def __init__(
        self,
        provider_name: str,
        code: str,
        message: str,
        *,
        retryable: bool,
    ) -> None:
        super().__init__(message)
        self.provider_name = provider_name
        self.code = code
        self.retryable = retryable


__all__ = ["AIProviderExecutionError"]
