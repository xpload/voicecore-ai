"""
Event Sourcing Example for VoiceCore AI 3.0 Enterprise

This example demonstrates how to use the Event Sourcing and CQRS
infrastructure for tracking call lifecycle events.
"""

import asyncio
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from voicecore.database import get_db
from voicecore.services.event_sourcing_service import (
    EventSourcingService,
    EventTypes,
    store_call_event
)
from voicecore.models.event_store import EventStore


async def call_lifecycle_example():
    """
    Example: Track complete call lifecycle using Event Sourcing
    """
    print("=" * 60)
    print("Event Sourcing Example: Call Lifecycle")
    print("=" * 60)
    
    # Setup
    db = next(get_db())
    service = EventSourcingService(db)
    
    # Generate IDs
    call_id = uuid.uuid4()
    tenant_id = uuid.uuid4()  # In production, get from authenticated user
    agent_id = uuid.uuid4()
    correlation_id = uuid.uuid4()
    
    print(f"\n📞 Call ID: {call_id}")
    print(f"🏢 Tenant ID: {tenant_id}")
    print(f"🔗 Correlation ID: {correlation_id}\n")
    
    # 1. Call Initiated
    print("1️⃣  Storing CallInitiated event...")
    event1 = await store_call_event(
        db=db,
        call_id=call_id,
        event_type=EventTypes.CALL_INITIATED,
        event_data={
            "caller_number": "+1234567890",
            "called_number": "+0987654321",
            "timestamp": datetime.utcnow().isoformat(),
            "source": "twilio"
        },
        tenant_id=tenant_id,
        correlation_id=correlation_id
    )
    print(f"   ✅ Event stored (sequence: {event1.sequence_number})")
    
    # 2. Call Connected
    print("\n2️⃣  Storing CallConnected event...")
    event2 = await store_call_event(
        db=db,
        call_id=call_id,
        event_type=EventTypes.CALL_CONNECTED,
        event_data={
            "agent_id": str(agent_id),
            "connection_time": datetime.utcnow().isoformat(),
            "wait_time_seconds": 15
        },
        tenant_id=tenant_id,
        correlation_id=correlation_id
    )
    print(f"   ✅ Event stored (sequence: {event2.sequence_number})")
    
    # 3. Call Recording Started
    print("\n3️⃣  Storing CallRecordingStarted event...")
    event3 = await store_call_event(
        db=db,
        call_id=call_id,
        event_type=EventTypes.CALL_RECORDING_STARTED,
        event_data={
            "recording_id": str(uuid.uuid4()),
            "start_time": datetime.utcnow().isoformat()
        },
        tenant_id=tenant_id,
        correlation_id=correlation_id
    )
    print(f"   ✅ Event stored (sequence: {event3.sequence_number})")
    
    # 4. Call Transferred
    print("\n4️⃣  Storing CallTransferred event...")
    event4 = await store_call_event(
        db=db,
        call_id=call_id,
        event_type=EventTypes.CALL_TRANSFERRED,
        event_data={
            "from_agent_id": str(agent_id),
            "to_agent_id": str(uuid.uuid4()),
            "reason": "escalation",
            "transfer_time": datetime.utcnow().isoformat()
        },
        tenant_id=tenant_id,
        correlation_id=correlation_id
    )
    print(f"   ✅ Event stored (sequence: {event4.sequence_number})")
    
    # 5. Call Recording Stopped
    print("\n5️⃣  Storing CallRecordingStopped event...")
    event5 = await store_call_event(
        db=db,
        call_id=call_id,
        event_type=EventTypes.CALL_RECORDING_STOPPED,
        event_data={
            "recording_id": event3.event_data["recording_id"],
            "stop_time": datetime.utcnow().isoformat(),
            "duration_seconds": 300
        },
        tenant_id=tenant_id,
        correlation_id=correlation_id
    )
    print(f"   ✅ Event stored (sequence: {event5.sequence_number})")
    
    # 6. Call Ended
    print("\n6️⃣  Storing CallEnded event...")
    event6 = await store_call_event(
        db=db,
        call_id=call_id,
        event_type=EventTypes.CALL_ENDED,
        event_data={
            "end_time": datetime.utcnow().isoformat(),
            "total_duration_seconds": 320,
            "end_reason": "completed",
            "customer_satisfaction": 5
        },
        tenant_id=tenant_id,
        correlation_id=correlation_id
    )
    print(f"   ✅ Event stored (sequence: {event6.sequence_number})")
    
    # Retrieve all events for the call
    print("\n" + "=" * 60)
    print("📋 Retrieving all events for the call...")
    print("=" * 60)
    
    events = await service.get_events(call_id)
    print(f"\nTotal events: {len(events)}\n")
    
    for event in events:
        print(f"Sequence {event.sequence_number}: {event.event_type}")
        print(f"  Timestamp: {event.timestamp}")
        print(f"  Data: {event.event_data}")
        print()
    
    # Replay events to rebuild call state
    print("=" * 60)
    print("🔄 Replaying events to rebuild call state...")
    print("=" * 60)
    
    state = await service.replay_events(
        aggregate_id=call_id,
        aggregate_type="Call"
    )
    
    print("\n📊 Reconstructed Call State:")
    print(f"  Caller: {state.get('caller_number')}")
    print(f"  Called: {state.get('called_number')}")
    print(f"  Duration: {state.get('total_duration_seconds')} seconds")
    print(f"  End Reason: {state.get('end_reason')}")
    print(f"  Satisfaction: {state.get('customer_satisfaction')}/5")
    print(f"  Last Sequence: {state.get('last_sequence')}")
    
    # Create snapshot
    print("\n" + "=" * 60)
    print("📸 Creating snapshot for performance optimization...")
    print("=" * 60)
    
    await service.create_snapshot(
        aggregate_id=call_id,
        aggregate_type="Call",
        tenant_id=tenant_id
    )
    print("✅ Snapshot created successfully")
    
    # Update read model (CQRS)
    print("\n" + "=" * 60)
    print("📝 Updating CQRS read model...")
    print("=" * 60)
    
    await service.update_read_model(
        model_type="CallSummary",
        model_id=str(call_id),
        data={
            "call_id": str(call_id),
            "caller_number": state.get('caller_number'),
            "duration": state.get('total_duration_seconds'),
            "status": "completed",
            "satisfaction": state.get('customer_satisfaction'),
            "agent_id": str(agent_id),
            "recording_available": True
        },
        tenant_id=tenant_id,
        last_event_id=event6.id,
        last_event_sequence=event6.sequence_number
    )
    print("✅ Read model updated successfully")
    
    print("\n" + "=" * 60)
    print("✨ Event Sourcing Example Completed!")
    print("=" * 60)


async def event_handler_example():
    """
    Example: Register custom event handlers
    """
    print("\n" + "=" * 60)
    print("Event Handler Example")
    print("=" * 60)
    
    db = next(get_db())
    service = EventSourcingService(db)
    
    # Define custom event handlers
    async def on_call_ended(event: EventStore):
        """Handler for call ended events"""
        print(f"\n🔔 Handler triggered: Call {event.aggregate_id} ended")
        print(f"   Duration: {event.event_data.get('total_duration_seconds')}s")
        print(f"   Satisfaction: {event.event_data.get('customer_satisfaction')}/5")
        
        # In production, you might:
        # - Update analytics
        # - Send notifications
        # - Trigger billing
        # - Update CRM
    
    async def on_call_transferred(event: EventStore):
        """Handler for call transfer events"""
        print(f"\n🔔 Handler triggered: Call {event.aggregate_id} transferred")
        print(f"   Reason: {event.event_data.get('reason')}")
        
        # In production, you might:
        # - Notify new agent
        # - Update queue metrics
        # - Log escalation
    
    # Register handlers
    service.register_handler(EventTypes.CALL_ENDED, on_call_ended)
    service.register_handler(EventTypes.CALL_TRANSFERRED, on_call_transferred)
    
    print("\n✅ Event handlers registered")
    print("\nStoring events to trigger handlers...\n")
    
    # Store events that will trigger handlers
    call_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    
    await store_call_event(
        db=db,
        call_id=call_id,
        event_type=EventTypes.CALL_TRANSFERRED,
        event_data={"reason": "escalation"},
        tenant_id=tenant_id
    )
    
    await store_call_event(
        db=db,
        call_id=call_id,
        event_type=EventTypes.CALL_ENDED,
        event_data={
            "total_duration_seconds": 180,
            "customer_satisfaction": 4
        },
        tenant_id=tenant_id
    )
    
    print("\n✅ Handlers executed successfully")


async def time_travel_example():
    """
    Example: Time travel - reconstruct state at any point in time
    """
    print("\n" + "=" * 60)
    print("Time Travel Example")
    print("=" * 60)
    
    db = next(get_db())
    service = EventSourcingService(db)
    
    call_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    
    # Store events over time
    print("\n📝 Storing events...")
    
    await store_call_event(
        db=db,
        call_id=call_id,
        event_type=EventTypes.CALL_INITIATED,
        event_data={"status": "initiated", "step": 1},
        tenant_id=tenant_id
    )
    
    await store_call_event(
        db=db,
        call_id=call_id,
        event_type=EventTypes.CALL_CONNECTED,
        event_data={"status": "connected", "step": 2},
        tenant_id=tenant_id
    )
    
    await store_call_event(
        db=db,
        call_id=call_id,
        event_type=EventTypes.CALL_ON_HOLD,
        event_data={"status": "on_hold", "step": 3},
        tenant_id=tenant_id
    )
    
    await store_call_event(
        db=db,
        call_id=call_id,
        event_type=EventTypes.CALL_RESUMED,
        event_data={"status": "resumed", "step": 4},
        tenant_id=tenant_id
    )
    
    await store_call_event(
        db=db,
        call_id=call_id,
        event_type=EventTypes.CALL_ENDED,
        event_data={"status": "ended", "step": 5},
        tenant_id=tenant_id
    )
    
    # Time travel: reconstruct state at different points
    print("\n🕐 Time Travel: Reconstructing state at different points...\n")
    
    # State after event 2
    state_at_2 = await service.replay_events(
        aggregate_id=call_id,
        aggregate_type="Call",
        from_sequence=0
    )
    events_up_to_2 = await service.get_events(call_id, to_sequence=2)
    print(f"After sequence 2: status = {events_up_to_2[-1].event_data.get('status')}")
    
    # State after event 3
    events_up_to_3 = await service.get_events(call_id, to_sequence=3)
    print(f"After sequence 3: status = {events_up_to_3[-1].event_data.get('status')}")
    
    # Current state
    current_state = await service.replay_events(
        aggregate_id=call_id,
        aggregate_type="Call"
    )
    print(f"Current state: status = {current_state.get('status')}")
    
    print("\n✅ Time travel completed - state reconstructed at multiple points!")


async def main():
    """Run all examples"""
    try:
        await call_lifecycle_example()
        await event_handler_example()
        await time_travel_example()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
