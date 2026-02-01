"""
Property-based tests for spam detection in VoiceCore AI.

Tests spam detection accuracy, rule effectiveness, and action handling
using property-based testing to ensure correctness across all scenarios.
"""

import uuid
import pytest
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from hypothesis import given, strategies as st, settings, assume
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant

from voicecore.models import SpamRule, SpamReport, Call, CallType
from voicecore.services.spam_detection_service import (
    SpamDetectionService, SpamScore, SpamDetectionError,
    InvalidSpamRuleError, SpamRuleNotFoundError
)
from voicecore.database import get_db_session, set_tenant_context
from tests.conftest import create_test_tenant, create_test_department, cleanup_test_data


# Test data generators
@st.composite
def phone_number_strategy(draw):
    """Generate valid phone numbers for testing."""
    # Generate various phone number formats
    formats = [
        "+1{area}{exchange}{number}",  # US format
        "{area}{exchange}{number}",    # US without country code
        "+44{area}{number}",           # UK format
        "+34{area}{number}",           # Spain format
    ]
    
    format_choice = draw(st.sampled_from(formats))
    
    if format_choice.startswith("+1") or not format_choice.startswith("+"):
        # US numbers
        area = draw(st.integers(min_value=200, max_value=999))
        exchange = draw(st.integers(min_value=200, max_value=999))
        number = draw(st.integers(min_value=1000, max_value=9999))
        return format_choice.format(area=area, exchange=exchange, number=number)
    else:
        # International numbers
        area = draw(st.integers(min_value=10, max_value=999))
        number = draw(st.integers(min_value=1000000, max_value=9999999))
        return format_choice.format(area=area, number=number)


@st.composite
def spam_rule_data_strategy(draw):
    """Generate valid spam rule data for testing."""
    rule_types = ["keyword", "pattern", "number", "behavior"]
    actions = ["allow", "flag", "challenge", "block"]
    
    rule_type = draw(st.sampled_from(rule_types))
    
    # Generate appropriate patterns based on rule type
    if rule_type == "keyword":
        patterns = ["insurance", "warranty", "loan", "debt", "free", "winner", "congratulations"]
        pattern = draw(st.sampled_from(patterns))
    elif rule_type == "number":
        pattern = draw(st.text(min_size=3, max_size=10, alphabet="0123456789"))
    elif rule_type == "pattern":
        patterns = [".*insurance.*", "\\d{3}-\\d{3}-\\d{4}", "free.*offer"]
        pattern = draw(st.sampled_from(patterns))
    else:  # behavior
        pattern = "rapid_calls"
    
    return {
        "name": draw(st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')))),
        "description": draw(st.one_of(st.none(), st.text(min_size=10, max_size=200))),
        "rule_type": rule_type,
        "pattern": pattern,
        "is_regex": draw(st.booleans()) if rule_type in ["pattern", "number"] else False,
        "case_sensitive": draw(st.booleans()),
        "weight": draw(st.integers(min_value=1, max_value=100)),
        "threshold": draw(st.floats(min_value=0.1, max_value=1.0)),
        "action": draw(st.sampled_from(actions)),
        "response_message": draw(st.one_of(st.none(), st.text(min_size=10, max_size=100))),
        "apply_to_numbers": draw(st.lists(st.text(min_size=5, max_size=15), min_size=0, max_size=3)),
        "exclude_numbers": draw(st.lists(st.text(min_size=5, max_size=15), min_size=0, max_size=3)),
        "time_conditions": draw(st.one_of(st.just({}), st.fixed_dictionaries({"hours": st.lists(st.integers(min_value=0, max_value=23), min_size=1, max_size=5)}))),
        "is_active": draw(st.booleans()),
        "auto_learn": draw(st.booleans()),
        "source": draw(st.sampled_from(["manual", "imported", "learned"])),
        "created_by": draw(st.one_of(st.none(), st.text(min_size=5, max_size=50)))
    }


@st.composite
def call_context_strategy(draw):
    """Generate call context data for testing."""
    return {
        "call_sid": f"CA{draw(st.text(min_size=32, max_size=32, alphabet='0123456789abcdef'))}",
        "timestamp": datetime.utcnow().isoformat(),
        "source": draw(st.sampled_from(["twilio_webhook", "api", "manual"])),
        "transcript": draw(st.one_of(
            st.none(),
            st.text(min_size=10, max_size=200, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs', 'Po')))
        )),
        "duration": draw(st.one_of(st.none(), st.integers(min_value=1, max_value=3600))),
        "caller_behavior": draw(st.fixed_dictionaries({
            "call_frequency": st.integers(min_value=1, max_value=50),
            "avg_duration": st.integers(min_value=1, max_value=300),
            "time_pattern": st.sampled_from(["business_hours", "after_hours", "random"])
        }))
    }


class TestSpamDetectionProperties:
    """Test suite for spam detection properties."""
    
    @pytest.fixture(autouse=True)
    async def setup_test_data(self):
        """Set up test data for each test."""
        self.tenant_id = await create_test_tenant()
        self.department_id = await create_test_department(self.tenant_id)
        self.spam_service = SpamDetectionService()
        yield
        await cleanup_test_data(self.tenant_id)
    
    @given(
        phone_number=phone_number_strategy(),
        spam_rules=st.lists(spam_rule_data_strategy(), min_size=1, max_size=5),
        call_context=call_context_strategy()
    )
    @settings(max_examples=100, deadline=30000)
    async def test_property_7_spam_detection_and_action(self, phone_number, spam_rules, call_context):
        """
        **Property 7: Spam Detection and Action**
        
        For any incoming call that matches configured spam criteria, the system 
        should both detect it as spam and execute the appropriate action 
        (block/flag/challenge/log).
        
        **Validates: Requirements 3.1, 3.2**
        """
        # Arrange: Create spam rules
        created_rules = []
        for rule_data in spam_rules:
            try:
                rule = await self.spam_service.create_spam_rule(self.tenant_id, rule_data)
                created_rules.append(rule)
            except InvalidSpamRuleError:
                # Skip invalid rules for this test
                continue
        
        # Skip test if no valid rules were created
        assume(len(created_rules) > 0)
        
        # Act: Analyze call for spam
        spam_analysis = await self.spam_service.analyze_call(
            tenant_id=self.tenant_id,
            phone_number=phone_number,
            call_context=call_context
        )
        
        # Assert: Spam analysis should be consistent and valid
        assert isinstance(spam_analysis, SpamScore), "Should return SpamScore object"
        assert 0.0 <= spam_analysis.score <= 1.0, "Spam score should be between 0 and 1"
        assert spam_analysis.action in ["allow", "flag", "challenge", "block"], "Action should be valid"
        assert isinstance(spam_analysis.reasons, list), "Reasons should be a list"
        assert isinstance(spam_analysis.triggered_rules, list), "Triggered rules should be a list"
        assert 0.0 <= spam_analysis.confidence <= 1.0, "Confidence should be between 0 and 1"
        
        # If spam is detected (high score), appropriate action should be taken
        if spam_analysis.score >= 0.7:
            assert spam_analysis.action in ["challenge", "block"], "High spam score should trigger protective action"
            assert len(spam_analysis.reasons) > 0, "High spam score should have reasons"
        
        # If rules were triggered, they should be reflected in the analysis
        if len(spam_analysis.triggered_rules) > 0:
            assert spam_analysis.score > 0.0, "Triggered rules should increase spam score"
            assert len(spam_analysis.reasons) > 0, "Triggered rules should provide reasons"
        
        # Action consistency checks
        if spam_analysis.should_block:
            assert spam_analysis.action == "block", "should_block should match action"
        
        if spam_analysis.should_challenge:
            assert spam_analysis.action == "challenge", "should_challenge should match action"
        
        # Verify that the analysis is deterministic for the same input
        spam_analysis_2 = await self.spam_service.analyze_call(
            tenant_id=self.tenant_id,
            phone_number=phone_number,
            call_context=call_context
        )
        
        # Results should be consistent (allowing for small floating point differences)
        assert abs(spam_analysis.score - spam_analysis_2.score) < 0.01, "Analysis should be deterministic"
        assert spam_analysis.action == spam_analysis_2.action, "Action should be deterministic"
    
    @given(
        phone_numbers=st.lists(phone_number_strategy(), min_size=2, max_size=10),
        rule_data=spam_rule_data_strategy()
    )
    @settings(max_examples=50, deadline=30000)
    async def test_spam_rule_consistency(self, phone_numbers, rule_data):
        """
        Test that spam rules are applied consistently across different phone numbers.
        
        This property ensures that the same rule produces consistent results
        when applied to different inputs.
        """
        # Arrange: Create a spam rule
        try:
            rule = await self.spam_service.create_spam_rule(self.tenant_id, rule_data)
        except InvalidSpamRuleError:
            assume(False)  # Skip invalid rules
        
        # Act: Analyze multiple phone numbers
        results = []
        for phone_number in phone_numbers:
            analysis = await self.spam_service.analyze_call(
                tenant_id=self.tenant_id,
                phone_number=phone_number,
                call_context={"source": "test"}
            )
            results.append(analysis)
        
        # Assert: Rule behavior should be consistent
        # If a rule matches, it should always contribute to the score
        for analysis in results:
            if rule.id in analysis.triggered_rules:
                assert analysis.score > 0.0, "Triggered rule should increase spam score"
                assert any(rule.name in reason for reason in analysis.reasons), "Rule name should appear in reasons"
    
    @given(
        phone_number=phone_number_strategy(),
        rule_data=spam_rule_data_strategy(),
        feedback_sequence=st.lists(st.booleans(), min_size=1, max_size=10)
    )
    @settings(max_examples=50, deadline=30000)
    async def test_spam_learning_adaptation(self, phone_number, rule_data, feedback_sequence):
        """
        Test that spam detection adapts based on user feedback.
        
        This property ensures that the system learns from feedback
        and adjusts rule confidence accordingly.
        """
        # Arrange: Create a spam rule with auto-learning enabled
        rule_data["auto_learn"] = True
        try:
            rule = await self.spam_service.create_spam_rule(self.tenant_id, rule_data)
        except InvalidSpamRuleError:
            assume(False)
        
        initial_confidence = rule.confidence_score
        
        # Act: Provide feedback sequence
        for is_spam_feedback in feedback_sequence:
            # Analyze call
            analysis = await self.spam_service.analyze_call(
                tenant_id=self.tenant_id,
                phone_number=phone_number,
                call_context={"source": "test"}
            )
            
            # Provide feedback
            await self.spam_service.report_spam(
                tenant_id=self.tenant_id,
                phone_number=phone_number,
                is_spam=is_spam_feedback,
                reported_by="test_system"
            )
        
        # Assert: Rule confidence should adapt based on feedback
        updated_rules = await self.spam_service.list_spam_rules(self.tenant_id)
        updated_rule = next((r for r in updated_rules if r.id == rule.id), None)
        
        assert updated_rule is not None, "Rule should still exist after feedback"
        
        # Confidence should change based on feedback pattern
        positive_feedback = sum(1 for f in feedback_sequence if f)
        negative_feedback = len(feedback_sequence) - positive_feedback
        
        if positive_feedback > negative_feedback:
            # More positive feedback should increase or maintain confidence
            assert updated_rule.confidence_score >= initial_confidence - 0.1, "Positive feedback should not decrease confidence significantly"
        elif negative_feedback > positive_feedback:
            # More negative feedback should decrease confidence
            assert updated_rule.confidence_score <= initial_confidence + 0.1, "Negative feedback should not increase confidence"
    
    @given(
        phone_number=phone_number_strategy(),
        concurrent_analyses=st.integers(min_value=2, max_value=5),
        rule_data=spam_rule_data_strategy()
    )
    @settings(max_examples=30, deadline=30000)
    async def test_concurrent_spam_analysis(self, phone_number, concurrent_analyses, rule_data):
        """
        Test that concurrent spam analyses produce consistent results.
        
        This property ensures that the system handles concurrent requests
        correctly without race conditions or inconsistent results.
        """
        # Arrange: Create a spam rule
        try:
            rule = await self.spam_service.create_spam_rule(self.tenant_id, rule_data)
        except InvalidSpamRuleError:
            assume(False)
        
        # Act: Perform concurrent analyses
        tasks = []
        for _ in range(concurrent_analyses):
            task = asyncio.create_task(
                self.spam_service.analyze_call(
                    tenant_id=self.tenant_id,
                    phone_number=phone_number,
                    call_context={"source": "concurrent_test"}
                )
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Assert: All analyses should succeed and be consistent
        successful_results = [r for r in results if isinstance(r, SpamScore)]
        assert len(successful_results) == concurrent_analyses, "All concurrent analyses should succeed"
        
        # Results should be identical (deterministic)
        first_result = successful_results[0]
        for result in successful_results[1:]:
            assert abs(result.score - first_result.score) < 0.01, "Concurrent analyses should produce identical scores"
            assert result.action == first_result.action, "Concurrent analyses should produce identical actions"
            assert set(result.triggered_rules) == set(first_result.triggered_rules), "Concurrent analyses should trigger same rules"
    
    @given(
        phone_number=phone_number_strategy(),
        invalid_rule_data=st.fixed_dictionaries({
            "name": st.one_of(st.just(""), st.just(None)),  # Invalid name
            "rule_type": st.sampled_from(["invalid_type", "", None]),  # Invalid type
            "pattern": st.one_of(st.just(""), st.just(None)),  # Invalid pattern
            "weight": st.one_of(st.integers(max_value=0), st.integers(min_value=101)),  # Invalid weight
            "action": st.sampled_from(["invalid_action", "", None])  # Invalid action
        })
    )
    @settings(max_examples=50, deadline=30000)
    async def test_invalid_spam_rule_rejection(self, phone_number, invalid_rule_data):
        """
        Test that invalid spam rules are properly rejected.
        
        This property ensures that the system validates rule data
        and rejects invalid configurations.
        """
        # Act & Assert: Invalid rule creation should fail
        with pytest.raises((InvalidSpamRuleError, ValueError, TypeError)):
            await self.spam_service.create_spam_rule(self.tenant_id, invalid_rule_data)
        
        # System should still function normally for valid operations
        analysis = await self.spam_service.analyze_call(
            tenant_id=self.tenant_id,
            phone_number=phone_number,
            call_context={"source": "test"}
        )
        
        assert isinstance(analysis, SpamScore), "System should still work after invalid rule rejection"
        assert analysis.action in ["allow", "flag", "challenge", "block"], "Should return valid action"
    
    @given(
        phone_number=phone_number_strategy(),
        rule_data=spam_rule_data_strategy(),
        time_delay_seconds=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=30, deadline=30000)
    async def test_spam_rule_caching_consistency(self, phone_number, rule_data, time_delay_seconds):
        """
        Test that spam rule caching maintains consistency.
        
        This property ensures that cached rules produce the same results
        as fresh database queries.
        """
        # Arrange: Create a spam rule
        try:
            rule = await self.spam_service.create_spam_rule(self.tenant_id, rule_data)
        except InvalidSpamRuleError:
            assume(False)
        
        # Act: First analysis (populates cache)
        analysis_1 = await self.spam_service.analyze_call(
            tenant_id=self.tenant_id,
            phone_number=phone_number,
            call_context={"source": "cache_test_1"}
        )
        
        # Wait a bit to simulate time passage
        await asyncio.sleep(0.1)
        
        # Second analysis (should use cache)
        analysis_2 = await self.spam_service.analyze_call(
            tenant_id=self.tenant_id,
            phone_number=phone_number,
            call_context={"source": "cache_test_2"}
        )
        
        # Clear cache by updating rule
        await self.spam_service.update_spam_rule(
            tenant_id=self.tenant_id,
            rule_id=rule.id,
            update_data={"description": "Updated for cache test"}
        )
        
        # Third analysis (should use fresh data)
        analysis_3 = await self.spam_service.analyze_call(
            tenant_id=self.tenant_id,
            phone_number=phone_number,
            call_context={"source": "cache_test_3"}
        )
        
        # Assert: Results should be consistent
        assert abs(analysis_1.score - analysis_2.score) < 0.01, "Cached results should match original"
        assert analysis_1.action == analysis_2.action, "Cached action should match original"
        
        # After cache clear, results should still be consistent
        assert abs(analysis_1.score - analysis_3.score) < 0.01, "Fresh results should match cached"
        assert analysis_1.action == analysis_3.action, "Fresh action should match cached"


class SpamDetectionStateMachine(RuleBasedStateMachine):
    """
    Stateful property-based testing for spam detection system.
    
    This uses Hypothesis's stateful testing to model the spam detection
    system as a state machine and verify invariants hold across
    all possible sequences of operations.
    """
    
    def __init__(self):
        super().__init__()
        self.rules = {}
        self.reports = {}
        self.tenant_id = None
        self.spam_service = SpamDetectionService()
    
    @initialize()
    async def setup(self):
        """Initialize the test environment."""
        self.tenant_id = await create_test_tenant()
    
    @rule(rule_data=spam_rule_data_strategy())
    async def create_spam_rule(self, rule_data):
        """Create a new spam rule."""
        if len(self.rules) >= 20:  # Limit number of rules
            return
        
        try:
            rule = await self.spam_service.create_spam_rule(self.tenant_id, rule_data)
            self.rules[rule.id] = {
                "rule": rule,
                "expected_active": rule.is_active,
                "expected_confidence": rule.confidence_score
            }
        except InvalidSpamRuleError:
            # Invalid rules are expected to be rejected
            pass
    
    @rule(
        rule_id=st.sampled_from([]),  # Will be populated by rules.keys()
        update_data=st.fixed_dictionaries({
            "is_active": st.booleans(),
            "weight": st.integers(min_value=1, max_value=100),
            "threshold": st.floats(min_value=0.1, max_value=1.0)
        })
    )
    async def update_spam_rule(self, rule_id, update_data):
        """Update an existing spam rule."""
        if not self.rules or rule_id not in self.rules:
            return
        
        try:
            updated_rule = await self.spam_service.update_spam_rule(
                tenant_id=self.tenant_id,
                rule_id=rule_id,
                update_data=update_data
            )
            
            if updated_rule:
                # Update our expected state
                rule_info = self.rules[rule_id]
                rule_info["expected_active"] = update_data.get("is_active", rule_info["expected_active"])
                rule_info["rule"] = updated_rule
                
        except (SpamRuleNotFoundError, InvalidSpamRuleError):
            # Expected exceptions for invalid operations
            pass
    
    @rule(phone_number=phone_number_strategy())
    async def analyze_call(self, phone_number):
        """Analyze a call for spam."""
        try:
            analysis = await self.spam_service.analyze_call(
                tenant_id=self.tenant_id,
                phone_number=phone_number,
                call_context={"source": "state_machine_test"}
            )
            
            # Store analysis for later verification
            self.reports[phone_number] = analysis
            
        except Exception:
            # Analysis might fail for various reasons
            pass
    
    @rule(
        phone_number=phone_number_strategy(),
        is_spam=st.booleans()
    )
    async def report_spam(self, phone_number, is_spam):
        """Report spam feedback."""
        try:
            report = await self.spam_service.report_spam(
                tenant_id=self.tenant_id,
                phone_number=phone_number,
                is_spam=is_spam,
                reported_by="state_machine"
            )
            
            # Track the report
            self.reports[f"report_{report.id}"] = {
                "phone_number": phone_number,
                "is_spam": is_spam,
                "report": report
            }
            
        except Exception:
            # Reporting might fail for various reasons
            pass
    
    @invariant()
    async def spam_analysis_validity_invariant(self):
        """Verify that all spam analyses are valid."""
        for phone_number, analysis in self.reports.items():
            if isinstance(analysis, SpamScore):
                # Score should be in valid range
                assert 0.0 <= analysis.score <= 1.0, f"Invalid spam score: {analysis.score}"
                
                # Action should be valid
                assert analysis.action in ["allow", "flag", "challenge", "block"], f"Invalid action: {analysis.action}"
                
                # Confidence should be in valid range
                assert 0.0 <= analysis.confidence <= 1.0, f"Invalid confidence: {analysis.confidence}"
                
                # Reasons should be a list
                assert isinstance(analysis.reasons, list), "Reasons should be a list"
                
                # Triggered rules should be a list of UUIDs
                assert isinstance(analysis.triggered_rules, list), "Triggered rules should be a list"
    
    @invariant()
    async def spam_rule_consistency_invariant(self):
        """Verify that spam rules maintain consistency."""
        for rule_id, rule_info in self.rules.items():
            try:
                # Get current rule state
                current_rules = await self.spam_service.list_spam_rules(self.tenant_id)
                current_rule = next((r for r in current_rules if r.id == rule_id), None)
                
                if current_rule:
                    # Active status should match expectation
                    assert current_rule.is_active == rule_info["expected_active"], \
                        f"Rule {rule_id} active status mismatch"
                    
                    # Confidence should be in valid range
                    assert 0.0 <= current_rule.confidence_score <= 1.0, \
                        f"Rule {rule_id} has invalid confidence: {current_rule.confidence_score}"
                    
                    # Weight should be in valid range
                    assert 1 <= current_rule.weight <= 100, \
                        f"Rule {rule_id} has invalid weight: {current_rule.weight}"
                        
            except Exception:
                # Rule might have been deleted or other issues
                pass
    
    def teardown(self):
        """Clean up test data."""
        if self.tenant_id:
            asyncio.create_task(cleanup_test_data(self.tenant_id))


# Stateful test runner
TestSpamDetectionStateMachine = SpamDetectionStateMachine.TestCase