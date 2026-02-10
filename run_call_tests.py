"""
VoiceCore AI - Call Flow Test Runner
Executes comprehensive call flow tests
"""

import sys
import subprocess
from colorama import init, Fore, Style

init(autoreset=True)


def print_header(text):
    """Print formatted header"""
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}{text.center(80)}")
    print(f"{Fore.CYAN}{'='*80}\n")


def print_success(text):
    """Print success message"""
    print(f"{Fore.GREEN}✅ {text}")


def print_error(text):
    """Print error message"""
    print(f"{Fore.RED}❌ {text}")


def print_info(text):
    """Print info message"""
    print(f"{Fore.YELLOW}ℹ️  {text}")


def run_command(command, description):
    """Run a command and return success status"""
    print_info(f"Running: {description}")
    print(f"{Fore.WHITE}Command: {' '.join(command)}\n")
    
    try:
        result = subprocess.run(
            command,
            capture_output=False,
            text=True,
            check=True
        )
        print_success(f"{description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"{description} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print_error(f"Command not found: {command[0]}")
        print_info("Make sure pytest is installed: pip install pytest pytest-asyncio")
        return False


def main():
    """Main test runner"""
    print_header("VoiceCore AI - Call Flow Test Suite")
    
    print(f"{Fore.CYAN}This test suite will validate:")
    print("  • Inbound call handling")
    print("  • Outbound call initiation")
    print("  • AI conversation flow")
    print("  • Call escalation to agents")
    print("  • Sentiment detection")
    print("  • Call recording")
    print("  • Event sourcing integration")
    
    input(f"\n{Fore.YELLOW}Press Enter to start tests...{Style.RESET_ALL}")
    
    # Test configurations
    tests = [
        {
            "command": ["pytest", "tests/test_call_flow_e2e.py::TestInboundCallFlow::test_complete_inbound_call_with_ai", "-v", "-s"],
            "description": "Inbound Call with AI"
        },
        {
            "command": ["pytest", "tests/test_call_flow_e2e.py::TestInboundCallFlow::test_call_escalation_to_human_agent", "-v", "-s"],
            "description": "Call Escalation to Human"
        },
        {
            "command": ["pytest", "tests/test_call_flow_e2e.py::TestOutboundCallFlow::test_agent_initiated_outbound_call", "-v", "-s"],
            "description": "Outbound Call by Agent"
        },
        {
            "command": ["pytest", "tests/test_call_flow_e2e.py::TestAIConversationFlow::test_multi_turn_ai_conversation", "-v", "-s"],
            "description": "Multi-turn AI Conversation"
        },
        {
            "command": ["pytest", "tests/test_call_flow_e2e.py::TestAIConversationFlow::test_ai_sentiment_detection", "-v", "-s"],
            "description": "AI Sentiment Detection"
        },
        {
            "command": ["pytest", "tests/test_call_flow_e2e.py::TestCallRecordingFlow::test_call_recording_lifecycle", "-v", "-s"],
            "description": "Call Recording Lifecycle"
        }
    ]
    
    results = []
    
    # Run each test
    for i, test in enumerate(tests, 1):
        print_header(f"Test {i}/{len(tests)}: {test['description']}")
        success = run_command(test["command"], test["description"])
        results.append((test["description"], success))
        
        if not success:
            print_error(f"Test failed: {test['description']}")
            retry = input(f"\n{Fore.YELLOW}Continue with remaining tests? (y/n): {Style.RESET_ALL}")
            if retry.lower() != 'y':
                break
    
    # Print summary
    print_header("Test Summary")
    
    passed = sum(1 for _, success in results if success)
    failed = len(results) - passed
    
    print(f"\n{Fore.CYAN}Results:")
    for description, success in results:
        status = f"{Fore.GREEN}PASSED" if success else f"{Fore.RED}FAILED"
        print(f"  {status}{Style.RESET_ALL} - {description}")
    
    print(f"\n{Fore.CYAN}Summary:")
    print(f"  Total: {len(results)}")
    print(f"  {Fore.GREEN}Passed: {passed}")
    print(f"  {Fore.RED}Failed: {failed}")
    
    if failed == 0:
        print(f"\n{Fore.GREEN}{Style.BRIGHT}🎉 All tests passed!")
        return 0
    else:
        print(f"\n{Fore.RED}{Style.BRIGHT}⚠️  Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Tests interrupted by user.")
        sys.exit(1)
