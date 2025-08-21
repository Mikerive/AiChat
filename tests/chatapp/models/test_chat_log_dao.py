import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from datetime import datetime

# Ensure src/ is importable
ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from backend.chat_app.dao.chat_log_dao import ChatLogDAO


@pytest.fixture
def mock_db_connection():
    mock_conn = AsyncMock()
    mock_cursor = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
    mock_conn.commit = AsyncMock()
    return mock_conn, mock_cursor


@pytest.fixture
def chat_log_dao(mock_db_connection):
    mock_conn, _ = mock_db_connection
    with patch(
        "backend.chat_app.dao.chat_log_dao.get_db_connection", return_value=mock_conn
    ):
        return ChatLogDAO()


@pytest.mark.asyncio
async def test_create_chat_log(chat_log_dao, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.lastrowid = 10

    test_metadata = {"model": "gpt-4", "temperature": 0.7}

    log_id = await chat_log_dao.create_chat_log(
        character_id=1,
        user_message="Hello",
        character_response="Hi there!",
        emotion="happy",
        metadata=test_metadata,
    )

    assert log_id == 10
    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()

    sql_query = mock_cursor.execute.call_args[0][0]
    assert "INSERT INTO" in sql_query
    assert "chat_logs" in sql_query

    params = mock_cursor.execute.call_args[0][1]
    assert params[0] == 1  # character_id
    assert params[1] == "Hello"  # user_message
    assert params[2] == "Hi there!"  # character_response
    assert params[3] == "happy"  # emotion
    assert '"model": "gpt-4"' in params[4]  # metadata as JSON string


@pytest.mark.asyncio
async def test_create_chat_log_minimal(chat_log_dao, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.lastrowid = 11

    log_id = await chat_log_dao.create_chat_log(
        character_id=1, user_message="Hello", character_response="Hi!"
    )

    assert log_id == 11
    params = mock_cursor.execute.call_args[0][1]
    assert params[3] is None  # emotion
    assert params[4] == "{}"  # empty metadata


@pytest.mark.asyncio
async def test_get_chat_log(chat_log_dao, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    test_timestamp = datetime(2024, 1, 1, 12, 0, 0)
    mock_cursor.fetchone.return_value = (
        1,
        2,
        "Hello",
        "Hi there!",
        test_timestamp,
        "happy",
        '{"model": "gpt-4"}',
    )

    chat_log = await chat_log_dao.get_chat_log(1)

    assert chat_log.id == 1
    assert chat_log.character_id == 2
    assert chat_log.user_message == "Hello"
    assert chat_log.character_response == "Hi there!"
    assert chat_log.timestamp == test_timestamp
    assert chat_log.emotion == "happy"
    assert chat_log.metadata["model"] == "gpt-4"

    mock_cursor.execute.assert_called_once()
    assert mock_cursor.execute.call_args[0][1] == (1,)


@pytest.mark.asyncio
async def test_get_chat_log_not_found(chat_log_dao, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchone.return_value = None

    chat_log = await chat_log_dao.get_chat_log(999)

    assert chat_log is None


@pytest.mark.asyncio
async def test_get_chat_logs_all(chat_log_dao, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    test_timestamp = datetime.now()
    mock_cursor.fetchall.return_value = [
        (1, 1, "Hello", "Hi!", test_timestamp, "happy", "{}"),
        (2, 1, "How are you?", "I'm fine!", test_timestamp, "cheerful", "{}"),
    ]

    chat_logs = await chat_log_dao.get_chat_logs()

    assert len(chat_logs) == 2
    assert chat_logs[0].id == 1
    assert chat_logs[0].user_message == "Hello"
    assert chat_logs[1].id == 2
    assert chat_logs[1].user_message == "How are you?"

    mock_cursor.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_chat_logs_by_character(chat_log_dao, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchall.return_value = [
        (1, 2, "Hello", "Hi!", datetime.now(), "happy", "{}")
    ]

    chat_logs = await chat_log_dao.get_chat_logs(character_id=2)

    assert len(chat_logs) == 1
    assert chat_logs[0].character_id == 2

    sql_query = mock_cursor.execute.call_args[0][0]
    assert "WHERE character_id = ?" in sql_query
    assert mock_cursor.execute.call_args[0][1] == (2, 100)  # character_id, limit


@pytest.mark.asyncio
async def test_get_chat_logs_with_limit(chat_log_dao, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchall.return_value = []

    await chat_log_dao.get_chat_logs(limit=50)

    sql_query = mock_cursor.execute.call_args[0][0]
    assert "LIMIT" in sql_query
    assert mock_cursor.execute.call_args[0][1] == (50,)


@pytest.mark.asyncio
async def test_get_chat_logs_by_character_with_limit(chat_log_dao, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchall.return_value = []

    await chat_log_dao.get_chat_logs(character_id=1, limit=25)

    sql_query = mock_cursor.execute.call_args[0][0]
    assert "WHERE character_id = ?" in sql_query
    assert "LIMIT" in sql_query
    assert mock_cursor.execute.call_args[0][1] == (1, 25)


@pytest.mark.asyncio
async def test_delete_chat_log(chat_log_dao, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.rowcount = 1

    success = await chat_log_dao.delete_chat_log(1)

    assert success is True
    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()

    sql_query = mock_cursor.execute.call_args[0][0]
    assert "DELETE FROM" in sql_query
    assert "chat_logs" in sql_query
    assert mock_cursor.execute.call_args[0][1] == (1,)


@pytest.mark.asyncio
async def test_delete_chat_log_not_found(chat_log_dao, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.rowcount = 0

    success = await chat_log_dao.delete_chat_log(999)

    assert success is False


@pytest.mark.asyncio
async def test_delete_chat_logs_by_character(chat_log_dao, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.rowcount = 5

    deleted_count = await chat_log_dao.delete_chat_logs_by_character(1)

    assert deleted_count == 5
    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()

    sql_query = mock_cursor.execute.call_args[0][0]
    assert "DELETE FROM" in sql_query
    assert "WHERE character_id = ?" in sql_query
    assert mock_cursor.execute.call_args[0][1] == (1,)


@pytest.mark.asyncio
async def test_get_chat_logs_count(chat_log_dao, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchone.return_value = (42,)

    count = await chat_log_dao.get_chat_logs_count()

    assert count == 42
    mock_cursor.execute.assert_called_once()
    sql_query = mock_cursor.execute.call_args[0][0]
    assert "SELECT COUNT(*)" in sql_query
    assert "chat_logs" in sql_query


@pytest.mark.asyncio
async def test_get_chat_logs_count_by_character(chat_log_dao, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchone.return_value = (15,)

    count = await chat_log_dao.get_chat_logs_count(character_id=1)

    assert count == 15
    sql_query = mock_cursor.execute.call_args[0][0]
    assert "SELECT COUNT(*)" in sql_query
    assert "WHERE character_id = ?" in sql_query
    assert mock_cursor.execute.call_args[0][1] == (1,)
