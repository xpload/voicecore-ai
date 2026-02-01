#!/usr/bin/env python3
"""
VoiceCore AI Project Initialization Script.

This script sets up the development environment and initializes
the database with proper schema and sample data.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from voicecore.config import settings
from voicecore.database import init_database, get_db_session
from voicecore.logging import configure_logging, get_logger
from voicecore.models import Tenant, TenantSettings, Department, Agent


# Configure logging
configure_logging()
logger = get_logger(__name__)


async def create_sample_tenant():
    """Create a sample tenant for development and testing."""
    try:
        async with get_db_session() as session:
            # Check if sample tenant already exists
            existing_tenant = await session.execute(
                "SELECT id FROM tenants WHERE name = 'Sample Company' LIMIT 1"
            )
            
            if existing_tenant.fetchone():
                logger.info("Sample tenant already exists, skipping creation")
                return
            
            # Create sample tenant
            tenant = Tenant(
                name="Sample Company",
                subdomain="sample",
                is_active=True,
                plan_type="enterprise",
                contact_email="admin@sample.com",
                monthly_credit_limit=5000,
                current_usage=0,
                settings={
                    "welcome_message": "Thank you for calling Sample Company. How may I assist you today?",
                    "business_hours": "9:00 AM - 5:00 PM EST",
                    "timezone": "America/New_York"
                },
                twilio_phone_number="+15551234567"
            )
            
            session.add(tenant)
            await session.flush()  # Get the tenant ID
            
            # Create tenant settings
            tenant_settings = TenantSettings(
                tenant_id=tenant.id,
                ai_name="Sofia",
                ai_gender="female",
                ai_voice_id="alloy",
                ai_personality="Professional, friendly, and helpful virtual receptionist",
                company_description="Sample Company provides excellent customer service and support",
                company_services=["Customer Support", "Sales", "Technical Support"],
                max_transfer_attempts=3,
                default_department="customer_service",
                business_hours_start="09:00",
                business_hours_end="17:00",
                timezone="America/New_York",
                business_days=["monday", "tuesday", "wednesday", "thursday", "friday"],
                enable_spam_detection=True,
                enable_call_recording=True,
                enable_transcription=True,
                enable_emotion_detection=False,
                enable_vip_handling=True,
                primary_language="auto",
                supported_languages=["en", "es"],
                welcome_message="Hello! Thank you for calling Sample Company. I'm Sofia, your AI assistant. How may I help you today?",
                afterhours_message="Thank you for calling Sample Company. We are currently closed. Please leave a message or call back during business hours.",
                transfer_rules=[
                    {
                        "keywords": ["billing", "payment", "invoice"],
                        "department": "accounting",
                        "priority": 1
                    },
                    {
                        "keywords": ["technical", "support", "help"],
                        "department": "technical_support",
                        "priority": 1
                    },
                    {
                        "keywords": ["sales", "purchase", "buy"],
                        "department": "sales",
                        "priority": 1
                    }
                ],
                spam_keywords=["insurance", "warranty", "loan", "debt", "credit card"],
                vip_phone_numbers=["+15559876543", "+15555551234"]
            )
            
            session.add(tenant_settings)
            
            # Create sample departments
            departments = [
                Department(
                    tenant_id=tenant.id,
                    name="Customer Service",
                    code="CS",
                    description="General customer service and support",
                    is_active=True,
                    is_default=True,
                    max_queue_size=10,
                    queue_timeout=300,
                    transfer_keywords=["help", "support", "service"],
                    priority=1,
                    routing_strategy="round_robin"
                ),
                Department(
                    tenant_id=tenant.id,
                    name="Sales",
                    code="SALES",
                    description="Sales and new customer inquiries",
                    is_active=True,
                    is_default=False,
                    max_queue_size=5,
                    queue_timeout=180,
                    transfer_keywords=["sales", "buy", "purchase", "pricing"],
                    priority=2,
                    routing_strategy="skills_based"
                ),
                Department(
                    tenant_id=tenant.id,
                    name="Technical Support",
                    code="TECH",
                    description="Technical support and troubleshooting",
                    is_active=True,
                    is_default=False,
                    max_queue_size=8,
                    queue_timeout=600,
                    transfer_keywords=["technical", "tech", "bug", "error"],
                    priority=1,
                    routing_strategy="skills_based"
                )
            ]
            
            for dept in departments:
                session.add(dept)
            
            await session.flush()  # Get department IDs
            
            # Create sample agents
            cs_dept = next(d for d in departments if d.code == "CS")
            sales_dept = next(d for d in departments if d.code == "SALES")
            tech_dept = next(d for d in departments if d.code == "TECH")
            
            agents = [
                Agent(
                    tenant_id=tenant.id,
                    email="john.manager@sample.com",
                    name="John Smith",
                    first_name="John",
                    last_name="Smith",
                    extension="101",
                    department_id=cs_dept.id,
                    is_manager=True,
                    status="not_available",
                    is_active=True,
                    max_concurrent_calls=2,
                    skills=["customer_service", "management"],
                    languages=["en", "es"]
                ),
                Agent(
                    tenant_id=tenant.id,
                    email="sarah.agent@sample.com",
                    name="Sarah Johnson",
                    first_name="Sarah",
                    last_name="Johnson",
                    extension="102",
                    department_id=cs_dept.id,
                    is_manager=False,
                    status="not_available",
                    is_active=True,
                    max_concurrent_calls=1,
                    skills=["customer_service"],
                    languages=["en"]
                ),
                Agent(
                    tenant_id=tenant.id,
                    email="mike.sales@sample.com",
                    name="Mike Wilson",
                    first_name="Mike",
                    last_name="Wilson",
                    extension="201",
                    department_id=sales_dept.id,
                    is_manager=True,
                    status="not_available",
                    is_active=True,
                    max_concurrent_calls=1,
                    skills=["sales", "management"],
                    languages=["en"]
                ),
                Agent(
                    tenant_id=tenant.id,
                    email="alex.tech@sample.com",
                    name="Alex Rodriguez",
                    first_name="Alex",
                    last_name="Rodriguez",
                    extension="301",
                    department_id=tech_dept.id,
                    is_manager=True,
                    status="not_available",
                    is_active=True,
                    max_concurrent_calls=1,
                    skills=["technical_support", "troubleshooting", "management"],
                    languages=["en", "es"]
                )
            ]
            
            for agent in agents:
                session.add(agent)
            
            await session.commit()
            
            logger.info(
                "Sample tenant created successfully",
                tenant_id=str(tenant.id),
                tenant_name=tenant.name,
                departments_created=len(departments),
                agents_created=len(agents)
            )
            
    except Exception as e:
        logger.error("Failed to create sample tenant", error=str(e))
        raise


async def initialize_database():
    """Initialize the database with schema and sample data."""
    try:
        logger.info("Initializing VoiceCore AI database...")
        
        # Initialize database connections
        await init_database()
        logger.info("Database connections initialized")
        
        # Create sample tenant and data
        await create_sample_tenant()
        
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error("Database initialization failed", error=str(e))
        raise


def check_environment():
    """Check that required environment variables are set."""
    required_vars = [
        "DATABASE_URL",
        "SECRET_KEY",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "OPENAI_API_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(
            "Missing required environment variables",
            missing_vars=missing_vars
        )
        print("\nMissing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these variables in your .env file or environment.")
        return False
    
    return True


async def main():
    """Main initialization function."""
    print("🎯 VoiceCore AI - Project Initialization")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    try:
        # Initialize database
        await initialize_database()
        
        print("\n✅ Project initialization completed successfully!")
        print("\nNext steps:")
        print("1. Start the development server: python -m uvicorn voicecore.main:app --reload")
        print("2. Visit http://localhost:8000/docs for API documentation")
        print("3. Check http://localhost:8000/health for system status")
        
    except Exception as e:
        print(f"\n❌ Initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())