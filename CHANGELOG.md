# Changelog[^1]

Notable changes to Snowflake will be documented here. Breaking changes are marked with a 🚩.


Snowflake adheres to [semantic versioning](https://semver.org/spec/v2.0.0.html).

## <a name="1-2-0">1.2.1 — 2025-05-28</a>

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
