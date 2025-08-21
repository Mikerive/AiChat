import sys
from pathlib import Path
import pytest
from datetime import datetime

# Ensure src/ is importable
ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from backend.chat_app.dao.character_dao import CharacterDAO


@pytest.mark.asyncio
async def test_get_character_by_id(character_dao, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchone.return_value = (
        1,
        "hatsune_miku",
        "A virtual singer",
        "cheerful",
        "http://example.com/avatar.jpg",
    )

    character = await character_dao.get_character(1)

    assert character.id == 1
    assert character.name == "hatsune_miku"
    assert character.profile == "A virtual singer"
    assert character.personality == "cheerful"
    assert character.avatar_url == "http://example.com/avatar.jpg"

    mock_cursor.execute.assert_called_once()
    assert "SELECT" in mock_cursor.execute.call_args[0][0]
    assert mock_cursor.execute.call_args[0][1] == (1,)


@pytest.mark.asyncio
async def test_get_character_by_id_not_found(character_dao, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchone.return_value = None

    character = await character_dao.get_character(999)

    assert character is None


@pytest.mark.asyncio
async def test_get_character_by_name(character_dao, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchone.return_value = (
        1,
        "hatsune_miku",
        "A virtual singer",
        "cheerful",
        None,
    )

    character = await character_dao.get_character_by_name("hatsune_miku")

    assert character.id == 1
    assert character.name == "hatsune_miku"
    assert character.avatar_url is None

    mock_cursor.execute.assert_called_once()
    assert mock_cursor.execute.call_args[0][1] == ("hatsune_miku",)


@pytest.mark.asyncio
async def test_list_characters(character_dao, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchall.return_value = [
        (1, "hatsune_miku", "A virtual singer", "cheerful", None),
        (2, "kagamine_rin", "Twin vocalist", "energetic", "http://example.com/rin.jpg"),
    ]

    characters = await character_dao.list_characters()

    assert len(characters) == 2
    assert characters[0].name == "hatsune_miku"
    assert characters[1].name == "kagamine_rin"
    assert characters[1].avatar_url == "http://example.com/rin.jpg"

    mock_cursor.execute.assert_called_once()


@pytest.mark.asyncio
async def test_list_characters_with_limit(character_dao, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchall.return_value = [
        (1, "hatsune_miku", "A virtual singer", "cheerful", None)
    ]

    characters = await character_dao.list_characters(limit=1)

    assert len(characters) == 1
    mock_cursor.execute.assert_called_once()
    sql_query = mock_cursor.execute.call_args[0][0]
    assert "LIMIT" in sql_query
    assert mock_cursor.execute.call_args[0][1] == (1,)


@pytest.mark.asyncio
async def test_create_character(character_dao, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.lastrowid = 5

    character_id = await character_dao.create_character(
        name="new_character",
        profile="A new character",
        personality="mysterious",
        avatar_url="http://example.com/new.jpg",
    )

    assert character_id == 5
    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()

    sql_query = mock_cursor.execute.call_args[0][0]
    assert "INSERT INTO" in sql_query
    assert "characters" in sql_query

    params = mock_cursor.execute.call_args[0][1]
    assert params == (
        "new_character",
        "A new character",
        "mysterious",
        "http://example.com/new.jpg",
    )


@pytest.mark.asyncio
async def test_create_character_without_avatar(character_dao, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.lastrowid = 6

    character_id = await character_dao.create_character(
        name="simple_character", profile="Simple profile", personality="friendly"
    )

    assert character_id == 6
    params = mock_cursor.execute.call_args[0][1]
    assert params == ("simple_character", "Simple profile", "friendly", None)


@pytest.mark.asyncio
async def test_update_character(character_dao, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.rowcount = 1

    success = await character_dao.update_character(
        character_id=1,
        name="updated_miku",
        profile="Updated profile",
        personality="updated personality",
        avatar_url="http://example.com/updated.jpg",
    )

    assert success is True
    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()

    sql_query = mock_cursor.execute.call_args[0][0]
    assert "UPDATE" in sql_query
    assert "characters" in sql_query
    assert "WHERE id = ?" in sql_query


@pytest.mark.asyncio
async def test_update_character_not_found(character_dao, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.rowcount = 0

    success = await character_dao.update_character(
        character_id=999,
        name="nonexistent",
        profile="Profile",
        personality="personality",
    )

    assert success is False


@pytest.mark.asyncio
async def test_delete_character(character_dao, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.rowcount = 1

    success = await character_dao.delete_character(1)

    assert success is True
    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()

    sql_query = mock_cursor.execute.call_args[0][0]
    assert "DELETE FROM" in sql_query
    assert "characters" in sql_query
    assert mock_cursor.execute.call_args[0][1] == (1,)


@pytest.mark.asyncio
async def test_delete_character_not_found(character_dao, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.rowcount = 0

    success = await character_dao.delete_character(999)

    assert success is False


@pytest.mark.asyncio
async def test_character_exists(character_dao, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchone.return_value = (1,)

    exists = await character_dao.character_exists("hatsune_miku")

    assert exists is True
    mock_cursor.execute.assert_called_once()
    sql_query = mock_cursor.execute.call_args[0][0]
    assert "SELECT COUNT(*)" in sql_query or "SELECT 1" in sql_query


@pytest.mark.asyncio
async def test_character_not_exists(character_dao, mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchone.return_value = (0,) or None

    exists = await character_dao.character_exists("nonexistent")

    assert exists is False
