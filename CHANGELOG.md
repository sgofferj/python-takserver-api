# Changelog

All notable changes to `python-takserver-api`.

This project supersedes the deprecated `takserver-api-python` repository
(https://github.com/sgofferj/takserver-api-python). Development moved here on
2026-01-25; the old repository was formally marked DEPRECATED on 2026-07-13.

No tagged releases exist yet; sections are dated by commit. The current
development state is tracked under `[Unreleased]`.

## [Unreleased]

### Added

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

### Fixed

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
