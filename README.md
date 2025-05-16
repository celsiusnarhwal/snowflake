# Snowflake

Snowflake enables you to use [Discord](https://discord.com) as
an [OpenID Connect](https://auth0.com/docs/authenticate/protocols/openid-connect-protocol) (OIDC) provider. With it, you
can use Discord to identify your application's users without needing to implement specific support for Discord's OAuth2 
API.

As far as I know, Snowflake is the only self-hostable, universally compatible, application that does this. 

## Installation

There are two supported ways to run Snowflake: [Docker](https://docker.com) and [uv](https://docs.astral.sh/uv).
(See also: [Configuration](#configuration)).

### Docker

Docker is the preferred way to run Snowflake. You can tailor the following Docker Compose configuration or
`docker run` command to your needs:

#### Docker Compose

```yaml
services:
  snowflake:
    image: ghcr.io/celsiusnarhwal/snowflake
    container_name: snowflake
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - SNOWFLAKE_PUBLIC_URL=https://{YOUR_SNOWFLAKE_INSTACE_URL}
    volumes:
      - {SOME_DIRECTORY_ON_YOUR_MACHINE}:/app/snowflake/data
```

#### Docker CLI

```shell
docker run --name snowflake \
--restart unless-stopped \
-p "8000:8000" \
-e "SNOWFLAKE_PUBLIC_URL=https://{YOUR_SNOWFLAKE_INSTANCE_URL}" \
-v "{SOME_DIRECTORY_ON_YOUR_MACHINE}:/app/snowflake/data" \
ghcr.io/celsiusnarhwal/snowflake
```

### uv

Snowflake can be installed via [uv](https://docs.astral.sh/uv).

```shell
uv tool install https://github.com/celsiusnarhwal/snowflake@latest
export SNOWFLAKE_PUBLIC_URL=https://{YOUR_SNOWFLAKE_INSTACE_URL}
snowflake
```

When running Snowflake this way, a `.env` file in the current working directory may be used in lieu
of setting environment variables in the shell.

## Usage

First, [Create an application in the Discord Developer Portal](https://discord.com/developers/applications). In your
application's OAuth2 settings, note your client ID and client secret and set appropriate redirect URIs.

From there, Snowflake works just like any other OIDC provider. You provide the client ID, client secret,
redirect URI, and scopes; clients will be redirected to Discord for authorization; Discord will provide you
an authorization code, which you will send to Snowflake in exchange for an OIDC ID token. Frankly, if you're reading
this then you should already know how this works.

### OIDC Routes

| **Route**        | **Path**                            |
|------------------|-------------------------------------|
| Authorization    | `/authorize`                        |
| Token            | `/token`                            |
| User Info        | `/userinfo`                         |
| JSON Web Key Set | `/.well-known/jwks`                 |
| OIDC Discovery   | `/.well-known/openid-configuration` |

### Scopes

Snowflake supports the `openid`, `profile`, and `email` scopes. `openid` and `profile` are required; `email` may be
optionally included if you want email information.

### Claims

Snowflake's ID tokens have the following claims:

| **Claim**            | **Description**                                                                                                                                                          |
|----------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `iss`                | The issuer of the ID token (i.e., [`SNOWFLAKE_PUBLIC_URL`](#configuration)).                                                                                             |
| `sub`                | The ID of the user's Discord account.                                                                                                                                    |
| `aud`                | The client ID of your Discord application.                                                                                                                               |
| `iat`                | The [Unix time](https://en.wikipedia.org/wiki/Unix_time) at which the token was issued.                                                                                  |
| `exp`                | The [Unix time](https://en.wikipedia.org/wiki/Unix_time) past which the token should be considered expired and no longer valid.                                          |
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

Snowflake is configurable through the following environment variables:

| **Environment Variable**         | **Description**                                                                                                                                                                                                                                                                                                                                           | **Required?** |
|----------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------|
| `SNOWFLAKE_PUBLIC_URL`           | The externally-accessible HTTPS URL where Snowflake is reachable.                                                                                                                                                                                                                                                                                         | Yes           |
| `SNOWFLAKE_TOKEN_LIFETIME`       | A [Go duration string](https://pkg.go.dev/time#ParseDuration) representing the amount of time after which ID tokens should expire. In addition to the standard Go units, you can also use `d` for day, `w` for week, `mm` for month, and `y` for year.[^1]<br/><br/>This must resolve to something greater than or equal to 60 seconds. Defaults to `1h`. | No            |
| `SNOWFLAKE_REDIRECT_STATUS_CODE` | The HTTP status code Snowflake will use when redirecting clients to authorize with Discord. Must be either `302` or `303`. Defaults to `303`.                                                                                                                                                                                                             |               |

Additionally, [Uvicorn](https://www.uvicorn.org/) will respect any
of [its own environment variables](https://www.uvicorn.org/settings/) if they are set.

[^1]: 1 day = 24 hours, 1 week = 7 days, 1 month = 30 days, and 1 year = 365 days.