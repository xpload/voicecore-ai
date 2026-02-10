#!/usr/bin/env python3
"""
Pre-Deployment Checklist for VoiceCore AI
Verifies everything is ready for Railway deployment
"""

import os
import sys
from pathlib import Path


def check_file_exists(filepath: str, description: str) -> bool:
    """Check if a file exists."""
    exists = Path(filepath).exists()
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {filepath}")
    return exists


def check_env_file() -> bool:
    """Check .env file has required variables."""
    print("\n📋 Checking .env file...")
    
    if not Path(".env").exists():
        print("❌ .env file not found")
        return False
    
    required_vars = []
    optional_vars = [
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN", 
        "TWILIO_PHONE_NUMBER",
        "OPENAI_API_KEY"
    ]
    
    with open(".env", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    print("✅ .env file exists")
    
    missing_optional = []
    for var in optional_vars:
        if var not in content or f"{var}=" not in content:
            missing_optional.append(var)
    
    if missing_optional:
        print(f"\n⚠️  Optional variables not set (app will run but with limited functionality):")
        for var in missing_optional:
            print(f"   - {var}")
    
    return True


def check_requirements() -> bool:
    """Check requirements.txt exists."""
    print("\n📋 Checking requirements.txt...")
    return check_file_exists("requirements.txt", "Requirements file")


def check_alembic() -> bool:
    """Check Alembic migrations."""
    print("\n📋 Checking Alembic migrations...")
    
    checks = [
        check_file_exists("alembic.ini", "Alembic config"),
        check_file_exists("alembic/env.py", "Alembic environment"),
        check_file_exists("alembic/versions", "Migration versions directory")
    ]
    
    if all(checks):
        # Count migrations
        versions_dir = Path("alembic/versions")
        migrations = list(versions_dir.glob("*.py"))
        migrations = [m for m in migrations if m.name != "__pycache__"]
        print(f"✅ Found {len(migrations)} migrations")
        return True
    
    return False


def check_railway_files() -> bool:
    """Check Railway deployment files."""
    print("\n📋 Checking Railway deployment files...")
    
    checks = [
        check_file_exists("Procfile", "Procfile"),
        check_file_exists("railway.toml", "Railway config"),
        check_file_exists("runtime.txt", "Python runtime")
    ]
    
    return all(checks)


def check_models() -> bool:
    """Check model files exist."""
    print("\n📋 Checking model files...")
    
    model_files = [
        "voicecore/models/__init__.py",
        "voicecore/models/base.py",
        "voicecore/models/tenant.py",
        "voicecore/models/agent.py",
        "voicecore/models/call.py",
        "voicecore/models/event_store.py"
    ]
    
    checks = [check_file_exists(f, f"Model: {Path(f).name}") for f in model_files]
    return all(checks)


def check_services() -> bool:
    """Check service files exist."""
    print("\n📋 Checking service files...")
    
    service_files = [
        "voicecore/services/event_sourcing_service.py",
        "voicecore/services/call_routing_service.py",
        "voicecore/services/openai_service.py"
    ]
    
    checks = [check_file_exists(f, f"Service: {Path(f).name}") for f in service_files]
    return all(checks)


def check_main_app() -> bool:
    """Check main application file."""
    print("\n📋 Checking main application...")
    return check_file_exists("voicecore/main.py", "Main application")


def print_summary(results: dict):
    """Print summary of checks."""
    print("\n" + "="*60)
    print("📊 PRE-DEPLOYMENT CHECK SUMMARY")
    print("="*60)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    for check, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {check}")
    
    print("\n" + "="*60)
    print(f"Total: {total} | Passed: {passed} | Failed: {failed}")
    print("="*60)
    
    if failed == 0:
        print("""
✅ ALL CHECKS PASSED!

Your application is ready for Railway deployment.

Next steps:
1. Run: python deploy_railway.py
2. Or follow: DEPLOY_NOW.md

🚀 Ready to deploy!
        """)
        return True
    else:
        print("""
❌ SOME CHECKS FAILED

Please fix the issues above before deploying.

Common fixes:
- Missing files: Check if files were deleted or moved
- .env file: Copy from .env.example and configure
- Migrations: Run 'alembic upgrade head' locally first

After fixing, run this script again.
        """)
        return False


def main():
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║         VoiceCore AI - Pre-Deployment Check              ║
    ║         Verify everything is ready                       ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    results = {
        "Environment file": check_env_file(),
        "Requirements": check_requirements(),
        "Alembic migrations": check_alembic(),
        "Railway files": check_railway_files(),
        "Model files": check_models(),
        "Service files": check_services(),
        "Main application": check_main_app()
    }
    
    success = print_summary(results)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Check cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Check failed: {e}")
        sys.exit(1)
