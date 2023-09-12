class FlagError(Exception):
    pass


class ParserError(Exception):
    pass


class GeoBlockedError(Exception):
    pass


class ResolutionError(Exception):
    pass


class LoginRequiredError(Exception):
    pass


class HTTPError(Exception):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

    def __str__(self) -> str:
        return self.message


class LoginError(Exception):
    pass


class CaptchaError(Exception):
    pass
