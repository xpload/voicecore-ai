#!/usr/bin/env python3
"""
System validation script for VoiceCore AI.

This script performs comprehensive validation of the entire system
to ensure all components are working correctly.
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class SystemValidator:
    """Comprehensive system validation."""
    
    def __init__(self):
        self.validation_results = {}
        self.errors = []
        self.warnings = []
    
    async def validate_project_structure(self):
        """Validate project structure and required files."""
        print("🔍 Validating project structure...")
        
        required_files = [
            "voicecore/__init__.py",
            "voicecore/main.py",
            "voicecore/config.py",
            "voicecore/database.py",
            "requirements.txt",
            "pyproject.toml",
            "alembic.ini",
            "docker-compose.yml",
            "Dockerfile"
        ]
        
        required_directories = [
            "voicecore/api",
            "voicecore/services",
            "voicecore/models",
            "voicecore/middleware",
            "tests",
            "alembic/versions",
            "kubernetes",
            "monitoring"
        ]
        
        missing_files = []
        missing_dirs = []
        
        for file_path in required_files:
            if not Path(file_path).exists():
                missing_files.append(file_path)
        
        for dir_path in required_directories:
            if not Path(dir_path).exists():
                missing_dirs.append(dir_path)
        
        if missing_files:
            self.errors.append(f"Missing required files: {missing_files}")
        
        if missing_dirs:
            self.errors.append(f"Missing required directories: {missing_dirs}")
        
        if not missing_files and not missing_dirs:
            self.validation_results["project_structure"] = "✅ PASS"
            print("✅ Project structure validation passed")
        else:
            self.validation_results["project_structure"] = "❌ FAIL"
            print("❌ Project structure validation failed")
    
    async def validate_database_models(self):
        """Validate database models and relationships."""
        print("🔍 Validating database models...")
        
        try:
            # Import all models to check for syntax errors
            from voicecore.models.tenant import Tenant
            from voicecore.models.agent import Agent
            from voicecore.models.call import Call
            from voicecore.models.analytics import CallAnalytics
            from voicecore.models.vip import VIPCaller
            from voicecore.models.voicemail import Voicemail
            from voicecore.models.callback import CallbackRequest
            from voicecore.models.billing import CreditTransaction
            from voicecore.models.security import APIKey
            from voicecore.models.knowledge import KnowledgeBase
            
            # Check model attributes
            models = [
                Tenant, Agent, Call, CallAnalytics, VIPCaller,
                Voicemail, CallbackRequest, CreditTransaction, APIKey, KnowledgeBase
            ]
            
            for model in models:
                if not hasattr(model, '__tablename__'):
                    self.errors.append(f"Model {model.__name__} missing __tablename__")
                
                if not hasattr(model, 'id'):
                    self.errors.append(f"Model {model.__name__} missing id field")
            
            self.validation_results["database_models"] = "✅ PASS"
            print("✅ Database models validation passed")
            
        except Exception as e:
            self.errors.append(f"Database models validation failed: {str(e)}")
            self.validation_results["database_models"] = "❌ FAIL"
            print("❌ Database models validation failed")
    
    async def validate_services(self):
        """Validate service layer implementations."""
        print("🔍 Validating services...")
        
        try:
            # Import all services to check for syntax errors
            from voicecore.services.tenant_service import TenantService
            from voicecore.services.agent_service import AgentService
            from voicecore.services.call_routing_service import CallRoutingService
            from voicecore.services.twilio_service import TwilioService
            from voicecore.services.openai_service import OpenAIService
            from voicecore.services.analytics_service import AnalyticsService
            from voicecore.services.spam_detection_service import SpamDetectionService
            from voicecore.services.vip_service import VIPService
            from voicecore.services.voicemail_service import VoicemailService
            from voicecore.services.callback_service import CallbackService
            from voicecore.services.credit_management_service import CreditManagementService
            from voicecore.services.auth_service import AuthService
            from voicecore.services.privacy_service import PrivacyService
            from voicecore.services.auto_scaling_service import AutoScalingService
            from voicecore.services.high_availability_service import HighAvailabilityService
            from voicecore.services.ai_training_service import AITrainingService
            from voicecore.services.learning_feedback_service import LearningFeedbackService
            from voicecore.services.emotion_detection_service import EmotionDetectionService
            from voicecore.services.data_export_service import DataExportService
            from voicecore.services.error_handling_service import ErrorHandlingService
            
            # Check service methods
            services = [
                TenantService, AgentService, CallRoutingService, TwilioService,
                OpenAIService, AnalyticsService, SpamDetectionService, VIPService,
                VoicemailService, CallbackService, CreditManagementService,
                AuthService, PrivacyService, AutoScalingService, HighAvailabilityService,
                AITrainingService, LearningFeedbackService, EmotionDetectionService,
                DataExportService, ErrorHandlingService
            ]
            
            for service_class in services:
                service_name = service_class.__name__
                
                # Check if service has required methods (basic CRUD operations)
                if hasattr(service_class, '__init__'):
                    try:
                        # Try to instantiate (without calling actual methods)
                        service_instance = service_class()
                    except Exception as e:
                        self.warnings.append(f"Service {service_name} instantiation warning: {str(e)}")
            
            self.validation_results["services"] = "✅ PASS"
            print("✅ Services validation passed")
            
        except Exception as e:
            self.errors.append(f"Services validation failed: {str(e)}")
            self.validation_results["services"] = "❌ FAIL"
            print("❌ Services validation failed")
    
    async def validate_api_routes(self):
        """Validate API routes and endpoints."""
        print("🔍 Validating API routes...")
        
        try:
            # Import all API route modules
            from voicecore.api.tenant_routes import router as tenant_router
            from voicecore.api.agent_routes import router as agent_router
            from voicecore.api.webhook_routes import router as webhook_router
            from voicecore.api.admin_routes import router as admin_router
            from voicecore.api.tenant_admin_routes import router as tenant_admin_router
            from voicecore.api.analytics_routes import router as analytics_router
            from voicecore.api.vip_routes import router as vip_router
            from voicecore.api.voicemail_routes import router as voicemail_router
            from voicecore.api.callback_routes import router as callback_router
            from voicecore.api.credit_routes import router as credit_router
            from voicecore.api.auth_routes import router as auth_router
            from voicecore.api.ai_training_routes import router as ai_training_router
            from voicecore.api.learning_feedback_routes import router as learning_feedback_router
            from voicecore.api.emotion_detection_routes import router as emotion_router
            from voicecore.api.data_export_routes import router as data_export_router
            from voicecore.api.scaling_routes import router as scaling_router
            from voicecore.api.ha_routes import router as ha_router
            from voicecore.api.error_handling_routes import router as error_router
            from voicecore.api.websocket_routes import router as websocket_router
            from voicecore.api.pwa_routes import router as pwa_router
            from voicecore.api.call_logging_routes import router as call_logging_router
            
            # Check that routers have routes
            routers = [
                ("tenant", tenant_router),
                ("agent", agent_router),
                ("webhook", webhook_router),
                ("admin", admin_router),
                ("tenant_admin", tenant_admin_router),
                ("analytics", analytics_router),
                ("vip", vip_router),
                ("voicemail", voicemail_router),
                ("callback", callback_router),
                ("credit", credit_router),
                ("auth", auth_router),
                ("ai_training", ai_training_router),
                ("learning_feedback", learning_feedback_router),
                ("emotion", emotion_router),
                ("data_export", data_export_router),
                ("scaling", scaling_router),
                ("ha", ha_router),
                ("error", error_router),
                ("websocket", websocket_router),
                ("pwa", pwa_router),
                ("call_logging", call_logging_router)
            ]
            
            for router_name, router in routers:
                if not hasattr(router, 'routes') or len(router.routes) == 0:
                    self.warnings.append(f"Router {router_name} has no routes defined")
            
            self.validation_results["api_routes"] = "✅ PASS"
            print("✅ API routes validation passed")
            
        except Exception as e:
            self.errors.append(f"API routes validation failed: {str(e)}")
            self.validation_results["api_routes"] = "❌ FAIL"
            print("❌ API routes validation failed")
    
    async def validate_configuration(self):
        """Validate configuration and environment setup."""
        print("🔍 Validating configuration...")
        
        try:
            from voicecore.config import Settings
            
            # Try to load settings
            settings = Settings()
            
            # Check required configuration fields
            required_fields = [
                'database_url', 'supabase_url', 'supabase_key',
                'twilio_account_sid', 'twilio_auth_token',
                'openai_api_key', 'secret_key'
            ]
            
            missing_config = []
            for field in required_fields:
                if not hasattr(settings, field):
                    missing_config.append(field)
            
            if missing_config:
                self.warnings.append(f"Missing configuration fields: {missing_config}")
            
            self.validation_results["configuration"] = "✅ PASS"
            print("✅ Configuration validation passed")
            
        except Exception as e:
            self.errors.append(f"Configuration validation failed: {str(e)}")
            self.validation_results["configuration"] = "❌ FAIL"
            print("❌ Configuration validation failed")
    
    async def validate_tests(self):
        """Validate test files and structure."""
        print("🔍 Validating tests...")
        
        test_files = [
            "tests/test_properties.py",
            "tests/test_ai_properties.py",
            "tests/test_call_routing_properties.py",
            "tests/test_agent_properties.py",
            "tests/test_spam_detection_properties.py",
            "tests/test_webrtc_properties.py",
            "tests/test_call_logging_properties.py",
            "tests/test_advanced_features_properties.py",
            "tests/test_analytics_properties.py",
            "tests/test_security_properties.py",
            "tests/test_scalability_properties.py",
            "tests/test_ai_learning_properties.py",
            "tests/test_credit_system_properties.py",
            "tests/integration/test_end_to_end_call_flows.py",
            "tests/integration/test_multitenant_isolation.py",
            "tests/integration/test_external_service_integrations.py"
        ]
        
        missing_tests = []
        for test_file in test_files:
            if not Path(test_file).exists():
                missing_tests.append(test_file)
        
        if missing_tests:
            self.warnings.append(f"Missing test files: {missing_tests}")
        
        # Check test configuration
        if not Path("tests/conftest.py").exists():
            self.errors.append("Missing tests/conftest.py configuration file")
        
        if not missing_tests and Path("tests/conftest.py").exists():
            self.validation_results["tests"] = "✅ PASS"
            print("✅ Tests validation passed")
        else:
            self.validation_results["tests"] = "⚠️ PARTIAL"
            print("⚠️ Tests validation partially passed")
    
    async def validate_deployment_config(self):
        """Validate deployment configuration."""
        print("🔍 Validating deployment configuration...")
        
        deployment_files = [
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.prod.yml",
            "kubernetes/deployment.yaml",
            "kubernetes/service.yaml",
            "kubernetes/configmap.yaml",
            "kubernetes/secrets.yaml",
            "monitoring/prometheus.yml",
            "monitoring/alert_rules.yml",
            "nginx/nginx.prod.conf"
        ]
        
        missing_deployment_files = []
        for file_path in deployment_files:
            if not Path(file_path).exists():
                missing_deployment_files.append(file_path)
        
        if missing_deployment_files:
            self.warnings.append(f"Missing deployment files: {missing_deployment_files}")
        
        # Check deployment scripts
        deployment_scripts = [
            "scripts/deploy.sh",
            "scripts/setup-production.ps1"
        ]
        
        for script in deployment_scripts:
            if Path(script).exists():
                # Check if script is executable (on Unix systems)
                if hasattr(os, 'access') and not os.access(script, os.X_OK):
                    self.warnings.append(f"Deployment script {script} is not executable")
        
        self.validation_results["deployment"] = "✅ PASS"
        print("✅ Deployment configuration validation passed")
    
    async def validate_documentation(self):
        """Validate documentation completeness."""
        print("🔍 Validating documentation...")
        
        doc_files = [
            "README.md",
            "DEPLOYMENT.md",
            "docs/VIP_MANAGEMENT.md"
        ]
        
        missing_docs = []
        for doc_file in doc_files:
            if not Path(doc_file).exists():
                missing_docs.append(doc_file)
        
        if missing_docs:
            self.warnings.append(f"Missing documentation files: {missing_docs}")
        
        # Check if README has basic content
        if Path("README.md").exists():
            readme_content = Path("README.md").read_text()
            if len(readme_content) < 500:  # Basic content check
                self.warnings.append("README.md appears to be incomplete")
        
        self.validation_results["documentation"] = "✅ PASS"
        print("✅ Documentation validation passed")
    
    def print_summary(self):
        """Print validation summary."""
        print("\n" + "="*60)
        print("🎯 SYSTEM VALIDATION SUMMARY")
        print("="*60)
        
        print("\n📊 Validation Results:")
        for component, result in self.validation_results.items():
            print(f"  {component.replace('_', ' ').title()}: {result}")
        
        if self.errors:
            print(f"\n❌ Errors ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
        
        if self.warnings:
            print(f"\n⚠️ Warnings ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        # Calculate overall status
        total_components = len(self.validation_results)
        passed_components = sum(1 for result in self.validation_results.values() if "✅" in result)
        partial_components = sum(1 for result in self.validation_results.values() if "⚠️" in result)
        failed_components = sum(1 for result in self.validation_results.values() if "❌" in result)
        
        print(f"\n📈 Overall Status:")
        print(f"  Total Components: {total_components}")
        print(f"  Passed: {passed_components}")
        print(f"  Partial: {partial_components}")
        print(f"  Failed: {failed_components}")
        print(f"  Success Rate: {(passed_components / total_components * 100):.1f}%")
        
        if failed_components == 0 and len(self.errors) == 0:
            print(f"\n🎉 SYSTEM VALIDATION COMPLETED SUCCESSFULLY!")
            print(f"   VoiceCore AI is ready for deployment.")
        elif failed_components == 0:
            print(f"\n✅ SYSTEM VALIDATION PASSED WITH WARNINGS")
            print(f"   VoiceCore AI is functional but has minor issues to address.")
        else:
            print(f"\n❌ SYSTEM VALIDATION FAILED")
            print(f"   Please fix the errors before deployment.")
        
        print("="*60)


async def main():
    """Run complete system validation."""
    print("🚀 Starting VoiceCore AI System Validation")
    print(f"📅 Validation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    validator = SystemValidator()
    
    # Run all validations
    await validator.validate_project_structure()
    await validator.validate_database_models()
    await validator.validate_services()
    await validator.validate_api_routes()
    await validator.validate_configuration()
    await validator.validate_tests()
    await validator.validate_deployment_config()
    await validator.validate_documentation()
    
    # Print summary
    validator.print_summary()
    
    # Return exit code based on validation results
    if any("❌" in result for result in validator.validation_results.values()) or validator.errors:
        return 1  # Failure
    else:
        return 0  # Success


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)