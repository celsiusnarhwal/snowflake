from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from snowflake.utils import settings


class HTTPSOnlyMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["scheme"] == "https" or settings().dev_mode:
            await self.app(scope, receive, send)
        else:
            resp = JSONResponse(
                {"detail": "Client sent an HTTP request to an HTTPS server"},
                status_code=400,
            )
            await resp(scope, receive, send)
