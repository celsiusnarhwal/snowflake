import typing as t

import httpx
from authlib.common.errors import AuthlibHTTPError
from authlib.oauth2.rfc6749 import list_to_scope, scope_to_list
from fastapi import Depends, FastAPI, Request
from fastapi.datastructures import URL
from fastapi.exceptions import HTTPException
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
)
from joserfc.errors import JoseError

from snowflake import security, utils
from snowflake.settings import settings
from snowflake.types import (
    SnowflakeAuthorizationData,
    SnowflakeStateData,
)

app = FastAPI(
    title="Snowflake",
    description="Snowflake lets you use Discord as an OpenID Connect provider. "
    "[github.com/celsiusnarhwal/snowflake](https://github.com/celsiusnarhwal/snowflake)",
    root_path=settings().base_path,
    openapi_url=settings().openapi_url,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings().allowed_host_list)


@app.middleware("http")
async def secure_transport_middleware(request: Request, call_next):
    if not utils.is_secure_transport(request.url):
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


@app.get("/", include_in_schema=False)
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
    nonce: str,
):
    if not utils.is_secure_transport(redirect_uri):
        raise HTTPException(
            400,
            f"Redirect URI {redirect_uri} is insecure. Redirect URIs must be either HTTPS or localhost",
        )

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

    scopes = set(scope_to_list(scope))

    if "openid" not in scopes:
        raise HTTPException(400, "openid scope is required")

    scope_map = {
        "profile": "identify",
        "email": "email",
        "groups": "guilds",
    }

    discord = utils.get_oauth_client(
        client_id=client_id,
        scope=list_to_scope([v for k, v in scope_map.items() if k in scopes]),
    )

    authorization_params = {
        k: v for k, v in request.query_params.items() if k not in ["client_id", "scope"]
    }

    state_data = SnowflakeStateData(state=state, scopes=scopes, nonce=nonce)

    authorization_params.update(
        {"state": state_data.to_jwt(), "redirect_uri": redirect_uri}
    )

    authorization_url_dict = await discord.create_authorization_url(
        **authorization_params
    )

    return RedirectResponse(authorization_url_dict["url"], status_code=302)


@app.get("/r", include_in_schema=False)
async def redirect():
    raise HTTPException(403)


@app.get("/r/{redirect_uri:path}")
async def redirect_to(
    request: Request,
    redirect_uri: str,
    state: str,
    code: str = None,
    error: str = None,
):
    state_data = SnowflakeStateData.from_jwt(state)

    if error or not code:
        full_redirect_uri = URL(redirect_uri).include_query_params(
            **{**request.query_params, "state": state_data.state}
        )
        return RedirectResponse(full_redirect_uri)

    authorization_data = SnowflakeAuthorizationData(
        code=code, scopes=state_data.scopes, nonce=state_data.nonce
    )

    full_redirect_uri = URL(redirect_uri).include_query_params(
        **{
            **request.query_params,
            "state": state_data.state,
            "code": authorization_data.to_jwt(),
        }
    )

    return RedirectResponse(full_redirect_uri, status_code=302)


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

    authorization_data = SnowflakeAuthorizationData.from_jwt(params.pop("code"))

    discord = utils.get_oauth_client(client_id=client_id, client_secret=client_secret)
    discord_token = await discord.fetch_access_token(
        **params, code=authorization_data.code
    )

    return await security.create_tokens(
        request=request,
        discord=discord,
        discord_token=discord_token,
        authorization_data=authorization_data,
    )


@app.get("/userinfo")
async def userinfo(
    request: Request,
    credentials: t.Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
):
    try:
        access_token = security.decode_jwt(
            credentials.credentials,
            security.get_private_key(),
            iss={"essential": True, "value": str(request.base_url)},
        )
    except JoseError:
        raise HTTPException(401)

    async with httpx.AsyncClient() as client:
        resp = await client.get(str(request.url_for("discovery")))
        resp.raise_for_status()

    userinfo_claims = {
        k: v
        for k, v in access_token.claims.items()
        if k in resp.json()["claims_supported"]
    }

    # This should not be possible but you never know.
    if not userinfo_claims:
        raise HTTPException(403)

    return userinfo_claims


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
            "groups",
        ],
        "grant_types_supported": ["authorization_code"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "response_types_supported": ["token", "id_token"],
        "subject_types_supported": ["public"],
        "scopes_supported": ["openid", "profile", "email", "groups"],
        "authorization_endpoint": str(request.url_for("authorize")),
        "token_endpoint": str(request.url_for("token")),
        "userinfo_endpoint": str(request.url_for("userinfo")),
        "jwks_uri": str(request.url_for("jwks")),
    }
