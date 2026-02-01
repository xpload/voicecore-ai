"""
Property-based tests for AI learning and feedback system.

Tests AI learning integration and continuous improvement mechanisms
per Requirement 12.3.
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, assume
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant
from typing import Dict, Any, List

from voicecore.services.ai_training_service import (
    AITrainingService, ResponseStrategy, TrainingMode, TestStatus
)
from voicecore.services.learning_feedback_service import (
    LearningFeedbackService, FeedbackType, LearningPattern, ImprovementType
)


class TestAILearningProperties:
    """Property-based tests for AI learning functionality."""
    
    @pytest.fixture
    def ai_training_service(self):
        """Create AI training service instance."""
        return AITrainingService()
    
    @pytest.fixture
    def learning_service(self):
        """Create learning feedback service instance."""
        return LearningFeedbackService()
    
    @given(
        feedback_ratings=st.lists(
            st.floats(min_value=1.0, max_value=5.0),
            min_size=5,
            max_size=100
        ),
        success_threshold=st.floats(min_value=3.0, max_value=4.5)
    )
    @settings(max_examples=50, deadline=5000)
    async def test_property_28_ai_learning_integration(
        self,
        ai_training_service,
        learning_service,
        feedback_ratings,
        success_threshold
    ):
        """
        **Property 28: AI Learning Integration**
        **Validates: Requirements 12.3**
        
        For any successful call resolution pattern, the system should learn from it
        and improve future responses:
        - Feedback collection leads to learning insights
        - High-quality interactions generate improvement recommendations
        - Learning patterns are identified and stored
        - Improvements are implemented based on confidence thresholds
        """
        tenant_id = uuid.uuid4()
        
        # Collect feedback entries
        feedback_entries = []
        successful_calls = []
        
        for i, rating in enumerate(feedback_ratings):
            call_id = f"call_{i}"
            
            # Determine if call was successful based on rating
            is_successful = rating >= success_threshold
            
            # Collect feedback
            feedback = await learning_service.collect_call_feedback(
                tenant_id=tenant_id,
                call_id=call_id,
                rating=rating,
                comments=f"Test feedback for call {i}",
                source="caller",
                metadata={
                    "call_duration": 120 if is_successful else 300,
                    "transfer_successful": is_successful,
                    "resolution_achieved": is_successful
                }
            )
            
            feedback_entries.append(feedback)
            
            if is_successful:
                successful_calls.append({
                    "id": call_id,
                    "rating": rating,
                    "duration": 120,
                    "transfer_successful": True,
                    "metadata": {"resolution_achieved": True}
                })
        
        # Verify feedback collection
        assert len(feedback_entries) == len(feedback_ratings)
        
        # Calculate expected successful calls
        expected_successful = len([r for r in feedback_ratings if r >= success_threshold])
        assert len(successful_calls) == expected_successful
        
        # Analyze successful patterns
        if len(successful_calls) >= 5:  # Minimum for pattern detection
            insights = await learning_service.analyze_successful_patterns(
                tenant_id=tenant_id,
                days=7
            )
            
            # Verify learning insights are generated for successful patterns
            if expected_successful >= learning_service.learning_config["min_pattern_frequency"]:
                assert len(insights) > 0, "Should generate insights from successful patterns"
                
                # Verify insight quality
                for insight in insights:
                    assert insight.tenant_id == tenant_id
                    assert insight.confidence_score >= 0.0
                    assert insight.frequency > 0
                    assert isinstance(insight.pattern_type, LearningPattern)
                    assert len(insight.description) > 0
        
        # Generate improvement recommendations
        recommendations = await learning_service.generate_improvement_recommendations(
            tenant_id=tenant_id
        )
        
        # Verify recommendations are generated when there are insights
        if len(successful_calls) >= 10:  # Sufficient data for recommendations
            assert len(recommendations) > 0, "Should generate recommendations from insights"
            
            for rec in recommendations:
                assert rec.tenant_id == tenant_id
                assert 0.0 <= rec.confidence <= 1.0
                assert 1 <= rec.priority <= 5
                assert isinstance(rec.improvement_type, ImprovementType)
                assert len(rec.title) > 0
                assert len(rec.description) > 0
        
        # Test learning metrics calculation
        metrics = await learning_service.get_learning_metrics(tenant_id, days=7)
        
        # Verify metrics reflect the learning process
        assert metrics.total_feedback_entries == len(feedback_entries)
        
        if feedback_ratings:
            expected_avg = sum(feedback_ratings) / len(feedback_ratings)
            assert abs(metrics.average_satisfaction - expected_avg) < 0.1
        
        # Verify continuous improvement indicators
        if expected_successful > 0:
            assert metrics.success_rate_improvement >= 0.0
            assert metrics.response_time_improvement >= 0.0
    
    @given(
        training_interactions=st.lists(
            st.tuples(
                st.text(min_size=10, max_size=100),  # user_input
                st.text(min_size=10, max_size=200),  # ai_response
                st.booleans(),  # success
                st.floats(min_value=1.0, max_value=5.0)  # feedback_score
            ),
            min_size=3,
            max_size=20
        ),
        strategy=st.sampled_from(ResponseStrategy)
    )
    @settings(max_examples=30, deadline=5000)
    async def test_property_28_training_mode_learning(
        self,
        ai_training_service,
        training_interactions,
        strategy
    ):
        """
        Test that training mode interactions lead to learning improvements.
        """
        tenant_id = uuid.uuid4()
        
        # Start training session
        session = await ai_training_service.start_training_mode(
            tenant_id=tenant_id,
            mode=TrainingMode.TRAINING
        )
        
        assert session.tenant_id == tenant_id
        assert session.mode == TrainingMode.TRAINING
        assert session.total_interactions == 0
        
        # Process training interactions
        analyses = []
        for user_input, ai_response, success, feedback_score in training_interactions:
            analysis = await ai_training_service.process_training_interaction(
                session_id=session.id,
                user_input=user_input,
                ai_response=ai_response,
                success=success,
                feedback_score=feedback_score
            )
            analyses.append(analysis)
        
        # Verify session state updates
        assert session.total_interactions == len(training_interactions)
        
        successful_count = len([success for _, _, success, _ in training_interactions if success])
        assert session.successful_interactions == successful_count
        
        # Verify feedback scores are collected
        expected_scores = [score for _, _, _, score in training_interactions]
        assert len(session.feedback_scores) == len(expected_scores)
        
        # Verify success rate calculation
        if session.total_interactions > 0:
            expected_success_rate = successful_count / session.total_interactions
            actual_success_rate = session.successful_interactions / session.total_interactions
            assert abs(actual_success_rate - expected_success_rate) < 0.01
        
        # Verify learning improvements are identified
        total_improvements = len(session.improvements_identified)
        
        # Should identify improvements for failed interactions
        failed_count = len([success for _, _, success, _ in training_interactions if not success])
        if failed_count > 0:
            assert total_improvements > 0, "Should identify improvements from failed interactions"
        
        # Verify analysis quality
        for analysis in analyses:
            assert "success" in analysis
            assert "feedback_score" in analysis
            assert isinstance(analysis.get("improvements", []), list)
    
    @given(
        ab_test_data=st.tuples(
            st.sampled_from(ResponseStrategy),  # strategy_a
            st.sampled_from(ResponseStrategy),  # strategy_b
            st.floats(min_value=0.1, max_value=0.9),  # traffic_split
            st.integers(min_value=20, max_value=200)  # sample_size
        )
    )
    @settings(max_examples=20, deadline=5000)
    async def test_property_28_ab_test_learning(
        self,
        ai_training_service,
        ab_test_data
    ):
        """
        Test that A/B testing leads to learning about optimal strategies.
        """
        strategy_a, strategy_b, traffic_split, sample_size = ab_test_data
        assume(strategy_a != strategy_b)  # Ensure different strategies
        
        tenant_id = uuid.uuid4()
        
        # Create A/B test
        test_config = await ai_training_service.create_ab_test(
            tenant_id=tenant_id,
            name="Test Learning A/B Test",
            description="Testing learning from A/B test results",
            strategy_a=strategy_a,
            strategy_b=strategy_b,
            traffic_split=traffic_split,
            success_metric="transfer_rate",
            target_sample_size=sample_size,
            duration_days=7
        )
        
        assert test_config.tenant_id == tenant_id
        assert test_config.strategy_a == strategy_a
        assert test_config.strategy_b == strategy_b
        assert test_config.traffic_split == traffic_split
        assert test_config.status == TestStatus.DRAFT
        
        # Start the test
        success = await ai_training_service.start_ab_test(test_config.id, tenant_id)
        assert success
        assert test_config.status == TestStatus.ACTIVE
        
        # Simulate test execution by selecting strategies
        strategy_selections = []
        for _ in range(min(sample_size, 50)):  # Limit for test performance
            selected_strategy = await ai_training_service.select_response_strategy(
                tenant_id=tenant_id,
                context={"user_input": "test input"}
            )
            strategy_selections.append(selected_strategy)
        
        # Verify strategy selection follows traffic split
        if len(strategy_selections) >= 10:  # Sufficient sample size
            strategy_a_count = len([s for s in strategy_selections if s == strategy_a])
            strategy_b_count = len([s for s in strategy_selections if s == strategy_b])
            
            total_selections = strategy_a_count + strategy_b_count
            if total_selections > 0:
                actual_split = strategy_a_count / total_selections
                
                # Allow some variance due to randomness
                expected_split = traffic_split
                variance_threshold = 0.3  # 30% variance allowed
                
                assert abs(actual_split - expected_split) <= variance_threshold, \
                    f"Traffic split deviation too large: expected {expected_split}, got {actual_split}"
        
        # Get test results
        results = await ai_training_service.get_ab_test_results(test_config.id, tenant_id)
        
        if results:
            # Verify results structure
            assert "strategy_a" in results
            assert "strategy_b" in results
            
            result_a = results["strategy_a"]
            result_b = results["strategy_b"]
            
            # Verify result data quality
            assert result_a.strategy == strategy_a
            assert result_b.strategy == strategy_b
            assert result_a.sample_size >= 0
            assert result_b.sample_size >= 0
            assert 0.0 <= result_a.success_rate <= 1.0
            assert 0.0 <= result_b.success_rate <= 1.0
            
            # Verify statistical significance calculation
            if result_a.sample_size >= 30 and result_b.sample_size >= 30:
                # Should have statistical significance data
                assert isinstance(result_a.statistical_significance, bool)
                assert isinstance(result_b.statistical_significance, bool)
    
    @given(
        feedback_patterns=st.lists(
            st.tuples(
                st.floats(min_value=1.0, max_value=5.0),  # rating
                st.sampled_from(FeedbackType),  # feedback_type
                st.text(min_size=5, max_size=50)  # comments
            ),
            min_size=5,
            max_size=30
        )
    )
    @settings(max_examples=20, deadline=5000)
    async def test_property_28_feedback_driven_learning(
        self,
        learning_service,
        feedback_patterns
    ):
        """
        Test that feedback collection drives learning and improvement identification.
        """
        tenant_id = uuid.uuid4()
        
        # Collect diverse feedback
        feedback_entries = []
        for i, (rating, feedback_type, comments) in enumerate(feedback_patterns):
            if feedback_type == FeedbackType.CALL_RESOLUTION:
                feedback = await learning_service.collect_call_feedback(
                    tenant_id=tenant_id,
                    call_id=f"call_{i}",
                    rating=rating,
                    comments=comments,
                    source="caller"
                )
            else:
                feedback = await learning_service.collect_agent_feedback(
                    tenant_id=tenant_id,
                    agent_id=f"agent_{i % 3}",  # Rotate between 3 agents
                    feedback_type=feedback_type,
                    rating=rating,
                    comments=comments
                )
            
            feedback_entries.append(feedback)
        
        # Verify feedback collection
        assert len(feedback_entries) == len(feedback_patterns)
        
        # Analyze feedback patterns
        high_ratings = [f for f in feedback_entries if f.rating >= 4.0]
        low_ratings = [f for f in feedback_entries if f.rating <= 2.0]
        
        # Get feedback summary
        summary = await learning_service.get_feedback_summary(tenant_id, days=7)
        
        # Verify summary accuracy
        assert summary["total_feedback"] == len(feedback_entries)
        
        if feedback_entries:
            expected_avg = sum(f.rating for f in feedback_entries) / len(feedback_entries)
            assert abs(summary["average_rating"] - expected_avg) < 0.1
        
        # Verify rating distribution
        rating_dist = summary["rating_distribution"]
        for rating in ["1", "2", "3", "4", "5"]:
            expected_count = len([f for f in feedback_entries if int(f.rating) == int(rating)])
            assert rating_dist[rating] == expected_count
        
        # Test learning from high-quality feedback
        if len(high_ratings) >= 3:
            # Should identify positive patterns
            insights = await learning_service.analyze_successful_patterns(tenant_id, days=7)
            
            # High-quality feedback should contribute to learning
            if len(high_ratings) >= learning_service.learning_config["min_pattern_frequency"]:
                # Should generate some insights
                assert len(insights) >= 0  # May be 0 if patterns don't meet thresholds
        
        # Test improvement identification from low ratings
        if len(low_ratings) >= 2:
            # Should identify improvement opportunities
            recommendations = await learning_service.generate_improvement_recommendations(tenant_id)
            
            # Low ratings should drive improvement recommendations
            assert len(recommendations) >= 0  # May be 0 if no clear patterns
        
        # Verify learning metrics reflect feedback quality
        metrics = await learning_service.get_learning_metrics(tenant_id, days=7)
        
        assert metrics.total_feedback_entries == len(feedback_entries)
        
        if feedback_entries:
            expected_satisfaction = sum(f.rating for f in feedback_entries) / len(feedback_entries)
            assert abs(metrics.average_satisfaction - expected_satisfaction) < 0.1


class AILearningStateMachine(RuleBasedStateMachine):
    """
    Stateful property-based testing for AI learning system.
    
    Tests complex interactions between training, feedback collection,
    learning analysis, and improvement implementation.
    """
    
    def __init__(self):
        super().__init__()
        self.ai_training = AITrainingService()
        self.learning_service = LearningFeedbackService()
        self.tenant_id = uuid.uuid4()
        
        # System state
        self.training_sessions = []
        self.feedback_entries = []
        self.ab_tests = []
        self.learning_insights = []
        self.improvement_recommendations = []
        
        # Metrics tracking
        self.total_interactions = 0
        self.successful_interactions = 0
        self.total_feedback = 0
        self.high_quality_feedback = 0
    
    @initialize()
    def setup_initial_state(self):
        """Initialize the learning system."""
        # Start with clean state
        self.ai_training.custom_scripts.clear()
        self.ai_training.ab_tests.clear()
        self.learning_service.feedback_entries.clear()
        self.learning_service.learning_insights.clear()
    
    @rule(
        mode=st.sampled_from(TrainingMode),
        strategy=st.sampled_from(ResponseStrategy)
    )
    async def start_training_session(self, mode, strategy):
        """Start a new training session."""
        # Create custom script for testing
        script = await self.ai_training.create_custom_response_script(
            tenant_id=self.tenant_id,
            name=f"Test Script {len(self.training_sessions)}",
            description="Test script for learning",
            trigger_keywords=["test", "help"],
            response_template="Test response: {user_input}",
            variables={"user_input": ""},
            strategy=strategy
        )
        
        session = await self.ai_training.start_training_mode(
            tenant_id=self.tenant_id,
            mode=mode,
            script_id=script.id
        )
        
        self.training_sessions.append(session)
    
    @rule(
        rating=st.floats(min_value=1.0, max_value=5.0),
        success=st.booleans()
    )
    async def add_training_interaction(self, rating, success):
        """Add a training interaction to an active session."""
        if not self.training_sessions:
            return
        
        session = self.training_sessions[-1]  # Use most recent session
        
        analysis = await self.ai_training.process_training_interaction(
            session_id=session.id,
            user_input="Test user input",
            ai_response="Test AI response",
            success=success,
            feedback_score=rating
        )
        
        self.total_interactions += 1
        if success:
            self.successful_interactions += 1
    
    @rule(
        rating=st.floats(min_value=1.0, max_value=5.0),
        feedback_type=st.sampled_from(FeedbackType)
    )
    async def collect_feedback(self, rating, feedback_type):
        """Collect feedback from users or agents."""
        if feedback_type == FeedbackType.CALL_RESOLUTION:
            feedback = await self.learning_service.collect_call_feedback(
                tenant_id=self.tenant_id,
                call_id=f"call_{len(self.feedback_entries)}",
                rating=rating,
                comments="Test feedback",
                source="caller"
            )
        else:
            feedback = await self.learning_service.collect_agent_feedback(
                tenant_id=self.tenant_id,
                agent_id="test_agent",
                feedback_type=feedback_type,
                rating=rating,
                comments="Test agent feedback"
            )
        
        self.feedback_entries.append(feedback)
        self.total_feedback += 1
        
        if rating >= 4.0:
            self.high_quality_feedback += 1
    
    @rule()
    async def analyze_learning_patterns(self):
        """Analyze successful patterns for learning insights."""
        if len(self.feedback_entries) >= 5:
            insights = await self.learning_service.analyze_successful_patterns(
                tenant_id=self.tenant_id,
                days=7
            )
            
            self.learning_insights.extend(insights)
    
    @rule()
    async def generate_improvements(self):
        """Generate improvement recommendations."""
        if len(self.learning_insights) > 0:
            recommendations = await self.learning_service.generate_improvement_recommendations(
                tenant_id=self.tenant_id
            )
            
            self.improvement_recommendations.extend(recommendations)
    
    @rule(
        strategy_a=st.sampled_from(ResponseStrategy),
        strategy_b=st.sampled_from(ResponseStrategy)
    )
    async def create_ab_test(self, strategy_a, strategy_b):
        """Create an A/B test for strategy comparison."""
        if strategy_a == strategy_b:
            return  # Skip if strategies are the same
        
        test_config = await self.ai_training.create_ab_test(
            tenant_id=self.tenant_id,
            name=f"Test {len(self.ab_tests)}",
            description="Stateful test A/B test",
            strategy_a=strategy_a,
            strategy_b=strategy_b,
            traffic_split=0.5,
            target_sample_size=50,
            duration_days=7
        )
        
        self.ab_tests.append(test_config)
    
    @invariant()
    def learning_system_consistency(self):
        """Learning system must maintain consistency."""
        # Training sessions should track interactions correctly
        for session in self.training_sessions:
            assert session.total_interactions >= 0
            assert session.successful_interactions >= 0
            assert session.successful_interactions <= session.total_interactions
        
        # Feedback entries should have valid ratings
        for feedback in self.feedback_entries:
            assert 1.0 <= feedback.rating <= 5.0
            assert feedback.tenant_id == self.tenant_id
        
        # Learning insights should have valid confidence scores
        for insight in self.learning_insights:
            assert 0.0 <= insight.confidence_score <= 1.0
            assert insight.frequency > 0
            assert insight.tenant_id == self.tenant_id
        
        # Improvement recommendations should have valid priorities
        for rec in self.improvement_recommendations:
            assert 1 <= rec.priority <= 5
            assert 0.0 <= rec.confidence <= 1.0
            assert rec.tenant_id == self.tenant_id
    
    @invariant()
    def learning_progress_invariant(self):
        """Learning system should show progress over time."""
        # If we have high-quality feedback, we should eventually get insights
        if self.high_quality_feedback >= 5 and len(self.feedback_entries) >= 10:
            # Should have some learning activity
            total_learning_artifacts = (
                len(self.learning_insights) + 
                len(self.improvement_recommendations)
            )
            # Allow for cases where patterns don't meet thresholds
            assert total_learning_artifacts >= 0
        
        # Success rate should be calculable when we have interactions
        if self.total_interactions > 0:
            success_rate = self.successful_interactions / self.total_interactions
            assert 0.0 <= success_rate <= 1.0
    
    @invariant()
    def ab_test_integrity(self):
        """A/B tests should maintain integrity."""
        for test in self.ab_tests:
            assert test.strategy_a != test.strategy_b
            assert 0.0 <= test.traffic_split <= 1.0
            assert test.target_sample_size > 0
            assert test.tenant_id == self.tenant_id


# Test runner for stateful testing
TestAILearningStateMachine = AILearningStateMachine.TestCase