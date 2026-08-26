"""Domain errors. Controllers raise these; the error middleware maps them to HTTP."""


class AppError(Exception):
    """Base domain error.

    `include_sucesso` exists because the legacy API is inconsistent: some error
    bodies carry a "sucesso" flag and some do not. The refactor preserves each
    endpoint's original shape, so each raise site decides.
    """

    status_code = 500

    def __init__(self, message, status_code=None, include_sucesso=False):
        super().__init__(message)
        self.message = message
        self.include_sucesso = include_sucesso
        if status_code is not None:
            self.status_code = status_code

    def to_payload(self):
        payload = {"erro": self.message}
        if self.include_sucesso:
            payload["sucesso"] = False
        return payload


class ValidationError(AppError):
    status_code = 400


class NotFoundError(AppError):
    status_code = 404


class UnauthorizedError(AppError):
    status_code = 401


class ConflictError(AppError):
    status_code = 409
