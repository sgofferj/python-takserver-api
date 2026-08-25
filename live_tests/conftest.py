"""Live-test fixtures: real TAK server, local machine only.

These tests are NEVER part of CI. They require a local server configuration;
without it every test skips.

The server address and credentials are intentionally NOT committed. Configure
them in an untracked `.env` file in the repository root (see README, "Live
integration tests") or via environment variables:

    TAK_LIVE_HOST=tak.example.com
    TAK_LIVE_CERT=path/to/client.pem
    TAK_LIVE_KEY=path/to/client.key
"""

import os
from pathlib import Path

import pytest
import pytest_asyncio

from python_takserver_api import Server

REPO_ROOT = Path(__file__).resolve().parents[1]
DOTENV = REPO_ROOT / ".env"


def _load_dotenv(path: Path) -> dict[str, str]:
    """Minimal .env parser (no python-dotenv dependency)."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _get(key: str, dotenv: dict[str, str]) -> str | None:
    return os.environ.get(key) or dotenv.get(key)


@pytest_asyncio.fixture
async def server() -> Server:
    """Connected Server instance using the locally configured credentials."""
    dotenv = _load_dotenv(DOTENV)
    host = _get("TAK_LIVE_HOST", dotenv)
    cert = _get("TAK_LIVE_CERT", dotenv)
    key = _get("TAK_LIVE_KEY", dotenv)
    if not host or not cert or not key or not Path(cert).exists() or not Path(key).exists():
        pytest.skip("live server not configured: set TAK_LIVE_HOST/TAK_LIVE_CERT/TAK_LIVE_KEY in .env (see README)")
    srv = Server(host, cert, key)
    yield srv
    await srv.close()


@pytest.fixture
def live_host() -> str:
    """The bare hostname of the live TAK server (no scheme/port)."""
    dotenv = _load_dotenv(DOTENV)
    host = _get("TAK_LIVE_HOST", dotenv)
    if not host:
        pytest.skip("live server not configured")
    return host
