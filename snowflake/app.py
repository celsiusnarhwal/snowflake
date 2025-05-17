import secrets
import typing as t
import urllib.parse
import uuid

from authlib.common.errors import AuthlibHTTPError
from authlib.jose import JoseError, jwt
from authlib.oidc.core import IDToken
from fastapi import Depends, FastAPI, Request
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
)
from starlette.exceptions import HTTPException
from starlette.middleware.sessions import SessionMiddleware

from snowflake import utils
from snowflake.middleware import HTTPSOnlyMiddleware
from snowflake.settings import settings

app = FastAPI()
app.add_middleware(HTTPSOnlyMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=secrets.token_urlsafe(32),
    session_cookie=uuid.uuid4().hex,
    max_age=0,
)


# noinspection PyUnusedLocal
@app.exception_handler(AuthlibHTTPError)
async def oauth_exception_handler(request: Request, exception: AuthlibHTTPError):
    raise HTTPException(exception.status_code, exception.description)


@app.get("/authorize")
async def authorize(request: Request, client_id: str, scope: str, redirect_uri: str):
    scopes = set(scope.split(" "))

    if not (
        scopes == {"openid", "profile"} or scopes == {"openid", "profile", "email"}
    ):
        raise HTTPException(400, "Bad scopes")

    discord = utils.get_oauth_client(
        client_id=client_id, scope="identify" + (" email" if "email" in scopes else "")
    )

    authorization_params = {
        k: v for k, v in request.query_params.items() if k not in ["client_id", "scope"]
    }

    resp = await discord.authorize_redirect(request, **authorization_params)
    resp.status_code = settings().redirect_status_code

    return resp


@app.post("/token")
async def token(
    request: Request,
    credentials: t.Annotated[
        HTTPBasicCredentials, Depends(HTTPBasic(auto_error=False))
    ],
):
    body = urllib.parse.parse_qs((await request.body()).decode())
    params = {k: v[0] if len(v) == 1 else v for k, v in body.items()}

    if credentials:
        discord = utils.get_oauth_client(
            client_id=credentials.username, client_secret=credentials.password
        )
    else:
        discord = utils.get_oauth_client(client_id=params.pop("client_id"))

    discord_token = await discord.fetch_access_token(**params)

    resp = await discord.get("users/@me", token=discord_token)
    resp.raise_for_status()

    return utils.create_id_token(
        issuer=str(request.base_url), client_id=discord.client_id, user_info=resp.json()
    )


@app.get("/userinfo")
async def user_info(
    credentials: t.Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
):
    try:
        decoded_jwt = jwt.decode(
            credentials.credentials, utils.get_jwks(), claims_cls=IDToken
        )
        decoded_jwt.validate()
    except JoseError:
        raise HTTPException(401)

    return decoded_jwt


@app.get("/.well-known/jwks.json")
async def jwks():
    return utils.get_jwks()


@app.get("/.well-known/openid-configuration")
async def discovery(request: Request):
    return {
        "issuer": str(request.base_url),
        "claims_supported": [
            "sub",
            "name",
            "preferred_username",
            "locale",
            "picture",
            "email",
            "email_verified",
        ],
        "grant_types_supported": ["authorization_code"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "response_types_supported": ["code", "id_token"],
        "subject_types_supported": ["public"],
        "scopes_supported": ["openid", "profile", "email"],
        "authorization_endpoint": str(request.url_for("authorize")),
        "token_endpoint": str(request.url_for("token")),
        "userinfo_endpoint": str(request.url_for("user_info")),
        "jwks_uri": str(request.url_for("jwks")),
    }
