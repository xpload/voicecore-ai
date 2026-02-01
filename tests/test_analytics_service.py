"""
Tests for Analytics Service.

This module contains unit tests for the analytics data collection
and reporting functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from voicecore.services.analytics_service import AnalyticsService
from voicecore.models.analytics import CallAnalytics, AgentMetrics, SystemMetrics


class TestAnalyticsService:
    """Test suite for AnalyticsService."""
    
    @pytest.fixture
    def analytics_service(self):
        """Create analytics service instance."""
        return AnalyticsService()
    
    @pytest.fixture
    def sample_tenant_id(self):
        """Sample tenant ID for testing."""
        return uuid4()
    
    @pytest.fixture
    def sample_agent_id(self):
        """Sample agent ID for testing."""
        return uuid4()
    
    @pytest.mark.asyncio
    async def test_collect_call_metrics(self, analytics_service, sample_tenant_id):
        """Test call metrics collection."""
        with patch('voicecore.services.analytics_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Mock query results
            mock_result = MagicMock()
            mock_result.scalar.return_value = 150  # Total calls
            mock_session.execute.return_value = mock_result
            
            metrics = await analytics_service.collect_call_metrics(sample_tenant_id)
            
            assert metrics is not None
            assert 'total_calls' in metrics
            assert 'successful_calls' in metrics
            assert 'failed_calls' in metrics
            assert 'average_duration' in metrics
            
    @pytest.mark.asyncio
    async def test_collect_agent_metrics(self, analytics_service, sample_tenant_id, sample_agent_id):
        """Test agent metrics collection."""
        with patch('voicecore.services.analytics_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Mock query results
            mock_result = MagicMock()
            mock_result.scalar.return_value = 25  # Calls handled
            mock_session.execute.return_value = mock_result
            
            metrics = await analytics_service.collect_agent_metrics(
                sample_tenant_id, 
                sample_agent_id
            )
            
            assert metrics is not None
            assert 'calls_handled' in metrics
            assert 'average_call_duration' in metrics
            assert 'successful_transfers' in metrics
            
    @pytest.mark.asyncio
    async def test_collect_system_metrics(self, analytics_service):
        """Test system metrics collection."""
        with patch('voicecore.services.analytics_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Mock system metrics
            mock_result = MagicMock()
            mock_result.scalar.return_value = 5  # Active tenants
            mock_session.execute.return_value = mock_result
            
            metrics = await analytics_service.collect_system_metrics()
            
            assert metrics is not None
            assert 'active_tenants' in metrics
            assert 'total_calls_today' in metrics
            assert 'system_uptime' in metrics
            
    @pytest.mark.asyncio
    async def test_get_dashboard_data(self, analytics_service, sample_tenant_id):
        """Test dashboard data generation."""
        with patch('voicecore.services.analytics_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Mock dashboard queries
            mock_result = MagicMock()
            mock_result.scalar.return_value = 100
            mock_session.execute.return_value = mock_result
            
            dashboard_data = await analytics_service.get_dashboard_data(sample_tenant_id)
            
            assert dashboard_data is not None
            assert 'call_volume' in dashboard_data
            assert 'agent_performance' in dashboard_data
            assert 'system_health' in dashboard_data
            
    @pytest.mark.asyncio
    async def test_get_agent_performance_stats(self, analytics_service, sample_tenant_id):
        """Test agent performance statistics."""
        with patch('voicecore.services.analytics_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Mock agent performance data
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [
                (sample_tenant_id, "Agent 1", 50, 300.0, 45),
                (sample_tenant_id, "Agent 2", 35, 250.0, 30)
            ]
            mock_session.execute.return_value = mock_result
            
            stats = await analytics_service.get_agent_performance_stats(sample_tenant_id)
            
            assert isinstance(stats, list)
            assert len(stats) == 2
            assert all('agent_name' in stat for stat in stats)
            assert all('calls_handled' in stat for stat in stats)
            
    @pytest.mark.asyncio
    async def test_store_call_analytics(self, analytics_service, sample_tenant_id):
        """Test storing call analytics data."""
        with patch('voicecore.services.analytics_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            call_data = {
                'call_id': str(uuid4()),
                'duration': 300,
                'outcome': 'completed',
                'transfer_count': 1
            }
            
            await analytics_service.store_call_analytics(sample_tenant_id, call_data)
            
            # Verify session operations
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_store_agent_metrics(self, analytics_service, sample_tenant_id, sample_agent_id):
        """Test storing agent metrics data."""
        with patch('voicecore.services.analytics_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            agent_data = {
                'calls_handled': 25,
                'average_duration': 280.5,
                'successful_transfers': 20
            }
            
            await analytics_service.store_agent_metrics(
                sample_tenant_id, 
                sample_agent_id, 
                agent_data
            )
            
            # Verify session operations
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_get_call_volume_trends(self, analytics_service, sample_tenant_id):
        """Test call volume trend analysis."""
        with patch('voicecore.services.analytics_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Mock trend data
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [
                (datetime.utcnow().date(), 150),
                (datetime.utcnow().date() - timedelta(days=1), 120),
                (datetime.utcnow().date() - timedelta(days=2), 180)
            ]
            mock_session.execute.return_value = mock_result
            
            trends = await analytics_service.get_call_volume_trends(
                sample_tenant_id,
                days=7
            )
            
            assert isinstance(trends, list)
            assert len(trends) == 3
            assert all('date' in trend for trend in trends)
            assert all('call_count' in trend for trend in trends)
            
    @pytest.mark.asyncio
    async def test_error_handling_in_metrics_collection(self, analytics_service, sample_tenant_id):
        """Test error handling in metrics collection."""
        with patch('voicecore.services.analytics_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Simulate database error
            mock_session.execute.side_effect = Exception("Database connection failed")
            
            # Should not raise exception, should return None or empty data
            metrics = await analytics_service.collect_call_metrics(sample_tenant_id)
            
            # Verify graceful error handling
            assert metrics is None or metrics == {}
            
    @pytest.mark.asyncio
    async def test_tenant_isolation_in_analytics(self, analytics_service):
        """Test that analytics data is properly isolated by tenant."""
        tenant1_id = uuid4()
        tenant2_id = uuid4()
        
        with patch('voicecore.services.analytics_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Mock different results for different tenants
            def mock_execute(query):
                mock_result = MagicMock()
                # Simulate different data for different tenants
                if str(tenant1_id) in str(query):
                    mock_result.scalar.return_value = 100
                else:
                    mock_result.scalar.return_value = 200
                return mock_result
                
            mock_session.execute.side_effect = mock_execute
            
            metrics1 = await analytics_service.collect_call_metrics(tenant1_id)
            metrics2 = await analytics_service.collect_call_metrics(tenant2_id)
            
            # Verify different results for different tenants
            assert metrics1 != metrics2

# Additional tests for Task 13.2 - Reporting and Dashboard APIs

class TestReportingAndDashboard:
    """Test suite for reporting and dashboard functionality."""
    
    @pytest.fixture
    def sample_call_data(self):
        """Sample call data for testing."""
        return [
            {
                "id": uuid4(),
                "caller_phone_number": "+1234567890",
                "direction": "inbound",
                "status": "completed",
                "duration": 300,
                "created_at": datetime.utcnow(),
                "ended_at": datetime.utcnow() + timedelta(minutes=5),
                "ai_handled": True,
                "transferred_count": 0,
                "cost_cents": 150
            },
            {
                "id": uuid4(),
                "caller_phone_number": "+1234567891",
                "direction": "inbound", 
                "status": "missed",
                "duration": 0,
                "created_at": datetime.utcnow() - timedelta(hours=1),
                "ended_at": None,
                "ai_handled": False,
                "transferred_count": 1,
                "cost_cents": 0
            }
        ]
    
    @pytest.mark.asyncio
    async def test_generate_call_report(self, analytics_service, sample_tenant_id, sample_call_data):
        """Test call report generation."""
        with patch('voicecore.services.analytics_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Mock call query results
            mock_calls = []
            for call_data in sample_call_data:
                mock_call = MagicMock()
                for key, value in call_data.items():
                    setattr(mock_call, key, value)
                mock_call.agent = None
                mock_call.department = None
                mock_calls.append(mock_call)
            
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = mock_calls
            mock_session.execute.return_value = mock_result
            
            report = await analytics_service.generate_call_report(
                sample_tenant_id,
                date.today() - timedelta(days=7),
                date.today()
            )
            
            assert "report_info" in report
            assert "summary" in report
            assert "calls" in report
            assert report["summary"]["total_calls"] == 2
            assert len(report["calls"]) == 2
    
    @pytest.mark.asyncio
    async def test_generate_agent_report(self, analytics_service, sample_tenant_id, sample_agent_id):
        """Test agent report generation."""
        with patch('voicecore.services.analytics_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Mock agent query results
            mock_agent = MagicMock()
            mock_agent.id = sample_agent_id
            mock_agent.name = "Test Agent"
            mock_agent.email = "test@example.com"
            mock_agent.extension = "101"
            mock_agent.is_active = True
            mock_agent.department = None
            
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [mock_agent]
            mock_session.execute.return_value = mock_result
            
            report = await analytics_service.generate_agent_report(
                sample_tenant_id,
                date.today() - timedelta(days=7),
                date.today()
            )
            
            assert "report_info" in report
            assert "summary" in report
            assert "agents" in report
            assert len(report["agents"]) == 1
            assert report["agents"][0]["agent_name"] == "Test Agent"
    
    @pytest.mark.asyncio
    async def test_generate_conversation_analytics(self, analytics_service, sample_tenant_id):
        """Test conversation analytics generation."""
        with patch('voicecore.services.analytics_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Mock calls with transcripts
            mock_call = MagicMock()
            mock_call.id = uuid4()
            mock_call.duration = 300
            mock_call.ai_handled = True
            mock_call.status = MagicMock()
            mock_call.status.value = "completed"
            mock_call.transcript = "Hello, I need help with my billing. Thank you for the great service!"
            mock_call.transferred_count = 0
            
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [mock_call]
            mock_session.execute.return_value = mock_result
            
            analytics = await analytics_service.generate_conversation_analytics(
                sample_tenant_id,
                date.today() - timedelta(days=7),
                date.today(),
                include_transcripts=True
            )
            
            assert "analysis_info" in analytics
            assert "ai_performance" in analytics
            assert "conversations" in analytics
            assert len(analytics["conversations"]) == 1
            assert analytics["conversations"][0]["sentiment"] == "positive"
            assert "billing" in analytics["conversations"][0]["topics"]
    
    @pytest.mark.asyncio
    async def test_get_live_dashboard_data(self, analytics_service, sample_tenant_id):
        """Test live dashboard data retrieval."""
        with patch('voicecore.services.analytics_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Mock all the helper methods
            with patch.object(analytics_service, '_get_active_calls_count', return_value=5), \
                 patch.object(analytics_service, '_get_queue_length', return_value=2), \
                 patch.object(analytics_service, '_get_available_agents_count', return_value=10), \
                 patch.object(analytics_service, '_get_busy_agents_count', return_value=3), \
                 patch.object(analytics_service, '_get_calls_today_count', return_value=150), \
                 patch.object(analytics_service, '_get_ai_resolution_rate_today', return_value=0.85), \
                 patch.object(analytics_service, '_get_current_average_wait_time', return_value=45.0), \
                 patch.object(analytics_service, '_get_active_alerts', return_value=[]):
                
                dashboard_data = await analytics_service.get_live_dashboard_data(sample_tenant_id)
                
                assert "timestamp" in dashboard_data
                assert dashboard_data["active_calls"] == 5
                assert dashboard_data["queue_length"] == 2
                assert dashboard_data["available_agents"] == 10
                assert dashboard_data["busy_agents"] == 3
                assert dashboard_data["calls_today"] == 150
                assert dashboard_data["ai_resolution_rate_today"] == 0.85
    
    @pytest.mark.asyncio
    async def test_get_call_volume_trends(self, analytics_service, sample_tenant_id):
        """Test call volume trends analysis."""
        with patch('voicecore.services.analytics_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Mock trend data
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [
                (date.today(), 10, 150, 120),
                (date.today() - timedelta(days=1), 10, 130, 100),
                (date.today() - timedelta(days=2), 10, 180, 150)
            ]
            mock_session.execute.return_value = mock_result
            
            trends = await analytics_service.get_call_volume_trends(
                sample_tenant_id,
                days=7,
                granularity="hour"
            )
            
            assert "period_info" in trends
            assert "trends" in trends
            assert "summary" in trends
            assert len(trends["trends"]) == 3
            assert trends["summary"]["total_calls"] > 0
    
    @pytest.mark.asyncio
    async def test_get_ai_performance_insights(self, analytics_service, sample_tenant_id):
        """Test AI performance insights generation."""
        with patch('voicecore.services.analytics_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Mock analytics data
            mock_analytics = MagicMock()
            mock_analytics.total_calls = 100
            mock_analytics.ai_handled_calls = 80
            mock_analytics.ai_resolved_calls = 65
            mock_analytics.ai_transferred_calls = 15
            
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [mock_analytics]
            mock_session.execute.return_value = mock_result
            
            # Mock the trends method
            with patch.object(analytics_service, '_get_ai_performance_trends', return_value=[]):
                insights = await analytics_service.get_ai_performance_insights(
                    sample_tenant_id,
                    date.today() - timedelta(days=30),
                    date.today()
                )
                
                assert "period" in insights
                assert "ai_metrics" in insights
                assert "performance_trends" in insights
                assert "recommendations" in insights
                assert insights["ai_metrics"]["ai_handling_rate"] == 0.8
                assert insights["ai_metrics"]["ai_resolution_rate"] == 0.8125
    
    @pytest.mark.asyncio
    async def test_export_analytics_data(self, analytics_service, sample_tenant_id):
        """Test analytics data export functionality."""
        with patch.object(analytics_service, 'generate_call_report') as mock_call_report, \
             patch.object(analytics_service, 'generate_agent_report') as mock_agent_report, \
             patch.object(analytics_service, 'get_real_time_dashboard_data') as mock_dashboard:
            
            mock_call_report.return_value = {"calls": []}
            mock_agent_report.return_value = {"agents": []}
            mock_dashboard.return_value = {"metrics": {}}
            
            # Test calls export
            export_data = await analytics_service.export_analytics_data(
                sample_tenant_id,
                "calls",
                date.today() - timedelta(days=7),
                date.today(),
                "json"
            )
            
            assert "calls" in export_data
            mock_call_report.assert_called_once()
            
            # Test all data export
            export_data = await analytics_service.export_analytics_data(
                sample_tenant_id,
                "all",
                date.today() - timedelta(days=7),
                date.today(),
                "json"
            )
            
            assert "calls" in export_data
            assert "agents" in export_data
            assert "metrics" in export_data
    
    def test_sentiment_analysis(self, analytics_service):
        """Test sentiment analysis functionality."""
        # Test positive sentiment
        positive_text = "Thank you for the excellent service! I'm very satisfied and happy."
        sentiment = analytics_service._analyze_sentiment(positive_text)
        assert sentiment == "positive"
        
        # Test negative sentiment
        negative_text = "This is terrible service. I'm very frustrated and angry."
        sentiment = analytics_service._analyze_sentiment(negative_text)
        assert sentiment == "negative"
        
        # Test neutral sentiment
        neutral_text = "I called about my account information."
        sentiment = analytics_service._analyze_sentiment(neutral_text)
        assert sentiment == "neutral"
    
    def test_topic_extraction(self, analytics_service):
        """Test topic extraction functionality."""
        # Test billing topic
        billing_text = "I have a question about my bill and payment."
        topics = analytics_service._extract_topics(billing_text)
        assert "billing" in topics
        
        # Test technical topic
        technical_text = "I'm having a problem with the system, there's an error."
        topics = analytics_service._extract_topics(technical_text)
        assert "technical" in topics
        
        # Test multiple topics
        multi_topic_text = "I need help with my account login and billing issue."
        topics = analytics_service._extract_topics(multi_topic_text)
        assert "account" in topics
        assert "billing" in topics
        assert "support" in topics
    
    def test_ai_recommendations(self, analytics_service):
        """Test AI performance recommendations."""
        # Test low handling rate
        recommendations = analytics_service._generate_ai_recommendations(50, 40, 10, 100)
        assert any("expand AI capabilities" in rec for rec in recommendations)
        
        # Test low resolution rate
        recommendations = analytics_service._generate_ai_recommendations(80, 40, 20, 100)
        assert any("improve resolution rates" in rec for rec in recommendations)
        
        # Test high transfer rate
        recommendations = analytics_service._generate_ai_recommendations(80, 60, 40, 100)
        assert any("reduce unnecessary escalations" in rec for rec in recommendations)
        
        # Test good performance
        recommendations = analytics_service._generate_ai_recommendations(80, 70, 10, 100)
        assert any("within acceptable ranges" in rec for rec in recommendations)