# Test Modernization Guide

## Overview

The test suite needs to be updated to work with the new dependency injection architecture. This guide explains the changes needed and provides examples.

## Key Changes Needed

### 1. Import Path Updates

**BEFORE** (Old structure):
```python
from backend.chat_app.services.core_services.chat_service import ChatService
from backend.chat_app.routes.chat import router
```

**AFTER** (New structure):
```python
from aichat.backend.services.chat.chat_service import ChatService
from aichat.backend.routes.chat import router
```

### 2. Service Manager → DI Container

**BEFORE** (Manual mocking with patches):
```python
@pytest.fixture
def chat_service(mock_db_ops, mock_openrouter, mock_piper_tts):
    with patch("backend.chat_app.services.core_services.chat_service.db_ops", mock_db_ops), \
         patch("backend.chat_app.services.core_services.chat_service.get_openrouter_service", return_value=mock_openrouter), \
         patch("backend.chat_app.services.core_services.chat_service.get_piper_tts_service", return_value=mock_piper_tts):
        return ChatService()
```

**AFTER** (DI container with clean mocking):
```python
from tests.test_utils.di_test_helpers import test_di_container, mock_di_container

def test_chat_service(test_di_container):
    chat_service = test_di_container.resolve("chat_service")
    # Service automatically has mocked dependencies injected
```

### 3. Route Testing

**BEFORE** (Manual service patching):
```python
def test_chat_endpoint():
    with patch("routes.chat.get_chat_service") as mock_get_service:
        mock_get_service.return_value = mock_chat_service
        # ... test code
```

**AFTER** (DI container overrides):
```python
def test_chat_endpoint():
    with mock_di_container({"chat_service": create_mock_chat_service()}):
        client = TestClient(create_app())
        # ... test code
```

## Migration Steps

### Step 1: Update Import Paths

1. Change all imports from `backend.chat_app.*` to `aichat.backend.*`
2. Update path references from `src/` structure to package structure
3. Fix any remaining import errors

### Step 2: Replace Service Manager References

1. Replace `get_*_service()` calls with DI container resolution
2. Update service mocking to use DI container overrides
3. Remove manual patching where DI container handles it

### Step 3: Use New Test Utilities

1. Import test helpers from `tests.test_utils.di_test_helpers`
2. Use `test_di_container` fixture for unit tests
3. Use `mock_di_container` context manager for integration tests

### Step 4: Update Test Structure

1. Group tests by functionality, not just by service
2. Add integration tests that verify DI container behavior
3. Add tests for service lifetime behavior (singleton, scoped, transient)

## Migration Examples

### Example 1: Service Unit Test

**BEFORE:**
```python
@pytest.fixture
def mock_openrouter():
    mock = AsyncMock()
    mock.generate_response.return_value = MagicMock(response="test")
    return mock

def test_chat_service_process_message(mock_openrouter):
    with patch("chat_service.get_openrouter_service", return_value=mock_openrouter):
        service = ChatService()
        result = await service.process_message("hello", 1, "char")
        assert result.response == "test"
```

**AFTER:**
```python
def test_chat_service_process_message(test_di_container):
    # Mock is automatically injected via DI container
    chat_service = test_di_container.resolve("chat_service")
    result = await chat_service.process_message("hello", 1, "char")
    assert result.response == "Hello! How can I help?"
```

### Example 2: Route Integration Test

**BEFORE:**
```python
def test_tts_endpoint():
    mock_chat_service = AsyncMock()
    mock_chat_service.generate_tts.return_value = "/tmp/audio.wav"
    
    with patch("routes.chat.get_chat_service_dep", return_value=mock_chat_service):
        client = TestClient(app)
        response = client.post("/api/chat/tts", json={"text": "hello", "character": "test"})
        assert response.status_code == 200
```

**AFTER:**
```python
def test_tts_endpoint():
    mock_tts = create_mock_tts_service()
    mock_tts.generate_speech.return_value = "/tmp/audio.wav"
    
    with mock_di_container({"chatterbox_tts_service": mock_tts}):
        client = TestClient(create_app())
        response = client.post("/api/chat/tts", json={"text": "hello", "character": "test"})
        # Test passes with proper mocking
```

### Example 3: Testing New TTS Segmentation

**NEW TEST** (leveraging improved TTS):
```python
def test_tts_sentence_segmentation(test_di_container):
    tts_service = test_di_container.resolve("chatterbox_tts_service")
    
    # Test improved sentence-based segmentation
    segments = list(tts_service.split_text_by_punctuation(
        "Hello there! How are you doing? I hope you're well."
    ))
    
    # Should create fewer, more natural segments
    assert len(segments) == 3  # One per sentence
    assert "Hello there!" in segments[0]["text"]
    assert "How are you doing?" in segments[1]["text"]
```

## File-by-File Migration Priority

### High Priority (Core functionality):
1. `tests/chatapp/routes/test_chat_routes.py` - Chat API tests
2. `tests/chatapp/routes/test_voice_routes.py` - Voice API tests  
3. `tests/chatapp/services/test_chat_service.py` - Core chat logic
4. `tests/chatapp/services/test_whisper_service.py` - STT service

### Medium Priority (Supporting services):
5. `tests/chatapp/services/test_voice_service.py` - Voice orchestration
6. `tests/chatapp/models/test_schemas.py` - Data validation
7. `tests/integration/test_api_recreated.py` - End-to-end tests

### Low Priority (Legacy or less critical):
8. `tests/chatapp/services/test_piper_tts_service.py` - Old TTS (replaced by ChatterboxTTS)
9. Database tests (may need schema updates)

## Testing the DI Container Itself

Add tests to verify DI container behavior:

```python
def test_di_container_service_lifetimes():
    container = get_container()
    
    # Test singleton behavior
    tts1 = container.resolve("chatterbox_tts_service")
    tts2 = container.resolve("chatterbox_tts_service") 
    assert tts1 is tts2
    
    # Test scoped behavior
    chat1 = container.resolve("chat_service")
    chat2 = container.resolve("chat_service")
    assert chat1 is chat2
    
    container.clear_scoped()
    chat3 = container.resolve("chat_service")
    assert chat1 is not chat3
```

## Benefits After Migration

1. **Cleaner Tests**: Less manual mocking, more focus on business logic
2. **Better Isolation**: True unit tests with injected dependencies
3. **Easier Maintenance**: Changes to service structure don't break all tests
4. **Integration Testing**: Can test real service interactions when needed
5. **Performance**: Faster test execution with proper service lifecycle management

## Checklist for Each Test File

- [ ] Update import paths to new package structure
- [ ] Replace manual service patching with DI container mocks
- [ ] Use test utilities from `tests.test_utils.di_test_helpers`
- [ ] Add tests for new functionality (TTS segmentation, etc.)
- [ ] Verify tests run with `pytest tests/path/to/test.py`
- [ ] Update any hardcoded paths or service names

## Running Tests

After migration:
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/chatapp/routes/test_chat_routes.py

# Run with coverage
pytest --cov=aichat tests/

# Run only integration tests
pytest tests/integration/
```