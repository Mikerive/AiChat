# Testing Structure

This directory contains the test suite for the VtuberMiku project, organized for clear separation between unit tests and integration tests.

## Directory Structure

```
tests/
├── README.md                    # This file
├── database/                    # Test database configuration
│   ├── __init__.py             # Database module exports
│   ├── setup.py               # Test database setup and sample data
│   ├── manager.py             # Test database manager and operations
│   └── test_data.db           # SQLite test database (generated)
├── chatapp/                   # Chat app unit tests
│   ├── conftest.py           # Shared test configuration
│   ├── services/             # Service layer tests
│   │   ├── test_chat_service.py
│   │   ├── test_voice_service.py
│   │   ├── test_whisper_service.py
│   │   └── test_piper_tts_service.py
│   ├── routes/               # API route tests
│   │   ├── test_chat_routes.py
│   │   ├── test_voice_routes.py
│   │   ├── test_system_routes.py
│   │   └── test_routes_with_db.py
│   └── models/               # Model and DAO tests
│       ├── test_schemas.py
│       ├── test_character_dao.py
│       ├── test_chat_log_dao.py
│       └── test_dao_with_db.py
└── integration/              # Cross-application integration tests
    ├── test_api_recreated.py
    ├── test_voice_pipeline.py
    └── test_ws_and_rest.py
```

## Test Categories

### Unit Tests (`tests/chatapp/`)
- **Purpose**: Test individual components in isolation
- **Scope**: Chat app specific functionality
- **Database**: Uses test database with sample data
- **Speed**: Fast execution
- **Dependencies**: Minimal external dependencies

### Integration Tests (`tests/integration/`)
- **Purpose**: Test interactions between applications/services
- **Scope**: Cross-application communication and workflows
- **Database**: May use test database or mocked services
- **Speed**: Slower execution
- **Dependencies**: Multiple services and components

## Test Database (`tests/database/`)

### Overview
The test suite uses a dedicated SQLite database (`tests/database/test_data.db`) with pre-populated sample data to ensure consistent and realistic testing conditions. All database-related test configuration is organized in the `tests/database/` directory.

### Sample Data
- **3 Characters**: Hatsune Miku, Kagamine Rin, Megurine Luka
- **4 Chat Logs**: Conversations with different characters and emotions
- **3 Training Data**: Audio samples with transcripts
- **2 Voice Models**: Trained and training models
- **3 Event Logs**: System events with different severity levels

### Database Module Structure
- **`setup.py`**: Database schema creation and sample data insertion
- **`manager.py`**: Test database manager and operations interface
- **`__init__.py`**: Module exports and convenience imports
- **`test_data.db`**: The actual SQLite database file (auto-generated)

### Database Operations
The test database provides the same interface as the production database:
- Character management (CRUD operations)
- Chat log storage and retrieval
- Training data management
- Voice model tracking
- Event logging

## Running Tests

### Using pytest directly:
```bash
# Run all tests
pytest tests/

# Run only chat app unit tests
pytest tests/chatapp/

# Run only integration tests  
pytest tests/integration/

# Run with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/chatapp/services/test_chat_service.py
```

### Using the test runner script:
```bash
# Run all tests with automatic setup/cleanup
python run_tests.py

# Run only chat app tests
python run_tests.py --chatapp

# Run only integration tests
python run_tests.py --integration

# Set up test database only
python run_tests.py --setup-only

# Clean up test environment
python run_tests.py --cleanup
```

## Test Configuration

### Fixtures
Common test fixtures are provided in `tests/chatapp/conftest.py`:
- `test_database`: Access to test database manager
- `test_db_operations`: Database operations interface
- `sample_character_data`: Sample character data
- `sample_chat_log_data`: Sample chat log data
- `sample_training_data`: Sample training data
- `sample_voice_model_data`: Sample voice model data

### Database Reset
The test database is automatically reset to its initial state before each test to ensure test isolation and consistency.

### Async Support
The test configuration includes proper async support for testing async database operations and services.

## Writing New Tests

### Unit Tests
When writing unit tests for chat app components:
1. Place them in the appropriate `tests/chatapp/` subdirectory
2. Use the provided fixtures for database access
3. Mock external services and dependencies
4. Focus on testing single components in isolation

### Integration Tests
When writing integration tests:
1. Place them in `tests/integration/`
2. Test interactions between multiple components
3. Use real or minimal mocking of services
4. Focus on end-to-end workflows

### Database Tests
When writing tests that use the database:
1. Use `test_db_operations` fixture for database access
2. Leverage the pre-populated sample data
3. Test both success and error cases
4. Ensure tests are independent (database resets between tests)

## Benefits of This Structure

1. **Clear Separation**: Unit tests are isolated from integration tests
2. **Realistic Testing**: Uses actual database with sample data
3. **Fast Feedback**: Unit tests run quickly with minimal dependencies
4. **Comprehensive Coverage**: Tests both individual components and their interactions
5. **Easy Maintenance**: Well-organized structure makes tests easy to find and update
6. **Consistent Data**: Sample data ensures predictable test conditions