# VTuber AI Testing Suite

This directory contains a comprehensive testing suite for the VTuber AI system, organized by functionality and purpose. All testing scripts have been moved from the root directory to this organized structure.

## Directory Structure

```
tests/
├── README.md                    # This file - comprehensive testing guide
├── conftest.py                  # Global test configuration
├── test_api_endpoints.py        # Core API endpoint tests
│
├── chatapp/                     # Chat application unit tests
│   ├── conftest.py             # Chat app test configuration  
│   ├── routes/                 # API route tests
│   ├── services/              # Service layer tests
│   └── models/                # Model and DAO tests
│
├── database/                    # Database testing utilities
│   ├── fixtures/              # Test data fixtures
│   ├── setup.py              # Database setup and sample data
│   ├── manager.py            # Test database operations
│   └── test_data.db          # SQLite test database
│
├── frontend/                    # GUI and frontend tests (MOVED HERE)
│   ├── test_frontend_routes.py    # API integration from frontend perspective
│   ├── test_gui_integration.py    # Complete GUI component integration  
│   ├── test_gui_routes.py         # GUI route handling tests
│   └── test_gui_voice.py          # Voice interface testing
│
├── integration/                 # Cross-component integration tests
│   └── test_api_recreated.py     # Comprehensive API integration
│
├── system/                      # System-level functionality tests (NEW)
│   ├── test_audio_system.py      # Audio system integration
│   └── audio_system_test_original.py  # Original audio testing script
│
├── voice/                       # Voice processing tests (MOVED HERE)
│   ├── speech_test.py            # Speech processing validation
│   ├── streaming_test.py         # Real-time audio streaming
│   └── test_speech_pipeline.py   # Complete speech pipeline
│
├── startup/                     # Application initialization tests (MOVED HERE) 
│   ├── test_frontend_backend_startup.py  # Startup coordination
│   └── test_improved_startup.py          # Enhanced startup procedures
│
├── debug/                       # Debugging and troubleshooting (MOVED HERE)
│   ├── debug_backend_crash.py    # Backend crash investigation
│   └── debug_frontend_startup.py # Frontend startup debugging
│
├── interactive/                 # Manual testing tools (MOVED HERE)
│   └── interactive_voice_demo.py # Interactive voice demo
│
├── examples/                    # Test examples and templates
│   └── modern_test_example.py   # Modern testing patterns
│
├── test_utils/                  # Testing utilities and helpers
│   └── di_test_helpers.py      # Dependency injection helpers
│
└── reports/                     # Test execution reports
    ├── FINAL_SUCCESS_REPORT.md        # Overall success summary
    ├── FIXES_APPLIED_REPORT.md        # Issues resolved  
    └── frontend_integration_report.json # Detailed frontend results
```

## 📂 Test Categories (Organized from Root Directory)

### 🎨 Frontend Tests (`tests/frontend/`) - **MOVED FROM ROOT**
- **`test_frontend_routes.py`** - API integration testing from frontend perspective (100% success rate)
- **`test_gui_integration.py`** - Complete GUI component integration tests
- **`test_gui_routes.py`** - GUI route handling and navigation tests  
- **`test_gui_voice.py`** - Voice interface and audio controls testing

### 🔊 Voice & Audio Tests (`tests/voice/`) - **MOVED FROM ROOT**
- **`speech_test.py`** - Speech processing and recognition validation
- **`streaming_test.py`** - Real-time audio streaming functionality
- **`test_speech_pipeline.py`** - Complete speech processing pipeline tests

### 🚀 Startup Tests (`tests/startup/`) - **MOVED FROM ROOT**
- **`test_frontend_backend_startup.py`** - Frontend/backend startup coordination
- **`test_improved_startup.py`** - Enhanced startup procedure validation

### 🔧 Debug Tools (`tests/debug/`) - **MOVED FROM ROOT**
- **`debug_backend_crash.py`** - Backend crash investigation and diagnostics
- **`debug_frontend_startup.py`** - Frontend startup debugging utilities

### 🖥️ System Tests (`tests/system/`) - **NEWLY ORGANIZED**
- **`test_audio_system.py`** - Audio system integration and hardware tests
- **`audio_system_test_original.py`** - Original comprehensive audio testing

### 🎭 Interactive Tools (`tests/interactive/`) - **MOVED FROM ROOT**
- **`interactive_voice_demo.py`** - Interactive voice functionality demonstration

### 🧪 Core Test Categories (Existing Structure)

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

## 🚀 Running Tests

### Quick Test Commands
```bash
# Run all tests
pytest tests/

# Run specific test categories  
pytest tests/frontend/          # Frontend GUI tests
pytest tests/voice/            # Voice processing tests
pytest tests/system/           # System integration tests
pytest tests/startup/          # Startup procedure tests
pytest tests/chatapp/          # Chat app unit tests
pytest tests/integration/     # Cross-component tests

# Run with different output levels
pytest tests/ -v              # Verbose output
pytest tests/ -q              # Quiet output

# Run specific test files
pytest tests/frontend/test_gui_integration.py
pytest tests/voice/test_speech_pipeline.py
pytest tests/system/test_audio_system.py
```

### Interactive & Debug Testing
```bash
# Run interactive demonstrations
python tests/interactive/interactive_voice_demo.py

# Debug specific issues
python tests/debug/debug_backend_crash.py
python tests/debug/debug_frontend_startup.py

# Test startup procedures  
python tests/startup/test_frontend_backend_startup.py
python tests/startup/test_improved_startup.py

# Voice and audio testing
python tests/voice/speech_test.py
python tests/voice/streaming_test.py
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