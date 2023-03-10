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
    pass


class LoginError(Exception):
    pass


class CaptchaError(Exception):
    pass
