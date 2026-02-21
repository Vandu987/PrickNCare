"""Tests for async DB session management — task 3.2."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.database import (
    close_db,
    get_db,
    get_engine,
    get_session_factory,
    init_db,
)

# ---------------------------------------------------------------------------
# Engine / session factory
# ---------------------------------------------------------------------------


class TestGetEngine:
    def test_returns_engine(self) -> None:
        engine = get_engine()
        assert engine is not None

    def test_singleton(self) -> None:
        e1 = get_engine()
        e2 = get_engine()
        assert e1 is e2

    def test_engine_url_matches_settings(self) -> None:
        from app.core.config import settings

        engine = get_engine()
        assert "prickncare" in str(engine.url)
        assert settings.APP_ENV  # settings loaded OK


class TestGetSessionFactory:
    def test_returns_session_factory(self) -> None:
        factory = get_session_factory()
        assert factory is not None

    def test_singleton(self) -> None:
        f1 = get_session_factory()
        f2 = get_session_factory()
        assert f1 is f2


# ---------------------------------------------------------------------------
# get_db dependency
# ---------------------------------------------------------------------------


class TestGetDb:
    @pytest.mark.asyncio
    async def test_yields_session(self) -> None:
        mock_session = AsyncMock()
        mock_factory = MagicMock(return_value=mock_session)

        with patch("app.core.database.get_session_factory", return_value=mock_factory):
            gen = get_db()
            session = await gen.__anext__()
            assert session is mock_session

    @pytest.mark.asyncio
    async def test_commits_on_success(self) -> None:
        mock_session = AsyncMock()
        mock_factory = MagicMock(return_value=mock_session)

        with patch("app.core.database.get_session_factory", return_value=mock_factory):
            gen = get_db()
            await gen.__anext__()
            # Drive the generator past the yield so commit + close run
            with pytest.raises(StopAsyncIteration):
                await gen.__anext__()
            mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rolls_back_on_exception(self) -> None:
        mock_session = AsyncMock()
        mock_factory = MagicMock(return_value=mock_session)

        with patch("app.core.database.get_session_factory", return_value=mock_factory):
            gen = get_db()
            await gen.__anext__()
            with pytest.raises(ValueError):
                await gen.athrow(ValueError("boom"))
            mock_session.rollback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_always_closes_session(self) -> None:
        mock_session = AsyncMock()
        mock_factory = MagicMock(return_value=mock_session)

        with patch("app.core.database.get_session_factory", return_value=mock_factory):
            gen = get_db()
            await gen.__anext__()
            with pytest.raises(StopAsyncIteration):
                await gen.__anext__()
            mock_session.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_closes_even_after_exception(self) -> None:
        mock_session = AsyncMock()
        mock_factory = MagicMock(return_value=mock_session)

        with patch("app.core.database.get_session_factory", return_value=mock_factory):
            gen = get_db()
            await gen.__anext__()
            with pytest.raises(RuntimeError):
                await gen.athrow(RuntimeError("db error"))
            mock_session.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# init_db / close_db
# ---------------------------------------------------------------------------


class TestInitDb:
    @pytest.mark.asyncio
    async def test_succeeds_on_first_connect(self) -> None:
        mock_conn = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_engine = MagicMock()
        mock_engine.connect = MagicMock(return_value=mock_ctx)

        with patch("app.core.database.get_engine", return_value=mock_engine):
            await init_db()  # should not raise

    @pytest.mark.asyncio
    async def test_retries_and_succeeds(self) -> None:
        from sqlalchemy.exc import OperationalError

        mock_conn = AsyncMock()
        success_ctx = AsyncMock()
        success_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        success_ctx.__aexit__ = AsyncMock(return_value=False)

        fail_ctx = AsyncMock()
        fail_ctx.__aenter__ = AsyncMock(
            side_effect=OperationalError("conn", None, Exception("refused"))
        )

        mock_engine = MagicMock()
        mock_engine.connect = MagicMock(side_effect=[fail_ctx, success_ctx])

        with (
            patch("app.core.database.get_engine", return_value=mock_engine),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            await init_db()  # 1 failure then 1 success → no raise

    @pytest.mark.asyncio
    async def test_raises_after_three_failures(self) -> None:
        from sqlalchemy.exc import OperationalError

        fail_ctx = AsyncMock()
        fail_ctx.__aenter__ = AsyncMock(
            side_effect=OperationalError("conn", None, Exception("refused"))
        )

        mock_engine = MagicMock()
        mock_engine.connect = MagicMock(return_value=fail_ctx)

        with (
            patch("app.core.database.get_engine", return_value=mock_engine),
            patch("asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(OperationalError),
        ):
            await init_db()


class TestCloseDb:
    @pytest.mark.asyncio
    async def test_disposes_engine(self) -> None:
        import app.core.database as db_module

        mock_engine = AsyncMock()
        db_module._engine = mock_engine
        db_module._session_factory = MagicMock()

        await close_db()

        mock_engine.dispose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_resets_singletons(self) -> None:
        import app.core.database as db_module

        db_module._engine = AsyncMock()
        db_module._session_factory = MagicMock()

        await close_db()

        assert db_module._engine is None
        assert db_module._session_factory is None

    @pytest.mark.asyncio
    async def test_noop_if_no_engine(self) -> None:
        import app.core.database as db_module

        db_module._engine = None
        db_module._session_factory = None

        await close_db()  # should not raise
