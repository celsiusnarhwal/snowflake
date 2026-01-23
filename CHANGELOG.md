# Changelog[^1]

Notable changes to Snowflake are documented here.

Snowflake adheres to [semantic versioning](https://semver.org/spec/v2.0.0.html).

## <a name="2-2-0">2.2.0 — 2026-01-23</a>

### Added

- This version of Snowflake adds two new settings:
  - `SNOWFLAKE_TREAT_LOOPBACK_AS_SECURE`: Controls whether Snowflake should consider loopback addresses 
  (e.g., `localhost`) to be secure even if they don't use HTTPS.
  - `SNOWFLAKE_RETURN_TO_REFERRER`: Controls whether Snowflake should return to the initating URL when authorization
  requests are denied.


## <a name="2-1-0">2.1.0 — 2026-01-22</a>

### Added

- The `/userinfo` endpoint now supports POST requests.

## <a name="2-0-6">2.0.6 — 2026-01-21</a>

### Fixed

- Fixed an issue that allowed the `/userinfo` endpoint to decode ID tokens.

## <a name="2-0-4">2.0.4 — 2026-01-20</a>

### Fixed

- Fixed a vulnerability that allowed for improper manipulation of the redirect URI sent to the `/callback` endpoint.

## <a name="2-0-3">2.0.3 — 2026-01-20</a>

### Fixed

- Fixed a bug that caused the healthcheck in Snowflake's Docker image to erroneously fail.

## <a name="2-0-0">2.0.0 — 2026-01-20</a>

### 🚨 Breaking Changes

- The `/token` endpoint now returns an HTTP 400 error if you try to supply the client ID and secret via both
form fields and HTTP Basic authentication at the same time (though you shouldn't have been doing that anyway).
- The `/token` endpont now returns an HTTP 400 error if no client ID is supplied.
- The `resource` parameter of the WebFinger endpoint now only accepts URIs in the form `acct:<email>`, where
`<email>` is a valid (though not necessarily deliverable) email address. Email addresses must end in a hostname
permitted by the new `SNOWFLAKE_ALLOWED_WEBFINGER_HOSTS` environment variable (more on that later). The endpoint will
return an HTTP 404 error for emails with non-whitelisted hostnames.
- The `/ping` endpoint has been renamed to `/health` and now returns an empty response.
- The `SNOWFLAKE_ENABLE_SWAGGER` setting is now `SNOWFLAKE_ENABLE_DOCS`.

### Added

- The new `SNOWFLAKE_ALLOWED_WEBFINGER_HOSTS` environment variable controls what hostsnames URIs sent to the WebFinger
endpoint may end in. Wildcard domains (e.g., `*.example.com`) are supported, but the unqualified wildcard (`*`) is not.
- `SNOWFLAKE_ROOT_REDIRECT` can now be set to `docs` to cause Snowflake's root path to redirect to its interactive API
documentation. Doing so will force `SNOWFLAKE_ENABLE_DOCS` to be `true`.
- The OIDC discovery endpoint now includes the [`token_endpoint_auth_methods_supported`](https://openid.net/specs/openid-connect-discovery-1_0.html#:~:text=token_endpoint_auth_methods_supported)
key in its response.
- Snowflake's Dockerfile now includes an `EXPOSE` directive indicating that Snowflake listens on port 8000.
- The WebFinger endpoint now supports a `rel` parameter, though the response's `links` array will be empty if it's
anything other than `http://openid.net/specs/connect/1.0/issuer`.

### Changed

- Snowflake's interactive API documentation is now built with [Scalar](https://scalar.com) instead of Swagger UI.

## <a name="1-4-0">1.4.0 — 2025-07-20</a>

### Added

- Snowflake now has a [WebFinger](https://en.wikipedia.org/wiki/WebFinger) endpoint at `/.well-known/webfinger`.

## <a name="1-3-0">1.3.0 — 2025-05-29</a>

### Added

- The new `SNOWFLAKE_ALLOWED_CLIENTS` setting allows you to restrict the client IDs for which Snowflake will fulfill
  authorization requests.

## <a name="1-2-1">1.2.1 — 2025-05-28</a>

### Fixed

- Snowflake will no longer incorrectly warn about `SNOWFLAKE_ALLOWED_HOSTS` being set to `*` when one of the
  the allowed hosts is a wildcard domain.

## <a name="1-2-0">1.2.0 — 2025-05-27</a>

### Changed

- Snowflake's authorization endpoint no longer requires a `state` parameter. This change was made because Discord's
  OAuth2 flow also does not require a `state` parameter.

## <a name="1-1-0">1.1.0 — 2025-05-27</a>

### Added

- Snowflake's Docker image now contains a healthcheck.

### Changed

- `SNOWFLAKE_ALLOWED_HOSTS` now always includes loopback addresses (`localhost`, `127.0.0.1`, `::1`) and is thus
  no longer strictly required, though you will still need to set it if you wish to connect to Snowflake externally.

## <a name="1-0-0">1.0.0 — 2025-05-26</a>

This is the initial release of Snowflake.

[^1]: Format based on [Keep a Changelog](https://keepachangelog.com).
