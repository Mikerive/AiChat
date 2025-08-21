# Test Database Module

This directory contains all test database configuration, setup, and management utilities.

## Files

### `setup.py`
Contains the test database schema creation and sample data definitions:
- Database table creation functions
- Sample data constants (characters, chat logs, training data, etc.)
- Database population utilities
- Cleanup functions

### `manager.py` 
Provides the test database manager and operations interface:
- `TestDatabaseManager`: Manages database connections and lifecycle
- `TestDBOperations`: Provides the same interface as production database operations
- Async database session management
- Database reset functionality for test isolation

### `__init__.py`
Module exports and convenience imports:
- Exports all public functions and classes
- Provides clean import interface for test files
- Single point of access for all database functionality

### `test_data.db` (generated)
The actual SQLite database file containing sample data:
- Auto-generated when tests run
- Contains realistic sample data for all tables
- Reset between test runs to ensure isolation
- Ignored by git (see `.gitignore`)

## Sample Data

The database contains realistic sample data for comprehensive testing:

- **3 Characters**: Hatsune Miku, Kagamine Rin, Megurine Luka
- **4 Chat Logs**: Various conversations with different emotions
- **3 Training Data**: Audio samples with transcripts and metadata
- **2 Voice Models**: Models in different training states
- **3 Event Logs**: System events with different severity levels

## Usage

### Basic Import
```python
from database import (
    create_test_database,
    test_db_ops,
    setup_test_database,
    reset_test_database
)
```

### In Test Files
```python
@pytest.fixture
def test_db_operations():
    return test_db_ops

async def test_characters(test_db_operations):
    characters = await test_db_operations.list_characters()
    assert len(characters) >= 3
```

### Manual Database Setup
```python
from database import create_test_database
create_test_database()  # Creates database with sample data
```

## Benefits

1. **Realistic Testing**: Uses actual database with realistic data
2. **Test Isolation**: Database resets between tests
3. **Consistent Data**: Same sample data across all test runs
4. **Easy Setup**: Single function call to create database
5. **Clean Interface**: Same API as production database
6. **Performance**: SQLite provides fast test execution