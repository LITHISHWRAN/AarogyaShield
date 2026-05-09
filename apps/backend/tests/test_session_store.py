"""
Tests for session memory persistence:
- app.memory.session_store.SessionStore

Redis is fully mocked — no live connection required.
Tests verify that:
  - Session data is correctly serialised and deserialised
  - Sessions are isolated by session_id (different Redis keys)
  - Corrupt fields gracefully return None (no crash)
  - TTL is refreshed on every write (via pipeline mock inspection)
  - Message appending extends history correctly
  - Session info correctly counts user turns
"""
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call

from app.memory.session_store import SessionStore, _hkey
from app.memory.session_models import (
    SessionData, StoredMessage, StoredProfile, StoredRecommendations, StoredAlternative,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers and fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _make_profile(**kwargs) -> StoredProfile:
    defaults = {
        "name": "Arjun Sharma", "age": 34, "lifestyle": "sedentary",
        "pre_existing_conditions": ["diabetes"],
        "financial_band": "6-10 LPA", "city_tier": "Tier 2", "family_size": 3,
    }
    return StoredProfile(**{**defaults, **kwargs})


def _make_message(role: str = "user", content: str = "Hello") -> StoredMessage:
    return StoredMessage(role=role, content=content)


def _make_recs(**kwargs) -> StoredRecommendations:
    defaults = {
        "top_policy_name": "Star Health Optima",
        "top_insurer": "Star Health Insurance",
        "top_policy_id": "pol-star-001",
        "alternatives": [],
    }
    return StoredRecommendations(**{**defaults, **kwargs})


@pytest.fixture
def mock_pipe():
    """Async pipeline mock — pipeline commands are synchronous queuing calls;
    only execute() is awaited."""
    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=[True, True, True, True])
    return pipe


@pytest.fixture
def mock_redis(mock_pipe):
    """Full Redis mock with pipeline context manager support."""
    r = AsyncMock()

    # Pipeline context manager
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_pipe)
    cm.__aexit__ = AsyncMock(return_value=None)
    r.pipeline.return_value = cm

    # Default returns for individual commands
    r.hgetall = AsyncMock(return_value={})
    r.hget = AsyncMock(return_value=None)
    r.hmget = AsyncMock(return_value=[None, None, None, None, None])
    r.delete = AsyncMock(return_value=1)

    return r


@pytest.fixture
def store() -> SessionStore:
    return SessionStore()


@pytest.fixture
def patch_redis(mock_redis):
    """Patches get_redis() at the module level for all session_store calls."""
    with patch("app.memory.session_store.get_redis", return_value=mock_redis):
        yield mock_redis


# ─────────────────────────────────────────────────────────────────────────────
# TestSessionKeyIsolation — verify per-session key namespacing
# ─────────────────────────────────────────────────────────────────────────────

class TestSessionKeyIsolation:

    def test_different_session_ids_produce_different_keys(self):
        key1 = _hkey("session-abc")
        key2 = _hkey("session-xyz")
        assert key1 != key2

    def test_key_is_namespaced_with_prefix(self):
        key = _hkey("test-session")
        assert key.startswith("aarogya:session:")

    def test_session_id_appears_in_key(self):
        session_id = "unique-id-12345"
        key = _hkey(session_id)
        assert session_id in key


# ─────────────────────────────────────────────────────────────────────────────
# TestLoadSession — deserialisation correctness
# ─────────────────────────────────────────────────────────────────────────────

class TestLoadSession:

    async def test_empty_redis_returns_default_session(self, store, patch_redis):
        patch_redis.hgetall.return_value = {}
        session = await store.load_session("new-session")
        assert session.session_id == "new-session"
        assert session.profile is None
        assert session.recommendations is None
        assert session.history == []

    async def test_session_with_profile_loads_correctly(self, store, patch_redis):
        profile = _make_profile()
        patch_redis.hgetall.return_value = {
            "profile": profile.model_dump_json(),
        }
        session = await store.load_session("sess-1")
        assert session.profile is not None
        assert session.profile.name == "Arjun Sharma"
        assert session.profile.age == 34
        assert "diabetes" in session.profile.pre_existing_conditions

    async def test_session_with_history_loads_correctly(self, store, patch_redis):
        messages = [
            _make_message("user", "What is waiting period?"),
            _make_message("assistant", "It is the time before coverage applies."),
        ]
        patch_redis.hgetall.return_value = {
            "history": json.dumps([m.model_dump(mode="json") for m in messages], default=str),
        }
        session = await store.load_session("sess-2")
        assert len(session.history) == 2
        assert session.history[0].role == "user"
        assert session.history[1].role == "assistant"
        assert session.history[0].content == "What is waiting period?"

    async def test_session_with_recommendations_loads_correctly(self, store, patch_redis):
        recs = _make_recs()
        patch_redis.hgetall.return_value = {
            "recommendations": recs.model_dump_json(),
        }
        session = await store.load_session("sess-3")
        assert session.recommendations is not None
        assert session.recommendations.top_policy_name == "Star Health Optima"

    async def test_corrupt_profile_field_returns_none_not_crash(self, store, patch_redis):
        """Corrupt Redis data must not crash the application."""
        patch_redis.hgetall.return_value = {
            "profile": "this is not valid json {{{",
        }
        session = await store.load_session("sess-corrupt")
        assert session.profile is None  # graceful degradation

    async def test_corrupt_history_field_returns_empty_list(self, store, patch_redis):
        patch_redis.hgetall.return_value = {
            "history": "invalid-json-array",
        }
        session = await store.load_session("sess-bad-hist")
        assert session.history == []

    async def test_corrupt_recommendations_returns_none(self, store, patch_redis):
        patch_redis.hgetall.return_value = {
            "recommendations": "not-json",
        }
        session = await store.load_session("sess-bad-recs")
        assert session.recommendations is None

    async def test_created_at_parsed_from_redis(self, store, patch_redis):
        ts = "2026-05-09T10:30:00+00:00"
        patch_redis.hgetall.return_value = {"created_at": ts}
        session = await store.load_session("sess-ts")
        assert session.created_at.year == 2026
        assert session.created_at.month == 5
        assert session.created_at.day == 9

    async def test_invalid_timestamp_uses_now_as_fallback(self, store, patch_redis):
        patch_redis.hgetall.return_value = {"created_at": "not-a-datetime"}
        session = await store.load_session("sess-bad-ts")
        # Should not raise — fallback to current time
        assert isinstance(session.created_at, datetime)

    async def test_load_calls_hgetall_with_correct_key(self, store, patch_redis):
        await store.load_session("my-session-id")
        expected_key = _hkey("my-session-id")
        patch_redis.hgetall.assert_called_once_with(expected_key)


# ─────────────────────────────────────────────────────────────────────────────
# TestSaveProfile — profile persistence
# ─────────────────────────────────────────────────────────────────────────────

class TestSaveProfile:

    async def test_save_profile_stores_json(self, store, patch_redis, mock_pipe):
        profile = _make_profile()
        await store.save_profile("sess-1", profile)
        # hset must be called with _F_PROFILE and the JSON string
        mock_pipe.hset.assert_called()
        call_args = mock_pipe.hset.call_args_list
        profile_call = next(
            (c for c in call_args if "profile" in str(c)), None
        )
        assert profile_call is not None

    async def test_save_profile_refreshes_ttl(self, store, patch_redis, mock_pipe):
        """Every write must extend the session TTL."""
        await store.save_profile("sess-1", _make_profile())
        mock_pipe.expire.assert_called()

    async def test_save_profile_sets_last_active_at(self, store, patch_redis, mock_pipe):
        await store.save_profile("sess-1", _make_profile())
        last_active_calls = [
            c for c in mock_pipe.hset.call_args_list
            if "last_active_at" in str(c)
        ]
        assert len(last_active_calls) >= 1

    async def test_save_profile_sets_created_at_only_if_not_exists(self, store, patch_redis, mock_pipe):
        """hsetnx is used for created_at — only sets on first write."""
        await store.save_profile("sess-1", _make_profile())
        mock_pipe.hsetnx.assert_called()

    async def test_get_profile_returns_saved_profile(self, store, patch_redis):
        profile = _make_profile()
        patch_redis.hget.return_value = profile.model_dump_json()
        loaded = await store.get_profile("sess-1")
        assert loaded is not None
        assert loaded.name == "Arjun Sharma"

    async def test_get_profile_returns_none_when_missing(self, store, patch_redis):
        patch_redis.hget.return_value = None
        loaded = await store.get_profile("sess-empty")
        assert loaded is None


# ─────────────────────────────────────────────────────────────────────────────
# TestSaveHistory and AppendMessages
# ─────────────────────────────────────────────────────────────────────────────

class TestSaveAndAppendHistory:

    async def test_save_history_serialises_messages(self, store, patch_redis, mock_pipe):
        messages = [_make_message("user", "hi"), _make_message("assistant", "hello")]
        await store.save_history("sess-1", messages)
        mock_pipe.hset.assert_called()

    async def test_append_to_empty_history(self, store, patch_redis):
        patch_redis.hget.return_value = None  # no existing history
        new_msgs = [_make_message("user", "first message")]
        result = await store.append_messages("sess-1", new_msgs)
        assert len(result) == 1
        assert result[0].content == "first message"

    async def test_append_extends_existing_history(self, store, patch_redis):
        existing = [_make_message("user", "earlier message")]
        patch_redis.hget.return_value = json.dumps(
            [m.model_dump(mode="json") for m in existing], default=str
        )
        new_msgs = [_make_message("assistant", "later reply")]
        result = await store.append_messages("sess-1", new_msgs)
        assert len(result) == 2
        assert result[0].content == "earlier message"
        assert result[1].content == "later reply"

    async def test_append_multiple_messages_at_once(self, store, patch_redis):
        patch_redis.hget.return_value = None
        new_msgs = [
            _make_message("user", "question"),
            _make_message("assistant", "answer"),
        ]
        result = await store.append_messages("sess-1", new_msgs)
        assert len(result) == 2

    async def test_append_preserves_message_order(self, store, patch_redis):
        existing = [
            _make_message("user", "msg 1"),
            _make_message("assistant", "reply 1"),
        ]
        patch_redis.hget.return_value = json.dumps(
            [m.model_dump(mode="json") for m in existing], default=str
        )
        result = await store.append_messages("sess-1", [_make_message("user", "msg 2")])
        assert result[0].content == "msg 1"
        assert result[2].content == "msg 2"


# ─────────────────────────────────────────────────────────────────────────────
# TestClearSession
# ─────────────────────────────────────────────────────────────────────────────

class TestClearSession:

    async def test_clear_session_calls_delete_with_correct_key(self, store, patch_redis):
        await store.clear_session("sess-to-delete")
        expected_key = _hkey("sess-to-delete")
        patch_redis.delete.assert_called_once_with(expected_key)

    async def test_clear_session_does_not_raise_on_missing_key(self, store, patch_redis):
        patch_redis.delete.return_value = 0  # key did not exist
        await store.clear_session("non-existent-session")
        # Should complete without exception


# ─────────────────────────────────────────────────────────────────────────────
# TestSessionInfo
# ─────────────────────────────────────────────────────────────────────────────

class TestSessionInfo:

    async def test_empty_session_returns_zeroed_info(self, store, patch_redis):
        patch_redis.hmget.return_value = [None, None, None, None, None]
        info = await store.session_info("sess-empty")
        assert info["has_profile"] is False
        assert info["has_recommendations"] is False
        assert info["turn_count"] == 0

    async def test_session_with_profile_has_profile_true(self, store, patch_redis):
        patch_redis.hmget.return_value = [
            '{"name":"x","age":1,"lifestyle":"a","financial_band":"b","city_tier":"c"}',
            None, None, None, None,
        ]
        info = await store.session_info("sess-1")
        assert info["has_profile"] is True

    async def test_session_with_recommendations_has_recs_true(self, store, patch_redis):
        patch_redis.hmget.return_value = [
            None,
            '{"top_policy_name":"Plan","top_insurer":"X","top_policy_id":"1"}',
            None, None, None,
        ]
        info = await store.session_info("sess-1")
        assert info["has_recommendations"] is True

    async def test_turn_count_counts_only_user_messages(self, store, patch_redis):
        history = [
            {"role": "user",      "content": "q1", "timestamp": "2026-05-09T10:00:00+00:00"},
            {"role": "assistant", "content": "a1", "timestamp": "2026-05-09T10:01:00+00:00"},
            {"role": "user",      "content": "q2", "timestamp": "2026-05-09T10:02:00+00:00"},
            {"role": "assistant", "content": "a2", "timestamp": "2026-05-09T10:03:00+00:00"},
            {"role": "user",      "content": "q3", "timestamp": "2026-05-09T10:04:00+00:00"},
        ]
        patch_redis.hmget.return_value = [None, None, None, None, json.dumps(history)]
        info = await store.session_info("sess-1")
        assert info["turn_count"] == 3  # 3 user messages, 2 assistant messages

    async def test_turn_count_zero_for_empty_history(self, store, patch_redis):
        patch_redis.hmget.return_value = [None, None, None, None, json.dumps([])]
        info = await store.session_info("sess-empty-history")
        assert info["turn_count"] == 0

    async def test_turn_count_with_corrupt_history_returns_zero(self, store, patch_redis):
        patch_redis.hmget.return_value = [None, None, None, None, "not-json"]
        info = await store.session_info("sess-corrupt")
        assert info["turn_count"] == 0

    async def test_session_id_included_in_result(self, store, patch_redis):
        patch_redis.hmget.return_value = [None, None, None, None, None]
        info = await store.session_info("my-session")
        assert info["session_id"] == "my-session"


# ─────────────────────────────────────────────────────────────────────────────
# TestSessionIsolation — two users cannot see each other's data
# ─────────────────────────────────────────────────────────────────────────────

class TestSessionIsolation:

    async def test_two_sessions_use_different_redis_keys(self, store, patch_redis):
        """load_session must call hgetall with the session-specific key."""
        await store.load_session("user-alpha")
        await store.load_session("user-beta")

        calls = patch_redis.hgetall.call_args_list
        assert len(calls) == 2
        key_alpha = calls[0][0][0]
        key_beta = calls[1][0][0]
        assert key_alpha != key_beta
        assert "user-alpha" in key_alpha
        assert "user-beta" in key_beta

    async def test_save_profile_targets_correct_session_key(self, store, patch_redis, mock_pipe):
        await store.save_profile("session-123", _make_profile())
        # Find the hset call that set the profile field
        hset_calls = mock_pipe.hset.call_args_list
        # The key argument in all calls must contain the session id
        for c in hset_calls:
            key_arg = c[0][0] if c[0] else c.args[0]
            assert "session-123" in key_arg

    async def test_get_profile_reads_from_correct_key(self, store, patch_redis):
        await store.get_profile("specific-session-id")
        call = patch_redis.hget.call_args
        key = call[0][0] if call[0] else call.args[0]
        assert "specific-session-id" in key
