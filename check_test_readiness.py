"""
VoiceCore AI - Test Readiness Checker
Verifies that the system is ready for testing
"""

import sys
import os
from colorama import init, Fore, Style

init(autoreset=True)


def print_header(text):
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}{text.center(80)}")
    print(f"{Fore.CYAN}{'='*80}\n")


def print_check(name, status, message=""):
    symbol = "✅" if status else "❌"
    color = Fore.GREEN if status else Fore.RED
    print(f"{color}{symbol} {name}{Style.RESET_ALL}")
    if message:
        print(f"   {Fore.YELLOW}{message}{Style.RESET_ALL}")


def check_python_version():
    """Check Python version"""
    version = sys.version_info
    required = (3, 9)
    status = version >= required
    message = f"Python {version.major}.{version.minor}.{version.micro}"
    if not status:
        message += f" (Required: {required[0]}.{required[1]}+)"
    return status, message


def check_dependencies():
    """Check required dependencies"""
    required_packages = [
        'pytest',
        'pytest-asyncio',
        'colorama',
        'sqlalchemy',
        'fastapi',
        'pydantic',
        'alembic'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    status = len(missing) == 0
    message = "All dependencies installed" if status else f"Missing: {', '.join(missing)}"
    return status, message


def check_env_file():
    """Check if .env file exists"""
    status = os.path.exists('.env')
    message = ".env file found" if status else ".env file not found"
    return status, message


def check_database_config():
    """Check database configuration"""
    try:
        from voicecore.config import settings
        status = bool(settings.database_url)
        message = "Database URL configured" if status else "Database URL not configured"
        return status, message
    except Exception as e:
        return False, f"Error loading config: {str(e)}"


def check_test_files():
    """Check if test files exist"""
    test_files = [
        'tests/test_call_flow_e2e.py',
        'tests/conftest.py',
        'pytest.ini'
    ]
    
    missing = [f for f in test_files if not os.path.exists(f)]
    status = len(missing) == 0
    message = "All test files present" if status else f"Missing: {', '.join(missing)}"
    return status, message


def check_example_files():
    """Check if example files exist"""
    example_files = [
        'examples/interactive_call_demo.py',
        'examples/event_sourcing_example.py'
    ]
    
    missing = [f for f in example_files if not os.path.exists(f)]
    status = len(missing) == 0
    message = "All example files present" if status else f"Missing: {', '.join(missing)}"
    return status, message


def check_voicecore_module():
    """Check if voicecore module can be imported"""
    try:
        import voicecore
        status = True
        message = "VoiceCore module importable"
    except ImportError as e:
        status = False
        message = f"Cannot import voicecore: {str(e)}"
    return status, message


def check_database_connection():
    """Check database connection"""
    try:
        from voicecore.config import settings
        
        # For SQLite, just check if the database URL is configured
        if settings.database_url.startswith("sqlite"):
            status = True
            message = "Database configured (SQLite - async not required for tests)"
        else:
            # For PostgreSQL, test async connection
            import asyncio
            from voicecore.database import init_database, get_db_session
            from sqlalchemy import text
            
            async def test_connection():
                await init_database()
                async with get_db_session() as session:
                    await session.execute(text("SELECT 1"))
            
            asyncio.run(test_connection())
            status = True
            message = "Database connection successful"
    except Exception as e:
        status = False
        message = f"Database connection failed: {str(e)}"
    return status, message


def main():
    """Run all checks"""
    print_header("VoiceCore AI - Test Readiness Check")
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Environment File", check_env_file),
        ("Database Config", check_database_config),
        ("Test Files", check_test_files),
        ("Example Files", check_example_files),
        ("VoiceCore Module", check_voicecore_module),
        ("Database Connection", check_database_connection)
    ]
    
    results = []
    
    for name, check_func in checks:
        try:
            status, message = check_func()
            print_check(name, status, message)
            results.append((name, status))
        except Exception as e:
            print_check(name, False, f"Check failed: {str(e)}")
            results.append((name, False))
    
    # Summary
    print_header("Summary")
    
    passed = sum(1 for _, status in results if status)
    total = len(results)
    
    print(f"\n{Fore.CYAN}Checks passed: {Fore.GREEN}{passed}{Fore.CYAN}/{total}\n")
    
    if passed == total:
        print(f"{Fore.GREEN}{Style.BRIGHT}🎉 System is ready for testing!")
        print(f"\n{Fore.CYAN}Next steps:")
        print(f"  1. Run tests: {Fore.WHITE}python run_call_tests.py")
        print(f"  2. Try demo: {Fore.WHITE}python examples/interactive_call_demo.py")
        print(f"  3. Read guide: {Fore.WHITE}TESTING_GUIDE.md")
        return 0
    else:
        print(f"{Fore.RED}{Style.BRIGHT}⚠️  System is not ready for testing")
        print(f"\n{Fore.YELLOW}Please fix the issues above before running tests.")
        
        # Provide specific guidance
        failed_checks = [name for name, status in results if not status]
        
        if "Dependencies" in failed_checks:
            print(f"\n{Fore.CYAN}To install dependencies:")
            print(f"  {Fore.WHITE}pip install -r requirements.txt")
            print(f"  {Fore.WHITE}pip install pytest pytest-asyncio colorama")
        
        if "Environment File" in failed_checks:
            print(f"\n{Fore.CYAN}To create .env file:")
            print(f"  {Fore.WHITE}cp .env.example .env")
            print(f"  {Fore.WHITE}# Then edit .env with your configuration")
        
        if "Database Connection" in failed_checks:
            print(f"\n{Fore.CYAN}To setup database:")
            print(f"  {Fore.WHITE}alembic upgrade head")
            print(f"  {Fore.WHITE}python scripts/init_project.py")
        
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Check interrupted by user.")
        sys.exit(1)
