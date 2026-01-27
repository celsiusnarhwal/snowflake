# Snowflake

Snowflake enables you to use [Discord](https://discord.com) as
an [OpenID Connect](https://auth0.com/docs/authenticate/protocols/openid-connect-protocol) (OIDC) provider. With it, you
can use Discord to identify your application's users without needing to implement specific support for Discord's OAuth2
API.

> [!important]
> Snowflake requires HTTPS for external connections. (By default, HTTP connections on `localhost` are fine; see
> [Configuration](#configuration).)

## Installation

[Docker](https://docs.docker.com/get-started) is the only supported way of running Snowflake. You will almost always 
want to set the `SNOWFLAKE_ALLOWED_HOSTS` environment variable; see [Configuration](#configuration).

> [!note]
> Throughout this README, `snowflake.example.com` will be used as a placeholder for the domain at which your
> Snowflake instace is reachable.

<hr>

<details>
<summary>Supported tags</summary>
<br>

| **Name**             | **Description**                                                                               | **Example**                                                                            |
|----------------------|-----------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| `latest`             | The latest stable version of Snowflake.                                                       | `ghcr.io/celsiusnarhwal/snowflake:latest`                                              |
| Major version number | The latest release of this major version of Snowflake. May be optionally prefixed with a `v`. | `ghcr.io/celsiusnarhwal/snowflake:1`<br/>`ghcr.io/celsiusnarhwal/snowflake:v1`         |
| Minor version number | The latest release of this minor version of Snowflake. May be optionally prefixed with a `v`. | `ghcr.io/celsiusnarhwal/snowflake:1.0`<br/>`ghcr.io/celsiusnarhwal/snowflake:v1.0`     |
| Exact version number | This version of Snowflake exactly. May be optionally prefixed with a `v`.                     | `ghcr.io/celsiusnarhwal/snowflake:1.0.0`<br/>`ghcr.io/celsiusnarhwal/snowflake:v1.0.0` |
| `edge`               | The latest commit to Snowflake's `main` branch. Unstable.                                     | `ghcr.io/celsiusnarhwal/snowflake:edge`                                                |

</details>

<hr>

### Docker Compose

```yaml
services:
  snowflake:
    image: ghcr.io/celsiusnarhwal/snowflake:latest
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
ghcr.io/celsiusnarhwal/snowflake:latest
```

## Usage

First, [create an application in the Discord Developer Portal](https://discord.com/developers/applications?new_application=true). 
In your application's OAuth2 settings, note your client ID and client secret, then set your redirect URIs.

Your redirect URIs must be in the form `https://snowflake.example.com/r/{YOUR_REDIRECT_URI}`,
where `{YOUR_REDIRECT_URI}` is the actual intended redirect URI for your application. For example, a redirect
URI of `https://myapp.example.com/callback` would be set in the Developer Portal
as `https://snowflake.example.com/r/https://myapp.example.com/callback`.

> [!tip]
> If you're unable to control the redirect URI your OIDC client provides to Snowflake, set
> the `SNOWFLAKE_FIX_REDIRECT_URIS` environment variable to `true`. See [Configuration](#configuration)
> for details.

From there, Snowflake works just like any other OIDC provider. Your app redirects to Snowflake for authorization;
upon succcessful authorization, Snowflake provides your app with an authorization code, which your app returns
to Snowflake in exchange for an access token and an ID token. The access token can be sent to Snowflake's
`/userinfo` endpoint to obtain the associated identity claims, or your application can decode the ID token
directly to obtain the same claims.

Frankly, if you're reading this then you should already know how this works.

## OIDC Information

### Endpoints

| **Endpoint**                    | **Path**                            |
|---------------------------------|-------------------------------------|
| Authorization                   | `/authorize`                        |
| Token                           | `/token`                            |
| User Info                       | `/userinfo`                         |
| JSON Web Key Set                | `/.well-known/jwks.json`            |
| OIDC Discovery                  | `/.well-known/openid-configuration` |
| [WebFinger](#webfinger-support) | `/.well-known/webfinger`            |

### Supported Scopes

| **Scope** | **Requests**                                                                                    | **Required?** |
|-----------|-------------------------------------------------------------------------------------------------|---------------|
| `openid`  | To authenticate using OpenID Connect.                                                           | Yes           |
| `profile` | Basic information about the user's Discord account.                                             | No            |
| `email`   | The email address associated with the user's Discord account and whether or not it is verified. | No            |
| `groups`  | A list of IDs of guilds (a.k.a. "servers") the user is a member of.                             | No            |

> [!warning]
> Scopes are persistent. Once a scope is granted, your app maintains perpetual access to it — even if it later stops
> asking for it — until the user manually revokes their authorization. Applications should be prepared to
> receive data from scopes they did not explicitly request at authorization.
>
> This is a technical limitation of Discord's OAuth2 API.

### Supported Claims

#### Tokens

Depending on the provided scopes, Snowflake-issued access and ID tokens include some subset of the following claims:

| **Claim**            | **Description**                                                                                                                                                          | **Required Scopes (in addition to `openid`)** |
|----------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------|
| `iss`                | The URL at which the client accessed Snowflake.                                                                                                                          | None                                          |
| `sub`                | The ID of the user's Discord account.                                                                                                                                    | None                                          |
| `aud`                | For access tokens, the URL of Snowflake's `/userinfo` endpoint; for ID tokens, the client ID of your Discord application.                                                | None                                          |
| `iat`                | The [Unix time](https://en.wikipedia.org/wiki/Unix_time) at which the token was issued.                                                                                  | None                                          |
| `exp`                | The [Unix time](https://en.wikipedia.org/wiki/Unix_time) past which the token should be considered expired and thus no longer valid.                                     | None                                          |
| `preferred_username` | The username of the user's Discord account.                                                                                                                              | `profile`                                     |
| `name`               | The [display name](https://support.discord.com/hc/en-us/articles/12620128861463-New-Usernames-Display-Names#h_01GXPQABMYGEHGPRJJXJMPHF5C) of the user's Discord account. | `profile`                                     |
| `nickname`           | Same as `name`.                                                                                                                                                          | `profile`                                     |
| `locale`             | The locale of the user's Discord account. See all possible locales [here](https://discord.com/developers/docs/reference#locales).                                        | `profile`                                     |
| `picture`            | The URL of the avatar of the user's Discord account.                                                                                                                     | `profile`                                     |
| `email`              | The email address associated with the user's Discord account.                                                                                                            | `email`                                       |
| `email_verified`     | Whether the email address associated with the user's Discord account is verified.                                                                                        | `email`                                       |
| `groups`             | A list of IDs of guilds the user is a member of.                                                                                                                         | `groups`                                      |
| `nonce`              | If the `nonce` parameter was sent to the authorization endpoint, this claim will contain its value. It only appears in ID tokens.                                        | None                                          |


#### User Info

The `/userinfo` endpoint returns the same claims as access tokens but does not include `iss`, `aud`,
`iat`, or `exp`.

#### Refresh Tokens

Successful responses from Snowflake's token endpoint also include a refresh token. After the access and ID tokens 
expire, the refresh token can be sent to the token endpoint to obtain a new set of access, ID, and refresh tokens 
without having to make the user reauthorize.

See [OpenID Connect Core 1.0 § 12](https://openid.net/specs/openid-connect-core-1_0.html#RefreshTokens) 
for additional details.

> [!caution]
> **Public clients must keep their refresh tokens secure!** If an attacker steals a public client's refresh token,
> Discord doesn't provide any means to keep the attacker from using it and obtaining new access and ID tokens
> indefinitely.
> 
> Public clients may opt out of recieving refresh tokens by sending `include_refresh_token=false` to the `/token`
> endpoint.

### PKCE Support

For applications that cannot securely store a client secret, Snowflake supports the
[PKCE-enhanced authorization code flow](https://datatracker.ietf.org/doc/html/rfc7636).
Make sure the `Public Client` option is enabled in your Discord application's OAuth2 settings.

### WebFinger Support

Snowflake provides a [WebFinger](https://en.wikipedia.org/wiki/WebFinger) endpoint at `/.well-known/webfinger`
to enable the discovery of Snowflake as the OIDC provider for email addresses at domains permitted by the
`SNOWFLAKE_ALLOWED_WEBFINGER_HOSTS` environment variable (see [Configuration](#configuration)). The endpoint
only supports `acct:` URIs containing email addresses and does not support any link relations other than OpenID Connnect.

The endpoint will return an HTTP 404 error for email addresses at non-whitelisted domains.

## HTTPS and Reverse Proxies

As previously mentioned, Snowflake requires HTTPS for external connections. If you're serving Snowflake
behind a reverse proxy and connecting to the reverse proxy over HTTPS, you will likely need to configure
[Uvicorn](https://www.uvicorn.org) — which Snowflake uses under the hood — to trust the IP address
of your reverse proxy.

You can do this by setting the `UVICORN_FORWARDED_ALLOW_IPS` environment variable to a comma-separated list of IP
addresses or networks, at least one of which must match the IP of your reverse proxy. You can also set it to `*` to
trust all IP addresses, but this is generally not recommended.

For more information, see [Uvicorn's documentation](https://www.uvicorn.org/deployment/#proxies-and-forwarded-headers).

## Custom Private Keys

> [!note]
> This is an advanced feature most users won't need.

By default, Snowflake signs its JWTs with a private key that it generates and writes to `/app/snowflake/data`,
which you are instructed to mount on your host machine (see [Installation](#installation)). As an alternative to this,
Snowflake allows you to provide your own private key via the `SNOWFLAKE_PRIVATE_KEY` environment variable. This may
be useful, for example, in environments where mounting `/app/snowflake/data` isn't possible, or if you'd just prefer
to keep the private key in an environment variable rather than have it persisted to a file.

The value of `SNOWFLAKE_PRIVATE_KEY` must be an RS256 JSON Web Key. You can generate one by using
[mkjwk](https://mkjwk.org/?kty=rsa&size=2048&use=sig&alg=RS256) (using that link will prefill the configuration
options; you only need to click `Generate`) and then clicking `Copy to Clipboard` underneath 
`Public and Private Keypair`.

<details>
<summary>The result should look similar to this (click to expand):</summary>

```json5
// For demonstration purposes only, do not actually use this private key. Obviously.
{
    "p": "4AGfVeTcxkgbvqf0WP5c270L-p_WQyNwMmtn4pXPazhmfwVPW6j3f2n2_Ober4xObaD5KOJIR3ah3Wu9LCoYp2HNdxsddyBXYh7nZhYP21uq1MphX9jvw1l422qAEbPraISKfkPv71sJxnXMG1cm7SaUtkj4P6Lg7bTv8PxapQ0",
    "kty": "RSA",
    "q": "2ues113yqdjCdx9O_1piyYeWQhYbM-VZy_TTKmc3JqARj68wx8lUoggr_ybcN5dJ8JKPKh93SN5TnqbmscqYllEaXtSQPw6aDq5OkF5Z5M7J-kDtfVcHU-Z02NFa40ViU25seIDmejbJi442ox2yChTd9gbp_0Rfkhv9EuWdnaU",
    "d": "GMJcHduhQEp1EYSU7MGuA6RWUHFYWhuwxPorrY09E5PrAPmPJxFmrPls_2hSfJSSJ-TnnKKcHQpcNFt7BiZ6Th2D_qH5DH9FUKSRkl6kvb9gEI5bNDF_1lYZxnivG94OEtkqprVXURMaza5Hbz57Gl0iBpV28BmnZAg6Llb7AUUNONmZgtzhPYpwH9JxJOHCzQHbc4u9ZF1XfbW-iINHenJW34pN8jdWPlv_DYKt9SDd9qPQq4eCGkOU9uQFL4KeoPlGaDXA_7ps4i62klEtb-rdQFQD-gg8-nc2trMt9oMmqVl0XFdG4KN9_N4Qid4HgiaiMwjNsdkNKk2e8aZWvQ",
    "e": "AQAB",
    "use": "sig",
    "qi": "2vWPtbeCUETj7ZgqrOxUqtO_yD5I86tY_zoMK_woQ389VLg--fwXcY9amWo1FViHm1KmuA0nqxc0Sdbl5N1ibxZPqYglX_YnGH5AQ9HTOCmrPeAOTCOdUtUgBD0biG2y63VfiGKnrJz1QGVLIkEFub6V0JraUNDxE7nUJlxb3Lk",
    "dp": "YLISl79dVfJWl6xkm-3hI7GtdBh_IygvDHS0uWi1yrDj_bzLDuQXQlb5mR4Hznugd05ff7h-PusE4FHbrS7WyZo8WUfJJl09m0t_099-JNCjI4vhEMDSbt82fnCwq_OgkNN1_R9SeV4xEAxVeQ_b688VrsI89ytWMQZD9SDZ-Bk",
    "alg": "RS256",
    "dq": "JmN8jyQ9mwWVTNijvOo36smpUxuXV6l_7uGXapdBN7fYfI8nidHH0saGGK_S7LjOUa8SBjwQain7FhaE3GcADVRZwImcZkKER9DPnEe_kf2ltApQ26s4cME4epF0U-jmDmWOBi_su0ACZkPhVwetIlF4f13FCWwPKotX_UlhM7U",
    "n": "v4waY3YE-AFuYoVy_T7fgC48LRujLaQNaFb-GGZnZEbiFi7rkVJF_EVajmu3Ksz1TwTrIHhrJijKAuBg_p4UKNJVZATqjPCilIrOajbWWJ-OISYXqeUHmlaoqML3Qq1x8ti05G6DyUjZTfZRabqrx7UggB3nOL-Eog69FnNf7tf1XmEIKEvwfB9NFAQWG2Jiksts8jzU2PVDnmR5cpsAeOK2hwZnp0BKcezAnILGrVbt_NPvp4J2ldD6eV8_YMZ9YenZaTw6LuVAE0k4buPv7mNoP-QhDhhg2UrmY3xElhhk0VNxbNV7b0AAm07bfuPfEb-y8V0amzYLKb48F55aYQ"
}
```

</details>

If `SNOWFLAKE_PRIVATE_KEY` is set, there's no need to mount `/app/snowflake/data`. On startup, Snowflake
will log a message affirming that a custom private key is in use.

## Configuration

Snowflake is configurable through the following environment variables (all optional):

| **Environment Variable**             | **Type** | **Description**                                                                                                                                                                                                                                                                                                                                                                                       | **Default**               |
|--------------------------------------|----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------|
| `SNOWFLAKE_ALLOWED_HOSTS`            | String   | A comma-separated list of hostnames at which Snowflake may be accessed. Wildcard domains (e.g., `*.example.com`) and IP addresses are supported. You can also set this to `*` to allow all hostnames, but this is not recommended.<br/><br/>Loopback addresses (e.g., `localhost`) are always included.                                                                                               | `localhost,127.0.0.1,::1` |
| `SNOWFLAKE_ALLOWED_CLIENTS`          | String   | A comma-separated list of Discord application client IDs. Snowflake will only fulfill authorization requests for client IDs in this list.<br/><br/>This can be set to `*` to allow all client IDs.                                                                                                                                                                                                    | `*`                       |
| `SNOWFLAKE_BASE_PATH`                | String   | The URL path at which Snowflake is being served. This may be useful if you're serving Snowflake behind a reverse proxy.                                                                                                                                                                                                                                                                               | `/`                       |
| `SNOWFLAKE_FIX_REDIRECT_URIS`        | Boolean  | Whether to automatically correct redirect URIs to subpaths of Snowflake's `/r` endpoint as necessary. This may be useful for OIDC clients that don't allow you to set the redirect URI they use.<br/><br/>The redirect URIs you set in the Discord Developer Portal must always be subpaths of `/r` regardless of this setting.                                                                       | `false`                   |                                                                                                                                                                                                                                                                                                                                   |               |              |
| `SNOWFLAKE_TOKEN_LIFETIME`           | String   | A [Go duration string](https://pkg.go.dev/time#ParseDuration) representing the amount of time after which Snowflake-issued tokens should expire. In addition to the standard Go units, you can use `d` for day, `w` for week, `mm` for month, and `y` for year.[^1]<br/><br/>Must be greater than or equal to 60 seconds.                                                                             | `1h`                      |
| `SNOWFLAKE_ROOT_REDIRECT`            | String   | Where Snowflake's root path redirects to. Must be `repo`, `settings`, `docs`, or `off`.<br/><br/>`repo` redirects to Snowflake's GitHub repository; `settings` redirects to the user's Discord account settings; `docs` redirects to Snowflake's interactive API documentation; `off` responds with an HTTP 404 error.<br/><br/>Setting this to `docs` will force `SNOWFLAKE_ENABLE_DOCS` to be true. | `repo`                    |
| `SNOWFLAKE_TREAT_LOOPBACK_AS_SECURE` | Boolean  | Whether Snowflake will consider loopback addresses (e.g., `localhost`) to be secure even if they don't use HTTPS.                                                                                                                                                                                                                                                                                     | `true`                    |
| `SNOWFLAKE_RETURN_TO_REFERRER`       | Boolean  | If this is `true` and the user denies an authorization request, Snowflake will redirect the user back to the initiating URL.[^3] Otherwise, Snowflake behaves according to [OpenID Connect Core 1.0 § 3.1.2.6](https://openid.net/specs/openid-connect-core-1_0.html#AuthError).                                                                                                                      | `false`                   |
| `SNOWFLAKE_ALLOWED_WEBFINGER_HOSTS`  | String   | A comma-separated lists of domains allowed in `acct:` URIs sent to Snowflake's WebFinger endpoint. The endpoint will return an HTTP 404 error for URIs with domains not permitted by this setting.<br/><br/> Wildcard domains (e.g., `*.example.com`) are supported, but the unqualified wildcard (`*`) is not.                                                                                       | N/A                       |
| `SNOWFLAKE_PRIVATE_KEY`              | String   | A private RS256 JSON Web Key. If provided, Snowflake will use it instead of generating its own. See [Custom Private Keys](#custom-private-keys).                                                                                                                                                                                                                                                      |                           |
| `SNOWFLAKE_ENABLE_DOCS`              | Boolean  | Whether to serve Snowflake's interactive API documentation at `/docs`. This also controls whether Snowflake's [OpenAPI](https://spec.openapis.org/oas/latest.html) schema is served at `/openapi.json`.<br/><br/>This is forced to be `true` if `SNOWFLAKE_ROOT_REDIRECT` is set to `docs`.                                                                                                           | `false`                   |

<br>

Uvicorn will respect most[^2] of [its own environment variables](https://www.uvicorn.org/settings/) if they are set, but `UVICORN_FORWARDED_ALLOW_IPS` is the only one supported by Snowflake. Please don't open an issue if you set any of the others and something breaks.

[^1]: 1 day = 24 hours, 1 week = 7 days, 1 month = 30 days, and 1 year = 365 days.

[^2]: With the exceptions of `UVICORN_HOST` and `UVICORN_PORT`.

[^3]: Specifically, if the 
[`Referer` header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Referer) was sent to the 
authorization endpoint and the callback endpoint recieves an `error` parameter with a value of `access_denied`, 
Snowflake will redirect to the URL that was given by `Referer` at the authorization endpoint.