import typing as t

import dns.name
from authlib.common.errors import AuthlibHTTPError
from authlib.oauth2.rfc6749 import scope_to_list
from fastapi import Depends, FastAPI, Form, Header, Request
from fastapi.datastructures import URL
from fastapi.exceptions import HTTPException
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.params import Path as PathParam
from fastapi.params import Query
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
)
from httpx import HTTPStatusError
from joserfc.errors import JoseError
from pydantic import AfterValidator, Field, validate_email
from scalar_fastapi import get_scalar_api_reference

import snowflake.responses as r
from snowflake import security, utils
from snowflake.serializable import (
    SnowflakeAuthorizationData,
    SnowflakeStateData,
)
from snowflake.settings import settings

app = FastAPI(
    title="Snowflake",
    description="Snowflake lets you use Discord as an OpenID Connect provider. "
    "[github.com/celsiusnarhwal/snowflake](https://github.com/celsiusnarhwal/snowflake)",
    license_info={
        "name": "MIT License",
        "url": "https://github.com/celsiusnarhwal/snowflake/blob/main/LICENSE.md",
    },
    root_path=settings().base_path,
    version="2.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings().enable_docs else None,
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
@app.exception_handler(HTTPStatusError)
async def http_error_handler(
    request: Request, exception: AuthlibHTTPError | HTTPStatusError
):
    """
    Re-raise exceptions that correspond to HTTP status codes as `HTTPException` exceptions.
    """
    if isinstance(exception, HTTPStatusError):
        status_code = exception.response.status_code
        description = exception.response.json()
    else:
        status_code = exception.status_code
        description = exception.description

    raise HTTPException(status_code, description)


@app.get("/", include_in_schema=False)
def root(request: Request):
    if settings().root_redirect == "off":
        raise HTTPException(404)

    redirects = {
        "repo": "https://github.com/celsiusnarhwal/snowflake",
        "settings": "https://discord.com/settings/account",
        "docs": request.url_for("docs"),
    }

    return RedirectResponse(redirects[settings().root_redirect])


@app.get("/docs", include_in_schema=False)
async def docs():
    if settings().enable_docs:
        return get_scalar_api_reference(
            title="Snowflake",
            openapi_url=app.openapi_url,
            hide_models=True,
            hide_client_button=True,
            show_developer_tools="localhost"
            if settings().private.show_scalar_devtools_on_localhost
            else "never",
        )

    raise HTTPException(404)


@app.get("/health", summary="Healthcheck", response_class=Response)
def health():
    """
    This endpoint returns an empty HTTP 200 response and does nothing else.
    """
    return


@app.get(
    "/authorize",
    summary="Authorization",
    response_class=RedirectResponse,
    status_code=302,
    responses={400: {"model": r.HTTPClientErrorResponse}},
)
async def authorize(
    request: Request,
    client_id: t.Annotated[str, Query(title="Client ID")],
    scope: t.Annotated[
        str,
        Query(
            description="Supported scopes are `openid`, `profile`, `email`, and `groups`. Only`openid` is required, "
            'but you will get a "no scopes provided" error from Discord if you do not '
            "supply at least one other scope."
        ),
    ],
    redirect_uri: t.Annotated[
        str,
        Query(
            title="Redirect URI",
            description="Either this must point to Snowflake's [callback endpoint](#GET/r/{redirect_uri}) or "
            "`SNOWFLAKE_FIX_REDIRECT_URIS` must be `true`.",
        ),
    ] = None,
    state: t.Annotated[
        str,
        Field(
            description="While optional, it is "
            "[highly recommended](https://discord.com/developers/docs/topics/oauth2#state-and-security) "
            "to supply this parameter.",
        ),
    ] = None,
    nonce: str = None,
    referrer: t.Annotated[str | None, Header(alias="referer")] = None,
):
    """
    Clients are directed to this endpoint to begin the authorization process.
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
                f"(e.g., {fixed_redirect_uri})",
            )

    scopes = set(scope_to_list(scope))

    if "openid" not in scopes:
        raise HTTPException(400, "openid scope is required")

    discord = utils.get_oauth_client(
        client_id=client_id,
        scope=utils.convert_scopes(scopes, to_format="discord", output_type=str),
    )

    state_data = SnowflakeStateData(
        state=state,
        redirect_uri=redirect_uri,
        nonce=nonce,
        referrer=referrer,
    )

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
    raise HTTPException(404)


@app.get(
    "/r/{redirect_uri:path}",
    summary="Callback",
    response_class=RedirectResponse,
    status_code=302,
    responses={400: {"model": r.HTTPClientErrorResponse}},
)
async def callback(
    request: Request,
    redirect_uri: t.Annotated[str, PathParam(title="Redirect URI")],
    state: str,
    code: t.Annotated[str, Query(title="Authorization Code")] = None,
    error: str = None,
):
    """
    Discord must redirect to this endpoint upon successful authorization.
    """
    state_data = SnowflakeStateData.from_jwt(state)

    if (
        error == "access_denied"
        and state_data.referrer
        and settings().return_to_referrer
    ):
        return RedirectResponse(state_data.referrer, status_code=302)

    if utils.fix_redirect_uri(request, redirect_uri) != state_data.redirect_uri:
        raise HTTPException(
            400, "Redirect URI does not match what was sent at authorization"
        )

    full_redirect_uri = (
        URL(redirect_uri)
        .include_query_params(**request.query_params)
        .remove_query_params("state")
    )

    if state_data.state:
        full_redirect_uri = full_redirect_uri.include_query_params(
            state=state_data.state
        )

    if code and not error:
        authorization_data = SnowflakeAuthorizationData(
            code=code, nonce=state_data.nonce
        )

        full_redirect_uri = full_redirect_uri.include_query_params(
            code=authorization_data.to_jwt()
        )

    return RedirectResponse(full_redirect_uri, status_code=302)


@app.post(
    "/token",
    summary="Token",
    response_model=r.TokenResponse,
    responses={400: {"model": r.HTTPClientErrorResponse}},
)
async def token(
    request: Request,
    credentials: t.Annotated[
        HTTPBasicCredentials,
        Depends(
            HTTPBasic(
                auto_error=False,
                scheme_name="Client ID / Client Secret",
                description="The authenticating Discord application's client ID (username) and "
                "client secret (password).",
            )
        ),
    ],
    grant_type: t.Annotated[str, Form(title="Grant Type")] = None,
    client_id: t.Annotated[
        str,
        Form(
            title="Client ID",
            description="Required unless client credentials are provided via HTTP Basic authentication.",
        ),
    ] = None,
    client_secret: t.Annotated[
        str,
        Form(
            description="Required for non-public clients unless client credentials are provided via HTTP Basic "
            "authentication."
        ),
    ] = None,
    redirect_uri: t.Annotated[
        str,
        Form(
            title="Redirect URI",
            description="Required unless `grant_type` is `refresh_token`.",
        ),
    ] = None,
    code: t.Annotated[
        str,
        Form(
            title="Authorization Code",
            description="Required unless `grant_type` is `refresh_token`.",
        ),
    ] = None,
    refresh_token: t.Annotated[
        str,
        Form(
            title="Refresh Token",
            description="Required if `grant_type` is `refresh_token`.",
        ),
    ] = None,
):
    """
    Clients obtain tokens from this endpoint.

    The client ID and client secret may be provided via either form fields or HTTP Basic authentication, but not both.
    Public clients using the PKCE-enhanced authorization code flow may omit the client secret entirely.
    """
    oidc_metadata = utils.get_discovery_info(request)

    if (client_id or client_secret) and credentials:
        raise HTTPException(
            400,
            "You cannot supply client credentials via both form fields and HTTP Basic authentication at the "
            "same time",
        )

    if credentials:
        client_id = credentials.username
        client_secret = credentials.password

    if not client_id:
        raise HTTPException(400, "Client ID is required")

    if grant_type == "refresh_token":
        if not refresh_token:
            raise HTTPException(400, "Refresh Token is required")

        discord = utils.get_oauth_client(
            client_id=client_id, client_secret=client_secret
        )

        return await security.refresh_token(
            discord=discord,
            token=refresh_token,
            oidc_metadata=oidc_metadata,
            params=await request.form(),
        )

    if not redirect_uri:
        raise HTTPException(400, "Redirect URI is required")

    if not code:
        raise HTTPException(400, "Authorization code is required")

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
        discord=discord,
        discord_token=discord_token,
        nonce=authorization_data.nonce,
        oidc_metadata=oidc_metadata,
    )


@app.get(
    "/userinfo",
    summary="User Info",
    response_model=r.UserInfoResponse,
    responses={code: {"model": r.HTTPClientErrorResponse} for code in [401, 403]},
)
@app.post("/userinfo", include_in_schema=False)
async def userinfo(
    request: Request,
    credentials: t.Annotated[
        HTTPAuthorizationCredentials,
        Depends(
            HTTPBearer(
                scheme_name="Access Token",
                description="An access token recieved from the `/token` endpoint.",
            )
        ),
    ],
):
    """
    This endpoint recieves an access token via HTTP Bearer authentication and returns its claims.

    > [!note]
      It is recommended that clients obtain user claims by decoding the ID token directly rather than using this
      endpoint; the data is the same either way.

    Only `sub` is guaranteed to be present in the response. The presence of other claims is dependent on the scopes
    the token was granted with.

    This endpoint also accepts `POST` requests per
    [OpenID Connect Core 1.0 § 5.3](https://openid.net/specs/openid-connect-core-1_0.html#UserInfo). Usage is identical
    to `GET`.
    """
    oidc_metadata = utils.get_discovery_info(request)

    try:
        access_token = security.decode_jwt(
            credentials.credentials,
            iss={"essential": True, "value": oidc_metadata["issuer"]},
            aud={"essential": True, "value": oidc_metadata["userinfo_endpoint"]},
        )
    except (JoseError, ValueError):
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


@app.get("/.well-known/jwks.json", summary="JWKS", response_model=r.JWKSResponse)
async def jwks():
    """
    This endpoint returns the public JSON Web Key Set.
    """
    return security.get_jwks().as_dict()


@app.get(
    "/.well-known/webfinger",
    summary="WebFinger",
    response_model=r.WebFingerResponse,
    responses={404: {"model": r.HTTPClientErrorResponse}},
)
async def webfinger(
    request: Request,
    resource: t.Annotated[
        str,
        Query(
            pattern=r"acct:\S+",
            description="Must be an email address prepended with `acct:`.",
            example="acct:koumae@kitauji.ed.jp",
        ),
        AfterValidator(lambda x: "acct:" + validate_email(x.split("acct:")[1])[1]),
    ],
    rel: t.Annotated[
        str,
        Query(
            title="Link Relation",
            description="The `links` array in the response will be empty if this is anything other than its "
            "default value.",
        ),
    ] = "http://openid.net/specs/connect/1.0/issuer",
):
    """
    This endpoint implements limited support for the [WebFinger](https://en.wikipedia.org/wiki/WebFinger) protocol.
    """
    domain = dns.name.from_text(resource.split("@")[1])

    if any(
        domain == name or name.is_wild() and domain.is_subdomain(name.parent())
        for name in settings().allowed_webfinger_hosts
    ):
        response = {"subject": resource, "links": []}

        if rel == "http://openid.net/specs/connect/1.0/issuer":
            response["links"].append({"rel": rel, "href": str(request.base_url)})

        return response

    raise HTTPException(404, f"The resource {resource} does not exist on this server")


@app.get(
    "/.well-known/openid-configuration",
    summary="Discovery",
    response_model=r.DiscoveryResponse,
)
async def discovery(request: Request):
    """
    This endpoint implements [OpenID Connect Discovery 1.0](https://openid.net/specs/openid-connect-discovery-1_0.html).
    """
    return utils.get_discovery_info(request)
