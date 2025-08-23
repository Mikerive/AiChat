# Complex Test Suite Archive

This directory contains the comprehensive test suite with mocking infrastructure that was developed during the testing migration phase.

## Structure

### `chatapp/`
Application-level tests with full mocking:
- Route testing with FastAPI TestClient
- Service testing with AsyncMock
- Model validation testing

### `database/`
Database testing infrastructure:
- Test database fixtures and setup
- Mock data fixtures in JSON format
- Database operation testing utilities

### `frontend/`
Frontend GUI testing:
- Tkinter GUI integration tests
- WebSocket handler testing
- Frontend route validation

### `integration/`
End-to-end integration tests:
- Full API integration testing
- Service interaction testing

### `system/`
System-level testing:
- Audio system testing
- Hardware integration testing

### `voice/`
Voice processing pipeline tests:
- Speech-to-text testing
- Text-to-speech testing
- Audio streaming tests

## Usage Notes

These tests use extensive mocking and require the complex test fixtures defined in the various conftest.py files throughout the structure.

**Current Status**: These tests are archived. The main test suite in `/tests/` uses real functionality without mocking.

To run these archived tests (if needed):
```bash
cd scripts/tests
python -m pytest chatapp/ -v
python -m pytest integration/ -v
```

## Migration Context

These tests were created during a comprehensive testing modernization effort but were later simplified based on the principle of testing real functionality instead of mock behavior.

The current active test suite is in `/tests/` and follows the "no mocking" principle for more reliable integration testing.