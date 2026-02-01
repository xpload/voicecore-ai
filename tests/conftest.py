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