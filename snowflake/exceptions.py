from starlette.exceptions import HTTPException


class InsecureRedirectURIError(HTTPException):
    def __init__(self, redirect_uri):
        detail = f"Redirect URI {redirect_uri} is insecure. Redirect URIs must be either HTTPS or localhost"
        super().__init__(status_code=400, detail=detail)
