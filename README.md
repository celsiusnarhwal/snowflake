# Snowflake

Snowflake enables you to use [Discord](https://discord.com) as
an [OpenID Connect](https://auth0.com/docs/authenticate/protocols/openid-connect-protocol) (OIDC) provider. With it, you
can use Discord to identify your application's users without needing to implement specific support for Discord's OAuth2
API.

Conceptually, Snowflake itself is a spec-compliant OIDC provider and can be used like any other OIDC provider.

> [!IMPORTANT]
> Snowflake must be served over HTTPS.

## Installation

[Docker](https://docs.docker.com) is the only supported way of running Snowflake. The `SNOWFLAKE_ALLOWED_HOSTS`
environment variable must be set; see [Configuration](#configuration).

> [!TIP]
> Throughout this README, `snowflake.example.com` will be used as a placeholder for the domain at which your
> Snowflake instace is reachable.

<hr>

<details>
<summary>Supported Tags</summary>
<br>

| **Name**             | **Description**                                                                               | **Example**                                                                            |
|----------------------|-----------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| `latest`             | The latest stable version of Snowflake.                                                       | `ghcr.io/celsiusnarhwal/snowflake:latest`                                              |
| Major version number | The latest release of this major version of Snowflake. May be optionally prefixed with a `v`. | `ghcr.io/celsiusnarhwal/snowflake:1`<br/>`ghcr.io/celsiusnarhwal/snowflake:v1`         |
| Exact version number | This version of Snowflake exactly. May be optionally prefixed with a `v`.                     | `ghcr.io/celsiusnarhwal/snowflake:1.0.0`<br/>`ghcr.io/celsiusnarhwal/snowflake:v1.0.0` |
| `edge`               | The latest commit to Snowflake's `main` branch. Unstable.                                     | `ghcr.io/celsiusnarhwal/snowflake:edge`                                                |

</details>

<hr>

### Docker Compose

```yaml
services:
  snowflake:
    image: ghcr.io/celsiusnarhwal/snowflake
    container_name: snowflake
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - SNOWFLAKE_ALLOWED_HOSTS=snowflake.example.com
    volumes:
      - /some/directory/on/your/machine:/app/snowflake/data
```

### Docker CLI

```shell
docker run --name snowflake \
--restart unless-stopped \
-p "8000:8000" \
-e "SNOWFLAKE_ALLOWED_HOSTS=snowflake.example.com"
-v "/some/directory/on/your/machine:/app/snowflake/data" \
ghcr.io/celsiusnarhwal/snowflake
```

## Usage

First, [create an application in the Discord Developer Portal](https://discord.com/developers/applications). In your
application's OAuth2 settings, note your client ID and client secret, then set your redirect URIs.

Your redirect URIs must be in the form `https://snowflake.example.com/r/{YOUR_REDIRECT_URI}`,
where `{YOUR_REDIRECT_URI}` is the actual intended redirect URI for your application. For example, a redirect
URI of `https://myapp.example.com/callback` would be set in the Developer Portal
as `https://snowflake.example.com/r/https://myapp.example.com/callback`.

> [!TIP]
> If you're unable to control the redirect URI your OIDC client provides to Snowflake, setting
> the `SNOWFLAKE_FIX_REDIRECT_URIS` environment variable to `true` should help. See [Configuration](#configuration)
> for details.

From there, Snowflake works just like any other OIDC provider. Your app redirects to Snowflake for authorization
(which in turn redirects to Discord); upon succcessful authorization, Snowflake provides your app with an authorization
code, which your app returns to Snowflake in exchange for an access token and an ID token. The access token can be sent
to Snowflake's `/userinfo` endpoint to obtain the associated identity claims, or your application can decode the ID
token directly to obtain the same claims.

Frankly, if you're reading this then you should already know how this works.

### OIDC Endpoints

| **Endpoint**     | **Path**                            |
|------------------|-------------------------------------|
| Authorization    | `/authorize`                        |
| Token            | `/token`                            |
| User Info        | `/userinfo`                         |
| JSON Web Key Set | `/.well-known/jwks.json`            |
| OIDC Discovery   | `/.well-known/openid-configuration` |

### Supported Scopes

Snowflake supports the `openid`, `profile`, and `email` scopes. `openid` and `profile` are required; `email` may be
optionally included if you want email information.

### Supported Claims

Snowflake-issued access tokens have the following claims:

| **Claim** | **Description**                                                                                                                      |
|-----------|--------------------------------------------------------------------------------------------------------------------------------------|
| `iss`     | The issuer of the ID token (i.e., the URL where Snowflake is reachable).                                                             |
| `sub`     | The ID of the user's Discord account.                                                                                                |
| `aud`     | The client ID of your Discord application.                                                                                           |
| `iat`     | The [Unix time](https://en.wikipedia.org/wiki/Unix_time) at which the token was issued.                                              |
| `exp`     | The [Unix time](https://en.wikipedia.org/wiki/Unix_time) past which the token should be considered expired and thus no longer valid. |

Snowflake-issed ID tokens tokens have the same claims as Snowflake-issued access tokens as well as the following:

| **Claim**            | **Description**                                                                                                                                                          |
|----------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `preferred_username` | The username of the user's Discord account.                                                                                                                              |
| `name`               | The [display name](https://support.discord.com/hc/en-us/articles/12620128861463-New-Usernames-Display-Names#h_01GXPQABMYGEHGPRJJXJMPHF5C) of the user's Discord account. |
| `locale`             | The locale (i.e., chosen language setting) of the user's Discord account. See all possible locales [here](https://discord.com/developers/docs/reference#locales).        |
| `picture`            | The URL of the avatar of the user's Discord account.                                                                                                                     |

When the `email` scope is requested, ID tokens will also have the following claims:

| **Claim**        | **Description**                                                                   |
|------------------|-----------------------------------------------------------------------------------|
| `email`          | The email address associated with the user's Discord account.                     |
| `email_verified` | Whether the email address associated with the user's Discord account is verified. |

### PKCE Support

For applications that cannot securely store a client secret, Snowflake supports the
[PKCE-enhanced authorization code flow](https://auth0.com/docs/get-started/authentication-and-authorization-flow/authorization-code-flow-with-pkce).
Make sure the `Public Client` option is enabled in your Discord application's OAuth2 settings.

## HTTPS and Reverse Proxies

As mentioned at the top of the README, Snowflake must be served over HTTPS. If you're serving Snowflake behind a reverse
proxy and connecting to the reverse proxy over HTTPS, you will almost certainly need to configure
[Uvicorn](https://uvicorn.org) — which Snowflake uses under the hood — to trust the IP of your reverse proxy.
You can do this by setting the `UVICORN_FORWARDED_ALLOW_IPS` environment variable to either:

- The IPv4 or IPv6 address of your reverse proxy as seen by Snowflake (e.g., `172.17.0.2` or `fd12:3456:789a::2`)
- An IPv4 or IPv6 network containing the IP address of your reverse proxy as seen by Snowflake
  (e.g., `172.17.0.0/16`, `fd12:3456:789a::/64`)

You can also set it to `*` to trust all IP addresses, but this is generally not recommended.

For more information, see [Uvicorn's documentation](https://www.uvicorn.org/deployment/#proxies-and-forwarded-headers).

## Configuration

Snowflake is configurable through the following environment variables:

| **Environment Variable**         | **Type** | **Description**                                                                                                                                                                                                                                                                                                                                                                                             | **Required?** | **Default** |
|----------------------------------|----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------|-------------|
| `SNOWFLAKE_ALLOWED_HOSTS`        | String   | A comma-separated list of domain names at which Snowflake may be accessed. Wildcard domains (e.g., `*.example.com`) are supported. You can also set this to `*` to allow all domains, but this is not recommended.                                                                                                                                                                                          | Yes           | N/A         |
| `SNOWFLAKE_BASE_PATH`            | String   | The URL path at which Snowflake is being served. This may be useful if you're serving Snowflake behind a reverse proxy.                                                                                                                                                                                                                                                                                     | No            | `/`         |
| `SNOWFLAKE_FIX_REDIRECT_URIS`    | Boolean  | Whether to automatically correct redirect URIs to subpaths of Snowflake's `/r` endpoint as necessary. This may be useful for OIDC clients that don't allow you to set the redirect URI they use. The redirect URI's you set in the Discord Developer Portal must always be subpaths of `/r` regardless of this setting.                                                                                     | No            | `false`     ||          |                                                                                                                                                                                                                                                                                                                                    |               |              |
| `SNOWFLAKE_TOKEN_LIFETIME`       | String   | A [Go duration string](https://pkg.go.dev/time#ParseDuration) representing the amount of time after which Snowflake-issued tokens should expire. In addition to the standard Go units, you can also use `d` for day, `w` for week, `mm` for month, and `y` for year.[^1] Must resolve to a length of time greater than or equal to 60 seconds.                                                              | No            | `1h`        |
| `SNOWFLAKE_REDIS_URL`            | String   | A [Redis](https://redis.io/) connection string. Snowflake uses Redis to store important authorization data; if this variable is provided, Snowflake will use the Redis database it points to rather than its own internal one, allowing that data to persist across container restarts. Must begin with `redis://` or `rediss://`.                                                                          | No            | N/A         |
| `SNOWFLAKE_ROOT_REDIRECT`        | String   | Where Snowflake's root path should redirect to. Must be either `repo`, `web`, `app`, or `off`.<br/><br/>`repo` redirects to Snowflake's GitHub repository; `web` and `app` redirect to the user's Discord account settings on discord.com or in their platform's Discord app, respectively; `off` responds with an HTTP 404 error. Note that `app` only works if Discord is installed on the user's device. | No            | `repo`      |
| `SNOWFLAKE_REDIRECT_STATUS_CODE` | Integer  | The HTTP status code Snowflake will use when redirecting clients to authorize with Discord. Must be either `302` or `303`.                                                                                                                                                                                                                                                                                  | No            | `303`       |
| `SNOWFLAKE_ENABLE_SWAGGER`       | Boolean  | Whether to serve [Swagger UI](https://github.com/swagger-api/swagger-ui) documentation at `/docs`.                                                                                                                                                                                                                                                                                                          | No            | `false`     |

Additionally, Uvicorn will respect any of [its own environment variables](https://www.uvicorn.org/settings/)
if they are set.

[^1]: 1 day = 24 hours, 1 week = 7 days, 1 month = 30 days, and 1 year = 365 days.