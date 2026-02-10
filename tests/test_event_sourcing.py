"""
Tests for Event Sourcing and CQRS Implementation
"""

import pytest
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from voicecore.services.event_sourcing_service import (
    EventSourcingService,
    EventTypes,
    store_call_event,
    store_customer_event,
    store_transaction_event
)
from voicecore.models.event_store import EventStore, EventSnapshot, ReadModel


class TestEventStorage:
    """Test event storage functionality"""
    
    @pytest.mark.asyncio
    async def test_store_event(self, db: Session, test_tenant):
        """Test storing a single event"""
        service = EventSourcingService(db)
        aggregate_id = uuid.uuid4()
        
        event = await service.store_event(
            aggregate_id=aggregate_id,
            aggregate_type="Call",
            event_type=EventTypes.CALL_INITIATED,
            event_data={"caller": "+1234567890"},
            tenant_id=test_tenant.id
        )
        
        assert event.id is not None
        assert event.aggregate_id == aggregate_id
        assert event.sequence_number == 1
        assert event.event_type == EventTypes.CALL_INITIATED
    
    @pytest.mark.asyncio
    async def test_event_sequence_numbers(self, db: Session, test_tenant):
        """Test that sequence numbers increment correctly"""
        service = EventSourcingService(db)
        aggregate_id = uuid.uuid4()
        
        # Store multiple events
        event1 = await service.store_event(
            aggregate_id=aggregate_id,
            aggregate_type="Call",
            event_type=EventTypes.CALL_INITIATED,
            event_data={"step": 1},
            tenant_id=test_tenant.id
        )
        
        event2 = await service.store_event(
            aggregate_id=aggregate_id,
            aggregate_type="Call",
            event_type=EventTypes.CALL_CONNECTED,
            event_data={"step": 2},
            tenant_id=test_tenant.id
        )
        
        event3 = await service.store_event(
            aggregate_id=aggregate_id,
            aggregate_type="Call",
            event_type=EventTypes.CALL_ENDED,
            event_data={"step": 3},
            tenant_id=test_tenant.id
        )
        
        assert event1.sequence_number == 1
        assert event2.sequence_number == 2
        assert event3.sequence_number == 3
    
    @pytest.mark.asyncio
    async def test_event_immutability(self, db: Session, test_tenant):
        """Test that events cannot be modified"""
        service = EventSourcingService(db)
        aggregate_id = uuid.uuid4()
        
        event = await service.store_event(
            aggregate_id=aggregate_id,
            aggregate_type="Call",
            event_type=EventTypes.CALL_INITIATED,
            event_data={"original": "data"},
            tenant_id=test_tenant.id
        )
        
        # Attempt to modify event (should not affect stored event)
        original_data = event.event_data.copy()
        event.event_data["modified"] = "value"
        
        # Retrieve event again
        retrieved = db.query(EventStore).filter(EventStore.id == event.id).first()
        assert retrieved.event_data == original_data
    
    @pytest.mark.asyncio
    async def test_correlation_and_causation(self, db: Session, test_tenant):
        """Test correlation and causation tracking"""
        service = EventSourcingService(db)
        aggregate_id = uuid.uuid4()
        correlation_id = uuid.uuid4()
        
        event1 = await service.store_event(
            aggregate_id=aggregate_id,
            aggregate_type="Call",
            event_type=EventTypes.CALL_INITIATED,
            event_data={"step": 1},
            tenant_id=test_tenant.id,
            correlation_id=correlation_id
        )
        
        event2 = await service.store_event(
            aggregate_id=aggregate_id,
            aggregate_type="Call",
            event_type=EventTypes.CALL_CONNECTED,
            event_data={"step": 2},
            tenant_id=test_tenant.id,
            correlation_id=correlation_id,
            causation_id=event1.id
        )
        
        assert event1.correlation_id == correlation_id
        assert event2.correlation_id == correlation_id
        assert event2.causation_id == event1.id


class TestEventRetrieval:
    """Test event retrieval functionality"""
    
    @pytest.mark.asyncio
    async def test_get_aggregate_events(self, db: Session, test_tenant):
        """Test retrieving all events for an aggregate"""
        service = EventSourcingService(db)
        aggregate_id = uuid.uuid4()
        
        # Store multiple events
        for i in range(5):
            await service.store_event(
                aggregate_id=aggregate_id,
                aggregate_type="Call",
                event_type=EventTypes.CALL_INITIATED,
                event_data={"step": i},
                tenant_id=test_tenant.id
            )
        
        # Retrieve all events
        events = await service.get_events(aggregate_id)
        assert len(events) == 5
        assert all(e.aggregate_id == aggregate_id for e in events)
    
    @pytest.mark.asyncio
    async def test_get_events_with_sequence_range(self, db: Session, test_tenant):
        """Test retrieving events within a sequence range"""
        service = EventSourcingService(db)
        aggregate_id = uuid.uuid4()
        
        # Store 10 events
        for i in range(10):
            await service.store_event(
                aggregate_id=aggregate_id,
                aggregate_type="Call",
                event_type=EventTypes.CALL_INITIATED,
                event_data={"step": i},
                tenant_id=test_tenant.id
            )
        
        # Get events from sequence 3 to 7
        events = await service.get_events(
            aggregate_id=aggregate_id,
            from_sequence=3,
            to_sequence=7
        )
        
        assert len(events) == 4  # sequences 4, 5, 6, 7
        assert events[0].sequence_number == 4
        assert events[-1].sequence_number == 7


class TestEventReplay:
    """Test event replay functionality"""
    
    @pytest.mark.asyncio
    async def test_replay_events(self, db: Session, test_tenant):
        """Test replaying events to rebuild state"""
        service = EventSourcingService(db)
        aggregate_id = uuid.uuid4()
        
        # Store events
        await service.store_event(
            aggregate_id=aggregate_id,
            aggregate_type="Call",
            event_type=EventTypes.CALL_INITIATED,
            event_data={"status": "initiated", "caller": "+1234567890"},
            tenant_id=test_tenant.id
        )
        
        await service.store_event(
            aggregate_id=aggregate_id,
            aggregate_type="Call",
            event_type=EventTypes.CALL_CONNECTED,
            event_data={"status": "connected", "agent_id": "agent123"},
            tenant_id=test_tenant.id
        )
        
        # Replay events
        state = await service.replay_events(
            aggregate_id=aggregate_id,
            aggregate_type="Call"
        )
        
        assert state["status"] == "connected"
        assert state["caller"] == "+1234567890"
        assert state["agent_id"] == "agent123"
        assert "last_event_id" in state
        assert state["last_sequence"] == 2
    
    @pytest.mark.asyncio
    async def test_replay_from_snapshot(self, db: Session, test_tenant):
        """Test replaying events from a snapshot"""
        service = EventSourcingService(db)
        aggregate_id = uuid.uuid4()
        
        # Store many events
        for i in range(10):
            await service.store_event(
                aggregate_id=aggregate_id,
                aggregate_type="Call",
                event_type=EventTypes.CALL_INITIATED,
                event_data={"step": i},
                tenant_id=test_tenant.id
            )
        
        # Create snapshot at sequence 5
        await service.create_snapshot(
            aggregate_id=aggregate_id,
            aggregate_type="Call",
            tenant_id=test_tenant.id
        )
        
        # Store more events
        for i in range(10, 15):
            await service.store_event(
                aggregate_id=aggregate_id,
                aggregate_type="Call",
                event_type=EventTypes.CALL_INITIATED,
                event_data={"step": i},
                tenant_id=test_tenant.id
            )
        
        # Replay should use snapshot
        state = await service.replay_events(
            aggregate_id=aggregate_id,
            aggregate_type="Call"
        )
        
        assert state["last_sequence"] == 15


class TestSnapshots:
    """Test snapshot functionality"""
    
    @pytest.mark.asyncio
    async def test_create_snapshot(self, db: Session, test_tenant):
        """Test creating a snapshot"""
        service = EventSourcingService(db)
        aggregate_id = uuid.uuid4()
        
        # Store events
        for i in range(5):
            await service.store_event(
                aggregate_id=aggregate_id,
                aggregate_type="Call",
                event_type=EventTypes.CALL_INITIATED,
                event_data={"step": i},
                tenant_id=test_tenant.id
            )
        
        # Create snapshot
        await service.create_snapshot(
            aggregate_id=aggregate_id,
            aggregate_type="Call",
            tenant_id=test_tenant.id
        )
        
        # Verify snapshot exists
        snapshot = db.query(EventSnapshot).filter(
            EventSnapshot.aggregate_id == aggregate_id
        ).first()
        
        assert snapshot is not None
        assert snapshot.last_event_sequence == 5
        assert "last_sequence" in snapshot.snapshot_data
    
    @pytest.mark.asyncio
    async def test_automatic_snapshot_creation(self, db: Session, test_tenant):
        """Test automatic snapshot creation every N events"""
        service = EventSourcingService(db)
        service.snapshot_frequency = 10
        aggregate_id = uuid.uuid4()
        
        # Store exactly 10 events (should trigger snapshot)
        for i in range(10):
            await service.store_event(
                aggregate_id=aggregate_id,
                aggregate_type="Call",
                event_type=EventTypes.CALL_INITIATED,
                event_data={"step": i},
                tenant_id=test_tenant.id
            )
        
        # Verify snapshot was created
        snapshot = db.query(EventSnapshot).filter(
            EventSnapshot.aggregate_id == aggregate_id
        ).first()
        
        assert snapshot is not None
        assert snapshot.last_event_sequence == 10


class TestReadModels:
    """Test CQRS read model functionality"""
    
    @pytest.mark.asyncio
    async def test_create_read_model(self, db: Session, test_tenant):
        """Test creating a read model"""
        service = EventSourcingService(db)
        event_id = uuid.uuid4()
        
        await service.update_read_model(
            model_type="CallSummary",
            model_id="call123",
            data={"duration": 300, "status": "completed"},
            tenant_id=test_tenant.id,
            last_event_id=event_id,
            last_event_sequence=1
        )
        
        # Verify read model
        read_model = db.query(ReadModel).filter(
            ReadModel.model_type == "CallSummary",
            ReadModel.model_id == "call123"
        ).first()
        
        assert read_model is not None
        assert read_model.data["duration"] == 300
        assert read_model.version == 1
    
    @pytest.mark.asyncio
    async def test_update_read_model(self, db: Session, test_tenant):
        """Test updating an existing read model"""
        service = EventSourcingService(db)
        event_id = uuid.uuid4()
        
        # Create initial read model
        await service.update_read_model(
            model_type="CallSummary",
            model_id="call123",
            data={"duration": 300, "status": "in_progress"},
            tenant_id=test_tenant.id,
            last_event_id=event_id,
            last_event_sequence=1
        )
        
        # Update read model
        await service.update_read_model(
            model_type="CallSummary",
            model_id="call123",
            data={"duration": 450, "status": "completed"},
            tenant_id=test_tenant.id,
            last_event_id=uuid.uuid4(),
            last_event_sequence=2
        )
        
        # Verify update
        read_model = db.query(ReadModel).filter(
            ReadModel.model_type == "CallSummary",
            ReadModel.model_id == "call123"
        ).first()
        
        assert read_model.data["duration"] == 450
        assert read_model.data["status"] == "completed"
        assert read_model.version == 2


class TestHelperFunctions:
    """Test helper functions for common event patterns"""
    
    @pytest.mark.asyncio
    async def test_store_call_event(self, db: Session, test_tenant):
        """Test store_call_event helper"""
        call_id = uuid.uuid4()
        
        event = await store_call_event(
            db=db,
            call_id=call_id,
            event_type=EventTypes.CALL_INITIATED,
            event_data={"caller": "+1234567890"},
            tenant_id=test_tenant.id
        )
        
        assert event.aggregate_type == "Call"
        assert event.aggregate_id == call_id
    
    @pytest.mark.asyncio
    async def test_store_customer_event(self, db: Session, test_tenant):
        """Test store_customer_event helper"""
        customer_id = uuid.uuid4()
        
        event = await store_customer_event(
            db=db,
            customer_id=customer_id,
            event_type=EventTypes.CUSTOMER_CREATED,
            event_data={"name": "John Doe"},
            tenant_id=test_tenant.id
        )
        
        assert event.aggregate_type == "Customer"
        assert event.aggregate_id == customer_id
    
    @pytest.mark.asyncio
    async def test_store_transaction_event(self, db: Session, test_tenant):
        """Test store_transaction_event helper"""
        transaction_id = uuid.uuid4()
        
        event = await store_transaction_event(
            db=db,
            transaction_id=transaction_id,
            event_type=EventTypes.PAYMENT_COMPLETED,
            event_data={"amount": 100.00},
            tenant_id=test_tenant.id
        )
        
        assert event.aggregate_type == "Transaction"
        assert event.aggregate_id == transaction_id


class TestEventHandlers:
    """Test event handler registration and execution"""
    
    @pytest.mark.asyncio
    async def test_register_event_handler(self, db: Session, test_tenant):
        """Test registering and triggering event handlers"""
        service = EventSourcingService(db)
        handler_called = []
        
        async def test_handler(event: EventStore):
            handler_called.append(event.event_type)
        
        # Register handler
        service.register_handler(EventTypes.CALL_ENDED, test_handler)
        
        # Store event
        await service.store_event(
            aggregate_id=uuid.uuid4(),
            aggregate_type="Call",
            event_type=EventTypes.CALL_ENDED,
            event_data={"status": "completed"},
            tenant_id=test_tenant.id
        )
        
        # Verify handler was called
        assert EventTypes.CALL_ENDED in handler_called
    
    @pytest.mark.asyncio
    async def test_multiple_handlers(self, db: Session, test_tenant):
        """Test multiple handlers for same event type"""
        service = EventSourcingService(db)
        handler1_called = []
        handler2_called = []
        
        async def handler1(event: EventStore):
            handler1_called.append(True)
        
        async def handler2(event: EventStore):
            handler2_called.append(True)
        
        # Register multiple handlers
        service.register_handler(EventTypes.CALL_ENDED, handler1)
        service.register_handler(EventTypes.CALL_ENDED, handler2)
        
        # Store event
        await service.store_event(
            aggregate_id=uuid.uuid4(),
            aggregate_type="Call",
            event_type=EventTypes.CALL_ENDED,
            event_data={"status": "completed"},
            tenant_id=test_tenant.id
        )
        
        # Verify both handlers were called
        assert len(handler1_called) == 1
        assert len(handler2_called) == 1


class TestTenantIsolation:
    """Test tenant isolation in event sourcing"""
    
    @pytest.mark.asyncio
    async def test_events_isolated_by_tenant(self, db: Session, test_tenant, test_tenant2):
        """Test that events are isolated by tenant"""
        service = EventSourcingService(db)
        aggregate_id = uuid.uuid4()
        
        # Store event for tenant 1
        await service.store_event(
            aggregate_id=aggregate_id,
            aggregate_type="Call",
            event_type=EventTypes.CALL_INITIATED,
            event_data={"tenant": "1"},
            tenant_id=test_tenant.id
        )
        
        # Store event for tenant 2
        await service.store_event(
            aggregate_id=aggregate_id,
            aggregate_type="Call",
            event_type=EventTypes.CALL_INITIATED,
            event_data={"tenant": "2"},
            tenant_id=test_tenant2.id
        )
        
        # Query events for each tenant
        tenant1_events = db.query(EventStore).filter(
            EventStore.tenant_id == test_tenant.id
        ).all()
        
        tenant2_events = db.query(EventStore).filter(
            EventStore.tenant_id == test_tenant2.id
        ).all()
        
        assert len(tenant1_events) == 1
        assert len(tenant2_events) == 1
        assert tenant1_events[0].event_data["tenant"] == "1"
        assert tenant2_events[0].event_data["tenant"] == "2"
