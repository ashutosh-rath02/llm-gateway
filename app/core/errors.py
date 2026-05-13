class GatewayError(Exception):
    def __init__(
        self,
        message: str,
        *,
        error_type: str,
        status_code: int = 500,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.status_code = status_code
