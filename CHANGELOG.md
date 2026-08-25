# Changelog

All notable changes to `python-takserver-api`.

This project supersedes the deprecated `takserver-api-python` repository
(https://github.com/sgofferj/takserver-api-python). Development moved here on
2026-01-25; the old repository was formally marked DEPRECATED on 2026-07-13.

No tagged releases exist yet; sections are dated by commit. The current
development state is tracked under `[Unreleased]`.

## [Unreleased]

### Added

- Certificate Manager API (`CertManagerApi`, `server.certs`): complete
  wrapper for the `cert-manager-admin-api` tag - `get_certificates()`
  (with optional username filter), `get_active_certificates()`,
  `get_expired_certificates()`, `get_replaced_certificates()`,
  `get_revoked_certificates()`, `get_certificate()`,
  `download_certificate()` (returns PEM text),
  `delete_certificate()`, `delete_certificates()`,
  `revoke_certificates()`. The user-side `cert-manager-api` endpoints
  (`tls/config`, `makeClientKeyStore`, `signClient[/v2]`) are deliberately
  NOT wrapped: they answer HTTP 403 even for an admin certificate on the
  reference server, as does `cert/download/{ids}` (HTTP 500 with valid
  hashes). Live tests assert those failures so a fixing upgrade gets
  noticed. 12 unit tests; 10 live tests.
- Data Feed API (`DataFeedApi`, `server.datafeeds`): complete wrapper for
  the `data-feed-api` tag - `get_data_feeds()`,
  `get_data_feeds_in_bbox()`, `get_data_feeds_in_polygon()` (a GET-with-
  body endpoint; `ConnectionHelper.request()` now passes JSON bodies on
  GET), `create_predicate_data_feed()`, `update_predicate_data_feed()`,
  `delete_predicate_data_feed()`, `get_predicate_data_feed()`,
  `get_stats()`, `get_stats_for_feed()`, `get_existing_cot_types()`,
  `get_cots_by_cot_type()`. Plus the `build_predicate_feed()` helper that
  constructs a complete feed body (minimal bodies are rejected with HTTP
  500) and defaults `filter_groups` to `["__ANON__"]` to avoid the
  verified-live access lockout: a feed created with an empty filter-group
  list denies EVERYONE - including the admin - read, update and delete
  access. Shared ApiResponse unwrapping moved into
  `class_helpers.unwrap_api_response()`. 13 unit tests; live tests create,
  exercise, rename and delete their own predicate feed.
- Group API (`GroupApi`, `server.groups`): complete wrapper for the
  `groups-api` tag - `get_all_groups()`, `get_groups_for_user()`,
  `get_group()`, `set_active_groups()` (absolute semantics, optional
  `clientUid`), `set_active_groups_bits()`, `set_active_groups_force()`,
  `wait_for_group_update()`, `get_group_cache_enabled()`,
  `get_ldap_groups()`, `get_ldap_group_members()`. ApiResponse envelopes
  are unwrapped automatically. Helpers: `get_active_groups()`,
  `subscribe()` / `subscribe_many()`, `unsubscribe()` /
  `unsubscribe_many()`, `is_subscribed()`, `get_channels()`,
  `channel_exists()`, `wait_for_group_update_until()`. `Server` gained an
  optional `username=` argument (certificate CN) for APIs that address the
  authenticated user by name. Unit-tested (26 tests) and live-tested
  against tak.gofferje.net with a self-provisioned throwaway user/cert.
- Live integration tests in `live_tests/`, marked `live` and excluded from
  unit runs (`pytest live_tests/ -m live`, or `tox -e live`). They run only on
  the developer machine against the real TAK server and never in CI.
  Credentials come from the local, gitignored `test-secrets/` folder; without
  them the live tests skip automatically.
- CI workflow (`.github/workflows/ci.yml`): unit tests on AMD64 and ARM64,
  Python 3.11-3.13, plus the full pre-commit suite. Live tests are
  intentionally not part of CI.
- Secret hygiene: gitignore patterns for `*.pem`, `*.key`, `*.p12`, `*.pfx`,
  certificates, keystores and `test-secrets/`; pre-commit now also runs
  gitleaks, `detect-private-key`, and a hard block on sensitive file
  extensions (on top of the existing detect-secrets).
- `tests/openapispec.json` baseline: now pulled live from the test server's
  `/v3/api-docs` endpoint instead of docs.tak.gov.
- README section documenting the TAK server version the code is tested
  against (5.7-RELEASE-43-HEAD).
- Mission API completed: all name-based mission endpoints of the live spec
  are now wrapped in `MissionApi` (58 new methods), covering mission
  lifecycle (delete/copy/archive/send/expiration/parent), content keywords,
  external data, invitations, passwords, tokens, layers, map layers, feeds,
  mission logs, subscriptions (single, bulk, disconnect) and the global
  endpoints (count, names, paged list, all-invitations/logs/subscriptions,
  log entries). `get_mission` gained the optional filter parameters of the
  spec. `ConnectionHelper.request()` now accepts JSON list bodies and `data=`
  payloads on POST.
- Live mission CRUD test (`live_tests/test_live_mission.py`): creates and
  removes its own `live-test-<uuid>` mission; verified against the real
  server without leaving data behind.
- Convenience helpers `delete_content_keyword_by_hash()` and
  `delete_content_keyword_by_uid()`: remove a single keyword from a mission
  content item (by hash or UID) by reading the current keyword list,
  dropping the keyword and writing the reduced list back, since the TAK API
  only supports setting or clearing the whole list. Not found -> `404`,
  keyword already absent -> no-op `200` without a server write. Unit-tested
  (6 tests); live coverage deferred - the test server does not ingest
  mission content via CoT stream or package upload (see AGENTS.md).
- Home API completed: `get_home()` (`GET /Marti/api/home`) and
  `get_user_roles()` (`GET /Marti/api/util/user/roles`) wrap the remaining
  spec endpoints of the home-api tag next to the existing `is_admin()`.
  Convenience helpers `has_role()` (role membership check on top of
  `get_user_roles()`) and `server_version()` (version string from the
  working `GET /Marti/api/version` endpoint). The spec's `getVer`
  (`GET /Marti/api/ver`) is deliberately NOT wrapped: it returns HTTP 500
  on the reference server (5.7-RELEASE-43-HEAD); see Home-API wiki page.
  Unit-tested (8 new tests) and exercised by live tests (read-only).
- User Account Management API completed: all 10 operations of the
  `file-user-account-management-api` tag are now wrapped in
  `UserAccountManagementApi` - `get_users_in_group()`,
  `get_groups_for_user()`, `change_user_password()`, `delete_user()`,
  `create_file_users_in_bulk()` (bulk user generation, `[N]` placeholder in
  the username expression) and the membership update operations
  `update_users_for_group()` / `update_groups_for_user()`.
  `create_or_update_file_user()`, `create_file_users_in_bulk()` and the two
  update operations now always send all three group-list fields (empty
  arrays when not given) - the reference server replies with HTTP 500 when
  any of them is omitted. Unit-tested (10 new tests) and exercised by two
  live tests that create, update and delete their own `live-test-<uuid>`
  users and groups (groups are auto-created from user memberships and
  auto-deleted when no user has them).

### Fixed

- CI pipeline failed on `main`: the `no-commit-to-branch` pre-commit hook
  (which protects `main`/`master` from direct local commits) ran in CI and
  failed main's own runs. CI now skips it (`SKIP: no-commit-to-branch`) -
  the hook remains active locally.
- `test_add_mission_package_http_error`: mock asserted the pre-refactor
  base64-JSON payload contract; updated to the raw-ZIP-bytes contract.
- Removed unused `json` import in `tak_mission_api.py` (pylint W0611).

## 2026-07-25

### Fixed

- `add_mission_package`: strip certificate paths, send raw ZIP bytes as the
  payload, drop `Content-Type` on `create_mission`.

## 2026-07-15

### Added

- Mission package support: `build_mission_package()` and
  `add_mission_package()` (`commit 0f3b20b`).
- In-repo `wiki/` stub (2026-07-13, `commit 2011f4a`).

## 2026-02-08

### Changed

- Main class mixins refactored into sub-api classes: `Server.home`,
  `Server.mission`, `Server.user` accessors (`commit 831e98c`).

## 2026-01-25 - project start

### Added

- Initial cookiecutter scaffold: poetry/pyproject, tox, Dockerfiles,
  pre-commit configuration, test layout.
- First functionality (merged PR #1): `Server` class with certificate-based
  mutual TLS (`ConnectionHelper`), Home API (`is_admin`), file user account
  management (users/groups), and base Mission API coverage
  (`commits a1b1728, 548bbd6, 71d9dc0`).

### Deprecated

- Development moved from `takserver-api-python` to this repository; the old
  repository was formally marked DEPRECATED on 2026-07-13.
