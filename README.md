# Snowflake

Snowflake enables you to use [Discord](https://discord.com) as
an [OpenID Connect](https://auth0.com/docs/authenticate/protocols/openid-connect-protocol) (OIDC) provider. With it, you
can use Discord to identify your application's users without needing to implement specific support for Discord's OAuth2
API.

> [!IMPORTANT]
> Snowflake must be served over HTTPS.

## Installation

[Docker](https://docs.docker.com) is the only supported way of running Snowflake.

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
    volumes:
      - { SOME_DIRECTORY_ON_YOUR_MACHINE }:/app/snowflake/data
```

### Docker CLI

```shell
docker run --name snowflake \
--restart unless-stopped \
-p "8000:8000" \
-v "{SOME_DIRECTORY_ON_YOUR_MACHINE}:/app/snowflake/data" \
ghcr.io/celsiusnarhwal/snowflake
```

## Usage

First, [create an application in the Discord Developer Portal](https://discord.com/developers/applications). In your
application's OAuth2 settings, note your client ID and client secret and set appropriate redirect URIs.

From there, Snowflake works just like any other OIDC provider. Your app redirects to Snowflake for authorization
(which in turn redirects to Discord); Discord provides your app with an authorization code, which your app
sends to Snowflake in exchange for an OIDC ID token. Frankly, if you're reading this then you should
already know how this works.

### OIDC Routes

| **Route**        | **Path**                            |
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

Snowflake's ID tokens have the following claims:

| **Claim**            | **Description**                                                                                                                                                          |
|----------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `iss`                | The issuer of the ID token (i.e., [`SNOWFLAKE_PUBLIC_URL`](#configuration)).                                                                                             |
| `sub`                | The ID of the user's Discord account.                                                                                                                                    |
| `aud`                | The client ID of your Discord application.                                                                                                                               |
| `iat`                | The [Unix time](https://en.wikipedia.org/wiki/Unix_time) at which the token was issued.                                                                                  |
| `exp`                | The [Unix time](https://en.wikipedia.org/wiki/Unix_time) past which the token should be considered expired and thus no longer valid.                                     |
| `preferred_username` | The username of the user's Discord account.                                                                                                                              |
| `name`               | The [display name](https://support.discord.com/hc/en-us/articles/12620128861463-New-Usernames-Display-Names#h_01GXPQABMYGEHGPRJJXJMPHF5C) of the user's Discord account. |
| `locale`             | The locale (i.e., chosen language setting) of the user's Discord account. See all possible locales [here](https://discord.com/developers/docs/reference#locales).        |
| `picture`            | The URL of the avatar of the user's Discord account.                                                                                                                     |

If the `email` scope is requested, the ID token will also have the following claims:

| **Claim**        | **Description**                                                                   |
|------------------|-----------------------------------------------------------------------------------|
| `email`          | The email address associated with the user's Discord account.                     |
| `email_verified` | Whether the email address associated with the user's Discord account is verified. |

### PKCE Support

For applications that cannot securely store a client secret, Snowflake supports the
[PKCE-enhanced authorization code flow](https://auth0.com/docs/get-started/authentication-and-authorization-flow/authorization-code-flow-with-pkce).
Make sure the `Public Client` option is enabled in your Discord application's OAuth2 settings.

## Configuration

Snowflake is configurable through the following environment variables (all optional):

| **Environment Variable**         | **Description**                                                                                                                                                                                                                                                                                                                                                  |
|----------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `SNOWFLAKE_TOKEN_LIFETIME`       | A [Go duration string](https://pkg.go.dev/time#ParseDuration) representing the amount of time after which ID tokens should expire. In addition to the standard Go units, you can also use `d` for day, `w` for week, `mm` for month, and `y` for year.[^1]<br/><br/>This must resolve to a length of time greater than or equal to 60 seconds. Defaults to `1h`. |
| `SNOWFLAKE_REDIRECT_STATUS_CODE` | The HTTP status code Snowflake will use when redirecting clients to authorize with Discord. Must be either `302` or `303`. Defaults to `303`.                                                                                                                                                                                                                    |

Additionally, [Uvicorn](https://www.uvicorn.org/) will respect any
of [its own environment variables](https://www.uvicorn.org/settings/) if they are set.

[^1]: 1 day = 24 hours, 1 week = 7 days, 1 month = 30 days, and 1 year = 365 days.