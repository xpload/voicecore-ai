# VoiceCore AI - Test Suite

## Overview

Comprehensive test suite for VoiceCore AI's call handling system, covering end-to-end call flows, AI interactions, agent management, and event sourcing.

## Quick Start

```bash
# 1. Check if system is ready
python check_test_readiness.py

# 2. Run all tests
python run_call_tests.py

# 3. Or run specific tests
pytest tests/test_call_flow_e2e.py -v -s

# 4. Try interactive demo
python examples/interactive_call_demo.py
```

## Test Structure

```
tests/
├── conftest.py                    # Test fixtures and utilities
├── test_call_flow_e2e.py         # End-to-end call flow tests
├── test_event_sourcing.py        # Event sourcing tests
├── test_ai_properties.py         # AI service tests
├── test_agent_properties.py      # Agent management tests
├── test_call_routing_properties.py # Call routing tests
└── integration/                   # Integration tests
    ├── test_end_to_end_call_flows.py
    ├── test_multitenant_isolation.py
    └── test_external_service_integrations.py
```

## Test Categories

### 1. End-to-End Tests (`test_call_flow_e2e.py`)

Complete call lifecycle testing:

- **Inbound Calls**
  - AI handling
  - Agent escalation
  - Event tracking

- **Outbound Calls**
  - Agent initiation
  - Status management
  - Call notes

- **AI Conversations**
  - Multi-turn dialogues
  - Context maintenance
  - Sentiment detection

- **Call Recording**
  - Start/stop lifecycle
  - Metadata storage
  - Event integration

### 2. Event Sourcing Tests (`test_event_sourcing.py`)

Event store functionality:

- Event storage
- Event retrieval
- Event replay
- Snapshots
- Read models
- Tenant isolation

### 3. Property-Based Tests

Automated edge case discovery:

- `test_ai_properties.py` - AI service properties
- `test_agent_properties.py` - Agent management properties
- `test_call_routing_properties.py` - Routing logic properties

### 4. Integration Tests

Multi-service coordination:

- End-to-end call flows
- Multi-tenant isolation
- External service integration

## Running Tests

### All Tests

```bash
# Using test runner (recommended)
python run_call_tests.py

# Using pytest directly
pytest tests/ -v
```

### Specific Test File

```bash
pytest tests/test_call_flow_e2e.py -v -s
```

### Specific Test Class

```bash
pytest tests/test_call_flow_e2e.py::TestInboundCallFlow -v -s
```

### Specific Test Method

```bash
pytest tests/test_call_flow_e2e.py::TestInboundCallFlow::test_complete_inbound_call_with_ai -v -s
```

### With Coverage

```bash
pytest tests/ --cov=voicecore --cov-report=html
```

### Parallel Execution

```bash
pytest tests/ -n 4  # 4 parallel workers
```

## Test Markers

Use markers to run specific test categories:

```bash
# Run only call flow tests
pytest -m call_flow

# Run only AI tests
pytest -m ai

# Run only integration tests
pytest -m integration

# Run only fast tests (exclude slow)
pytest -m "not slow"
```

Available markers:
- `call_flow` - Call flow tests
- `ai` - AI-related tests
- `integration` - Integration tests
- `unit` - Unit tests
- `slow` - Slow-running tests
- `e2e` - End-to-end tests
- `event_sourcing` - Event sourcing tests

## Test Fixtures

### Database Fixtures

```python
@pytest.fixture
def db():
    """Database session"""
    
@pytest.fixture
async def test_tenant():
    """Test tenant with cleanup"""
    
@pytest.fixture
async def test_agent():
    """Test agent"""
```

### Mock Fixtures

```python
@pytest.fixture
def mock_twilio_client():
    """Mock Twilio client"""
    
@pytest.fixture
def mock_openai_service():
    """Mock OpenAI service"""
```

### Data Fixtures

```python
@pytest.fixture
def sample_call_data():
    """Sample call data"""
    
@pytest.fixture
def sample_ai_response():
    """Sample AI response"""
```

## Writing New Tests

### Test Template

```python
import pytest
from voicecore.services import YourService

class TestYourFeature:
    """Test your feature"""
    
    @pytest.mark.asyncio
    async def test_your_scenario(self, db, test_tenant):
        """
        Test Case: Description
        
        Flow:
        1. Step 1
        2. Step 2
        3. Step 3
        """
        # Arrange
        service = YourService(db)
        
        # Act
        result = await service.your_method()
        
        # Assert
        assert result is not None
        assert result.status == "expected"
```

### Best Practices

1. **Use descriptive names**
   ```python
   def test_ai_escalates_when_confidence_low()  # Good
   def test_ai_1()  # Bad
   ```

2. **Follow AAA pattern**
   - Arrange: Setup test data
   - Act: Execute the code
   - Assert: Verify results

3. **Test one thing**
   - Each test should verify one behavior
   - Split complex tests into multiple tests

4. **Use fixtures**
   - Reuse common setup code
   - Keep tests DRY

5. **Mock external services**
   - Don't call real Twilio/OpenAI
   - Use mocks for predictable tests

6. **Verify events**
   - Check event sourcing integration
   - Verify audit trail

## Debugging Tests

### Run with verbose output

```bash
pytest tests/test_call_flow_e2e.py -v -s
```

### Run with pdb debugger

```bash
pytest tests/test_call_flow_e2e.py --pdb
```

### Run specific test with print statements

```bash
pytest tests/test_call_flow_e2e.py::test_name -v -s
```

### Check test collection

```bash
pytest --collect-only
```

## Common Issues

### Import Errors

```bash
# Add project root to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or install in development mode
pip install -e .
```

### Database Errors

```bash
# Reset database
alembic downgrade base
alembic upgrade head

# Recreate test data
python scripts/init_project.py
```

### Async Errors

Ensure `pytest-asyncio` is installed:
```bash
pip install pytest-asyncio
```

### Mock Errors

Check mock patches are correct:
```python
with patch.object(service, 'method') as mock:
    mock.return_value = expected_value
```

## Performance

### Test Execution Times

- Unit tests: < 1 second each
- Integration tests: 1-5 seconds each
- E2E tests: 5-30 seconds each
- Full suite: ~2-3 minutes

### Optimization Tips

1. Use fixtures for expensive setup
2. Run tests in parallel (`-n` flag)
3. Use markers to run subsets
4. Mock external services
5. Use in-memory database for unit tests

## CI/CD Integration

### GitHub Actions

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run tests
        run: python run_call_tests.py
```

## Test Data

### Sample Data

Test data is automatically created and cleaned up:

- Test tenants
- Test agents
- Test calls
- Test events

### Cleanup

Automatic cleanup after each test:
- Database transactions rolled back
- Test data deleted
- Mocks reset

## Documentation

- [Testing Guide](../TESTING_GUIDE.md) - Comprehensive testing guide
- [Call Testing Summary](../CALL_TESTING_SUMMARY.md) - Implementation summary
- [Interactive Demo](../examples/interactive_call_demo.py) - Visual demonstrations

## Support

For issues or questions:
- Check test output for error messages
- Review logs: `tail -f logs/voicecore.log`
- Check database: Query `event_store` table
- Run readiness check: `python check_test_readiness.py`

## Contributing

When adding new tests:

1. Follow existing patterns
2. Add appropriate markers
3. Include docstrings
4. Update this README
5. Ensure tests pass locally
6. Check code coverage

## License

Copyright © 2026 VoiceCore AI. All rights reserved.
