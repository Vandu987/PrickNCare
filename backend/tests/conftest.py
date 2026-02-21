import time
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture(autouse=True)
def mock_rate_limit():
    """Prevent tests from hitting Redis via the rate-limit middleware.

    Tests in test_rate_limit.py override this with their own patches.
    """
    with patch(
        "app.middleware.rate_limit._sliding_window_check",
        new_callable=AsyncMock,
        return_value=(True, 99, int(time.time()) + 60),
    ):
        yield


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
