"""OpenAI-style error responses: {"error": {"message", "type", "param", "code"}}."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

_TYPES = {
    400: "invalid_request_error",
    401: "authentication_error",
    404: "invalid_request_error",
    429: "rate_limit_error",
}


def error_body(status: int, message: str, code: str | None = None, param: str | None = None):
    return {
        "error": {
            "message": message,
            "type": _TYPES.get(
                status, "server_error" if status >= 500 else "invalid_request_error"
            ),
            "param": param,
            "code": code,
        }
    }


class VortexError(Exception):
    def __init__(
        self, status_code: int, message: str, *, code: str | None = None, param: str | None = None
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.code = code
        self.param = param


class BackendError(VortexError):
    """The model backend (Ollama, llama.cpp, vLLM) failed or is unreachable."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(status_code, message, code="backend_error")


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(VortexError)
    async def _vortex_error(_: Request, exc: VortexError) -> JSONResponse:
        return JSONResponse(
            error_body(exc.status_code, exc.message, exc.code, exc.param),
            status_code=exc.status_code,
        )
