"""
Database configuration and connection management for VoiceCore AI.

This module handles Supabase PostgreSQL connections with Row-Level Security (RLS)
for multitenant data isolation and provides database utilities.
"""

from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text

from voicecore.config import settings
from voicecore.logging import get_logger


logger = get_logger(__name__)

# SQLAlchemy Base for ORM models
Base = declarative_base()

# Global database connections
supabase_client: Optional[object] = None
async_engine = None
AsyncSessionLocal = None


async def init_database() -> None:
    """
    Initialize database connections and verify connectivity.
    
    Sets up SQLAlchemy async engine for database operations.
    """
    global supabase_client, async_engine, AsyncSessionLocal
    
    try:
        # Skip Supabase initialization for now
        logger.info("Skipping Supabase client initialization (not configured)")
        
        # Initialize SQLAlchemy async engine
        async_engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        
        # Create session factory
        AsyncSessionLocal = async_sessionmaker(
            async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Test database connectivity
        async with async_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        logger.info("Database engine initialized successfully")
        
        # Skip RLS verification for SQLite
        if not settings.database_url.startswith("sqlite"):
            await verify_rls_setup()
        
    except Exception as e:
        logger.critical("Failed to initialize database", error=str(e))
        raise


async def close_database() -> None:
    """Close database connections gracefully."""
    global async_engine
    
    if async_engine:
        await async_engine.dispose()
        logger.info("Database connections closed")


async def verify_rls_setup() -> None:
    """
    Verify that Row-Level Security (RLS) is properly configured.
    
    This is critical for multitenant data isolation.
    """
    try:
        async with get_db_session() as session:
            # Check if RLS is enabled on key tables
            result = await session.execute(text("""
                SELECT schemaname, tablename, rowsecurity 
                FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename IN ('tenants', 'agents', 'calls', 'knowledge_base', 'departments', 'spam_rules')
            """))
            
            tables = result.fetchall()
            
            rls_enabled_count = 0
            for table in tables:
                if not table.rowsecurity:
                    logger.warning(
                        "RLS not enabled on table",
                        schema=table.schemaname,
                        table=table.tablename
                    )
                else:
                    logger.debug(
                        "RLS verified on table",
                        schema=table.schemaname,
                        table=table.tablename
                    )
                    rls_enabled_count += 1
            
            # Check if RLS policies exist
            policy_result = await session.execute(text("""
                SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
                FROM pg_policies 
                WHERE schemaname = 'public'
                ORDER BY tablename, policyname
            """))
            
            policies = policy_result.fetchall()
            logger.info(
                "RLS verification completed",
                tables_with_rls=rls_enabled_count,
                total_policies=len(policies)
            )
            
            # Verify tenant context function exists
            func_result = await session.execute(text("""
                SELECT EXISTS(
                    SELECT 1 FROM pg_proc p 
                    JOIN pg_namespace n ON p.pronamespace = n.oid 
                    WHERE n.nspname = 'public' AND p.proname = 'set_tenant_context'
                )
            """))
            
            func_exists = func_result.scalar()
            if not func_exists:
                logger.error("Tenant context function not found - RLS may not work properly")
            else:
                logger.debug("Tenant context function verified")
        
    except Exception as e:
        logger.error("Failed to verify RLS setup", error=str(e))


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session with proper error handling.
    
    Yields:
        AsyncSession: Database session
    """
    if not AsyncSessionLocal:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error("Database session error", error=str(e))
            raise
        finally:
            await session.close()


async def set_tenant_context(session: AsyncSession, tenant_id: str) -> None:
    """
    Set the tenant context for Row-Level Security (RLS).
    
    This function sets the PostgreSQL session variable that RLS policies
    use to filter data by tenant.
    
    Args:
        session: Database session
        tenant_id: Tenant UUID to set as context
    """
    try:
        await session.execute(
            text("SELECT set_config('app.current_tenant', :tenant_id, true)"),
            {"tenant_id": tenant_id}
        )
        
        logger.debug("Tenant context set", tenant_id=tenant_id)
        
    except Exception as e:
        logger.error("Failed to set tenant context", tenant_id=tenant_id, error=str(e))
        raise


async def get_tenant_context(session: AsyncSession) -> Optional[str]:
    """
    Get the current tenant context from the database session.
    
    Args:
        session: Database session
        
    Returns:
        Optional[str]: Current tenant ID or None
    """
    try:
        result = await session.execute(
            text("SELECT current_setting('app.current_tenant', true)")
        )
        tenant_id = result.scalar()
        return tenant_id if tenant_id else None
        
    except Exception as e:
        logger.error("Failed to get tenant context", error=str(e))
        return None


class DatabaseManager:
    """
    Database manager class for handling tenant-aware database operations.
    
    This class provides high-level database operations with automatic
    tenant context management and security compliance.
    """
    
    def __init__(self):
        self.supabase = supabase_client
    
    @asynccontextmanager
    async def get_tenant_session(self, tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session with tenant context pre-configured.
        
        Args:
            tenant_id: Tenant UUID
            
        Yields:
            AsyncSession: Database session with tenant context
        """
        async with get_db_session() as session:
            await set_tenant_context(session, tenant_id)
            yield session
    
    async def execute_query(
        self, 
        query: str, 
        params: dict = None, 
        tenant_id: str = None
    ) -> list:
        """
        Execute a raw SQL query with optional tenant context.
        
        Args:
            query: SQL query string
            params: Query parameters
            tenant_id: Optional tenant ID for context
            
        Returns:
            list: Query results
        """
        async with get_db_session() as session:
            if tenant_id:
                await set_tenant_context(session, tenant_id)
            
            result = await session.execute(text(query), params or {})
            return result.fetchall()
    
    async def create_tenant_with_isolation(self, tenant_data: dict) -> str:
        """
        Create a new tenant with proper isolation setup.
        
        This method ensures that all tenant-specific resources are
        properly provisioned with complete data isolation.
        
        Args:
            tenant_data: Tenant configuration data
            
        Returns:
            str: Created tenant ID
        """
        from voicecore.models import Tenant, TenantSettings, Department
        
        async with get_db_session() as session:
            try:
                # Create tenant record
                tenant = Tenant(
                    name=tenant_data['name'],
                    domain=tenant_data.get('domain'),
                    subdomain=tenant_data.get('subdomain'),
                    is_active=tenant_data.get('is_active', True),
                    plan_type=tenant_data.get('plan_type', 'basic'),
                    contact_email=tenant_data['contact_email'],
                    contact_phone=tenant_data.get('contact_phone'),
                    monthly_credit_limit=tenant_data.get('monthly_credit_limit', 1000),
                    settings=tenant_data.get('settings', {}),
                    twilio_phone_number=tenant_data.get('twilio_phone_number')
                )
                
                session.add(tenant)
                await session.flush()  # Get tenant ID
                
                tenant_id = str(tenant.id)
                
                # Set tenant context for subsequent operations
                await set_tenant_context(session, tenant_id)
                
                # Create default tenant settings
                tenant_settings = TenantSettings(
                    tenant_id=tenant.id,
                    ai_name=tenant_data.get('ai_name', 'Sofia'),
                    ai_gender=tenant_data.get('ai_gender', 'female'),
                    ai_voice_id=tenant_data.get('ai_voice_id', 'alloy'),
                    company_description=tenant_data.get('company_description', ''),
                    company_services=tenant_data.get('company_services', []),
                    max_transfer_attempts=tenant_data.get('max_transfer_attempts', 3),
                    default_department=tenant_data.get('default_department', 'customer_service'),
                    business_hours_start=tenant_data.get('business_hours_start', '09:00'),
                    business_hours_end=tenant_data.get('business_hours_end', '17:00'),
                    timezone=tenant_data.get('timezone', 'UTC'),
                    enable_spam_detection=tenant_data.get('enable_spam_detection', True),
                    enable_call_recording=tenant_data.get('enable_call_recording', True),
                    enable_transcription=tenant_data.get('enable_transcription', True),
                    primary_language=tenant_data.get('primary_language', 'auto'),
                    supported_languages=tenant_data.get('supported_languages', ['en', 'es'])
                )
                
                session.add(tenant_settings)
                
                # Create default customer service department
                default_dept = Department(
                    tenant_id=tenant.id,
                    name="Customer Service",
                    code="CS",
                    description="Default customer service department",
                    is_active=True,
                    is_default=True,
                    max_queue_size=10,
                    queue_timeout=300,
                    transfer_keywords=["help", "support", "service"],
                    priority=1,
                    routing_strategy="round_robin"
                )
                
                session.add(default_dept)
                
                await session.commit()
                
                logger.info(
                    "Tenant created with isolation",
                    tenant_id=tenant_id,
                    tenant_name=tenant.name,
                    plan_type=tenant.plan_type
                )
                
                return tenant_id
                
            except Exception as e:
                await session.rollback()
                logger.error("Failed to create tenant with isolation", error=str(e))
                raise
    
    async def delete_tenant_with_cleanup(self, tenant_id: str) -> bool:
        """
        Delete a tenant and all associated data completely.
        
        This method ensures complete data cleanup for tenant deletion
        while maintaining referential integrity.
        
        Args:
            tenant_id: Tenant UUID to delete
            
        Returns:
            bool: True if deletion was successful
        """
        async with get_db_session() as session:
            try:
                # Set tenant context
                await set_tenant_context(session, tenant_id)
                
                # Delete in proper order to maintain referential integrity
                # 1. Delete call-related data
                await session.execute(
                    text("DELETE FROM call_events WHERE tenant_id = :tenant_id"),
                    {"tenant_id": tenant_id}
                )
                
                await session.execute(
                    text("DELETE FROM call_queue WHERE tenant_id = :tenant_id"),
                    {"tenant_id": tenant_id}
                )
                
                await session.execute(
                    text("DELETE FROM calls WHERE tenant_id = :tenant_id"),
                    {"tenant_id": tenant_id}
                )
                
                # 2. Delete agent-related data
                await session.execute(
                    text("DELETE FROM agent_sessions WHERE tenant_id = :tenant_id"),
                    {"tenant_id": tenant_id}
                )
                
                await session.execute(
                    text("DELETE FROM agents WHERE tenant_id = :tenant_id"),
                    {"tenant_id": tenant_id}
                )
                
                # 3. Delete knowledge and spam data
                await session.execute(
                    text("DELETE FROM spam_reports WHERE tenant_id = :tenant_id"),
                    {"tenant_id": tenant_id}
                )
                
                await session.execute(
                    text("DELETE FROM spam_rules WHERE tenant_id = :tenant_id"),
                    {"tenant_id": tenant_id}
                )
                
                await session.execute(
                    text("DELETE FROM knowledge_base WHERE tenant_id = :tenant_id"),
                    {"tenant_id": tenant_id}
                )
                
                # 4. Delete analytics data
                await session.execute(
                    text("DELETE FROM call_analytics WHERE tenant_id = :tenant_id"),
                    {"tenant_id": tenant_id}
                )
                
                await session.execute(
                    text("DELETE FROM agent_metrics WHERE tenant_id = :tenant_id"),
                    {"tenant_id": tenant_id}
                )
                
                await session.execute(
                    text("DELETE FROM system_metrics WHERE tenant_id = :tenant_id"),
                    {"tenant_id": tenant_id}
                )
                
                # 5. Delete departments
                await session.execute(
                    text("DELETE FROM departments WHERE tenant_id = :tenant_id"),
                    {"tenant_id": tenant_id}
                )
                
                # 6. Delete tenant settings
                await session.execute(
                    text("DELETE FROM tenant_settings WHERE tenant_id = :tenant_id"),
                    {"tenant_id": tenant_id}
                )
                
                # 7. Finally delete tenant
                await session.execute(
                    text("DELETE FROM tenants WHERE id = :tenant_id"),
                    {"tenant_id": tenant_id}
                )
                
                await session.commit()
                
                logger.info(
                    "Tenant deleted with complete cleanup",
                    tenant_id=tenant_id
                )
                
                return True
                
            except Exception as e:
                await session.rollback()
                logger.error("Failed to delete tenant with cleanup", tenant_id=tenant_id, error=str(e))
                return False
    
    async def verify_tenant_isolation(self, tenant_id1: str, tenant_id2: str) -> dict:
        """
        Verify that tenant isolation is working correctly.
        
        This method tests that tenants cannot access each other's data
        by attempting cross-tenant queries.
        
        Args:
            tenant_id1: First tenant ID
            tenant_id2: Second tenant ID
            
        Returns:
            dict: Isolation verification results
        """
        results = {
            "tenant1_isolated": False,
            "tenant2_isolated": False,
            "cross_access_blocked": True,
            "errors": []
        }
        
        try:
            # Test tenant 1 isolation
            async with self.get_tenant_session(tenant_id1) as session:
                # Should only see tenant 1 data
                result = await session.execute(
                    text("SELECT COUNT(*) FROM agents WHERE tenant_id != :tenant_id"),
                    {"tenant_id": tenant_id1}
                )
                other_tenant_count = result.scalar()
                
                if other_tenant_count == 0:
                    results["tenant1_isolated"] = True
                else:
                    results["errors"].append(f"Tenant 1 can see {other_tenant_count} records from other tenants")
            
            # Test tenant 2 isolation
            async with self.get_tenant_session(tenant_id2) as session:
                # Should only see tenant 2 data
                result = await session.execute(
                    text("SELECT COUNT(*) FROM agents WHERE tenant_id != :tenant_id"),
                    {"tenant_id": tenant_id2}
                )
                other_tenant_count = result.scalar()
                
                if other_tenant_count == 0:
                    results["tenant2_isolated"] = True
                else:
                    results["errors"].append(f"Tenant 2 can see {other_tenant_count} records from other tenants")
            
            logger.info(
                "Tenant isolation verification completed",
                tenant1_isolated=results["tenant1_isolated"],
                tenant2_isolated=results["tenant2_isolated"],
                errors_count=len(results["errors"])
            )
            
        except Exception as e:
            results["errors"].append(f"Verification failed: {str(e)}")
            logger.error("Failed to verify tenant isolation", error=str(e))
        
        return results
    
    async def health_check(self) -> dict:
        """
        Perform database health check.
        
        Returns:
            dict: Health status information
        """
        try:
            async with get_db_session() as session:
                # Test basic connectivity
                await session.execute(text("SELECT 1"))
                
                # Check connection pool status
                pool_status = {
                    "size": async_engine.pool.size(),
                    "checked_in": async_engine.pool.checkedin(),
                    "checked_out": async_engine.pool.checkedout(),
                }
                
                # Check RLS status
                rls_result = await session.execute(text("""
                    SELECT COUNT(*) FROM pg_policies WHERE schemaname = 'public'
                """))
                rls_policies_count = rls_result.scalar()
                
                # Check tenant context function
                func_result = await session.execute(text("""
                    SELECT EXISTS(
                        SELECT 1 FROM pg_proc p 
                        JOIN pg_namespace n ON p.pronamespace = n.oid 
                        WHERE n.nspname = 'public' AND p.proname = 'set_tenant_context'
                    )
                """))
                tenant_func_exists = func_result.scalar()
                
                return {
                    "status": "healthy",
                    "database": "connected",
                    "pool": pool_status,
                    "rls_policies": rls_policies_count,
                    "tenant_function": tenant_func_exists,
                    "multitenant_ready": rls_policies_count > 0 and tenant_func_exists
                }
                
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
                "multitenant_ready": False
            }


# Global database manager instance
db_manager = DatabaseManager()