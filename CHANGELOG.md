# Changelog[^1]

Notable changes to Snowflake are documented here.

Snowflake adheres to [semantic versioning](https://semver.org/spec/v2.0.0.html).

## <a name="2-0-0">2.0.0 — Unreleased</a>

> [!IMPORTANT]
> This version of Snowflake has not yet been released. This is preview of changes to come.

### 🚨 Breaking Changes

- The value of the `sub` claim is now a string. It was previously an integer.
- The value of the `groups` claim is now an array of strings. It was previously an array of integers.
- The `/token` endpoint now returns an HTTP 400 error if you try to supply the client ID and secret via both
form fields and HTTP Basic authentication at the same time (though you shouldn't have been doing that anyway).
- The `/token` endpont now returns an HTTP 400 error if no client ID is supplied.
- The `resource` parameter of the `WebFinger` endpoint now only accepts URIs in the form `acct:<email>`, where
`<email>` is a valid (though not necessarily deliverable) email address. Email addresses must end in a hostname
permitted by the new `SNOWFLAKE_ALLOWED_WEBFINGER_HOSTS` environment variable (more on that later). The endpoint will
return an HTTP 404 error for emails with non-whitelisted hostnames.
- The `/ping` endpoint has been renamed to `/health`.
- The `SNOWFLAKE_ENABLE_SWAGGER` setting is now `SNOWFLAKE_ENABLE_DOCS`. It's still `false` by default.

### Added

- The new `SNOWFLAKE_ALLOWED_WEBFINGER_HOSTS` environment variable controls what hostsnames URIs sent to the WebFinger
endpoint may end in. Wildcard domains (e.g., `*.example.com`) are supported, but the unqualified wildcard (`*`) is not.
- The OIDC discovery endpoint now includes the [`token_endpoint_auth_methods_supported`](https://openid.net/specs/openid-connect-discovery-1_0.html#:~:text=token_endpoint_auth_methods_supported)
key in its response.

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
