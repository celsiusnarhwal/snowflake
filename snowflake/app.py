import logging
import secrets
import typing as t
import uuid

from authlib.common.errors import AuthlibHTTPError
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
)
from joserfc import jwt
from joserfc.errors import JoseError
from starlette.datastructures import URL
from starlette.exceptions import HTTPException
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse

from snowflake import security, utils
from snowflake.settings import settings
from snowflake.types import SnowflakeAuthorizationData, SnowflakeStateData

logger = logging.getLogger("uvicorn")

app = FastAPI(root_path=settings().base_path, docs_url=settings().docs_url)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings().allowed_host_list)
app.add_middleware(
    SessionMiddleware,
    secret_key=secrets.token_urlsafe(32),
    session_cookie=uuid.uuid4().hex,
    https_only=not settings().internal.dev_mode,
    max_age=0,
)


@app.middleware("http")
async def enforce_https(request: Request, call_next):
    if request.url.scheme != "https" and not settings().internal.dev_mode:
        return JSONResponse(
            {
                "detail": "Snowflake must be served over HTTPS. If you're using a reverse proxy, "
                "see https://github.com/celsiusnarhwal/snowflake#https-and-reverse-proxies."
            },
            status_code=400,
        )

    return await call_next(request)


# noinspection PyUnusedLocal
@app.exception_handler(AuthlibHTTPError)
async def oauth_exception_handler(request: Request, exception: AuthlibHTTPError):
    raise HTTPException(exception.status_code, exception.description)


@app.get("/")
def root():
    if settings().root_redirect_url:
        return RedirectResponse(settings().root_redirect_url)

    raise HTTPException(404)


@app.get("/authorize")
async def authorize(
    request: Request,
    client_id: str,
    scope: str,
    redirect_uri: str,
    state: str,
    nonce: str = None,
):
    fixed_redirect_uri = utils.fix_redirect_uri(request, redirect_uri)

    if redirect_uri != fixed_redirect_uri:
        if settings().fix_redirect_uris:
            redirect_uri = fixed_redirect_uri
        else:
            raise HTTPException(
                400,
                f"Redirect URI must be a subpath of {request.url_for('redirect')} "
                f"(e.g., {fixed_redirect_uri}",
            )

    scopes = set(scope.split(" "))

    for scope in ["openid", "profile"]:
        if scope not in scopes:
            raise HTTPException(400, f"{scope} scope is required")

    discord = utils.get_oauth_client(
        client_id=client_id,
        scope="identify " + ("email" if "email" in scopes else ""),
    )

    authorization_params = {
        k: v for k, v in request.query_params.items() if k not in ["client_id", "scope"]
    }

    authorization_params["redirect_uri"] = redirect_uri

    resp = await discord.authorize_redirect(request, **authorization_params)
    resp.status_code = settings().redirect_status_code

    state_data = SnowflakeStateData(scopes=scopes, nonce=nonce)

    async with settings().redis as redis:
        await redis.set(state, state_data.model_dump_json(), ex=300)

    return resp


@app.get("/r", include_in_schema=False)
async def redirect():
    raise HTTPException(403)


@app.get("/r/{redirect_uri:path}")
async def redirect_to(
    request: Request, redirect_uri: str, code: str, state: str = None
):
    async with settings().redis as redis:
        state_data = SnowflakeStateData.model_validate_json(await redis.getdel(state))

    snowflake_code = SnowflakeAuthorizationData(
        code=code, scopes=state_data.scopes, nonce=state_data.nonce
    )
    full_redirect_uri = URL(redirect_uri).include_query_params(
        **{**request.query_params, "code": snowflake_code.to_encrypted()}
    )

    return RedirectResponse(full_redirect_uri)


@app.post("/token")
async def token(
    request: Request,
    credentials: t.Annotated[
        HTTPBasicCredentials, Depends(HTTPBasic(auto_error=False))
    ],
):
    params = dict(await request.form())

    if settings().fix_redirect_uris:
        params["redirect_uri"] = utils.fix_redirect_uri(request, params["redirect_uri"])

    client_id = params.pop("client_id", None)
    client_secret = params.pop("client_secret", None)

    if credentials:
        client_id = client_id or credentials.username
        client_secret = client_secret or credentials.password

    authorization_data = SnowflakeAuthorizationData.from_encrypted(params.pop("code"))

    discord = utils.get_oauth_client(client_id=client_id, client_secret=client_secret)
    discord_token = await discord.fetch_access_token(
        **params, code=authorization_data.code
    )

    return await security.create_tokens(
        issuer=str(request.base_url),
        discord=discord,
        discord_token=discord_token,
        authorization_data=authorization_data,
    )


@app.get("/userinfo")
async def userinfo(
    credentials: t.Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
):
    access_token = credentials.credentials

    try:
        jwt.decode(credentials.credentials, security.get_private_key())
    except JoseError:
        raise HTTPException(401)

    async with settings().redis as redis:
        user_info = await redis.get(access_token)

    if not user_info:
        raise HTTPException(404)


@app.get("/.well-known/jwks.json")
async def jwks():
    return security.get_jwks()


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
        "jwks_uri": str(request.url_for("jwks")),
    }
