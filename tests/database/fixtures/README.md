# Test Database Fixtures

This directory contains JSON files with sample data for test database population.

## Files

### `characters.json`
Contains sample character data with:
- Character profiles and personalities
- Avatar URLs
- Character IDs for foreign key relationships

### `chat_logs.json`
Contains sample chat conversations with:
- User messages and character responses
- Emotion data
- LLM metadata (model, temperature, tokens)
- Character associations

### `training_data.json`
Contains sample training audio data with:
- Audio filenames and transcripts
- Speaker associations
- Quality ratings and duration
- Emotion labels

### `voice_models.json`
Contains sample voice model data with:
- Model paths and training status
- Character associations
- Training progress (epochs, loss)
- Model names and versions

### `event_logs.json`
Contains sample system events with:
- Event types and messages
- Severity levels (INFO, ERROR, etc.)
- Source services
- Event metadata

## Usage

### Loading Individual Fixtures
```python
from database.fixtures import load_fixture

characters = load_fixture("characters")
chat_logs = load_fixture("chat_logs")
```

### Loading All Fixtures
```python
from database.fixtures import load_all_fixtures

all_data = load_all_fixtures()
```

### Convenience Functions
```python
from database.fixtures import (
    get_sample_characters,
    get_sample_chat_logs,
    get_sample_training_data,
    get_sample_voice_models,
    get_sample_event_logs
)

characters = get_sample_characters()
```

## Data Structure

All JSON files contain arrays of objects with consistent field structures:

- **IDs**: Integer primary keys for database insertion
- **Relationships**: Foreign key references between entities
- **Metadata**: Nested objects for complex data (automatically JSON-serialized)
- **Timestamps**: Generated at insertion time, not stored in JSON

## Benefits

1. **Easy Maintenance**: Human-readable JSON format
2. **Version Control**: Changes to test data are clearly tracked
3. **Flexibility**: Easy to add/remove/modify sample data
4. **Validation**: JSON structure prevents malformed data
5. **Reusability**: Same data can be used across different test scenarios
6. **Documentation**: Self-documenting with clear field names and values

## Adding New Fixtures

1. Create a new JSON file with appropriate sample data
2. Add a loader function in `__init__.py`
3. Update the `load_all_fixtures()` function
4. Add the fixture to exports in the parent `__init__.py`

## Data Relationships

The fixtures maintain referential integrity:
- `chat_logs.character_id` references `characters.id`
- `voice_models.character_id` references `characters.id`
- `training_data.speaker` matches `characters.name`