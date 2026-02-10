# VoiceCore AI - Testing Guide

## Overview

This guide covers how to test the complete call flow functionality of VoiceCore AI, including AI interactions, agent escalations, and event sourcing.

## Prerequisites

### 1. Install Dependencies

```bash
pip install pytest pytest-asyncio colorama
```

### 2. Setup Environment

Ensure your `.env` file is configured with:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost/voicecore

# Twilio (for call handling)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# OpenAI (for AI responses)
OPENAI_API_KEY=your_openai_key

# Redis (for caching)
REDIS_URL=redis://localhost:6379
```

### 3. Initialize Database

```bash
# Run migrations
alembic upgrade head

# Create test tenant
python scripts/init_project.py
```

## Running Tests

### Option 1: Run All Tests (Recommended)

```bash
python run_call_tests.py
```

This will run all call flow tests in sequence with colored output and progress tracking.

### Option 2: Run Specific Test Categories

#### Inbound Call Tests
```bash
pytest tests/test_call_flow_e2e.py::TestInboundCallFlow -v -s
```

#### Outbound Call Tests
```bash
pytest tests/test_call_flow_e2e.py::TestOutboundCallFlow -v -s
```

#### AI Conversation Tests
```bash
pytest tests/test_call_flow_e2e.py::TestAIConversationFlow -v -s
```

#### Call Recording Tests
```bash
pytest tests/test_call_flow_e2e.py::TestCallRecordingFlow -v -s
```

### Option 3: Run Individual Tests

```bash
# Test complete inbound call with AI
pytest tests/test_call_flow_e2e.py::TestInboundCallFlow::test_complete_inbound_call_with_ai -v -s

# Test call escalation
pytest tests/test_call_flow_e2e.py::TestInboundCallFlow::test_call_escalation_to_human_agent -v -s

# Test sentiment detection
pytest tests/test_call_flow_e2e.py::TestAIConversationFlow::test_ai_sentiment_detection -v -s
```

## Interactive Demo

For a visual demonstration of call scenarios:

```bash
python examples/interactive_call_demo.py
```

This provides an interactive menu with 5 realistic scenarios:

1. **Simple Inquiry** - Customer asks about business hours
2. **Complex Escalation** - Enterprise contract modification
3. **Frustrated Customer** - Negative sentiment detection and escalation
4. **Multilingual Support** - Spanish language detection and switching
5. **VIP Customer** - Priority routing for high-value customers

## Test Scenarios Explained

### 1. Complete Inbound Call with AI

**What it tests:**
- Twilio webhook handling
- Call routing to AI
- AI greeting generation
- Customer question processing
- AI response generation
- Call completion
- Event sourcing integration

**Expected Flow:**
```
Customer calls → Twilio webhook → Route to AI → AI greets → 
Customer asks → AI responds → Call ends → Events stored
```

**Success Criteria:**
- Call created with correct status
- AI generates appropriate responses
- All events stored in event store
- Call marked as completed

### 2. Call Escalation to Human Agent

**What it tests:**
- AI handling initial interaction
- Complex question detection
- Escalation decision making
- Agent assignment
- Call transfer
- Agent status updates

**Expected Flow:**
```
Call starts with AI → Customer asks complex question → 
AI detects complexity → Transfer to agent → Agent handles → 
Call ends
```

**Success Criteria:**
- AI correctly identifies need for escalation
- Available agent found and assigned
- Call successfully transferred
- Agent status updated (available → on_call → available)
- Transfer event recorded

### 3. Agent Initiated Outbound Call

**What it tests:**
- Outbound call initiation
- Agent status management
- Call connection handling
- Call notes functionality

**Expected Flow:**
```
Agent initiates call → System dials customer → 
Customer answers → Conversation → Call ends
```

**Success Criteria:**
- Outbound call created
- Agent status updated to on_call
- Call connects successfully
- Notes can be added
- Agent returns to available status

### 4. Multi-Turn AI Conversation

**What it tests:**
- Context maintenance across turns
- Intent recognition
- Entity extraction
- Sentiment analysis
- Conversation history

**Expected Flow:**
```
AI greets → Customer asks → AI responds → 
Customer follows up → AI maintains context → 
Multiple turns → Resolution
```

**Success Criteria:**
- AI maintains conversation context
- Intents correctly identified
- Entities extracted from messages
- Sentiment tracked throughout
- Conversation history preserved

### 5. AI Sentiment Detection

**What it tests:**
- Negative sentiment detection
- Urgency assessment
- Automatic escalation
- Priority routing

**Expected Flow:**
```
Customer expresses frustration → AI detects negative sentiment → 
Immediate escalation triggered → Supervisor assigned → 
Issue resolved
```

**Success Criteria:**
- Negative sentiment detected (score < -0.5)
- Escalation triggered automatically
- High urgency flag set
- Supervisor/manager assigned
- Escalation event recorded

### 6. Call Recording Lifecycle

**What it tests:**
- Recording start/stop
- Recording metadata storage
- Event tracking
- Recording retrieval

**Expected Flow:**
```
Call starts → Recording starts → Call proceeds → 
Recording stops → Recording stored → Accessible
```

**Success Criteria:**
- Recording starts automatically
- Recording SID generated
- Duration tracked
- Recording stopped on call end
- Start/stop events recorded

## Event Sourcing Verification

All tests verify that events are properly stored:

### Expected Events for Complete Call:

1. `CallInitiated` - Call starts
2. `CallConnected` - Call connects
3. `AIResponseGenerated` - AI generates response
4. `AISentimentDetected` - Sentiment analyzed
5. `AIIntentRecognized` - Intent identified
6. `CallTransferred` - (if escalated)
7. `AgentAssignedToCall` - (if escalated)
8. `CallRecordingStarted` - Recording begins
9. `CallRecordingStopped` - Recording ends
10. `CallEnded` - Call completes

### Verify Events:

```python
from voicecore.services.event_sourcing_service import EventSourcingService

service = EventSourcingService(db)
events = await service.get_events(call_id)

# Check event types
event_types = [e.event_type for e in events]
assert 'CallInitiated' in event_types
assert 'CallEnded' in event_types
```

## Troubleshooting

### Tests Fail with Database Error

```bash
# Reset database
alembic downgrade base
alembic upgrade head

# Recreate test data
python scripts/init_project.py
```

### Tests Fail with Import Error

```bash
# Install missing dependencies
pip install -r requirements.txt

# Verify installation
python -c "import voicecore; print('OK')"
```

### Tests Timeout

```bash
# Increase timeout in pytest.ini
[pytest]
asyncio_mode = auto
timeout = 300
```

### Mock Services Not Working

Ensure you're using the correct mock patches:

```python
from unittest.mock import patch, Mock

with patch.object(twilio_service, 'client') as mock_client:
    # Your test code
    pass
```

## Performance Testing

### Load Testing

```bash
# Install locust
pip install locust

# Run load test
locust -f tests/load_test_calls.py --host=http://localhost:8000
```

### Stress Testing

```bash
# Test concurrent calls
pytest tests/test_call_flow_e2e.py -n 10  # 10 parallel workers
```

## Continuous Integration

### GitHub Actions

```yaml
name: Call Flow Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio
      
      - name: Run migrations
        run: alembic upgrade head
      
      - name: Run tests
        run: python run_call_tests.py
```

## Best Practices

### 1. Test Isolation

Each test should be independent:

```python
@pytest.fixture(autouse=True)
async def cleanup(db):
    yield
    # Cleanup after each test
    db.query(Call).delete()
    db.commit()
```

### 2. Use Fixtures

Create reusable test data:

```python
@pytest.fixture
def test_agent(db, test_tenant):
    agent = Agent(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        name="Test Agent",
        status=AgentStatus.AVAILABLE
    )
    db.add(agent)
    db.commit()
    return agent
```

### 3. Mock External Services

Always mock Twilio, OpenAI, etc.:

```python
@patch('voicecore.services.twilio_service.TwilioService.client')
@patch('voicecore.services.openai_service.OpenAIService.generate_response')
async def test_call(mock_openai, mock_twilio):
    # Test code
    pass
```

### 4. Verify Events

Always check event sourcing:

```python
events = await event_service.get_events(call.id)
assert len(events) > 0
assert events[0].event_type == EventTypes.CALL_INITIATED
```

## Reporting

### Generate Test Report

```bash
pytest tests/test_call_flow_e2e.py --html=report.html --self-contained-html
```

### Coverage Report

```bash
pytest tests/test_call_flow_e2e.py --cov=voicecore --cov-report=html
```

## Next Steps

After successful testing:

1. Review test coverage
2. Add more edge case tests
3. Implement load testing
4. Set up CI/CD pipeline
5. Monitor production metrics

## Support

For issues or questions:
- Check logs: `tail -f logs/voicecore.log`
- Review events: Query `event_store` table
- Contact: support@voicecore.ai
