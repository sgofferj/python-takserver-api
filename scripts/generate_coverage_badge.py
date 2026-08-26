#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# generate_coverage_badge.py from https://github.com/sgofferj/python-takserver-api
#
# Copyright Stefan Gofferje
#
# Licensed under the Gnu General Public License Version 3 or higher (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.gnu.org/licenses/gpl-3.0.en.html
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either expressed or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Generate the API-coverage badge for the README.

Counts the OpenAPI operations of the target tags in ``tests/openapispec.json``
and determines how many of them are wrapped by the classes in
``src/python_takserver_api`` by pairing each ``path = ...`` assignment with the
HTTP verb of the next ``connection.request()`` call. Writes a shields.io
*endpoint* JSON to ``docs/badges/api_coverage.json`` which the README renders:

    .. image:: https://img.shields.io/endpoint?url=<raw-url-to-json>

Run from the repository root::

    python scripts/generate_coverage_badge.py
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = REPO_ROOT / "tests" / "openapispec.json"
SRC_DIR = REPO_ROOT / "src" / "python_takserver_api"
OUT_PATH = REPO_ROOT / "docs" / "badges" / "api_coverage.json"

TARGET_TAGS = [
    "home-api",
    "file-user-account-management-api",
    "groups-api",
    "data-feed-api",
    "submission-api",
    "subscription-api",
    "cert-manager-api",
    "cert-manager-admin-api",
    "mission-api",
]

VERBS = ("get", "post", "put", "delete", "patch")

GUID_PATH_RE = re.compile(r"^/Marti/api/missions/guid/(.+)$")

EXPLICIT_ALIASES: dict[tuple[str, str], list[str]] = {
    ("POST", "/Marti/api/missions/{}"): ["/Marti/api/missions"],
    ("PUT", "/Marti/api/inputs/storeForwardChat/enable"): ["/Marti/api/inputs/storeForwardChat/{}"],
    ("PUT", "/Marti/api/inputs/storeForwardChat/disable"): ["/Marti/api/inputs/storeForwardChat/{}"],
}


def equivalent_paths(verb: str, norm_path: str) -> list[str]:
    """Return normalized wrapper paths known to hit the same server operation.

    - The spec exposes mission endpoints twice (``/missions/{name}`` and
      ``/missions/guid/{guid}``); the wrappers implement the guid variants
      via query parameters on the name-based paths.
    - ``storeForwardChat/enable|disable`` are wrapped through one dynamic
      path-segment call.
    """
    aliases = list(EXPLICIT_ALIASES.get((verb, norm_path), []))
    match = GUID_PATH_RE.match(norm_path)
    if match:
        aliases.append(f"/Marti/api/missions/{match.group(1)}")
    return aliases


PATH_RE = re.compile(r"""path\s*=\s*f?["']([^"']+)["']""")
REQUEST_RE = re.compile(r"""\.request\(\s*["'](get|post|put|delete|patch)["']""")


def strip_query(path: str) -> str:
    """Remove any query string from a URL path."""
    return re.sub(r"\?.*$", "", path)


def normalize(path: str) -> str:
    """Collapse query strings and {placeholder} segments for comparison."""
    return re.sub(r"\{[^{}]*\}", "{}", strip_query(path))


def spec_operations(spec: dict[str, Any]) -> dict[str, set[tuple[str, str]]]:
    """Map normalized path -> {(VERB, tag), ...}."""
    ops: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for raw_path, item in spec["paths"].items():
        for method, op in item.items():
            if method in VERBS:
                tag = op.get("tags", ["untagged"])[0]
                ops[normalize(raw_path)].add((method.upper(), tag))
    return ops


def wrapped_operations() -> set[tuple[str, str]]:
    """Extract (VERB, normalized-path) pairs actually wrapped in the source."""
    wrapped: set[tuple[str, str]] = set()
    for srcfile in sorted(SRC_DIR.glob("tak_*.py")):
        text = srcfile.read_text()
        pending_path: str | None = None
        for match in PATH_RE.finditer(text):
            pending_path = match.group(1)
            req = REQUEST_RE.search(text, match.end())
            if req is None:
                continue
            next_path = PATH_RE.search(text, match.end())
            if next_path is not None and next_path.start() < req.start():
                continue
            wrapped.add((req.group(1).upper(), normalize(pending_path)))
            pending_path = None
    return wrapped


def is_covered(verb: str, norm_path: str, wrapped: set[tuple[str, str]]) -> bool:
    """Check whether a spec operation is implemented by any wrapper call."""
    candidates = [norm_path] + equivalent_paths(verb, norm_path)
    for candidate in candidates:
        if (verb, candidate) in wrapped:
            return True
        if candidate.startswith("{}"):
            suffix = candidate[2:]
            if any(v == verb and p.endswith(suffix) for v, p in wrapped):
                return True
        prefix = "{}"
        if any(v == verb and p.startswith(prefix) and candidate.endswith(p[len(prefix) :]) for v, p in wrapped):
            return True
    return False


def color_for(pct: float) -> str:
    """Pick a shields.io color for a coverage percentage."""
    if pct >= 95:
        return "brightgreen"
    if pct >= 80:
        return "green"
    if pct >= 50:
        return "yellow"
    return "red"


def main() -> int:
    """Compute coverage and write the shields.io endpoint badge JSON."""
    spec = json.loads(SPEC_PATH.read_text())
    ops = spec_operations(spec)

    target_ops: dict[str, set[tuple[str, str]]] = {
        norm: {pair for pair in pairs if pair[1] in TARGET_TAGS} for norm, pairs in ops.items()
    }
    target_ops = {norm: pairs for norm, pairs in target_ops.items() if pairs}

    wrapped = wrapped_operations()

    total = sum(len(pairs) for pairs in target_ops.values())
    covered = sum(1 for norm, pairs in target_ops.items() for verb, _tag in pairs if is_covered(verb, norm, wrapped))
    pct = 100 * covered / total if total else 0

    print(f"API coverage: {covered} of {total} operations ({pct:.1f}%) in tags: {', '.join(TARGET_TAGS)}")
    uncovered = sorted(
        (verb, norm, tag)
        for norm, pairs in target_ops.items()
        for verb, tag in pairs
        if not is_covered(verb, norm, wrapped)
    )
    for verb, norm, tag in uncovered:
        print(f"  UNCOVERED {verb:6} {norm} [{tag}]")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    badge = {
        "schemaVersion": 1,
        "label": "API coverage",
        "message": f"{covered}/{total} ops",
        "color": color_for(pct),
    }
    OUT_PATH.write_text(json.dumps(badge, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
    print(f"badge written to {OUT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
