"""
Test configuration and utilities for VoiceCore AI tests.

Provides common fixtures, test data creation, and cleanup utilities
for property-based and unit tests.
"""

import uuid
import pytest
import asyncio
from typing import Optional
from datetime import datetime

from voicecore.database import get_db_session, set_tenant_context
from voicecore.models import Tenant, Department, Agent, AgentStatus
from voicecore.services.tenant_service import TenantService
from voicecore.logging import get_logger


logger = get_logger(__name__)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


async def create_test_tenant(name: Optional[str] = None) -> uuid.UUID:
    """
    Create a test tenant for testing purposes.
    
    Args:
        name: Optional tenant name, will generate random if not provided
        
    Returns:
        uuid.UUID: Created tenant ID
    """
    if not name:
        name = f"test_tenant_{uuid.uuid4().hex[:8]}"
    
    tenant_service = TenantService()
    
    tenant_data = {
        "name": name,
        "domain": f"{name.lower().replace(' ', '_')}.test.com",
        "settings": {
            "company_name": name,
            "default_language": "en",
            "business_hours": {
                "monday": {"start": "09:00", "end": "17:00"},
                "tuesday": {"start": "09:00", "end": "17:00"},
                "wednesday": {"start": "09:00", "end": "17:00"},
                "thursday": {"start": "09:00", "end": "17:00"},
                "friday": {"start": "09:00", "end": "17:00"},
                "saturday": {"start": "10:00", "end": "14:00"},
                "sunday": {"start": "closed", "end": "closed"}
            },
            "voice_settings": {
                "voice_type": "female",
                "voice_name": "Assistant",
                "language": "en"
            }
        }
    }
    
    try:
        tenant = await tenant_service.create_tenant(tenant_data)
        logger.info(f"Created test tenant: {tenant.id}")
        return tenant.id
    except Exception as e:
        logger.error(f"Failed to create test tenant: {e}")
        raise


async def create_test_department(
    tenant_id: uuid.UUID, 
    name: Optional[str] = None,
    code: Optional[str] = None
) -> uuid.UUID:
    """
    Create a test department for testing purposes.
    
    Args:
        tenant_id: Tenant ID to create department for
        name: Optional department name
        code: Optional department code
        
    Returns:
        uuid.UUID: Created department ID
    """
    if not name:
        name = f"Test Department {uuid.uuid4().hex[:8]}"
    if not code:
        code = f"TD{uuid.uuid4().hex[:4].upper()}"
    
    try:
        async with get_db_session() as session:
            await set_tenant_context(session, str(tenant_id))
            
            department = Department(
                tenant_id=tenant_id,
                name=name,
                code=code,
                description=f"Test department for {name}",
                is_active=True,
                is_default=True,
                max_queue_size=10,
                queue_timeout=300,
                transfer_keywords=["support", "help"],
                business_hours={},
                voicemail_enabled=True,
                priority=1,
                routing_strategy="round_robin",
                settings={}
            )
            
            session.add(department)
            await session.commit()
            
            logger.info(f"Created test department: {department.id}")
            return department.id
            
    except Exception as e:
        logger.error(f"Failed to create test department: {e}")
        raise


async def create_test_agent(
    tenant_id: uuid.UUID,
    department_id: uuid.UUID,
    email: Optional[str] = None,
    name: Optional[str] = None,
    extension: Optional[str] = None
) -> uuid.UUID:
    """
    Create a test agent for testing purposes.
    
    Args:
        tenant_id: Tenant ID
        department_id: Department ID
        email: Optional agent email
        name: Optional agent name
        extension: Optional agent extension
        
    Returns:
        uuid.UUID: Created agent ID
    """
    if not email:
        email = f"test.agent.{uuid.uuid4().hex[:8]}@test.com"
    if not name:
        name = f"Test Agent {uuid.uuid4().hex[:8]}"
    if not extension:
        extension = str(uuid.uuid4().int)[:4]
    
    try:
        async with get_db_session() as session:
            await set_tenant_context(session, str(tenant_id))
            
            agent = Agent(
                tenant_id=tenant_id,
                email=email,
                name=name,
                first_name=name.split()[0],
                last_name=" ".join(name.split()[1:]) if len(name.split()) > 1 else "Agent",
                extension=extension,
                department_id=department_id,
                is_manager=False,
                status=AgentStatus.NOT_AVAILABLE,
                is_active=True,
                max_concurrent_calls=1,
                current_calls=0,
                routing_weight=1,
                auto_answer=False,
                skills=[],
                languages=["en"],
                total_calls_handled=0,
                average_call_duration=0,
                settings={}
            )
            
            session.add(agent)
            await session.commit()
            
            logger.info(f"Created test agent: {agent.id}")
            return agent.id
            
    except Exception as e:
        logger.error(f"Failed to create test agent: {e}")
        raise


async def cleanup_test_data(tenant_id: uuid.UUID):
    """
    Clean up test data for a tenant.
    
    Args:
        tenant_id: Tenant ID to clean up
    """
    try:
        tenant_service = TenantService()
        await tenant_service.delete_tenant(tenant_id)
        logger.info(f"Cleaned up test tenant: {tenant_id}")
    except Exception as e:
        logger.warning(f"Failed to clean up test tenant {tenant_id}: {e}")


@pytest.fixture
async def test_tenant():
    """Fixture that provides a test tenant and cleans up after test."""
    tenant_id = await create_test_tenant()
    yield tenant_id
    await cleanup_test_data(tenant_id)


@pytest.fixture
async def test_department(test_tenant):
    """Fixture that provides a test department."""
    department_id = await create_test_department(test_tenant)
    yield department_id


@pytest.fixture
async def test_agent(test_tenant, test_department):
    """Fixture that provides a test agent."""
    agent_id = await create_test_agent(test_tenant, test_department)
    yield agent_id


# Property-based testing utilities

def generate_phone_number() -> str:
    """Generate a valid phone number for testing."""
    import random
    return f"+1{random.randint(2000000000, 9999999999)}"


def generate_extension() -> str:
    """Generate a valid extension for testing."""
    import random
    return str(random.randint(1000, 9999))


def generate_email() -> str:
    """Generate a valid email for testing."""
    import random
    import string
    username = ''.join(random.choices(string.ascii_lowercase, k=8))
    domain = ''.join(random.choices(string.ascii_lowercase, k=5))
    return f"{username}@{domain}.test"


# Test data validation utilities

def is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID."""
    try:
        uuid.UUID(value)
        return True
    except (ValueError, TypeError):
        return False


def is_valid_email(email: str) -> bool:
    """Check if a string is a valid email address."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def is_valid_phone_number(phone: str) -> bool:
    """Check if a string is a valid phone number."""
    import re
    # Simple validation for test purposes
    pattern = r'^\+?[1-9]\d{1,14}$'
    return re.match(pattern, phone.replace(' ', '').replace('-', '')) is not None


# Async test utilities

def run_async_test(coro):
    """Run an async test function."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


class AsyncTestCase:
    """Base class for async test cases."""
    
    def setUp(self):
        """Set up async test case."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """Tear down async test case."""
        self.loop.close()
    
    def run_async(self, coro):
        """Run an async coroutine in the test loop."""
        return self.loop.run_until_complete(coro)



# Additional fixtures for call flow testing

@pytest.fixture
def db():
    """Provide database session for tests"""
    from voicecore.database import SessionLocal
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
async def test_tenant2(db):
    """Second test tenant for multi-tenant testing"""
    from voicecore.models.tenant import Tenant
    
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Test Tenant 2",
        domain="tenant2.test.com",
        is_active=True,
        settings={}
    )
    db.add(tenant)
    db.commit()
    
    yield tenant
    
    # Cleanup
    db.delete(tenant)
    db.commit()


@pytest.fixture
def mock_twilio_client():
    """Mock Twilio client for testing"""
    from unittest.mock import Mock
    
    client = Mock()
    client.calls = Mock()
    client.calls.create = Mock()
    client.calls.return_value.fetch = Mock()
    client.calls.return_value.recordings = Mock()
    client.recordings = Mock()
    
    return client


@pytest.fixture
def mock_openai_service():
    """Mock OpenAI service for testing"""
    from unittest.mock import AsyncMock
    
    service = AsyncMock()
    service.generate_response = AsyncMock(return_value={
        'response': 'Test AI response',
        'intent': 'test_intent',
        'confidence': 0.95,
        'sentiment': 'neutral'
    })
    
    return service


@pytest.fixture
async def test_call(db, test_tenant):
    """Create a test call"""
    from voicecore.models.call import Call, CallStatus
    
    call = Call(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        from_number="+1234567890",
        to_number="+0987654321",
        status=CallStatus.INITIATED,
        direction='inbound'
    )
    db.add(call)
    db.commit()
    
    yield call
    
    # Cleanup
    db.delete(call)
    db.commit()


@pytest.fixture
async def test_agent_available(db, test_tenant):
    """Create an available test agent"""
    from voicecore.models.agent import Agent, AgentStatus
    
    agent = Agent(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        name="Test Agent",
        email="test@example.com",
        status=AgentStatus.AVAILABLE,
        is_active=True
    )
    db.add(agent)
    db.commit()
    
    yield agent
    
    # Cleanup
    db.delete(agent)
    db.commit()


@pytest.fixture
def sample_call_data():
    """Sample call data for testing"""
    return {
        'caller_number': '+1234567890',
        'business_number': '+0987654321',
        'call_sid': f"CA{uuid.uuid4().hex[:32]}",
        'direction': 'inbound'
    }


@pytest.fixture
def sample_ai_response():
    """Sample AI response for testing"""
    return {
        'response': 'Hello! How can I help you today?',
        'intent': 'greeting',
        'confidence': 0.95,
        'sentiment': 'positive',
        'requires_escalation': False
    }


@pytest.fixture
def sample_customer_message():
    """Sample customer message for testing"""
    return {
        'text': 'What are your business hours?',
        'intent': 'business_hours_inquiry',
        'sentiment': 'neutral'
    }


# Utility functions for call testing

def create_mock_twilio_call(call_sid=None, status='in-progress'):
    """Create a mock Twilio call object"""
    from unittest.mock import Mock
    
    if not call_sid:
        call_sid = f"CA{uuid.uuid4().hex[:32]}"
    
    mock_call = Mock()
    mock_call.sid = call_sid
    mock_call.status = status
    mock_call.from_ = '+1234567890'
    mock_call.to = '+0987654321'
    mock_call.duration = 0
    
    return mock_call


def create_mock_recording(recording_sid=None, status='completed'):
    """Create a mock Twilio recording object"""
    from unittest.mock import Mock
    
    if not recording_sid:
        recording_sid = f"RE{uuid.uuid4().hex[:32]}"
    
    mock_recording = Mock()
    mock_recording.sid = recording_sid
    mock_recording.status = status
    mock_recording.duration = 120
    mock_recording.uri = f"/Recordings/{recording_sid}"
    
    return mock_recording


# Assertion helpers

def assert_call_status(call, expected_status):
    """Assert call has expected status"""
    from voicecore.models.call import CallStatus
    
    if isinstance(expected_status, str):
        expected_status = CallStatus[expected_status.upper()]
    
    assert call.status == expected_status, \
        f"Expected call status {expected_status}, got {call.status}"


def assert_agent_status(agent, expected_status):
    """Assert agent has expected status"""
    from voicecore.models.agent import AgentStatus
    
    if isinstance(expected_status, str):
        expected_status = AgentStatus[expected_status.upper()]
    
    assert agent.status == expected_status, \
        f"Expected agent status {expected_status}, got {agent.status}"


def assert_event_exists(events, event_type):
    """Assert event of given type exists in event list"""
    event_types = [e.event_type for e in events]
    assert event_type in event_types, \
        f"Expected event type {event_type} not found in {event_types}"


# Performance testing utilities

class CallLoadGenerator:
    """Generate load for call testing"""
    
    def __init__(self, num_calls=10):
        self.num_calls = num_calls
        self.calls = []
    
    async def generate_calls(self):
        """Generate multiple concurrent calls"""
        tasks = []
        for i in range(self.num_calls):
            task = self.create_call(i)
            tasks.append(task)
        
        self.calls = await asyncio.gather(*tasks)
        return self.calls
    
    async def create_call(self, index):
        """Create a single call"""
        # Implementation would create actual call
        await asyncio.sleep(0.1)  # Simulate call creation
        return {
            'id': uuid.uuid4(),
            'index': index,
            'status': 'created'
        }


# Cleanup utilities

@pytest.fixture(autouse=True)
async def cleanup_after_test(db):
    """Automatically cleanup after each test"""
    yield
    
    # Cleanup any test data
    try:
        from voicecore.models.call import Call
        from voicecore.models.event_store import EventStore
        
        # Delete test calls
        db.query(Call).filter(
            Call.from_number.like('+1234%')
        ).delete()
        
        # Commit changes
        db.commit()
    except Exception as e:
        logger.warning(f"Cleanup failed: {e}")
        db.rollback()
