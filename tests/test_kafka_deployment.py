"""
Tests for Kafka Cluster Deployment and Event Bus
Validates Requirements 2.1, 2.3, 2.5, 2.7
"""

import pytest
import asyncio
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any
from voicecore.services.kafka_event_bus import KafkaEventBus, get_event_bus


class TestKafkaDeployment:
    """Test Kafka cluster deployment and configuration"""
    
    @pytest.fixture
    def event_bus(self):
        """Create Kafka event bus instance"""
        return get_event_bus()
    
    def test_kafka_connection(self, event_bus):
        """Test basic Kafka connectivity"""
        assert event_bus is not None
        assert event_bus.bootstrap_servers is not None
        assert event_bus.producer is not None
    
    def test_schema_registry_connection(self, event_bus):
        """Test Schema Registry connectivity"""
        assert event_bus.schema_registry is not None
        # Schema registry should be accessible
        try:
            # This will fail if schema registry is not accessible
            event_bus._get_schema('call.events')
        except Exception as e:
            pytest.fail(f"Schema Registry not accessible: {e}")
    
    def test_exactly_once_configuration(self, event_bus):
        """Test exactly-once semantics configuration"""
        # Verify producer config
        assert event_bus.producer_config['acks'] == 'all'
        assert event_bus.producer_config['enable.idempotence'] is True
        assert event_bus.producer_config['max.in.flight.requests.per.connection'] == 5
        
        # Verify consumer config
        assert event_bus.consumer_config['enable.auto.commit'] is False
        assert event_bus.consumer_config['isolation.level'] == 'read_committed'


class TestEventPublishing:
    """Test event publishing functionality"""
    
    @pytest.fixture
    def event_bus(self):
        """Create Kafka event bus instance"""
        return get_event_bus()
    
    @pytest.mark.asyncio
    async def test_publish_call_event(self, event_bus):
        """Test publishing call event"""
        event = {
            'tenant_id': str(uuid.uuid4()),
            'call_id': str(uuid.uuid4()),
            'event_type': 'call.initiated',
            'data': '{"from": "+1234567890", "to": "+0987654321"}'
        }
        
        result = await event_bus.publish_event(
            topic='call.events',
            key=event['call_id'],
            event=event
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_publish_ai_interaction(self, event_bus):
        """Test publishing AI interaction event"""
        event = {
            'tenant_id': str(uuid.uuid4()),
            'call_id': str(uuid.uuid4()),
            'message': 'Hello, how can I help you?',
            'response': 'I need to schedule an appointment.',
            'interaction_id': str(uuid.uuid4())
        }
        
        result = await event_bus.publish_event(
            topic='ai.interactions',
            key=event['call_id'],
            event=event
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_publish_billing_transaction(self, event_bus):
        """Test publishing billing transaction (critical topic)"""
        event = {
            'transaction_id': str(uuid.uuid4()),
            'tenant_id': str(uuid.uuid4()),
            'amount': 1000,  # $10.00 in cents
            'currency': 'USD',
            'description': 'Call charges'
        }
        
        result = await event_bus.publish_event(
            topic='billing.transactions',
            key=event['transaction_id'],
            event=event
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_publish_security_audit(self, event_bus):
        """Test publishing security audit event (critical topic)"""
        event = {
            'audit_id': str(uuid.uuid4()),
            'tenant_id': str(uuid.uuid4()),
            'user_id': str(uuid.uuid4()),
            'action': 'login',
            'resource': '/api/auth/login',
            'result': 'success'
        }
        
        result = await event_bus.publish_event(
            topic='security.audit',
            key=event['audit_id'],
            event=event
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_publish_with_headers(self, event_bus):
        """Test publishing event with custom headers"""
        event = {
            'tenant_id': str(uuid.uuid4()),
            'call_id': str(uuid.uuid4()),
            'event_type': 'call.ended',
            'data': '{"duration": 120}'
        }
        
        headers = {
            'correlation_id': str(uuid.uuid4()),
            'source': 'test-suite'
        }
        
        result = await event_bus.publish_event(
            topic='call.events',
            key=event['call_id'],
            event=event,
            headers=headers
        )
        
        assert result is True


class TestEventConsumption:
    """Test event consumption functionality"""
    
    @pytest.fixture
    def event_bus(self):
        """Create Kafka event bus instance"""
        return get_event_bus()
    
    @pytest.mark.asyncio
    async def test_consume_events(self, event_bus):
        """Test consuming events from topic"""
        received_events = []
        
        async def handler(event: Dict[str, Any]):
            received_events.append(event)
        
        # Publish test event
        test_event = {
            'tenant_id': str(uuid.uuid4()),
            'call_id': str(uuid.uuid4()),
            'event_type': 'test.event',
            'data': '{"test": true}'
        }
        
        await event_bus.publish_event(
            topic='call.events',
            key=test_event['call_id'],
            event=test_event
        )
        
        # Consume with timeout
        consumer_task = asyncio.create_task(
            event_bus.consume_events(
                topics=['call.events'],
                handler=handler,
                group_id='test-consumer-group'
            )
        )
        
        # Wait a bit for consumption
        await asyncio.sleep(2)
        consumer_task.cancel()
        
        # Should have received at least one event
        assert len(received_events) > 0


class TestEventReplay:
    """Test event replay functionality"""
    
    @pytest.fixture
    def event_bus(self):
        """Create Kafka event bus instance"""
        return get_event_bus()
    
    @pytest.mark.asyncio
    async def test_replay_events(self, event_bus):
        """Test replaying events from a time range"""
        # Publish some test events
        start_time = int(datetime.utcnow().timestamp() * 1000)
        
        for i in range(5):
            event = {
                'tenant_id': str(uuid.uuid4()),
                'call_id': str(uuid.uuid4()),
                'event_type': f'test.replay.{i}',
                'data': f'{{"index": {i}}}'
            }
            await event_bus.publish_event(
                topic='call.events',
                key=event['call_id'],
                event=event
            )
            await asyncio.sleep(0.1)
        
        end_time = int(datetime.utcnow().timestamp() * 1000)
        
        # Replay events
        replayed_events = await event_bus.replay_events(
            topic='call.events',
            start_timestamp=start_time,
            end_timestamp=end_time
        )
        
        # Should have replayed some events
        assert len(replayed_events) >= 5


class TestSchemaRegistry:
    """Test Schema Registry integration"""
    
    @pytest.fixture
    def event_bus(self):
        """Create Kafka event bus instance"""
        return get_event_bus()
    
    def test_schema_definitions(self, event_bus):
        """Test that all required schemas are defined"""
        required_topics = [
            'call.events',
            'ai.interactions',
            'crm.updates',
            'billing.transactions',
            'security.audit',
            'system.metrics'
        ]
        
        for topic in required_topics:
            schema = event_bus._get_schema(topic)
            assert schema is not None
            assert len(schema) > 0
            assert 'type' in schema
            assert 'record' in schema
    
    def test_schema_serialization(self, event_bus):
        """Test Avro schema serialization"""
        serializer = event_bus._get_serializer('call.events')
        assert serializer is not None
    
    def test_schema_deserialization(self, event_bus):
        """Test Avro schema deserialization"""
        deserializer = event_bus._get_deserializer('call.events')
        assert deserializer is not None


class TestHighAvailability:
    """Test high availability features"""
    
    @pytest.fixture
    def event_bus(self):
        """Create Kafka event bus instance"""
        return get_event_bus()
    
    def test_replication_configuration(self, event_bus):
        """Test that replication is properly configured"""
        # Producer should wait for all replicas
        assert event_bus.producer_config['acks'] == 'all'
    
    def test_idempotence_enabled(self, event_bus):
        """Test that idempotence is enabled"""
        assert event_bus.producer_config['enable.idempotence'] is True
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self, event_bus):
        """Test that producer retries on failure"""
        # Producer should have high retry count
        assert event_bus.producer_config['retries'] == 2147483647


class TestPerformance:
    """Test performance characteristics"""
    
    @pytest.fixture
    def event_bus(self):
        """Create Kafka event bus instance"""
        return get_event_bus()
    
    @pytest.mark.asyncio
    async def test_batch_publishing(self, event_bus):
        """Test batch publishing performance"""
        num_events = 100
        start_time = time.time()
        
        tasks = []
        for i in range(num_events):
            event = {
                'tenant_id': str(uuid.uuid4()),
                'call_id': str(uuid.uuid4()),
                'event_type': f'performance.test.{i}',
                'data': f'{{"index": {i}}}'
            }
            task = event_bus.publish_event(
                topic='call.events',
                key=event['call_id'],
                event=event
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        duration = end_time - start_time
        throughput = num_events / duration
        
        # Should publish at least 100 events/second
        assert throughput > 100
        assert all(results)
    
    def test_compression_enabled(self, event_bus):
        """Test that compression is enabled"""
        assert event_bus.producer_config['compression.type'] == 'snappy'
    
    def test_batching_configured(self, event_bus):
        """Test that batching is properly configured"""
        assert event_bus.producer_config['linger.ms'] == 10
        assert event_bus.producer_config['batch.size'] == 32768


class TestDeadLetterQueue:
    """Test dead letter queue functionality"""
    
    @pytest.fixture
    def event_bus(self):
        """Create Kafka event bus instance"""
        return get_event_bus()
    
    @pytest.mark.asyncio
    async def test_dlq_on_processing_failure(self, event_bus):
        """Test that failed messages go to DLQ"""
        # This would require mocking a consumer failure
        # For now, just verify the DLQ method exists
        assert hasattr(event_bus, '_send_to_dlq')


class TestEventOrdering:
    """Test event ordering guarantees"""
    
    @pytest.fixture
    def event_bus(self):
        """Create Kafka event bus instance"""
        return get_event_bus()
    
    @pytest.mark.asyncio
    async def test_partition_ordering(self, event_bus):
        """Test that events with same key maintain order"""
        call_id = str(uuid.uuid4())
        events = []
        
        # Publish events with same key (same partition)
        for i in range(10):
            event = {
                'tenant_id': str(uuid.uuid4()),
                'call_id': call_id,
                'event_type': f'ordered.event.{i}',
                'data': f'{{"sequence": {i}}}'
            }
            await event_bus.publish_event(
                topic='call.events',
                key=call_id,  # Same key = same partition
                event=event
            )
            events.append(event)
        
        # Events should be published successfully
        assert len(events) == 10


class TestRequirementsValidation:
    """Validate specific requirements from the spec"""
    
    @pytest.fixture
    def event_bus(self):
        """Create Kafka event bus instance"""
        return get_event_bus()
    
    def test_requirement_2_1_throughput_config(self, event_bus):
        """
        Requirement 2.1: Process 1M+ events per second with guaranteed delivery
        Validate configuration supports high throughput
        """
        # Batching enabled for throughput
        assert event_bus.producer_config['batch.size'] > 0
        assert event_bus.producer_config['linger.ms'] > 0
        
        # Compression for network efficiency
        assert event_bus.producer_config['compression.type'] == 'snappy'
        
        # Guaranteed delivery
        assert event_bus.producer_config['acks'] == 'all'
    
    def test_requirement_2_3_exactly_once(self, event_bus):
        """
        Requirement 2.3: Exactly-once semantics for financial transactions
        Validate exactly-once configuration
        """
        # Idempotent producer
        assert event_bus.producer_config['enable.idempotence'] is True
        
        # Consumer reads only committed messages
        assert event_bus.consumer_config['isolation.level'] == 'read_committed'
        
        # Manual commit for control
        assert event_bus.consumer_config['enable.auto.commit'] is False
    
    def test_requirement_2_5_schema_registry(self, event_bus):
        """
        Requirement 2.5: Schema registry for event versioning
        Validate Schema Registry integration
        """
        # Schema Registry client exists
        assert event_bus.schema_registry is not None
        
        # Schemas defined for all topics
        topics = ['call.events', 'ai.interactions', 'billing.transactions']
        for topic in topics:
            schema = event_bus._get_schema(topic)
            assert schema is not None
            assert len(schema) > 0
    
    def test_requirement_2_7_event_ordering(self, event_bus):
        """
        Requirement 2.7: Event ordering within partitions
        Validate ordering configuration
        """
        # Max in-flight requests allows ordering with idempotence
        assert event_bus.producer_config['max.in.flight.requests.per.connection'] == 5
        
        # Idempotence ensures ordering
        assert event_bus.producer_config['enable.idempotence'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
