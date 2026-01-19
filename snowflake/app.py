import typing as t

import dns.name
import httpx
from authlib.common.errors import AuthlibHTTPError
from authlib.oauth2.rfc6749 import list_to_scope, scope_to_list
from fastapi import Depends, FastAPI, Form, Request
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
from pydantic import AfterValidator, Field, validate_email

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
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings().allowed_hosts)


@app.middleware("http")
async def secure_transport_middleware(request: Request, call_next):
    """
    Enforce HTTPS for external connections.
    """
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
    """
    Re-raise `AuthlibHTTPError` exceptions as `HTTPException` exceptions.
    """
    raise HTTPException(exception.status_code, exception.description)


@app.get("/", include_in_schema=False)
def root():
    if settings().root_redirect_url:
        return RedirectResponse(settings().root_redirect_url)

    raise HTTPException(404)


@app.get("/health", include_in_schema=False)
def health():
    return


@app.get("/authorize")
async def authorize(
    request: Request,
    client_id: str,
    scope: str,
    redirect_uri: str,
    state: str = None,
    nonce: str = None,
):
    """
    Authorization endpoint.
    """
    if not {client_id, "*"}.intersection(settings().allowed_clients):
        raise HTTPException(400, f"Client ID {client_id} is not allowed")

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

    state_data = SnowflakeStateData(state=state, scopes=scopes, nonce=nonce)

    authorization_params = {
        **request.query_params,
        "state": state_data.to_jwt(),
        "redirect_uri": redirect_uri,
    }

    for param in "client_id", "scope":
        authorization_params.pop(param, None)

    authorization_url_dict = await discord.create_authorization_url(
        **authorization_params
    )

    return RedirectResponse(authorization_url_dict["url"], status_code=302)


@app.get("/r", include_in_schema=False)
async def redirect():
    """
    Dummy endpoint that exists so `snowflake.utils.fix_redirect_uri()` can work properly.
    """
    raise HTTPException(403)


@app.get("/r/{redirect_uri:path}")
async def callback(
    request: Request,
    redirect_uri: str,
    state: str,
    code: str = None,
    error: str = None,
):
    """
    Callback endpoint.
    """
    state_data = SnowflakeStateData.from_jwt(state)

    full_redirect_uri = URL(redirect_uri).include_query_params(
        **{**request.query_params, "state": state_data.state}
    )

    if not state_data.state:
        full_redirect_uri = full_redirect_uri.remove_query_params("state")

    if code and not error:
        authorization_data = SnowflakeAuthorizationData(
            code=code, scopes=state_data.scopes, nonce=state_data.nonce
        )

        full_redirect_uri = full_redirect_uri.include_query_params(
            code=authorization_data.to_jwt()
        )

    return RedirectResponse(full_redirect_uri, status_code=302)


@app.post("/token")
async def token(
    request: Request,
    code: t.Annotated[str, Form()],
    redirect_uri: t.Annotated[str, Form()],
    credentials: t.Annotated[
        HTTPBasicCredentials, Depends(HTTPBasic(auto_error=False))
    ],
    client_id: t.Annotated[str, Form()] = None,
    client_secret: t.Annotated[str, Form()] = None,
):
    """
    Token endpoint.
    """
    if (client_id or client_secret) and credentials:
        raise HTTPException(
            400,
            "You cannot supply both client_secret_basic and client_secret_post "
            "authentication at the same time",
        )

    client_id = client_id or credentials.username
    client_secret = client_secret or credentials.password

    authorization_data = SnowflakeAuthorizationData.from_jwt(code)

    token_params = {
        **(await request.form()),
        "code": authorization_data.code,
        "redirect_uri": utils.fix_redirect_uri(request, redirect_uri),
    }

    for param in "client_id", "client_secret":
        token_params.pop(param, None)

    discord = utils.get_oauth_client(client_id=client_id, client_secret=client_secret)
    discord_token = await discord.fetch_access_token(**token_params)

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
    """
    User info endpoint.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(str(request.url_for("discovery")))
        resp.raise_for_status()

    oidc_metadata = resp.json()

    try:
        access_token = security.decode_jwt(
            credentials.credentials,
            iss={"essential": True, "value": oidc_metadata["issuer"]},
        )
    except JoseError:
        raise HTTPException(401)

    userinfo_claims = {
        k: v
        for k, v in access_token.claims.items()
        if k in oidc_metadata["claims_supported"]
    }

    # This should not be possible but you never know.
    if not userinfo_claims:
        raise HTTPException(403)

    return userinfo_claims


@app.get("/.well-known/jwks.json")
async def jwks():
    """
    JWKS endpoint.
    """
    return security.get_jwks().as_dict()


@app.get("/.well-known/webfinger")
async def webfinger(
    resource: t.Annotated[
        str,
        Field(pattern="acct:\S+"),
        AfterValidator(lambda x: "acct:" + validate_email(x.split("acct:")[1])[1]),
    ],
    request: Request,
):
    """
    WebFinger endpoint.

    See Also
        https://webfinger.net/

    """
    domain = dns.name.from_text(resource.split("@")[1])

    if any(
        domain == name or name.is_wild() and domain.is_subdomain(name.parent())
        for name in settings().allowed_webfinger_hosts
    ):
        return {
            "subject": resource,
            "links": [
                {
                    "rel": "http://openid.net/specs/connect/1.0/issuer",
                    "href": str(request.base_url),
                }
            ],
        }

    raise HTTPException(404)


@app.get("/.well-known/openid-configuration")
async def discovery(request: Request):
    """
    OpenID Connect discovery endpoint.

    See Also
        https://openid.net/specs/openid-connect-discovery-1_0.html
    """
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
