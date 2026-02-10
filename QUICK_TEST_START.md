# VoiceCore AI - Quick Test Start

## 🚀 Get Testing in 5 Minutes

### Step 1: Check Readiness (30 seconds)

```bash
python check_test_readiness.py
```

This will verify:
- ✅ Python version
- ✅ Dependencies installed
- ✅ Environment configured
- ✅ Database connected
- ✅ Test files present

### Step 2: Run Tests (2 minutes)

```bash
python run_call_tests.py
```

This runs all call flow tests with progress tracking.

### Step 3: Try Interactive Demo (2 minutes)

```bash
python examples/interactive_call_demo.py
```

Select a scenario to see it in action!

## 📋 What Gets Tested

### ✅ Inbound Calls
- Customer calls business
- AI answers and helps
- Escalates to agent if needed
- Call recorded and tracked

### ✅ AI Conversations
- Multi-turn dialogues
- Intent recognition
- Sentiment analysis
- Context maintenance

### ✅ Agent Management
- Call assignment
- Status tracking
- Performance metrics

### ✅ Event Sourcing
- All events stored
- Complete audit trail
- Time travel capability

## 🎯 Quick Commands

```bash
# Check system readiness
python check_test_readiness.py

# Run all tests
python run_call_tests.py

# Run specific test
pytest tests/test_call_flow_e2e.py::TestInboundCallFlow::test_complete_inbound_call_with_ai -v -s

# Interactive demo
python examples/interactive_call_demo.py

# Run with coverage
pytest tests/ --cov=voicecore --cov-report=html
```

## 📊 Expected Output

### Successful Test Run

```
================================================================================
TEST: Complete Inbound Call with AI
================================================================================

📞 Step 1: Incoming call from +1234567890
   ✅ Call created

🤖 Step 2: Routing call to AI
   ✅ Call routed to AI

👋 Step 3: AI greeting
   AI: Hello! Thank you for calling. How can I help you today?
   ✅ Greeting generated

💬 Step 4: Customer interaction
   Customer: What are your business hours?
   AI: We are open Monday through Friday, 9 AM to 5 PM EST.
   ✅ AI responded successfully

📴 Step 5: Ending call
   ✅ Call ended successfully

✅ TEST PASSED
```

## 🔧 Troubleshooting

### Tests Won't Run?

```bash
# Install dependencies
pip install pytest pytest-asyncio colorama

# Setup database
alembic upgrade head
python scripts/init_project.py
```

### Import Errors?

```bash
# Add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or install in dev mode
pip install -e .
```

### Database Issues?

```bash
# Reset database
alembic downgrade base
alembic upgrade head
```

## 📚 Learn More

- **Full Guide**: [TESTING_GUIDE.md](TESTING_GUIDE.md)
- **Implementation**: [CALL_TESTING_SUMMARY.md](CALL_TESTING_SUMMARY.md)
- **Test README**: [tests/README.md](tests/README.md)

## 🎉 That's It!

You're now ready to test VoiceCore AI's call handling system!

### Next Steps

1. ✅ Run tests to verify everything works
2. ✅ Try the interactive demo
3. ✅ Read the full testing guide
4. ✅ Write your own tests
5. ✅ Deploy with confidence!

---

**Questions?** Check the troubleshooting section or review the logs.

**Ready to deploy?** All tests passing means you're good to go! 🚀
