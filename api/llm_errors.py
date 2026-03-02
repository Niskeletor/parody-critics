"""
LLM exception hierarchy for Parody Critics.
Typed errors allow callers to react differently to timeouts vs connection
failures vs bad responses — instead of catching bare Exception everywhere.
"""


class LLMError(Exception):
    """Base for all LLM-related errors."""


class LLMConnectionError(LLMError):
    """Could not reach the Ollama server (refused, unreachable)."""


class LLMTimeoutError(LLMError):
    """Request reached the server but timed out waiting for a response."""

    def __init__(self, message: str, timeout_seconds: int):
        super().__init__(message)
        self.timeout_seconds = timeout_seconds


class LLMHTTPError(LLMError):
    """Ollama returned a non-2xx HTTP response."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


class LLMParseError(LLMError):
    """Response received but could not be parsed into a usable critique."""
