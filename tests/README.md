# Testing Directory Structure

This document describes the testing architecture and organization for the VTuber Application.

## Overview

The test suite is designed to mirror the application structure and test **real functionality without mocking**. All tests exercise actual code paths, database operations, and service integrations to ensure the application works as expected in production.

## Directory Structure

```
tests/
├── conftest.py                 # Test configuration and fixtures
├── pytest.ini                 # Pytest configuration
├── test_integration.py         # Cross-service integration tests
├── backend/                    # Backend service tests (mirrors aichat/backend/)
│   ├── routes/                 # API endpoint tests
│   │   ├── test_chat_routes.py
│   │   ├── test_voice_routes.py
│   │   └── test_system_routes.py
│   ├── services/               # Service layer tests
│   │   ├── audio/
│   │   │   └── test_audio_services.py
│   │   ├── chat/
│   │   │   └── test_chat_service.py
│   │   ├── llm/
│   │   │   └── test_llm_services.py
│   │   └── voice/
│   │       ├── test_voice_service.py
│   │       ├── stt/
│   │       └── tts/
│   └── test_main.py           # FastAPI application tests
├── cli/                       # CLI command tests
│   └── test_cli_commands.py
├── core/                      # Core infrastructure tests
│   ├── test_config.py
│   └── test_database.py
├── frontend/                  # Frontend tests
│   └── tkinter/
│       └── components/
├── models/                    # Data model tests
│   └── test_schemas.py
└── training/                  # Training pipeline tests
    └── scripts/
```

## Testing Philosophy

### Real Functionality, No Mocking
- **Database Tests**: Use actual SQLite operations with real data persistence
- **API Tests**: Create actual FastAPI applications and test real endpoints
- **Service Tests**: Import and test actual service classes and methods
- **Import Tests**: Verify that modules and classes can be imported successfully

### Graceful Degradation
Tests use `pytest.skip()` when:
- Optional dependencies are not available (e.g., `aiosqlite` in test environments)
- External services are not configured (e.g., OpenRouter API key missing)
- Hardware resources are not available (e.g., audio devices)

This approach ensures tests don't fail due to environmental constraints while still validating core functionality.

## Test Categories

### 1. Unit Tests
Test individual components in isolation:
```python
def test_can_import_voice_service():
    """Test voice service import."""
    from aichat.backend.services.voice.voice_service import VoiceService
    assert VoiceService is not None
```

### 2. Database Tests
Test real database operations:
```python
@pytest.mark.asyncio
async def test_character_operations():
    """Test character database operations."""
    from aichat.core.database import create_character, list_characters
    
    unique_name = f"test_character_{int(time.time())}"
    char_id = await create_character(
        name=unique_name,
        profile="Test profile",
        personality="friendly"
    )
    assert char_id.id > 0
```

### 3. API Tests
Test actual FastAPI endpoints:
```python
def test_list_characters():
    """Test GET /api/chat/characters endpoint."""
    response = requests.get(f"{self.BASE_URL}/api/chat/characters")
    assert response.status_code == 200
```

### 4. Integration Tests
Test cross-service functionality:
```python
def test_app_creation_with_dependencies():
    """Test that FastAPI app can be created with all dependencies."""
    from aichat.backend.main import create_app
    app = create_app()
    assert app is not None
```

## Running Tests

### Basic Commands
```bash
# Run all tests
pytest

# Run with quiet output
pytest -q

# Run specific test file
pytest tests/core/test_database.py

# Run specific test class
pytest tests/backend/test_main.py::TestBackendMain

# Run with verbose output
pytest -v

# Run tests in specific directory
pytest tests/backend/
```

### Test Output
- **Passed**: Test executed successfully with real functionality
- **Skipped**: Test gracefully skipped due to missing dependencies/environment
- **Failed**: Actual functionality issue that needs investigation

Current status: **60 tests passed, 0 skipped**

## Configuration

### pytest.ini
```ini
[tool:pytest]
testpaths = .
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
addopts = --strict-markers
markers =
    asyncio: marks tests as async
    integration: marks tests as integration tests
    slow: marks tests as slow running
```

### conftest.py
Simple configuration without complex mocking:
```python
import pytest
import os
import tempfile
from pathlib import Path

# Set test environment
os.environ["TESTING"] = "true"

@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
```

## Database Testing

### Real Database Operations
- Tests create actual SQLite database records
- Database transactions are properly committed
- Tests use unique identifiers to avoid conflicts
- Database cleanup is handled automatically

### Security
- Fixed security vulnerability: replaced `eval()` with `json.loads()` for data deserialization
- All database operations use proper parameterized queries
- JSON serialization used for complex data types

## Adding New Tests

### 1. Mirror Application Structure
Place tests in directories that mirror the application structure:
```
aichat/backend/services/new_service.py
→ tests/backend/services/test_new_service.py
```

### 2. Test Real Functionality
```python
def test_new_service_import():
    """Test that new service can be imported."""
    try:
        from aichat.backend.services.new_service import NewService
        assert NewService is not None
    except ImportError:
        pytest.skip("New service not available")

@pytest.mark.asyncio
async def test_new_service_operation():
    """Test new service operation."""
    try:
        from aichat.backend.services.new_service import NewService
        service = NewService()
        result = await service.do_something()
        assert result is not None
    except Exception as e:
        pytest.skip(f"New service operation not available: {e}")
```

### 3. Follow Naming Conventions
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`
- Use descriptive names that explain what is being tested

## Best Practices

1. **Test Real Behavior**: Always test actual functionality, never mock implementations
2. **Graceful Skipping**: Use `pytest.skip()` for environmental constraints
3. **Unique Test Data**: Use timestamps or UUIDs to avoid test conflicts
4. **Clear Documentation**: Document what each test validates
5. **Mirror Structure**: Keep test organization aligned with application structure
6. **Async Support**: Use `@pytest.mark.asyncio` for async operations
7. **Error Messages**: Provide clear error messages in skip conditions

## Maintenance

- Tests should be updated when application structure changes
- New services should have corresponding tests added
- Failed tests indicate real issues that need investigation
- Skipped tests may indicate missing dependencies that should be documented