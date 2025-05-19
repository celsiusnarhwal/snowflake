from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from snowflake.utils import settings


class HTTPSOnlyMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        scheme = scope["scheme"]

        if scheme == "https" or settings().dev_mode:
            await self.app(scope, receive, send)
        else:
            resp = JSONResponse(
                {
                    "detail": "Snowflake must be served over HTTPS. If you're using a reverse proxy, "
                    "see https://github.com/celsiusnarhwal/snowflake#using-reverse-proxies."
                },
                status_code=400,
            )

            await resp(scope, receive, send)
