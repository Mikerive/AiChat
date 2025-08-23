"""
Test database module.
Provides database setup, management, and operations for testing.
"""

from .setup import create_test_database, cleanup_test_database, get_test_db_path

from .fixtures import (
    load_fixture,
    load_all_fixtures,
    get_sample_characters,
    get_sample_chat_logs,
    get_sample_training_data,
    get_sample_voice_models,
    get_sample_event_logs,
)

from .manager import (
    TestDatabaseManager,
    TestDBOperations,
    test_db_manager,
    test_db_ops,
    setup_test_database,
    cleanup_test_database,
    reset_test_database,
)

__all__ = [
    "create_test_database",
    "cleanup_test_database",
    "get_test_db_path",
    "load_fixture",
    "load_all_fixtures",
    "get_sample_characters",
    "get_sample_chat_logs",
    "get_sample_training_data",
    "get_sample_voice_models",
    "get_sample_event_logs",
    "TestDatabaseManager",
    "TestDBOperations",
    "test_db_manager",
    "test_db_ops",
    "setup_test_database",
    "reset_test_database",
]
