class XSenseError(Exception):
    pass


class SessionExpired(XSenseError):
    pass


class AuthFailed(XSenseError):
    pass


class APIFailure(XSenseError):
    pass


class NotFoundError(XSenseError):
    pass
