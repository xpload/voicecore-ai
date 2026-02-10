# Event Sourcing & CQRS Implementation

## Overview

VoiceCore AI 3.0 Enterprise implements a comprehensive Event Sourcing and CQRS (Command Query Responsibility Segregation) architecture for critical business transactions. This provides:

- **Complete Audit Trail**: Every business transaction is stored as an immutable event
- **Time Travel**: Ability to replay events and reconstruct state at any point in time
- **Scalability**: Separate read and write models for optimal performance
- **Blockchain Integration**: Optional blockchain anchoring for regulatory compliance
- **Distributed Tracing**: Full causation and correlation tracking

## Architecture

### Event Store

The Event Store is the source of truth for all business transactions. Events are:

- **Immutable**: Once written, events cannot be modified or deleted
- **Ordered**: Each event has a sequence number within its aggregate
- **Versioned**: Events support schema evolution through versioning
- **Tenant-Isolated**: Full multi-tenancy support with RLS policies

### CQRS Read Models

Read Models are materialized views optimized for queries:

- **Denormalized**: Data is pre-joined and optimized for specific queries
- **Eventually Consistent**: Updated asynchronously from events
- **Cacheable**: Can be cached aggressively for performance
- **Disposable**: Can be rebuilt from events at any time

### Event Snapshots

Snapshots optimize performance by reducing event replay:

- **Configurable Frequency**: Create snapshots every N events
- **Automatic Creation**: Triggered automatically during event storage
- **State Reconstruction**: Combine snapshot + subsequent events

## Event Types

### Call Events
- `CallInitiated`: New call started
- `CallConnected`: Call successfully connected
- `CallTransferred`: Call transferred to another agent
- `CallOnHold`: Call placed on hold
- `CallResumed`: Call resumed from hold
- `CallEnded`: Call completed normally
- `CallFailed`: Call failed or dropped
- `CallRecordingStarted`: Recording started
- `CallRecordingStopped`: Recording stopped

### Customer Events
- `CustomerCreated`: New customer registered
- `CustomerUpdated`: Customer information updated
- `CustomerVerified`: Customer identity verified
- `CustomerVIPStatusChanged`: VIP status modified
- `CustomerBlocked`: Customer blocked
- `CustomerUnblocked`: Customer unblocked

### Agent Events
- `AgentLoggedIn`: Agent logged into system
- `AgentLoggedOut`: Agent logged out
- `AgentStatusChanged`: Agent status updated (available, busy, etc.)
- `AgentAssignedToCall`: Agent assigned to handle call
- `AgentPerformanceUpdated`: Performance metrics updated

### AI Events
- `AIResponseGenerated`: AI generated a response
- `AISentimentDetected`: Sentiment analysis completed
- `AIIntentRecognized`: Intent classification completed
- `AIModelTrained`: AI model training completed
- `AIEscalationTriggered`: AI triggered escalation to human

### Transaction Events
- `PaymentInitiated`: Payment process started
- `PaymentCompleted`: Payment successfully processed
- `PaymentFailed`: Payment failed
- `RefundInitiated`: Refund process started
- `RefundCompleted`: Refund successfully processed

### Credit Events
- `CreditsPurchased`: Credits purchased by tenant
- `CreditsConsumed`: Credits consumed for service usage
- `CreditsRefunded`: Credits refunded
- `CreditBalanceLow`: Credit balance below threshold

### Security Events
- `LoginSuccessful`: Successful authentication
- `LoginFailed`: Failed authentication attempt
- `PasswordChanged`: Password updated
- `MFAEnabled`: Multi-factor authentication enabled
- `MFADisabled`: Multi-factor authentication disabled
- `SuspiciousActivityDetected`: Security anomaly detected
- `AccessDenied`: Unauthorized access attempt

## API Endpoints

### Store Event
```http
POST /api/v1/events/store
Content-Type: application/json

{
  "aggregate_id": "uuid",
  "aggregate_type": "Call",
  "event_type": "CallInitiated",
  "event_data": {
    "caller_number": "+1234567890",
    "timestamp": "2026-02-10T10:00:00Z"
  },
  "metadata": {
    "source": "twilio",
    "ip_address": "192.168.1.1"
  }
}
```

### Get Aggregate Events
```http
GET /api/v1/events/aggregate/{aggregate_id}?from_sequence=0&to_sequence=100
```

### Replay Aggregate State
```http
GET /api/v1/events/aggregate/{aggregate_id}/state?aggregate_type=Call
```

### Create Snapshot
```http
POST /api/v1/events/aggregate/{aggregate_id}/snapshot?aggregate_type=Call
```

### Get Read Model
```http
GET /api/v1/events/read-models/{model_type}/{model_id}
```

### List Read Models
```http
GET /api/v1/events/read-models/{model_type}?limit=100&offset=0
```

### Get Event Types
```http
GET /api/v1/events/types
```

### Get Event Statistics
```http
GET /api/v1/events/statistics?aggregate_type=Call&from_date=2026-01-01
```

## Usage Examples

### Python SDK

```python
from voicecore.services.event_sourcing_service import (
    EventSourcingService,
    EventTypes,
    store_call_event
)
import uuid

# Store a call event
call_id = uuid.uuid4()
tenant_id = uuid.uuid4()

event = await store_call_event(
    db=db,
    call_id=call_id,
    event_type=EventTypes.CALL_INITIATED,
    event_data={
        "caller_number": "+1234567890",
        "called_number": "+0987654321",
        "timestamp": "2026-02-10T10:00:00Z"
    },
    tenant_id=tenant_id
)

# Replay events to get current state
service = EventSourcingService(db)
state = await service.replay_events(
    aggregate_id=call_id,
    aggregate_type="Call"
)

# Create snapshot for performance
await service.create_snapshot(
    aggregate_id=call_id,
    aggregate_type="Call",
    tenant_id=tenant_id
)

# Update read model
await service.update_read_model(
    model_type="CallSummary",
    model_id=str(call_id),
    data={
        "duration": 300,
        "status": "completed",
        "agent_id": str(agent_id)
    },
    tenant_id=tenant_id,
    last_event_id=event.id,
    last_event_sequence=event.sequence_number
)
```

### Event Handlers

```python
# Register custom event handler
service = EventSourcingService(db)

async def handle_call_ended(event: EventStore):
    """Custom handler for call ended events"""
    print(f"Call {event.aggregate_id} ended")
    # Update analytics, send notifications, etc.

service.register_handler(
    EventTypes.CALL_ENDED,
    handle_call_ended
)
```

## Best Practices

### Event Design

1. **Events are Facts**: Name events in past tense (CallEnded, not EndCall)
2. **Immutable**: Never modify event data after storage
3. **Complete**: Include all necessary data in the event
4. **Versioned**: Use event_version for schema evolution

### Aggregate Design

1. **Consistency Boundary**: Aggregate defines transaction boundary
2. **Small Aggregates**: Keep aggregates focused and small
3. **Unique ID**: Each aggregate has a unique identifier
4. **Sequence Numbers**: Ensure ordered event processing

### Performance Optimization

1. **Snapshots**: Create snapshots for aggregates with many events
2. **Read Models**: Use read models for complex queries
3. **Caching**: Cache read models aggressively
4. **Async Processing**: Process events asynchronously when possible

### Security

1. **Tenant Isolation**: All events are tenant-isolated
2. **Audit Trail**: Events provide complete audit trail
3. **Encryption**: Sensitive data in events should be encrypted
4. **Access Control**: Implement proper authorization

## Kafka Integration

Events are automatically published to Kafka for:

- **Event-Driven Architecture**: Microservices react to events
- **Real-Time Processing**: Stream processing of events
- **Integration**: External systems consume events
- **Scalability**: Distributed event processing

Topics:
- `events.call` - Call-related events
- `events.customer` - Customer-related events
- `events.transaction` - Transaction events
- `events.security` - Security events

## Blockchain Integration

Optional blockchain anchoring for compliance:

```python
# Events can reference blockchain transactions
event = EventStore(
    ...
    blockchain_tx_hash="0x1234567890abcdef..."
)
```

Benefits:
- **Immutability Proof**: Cryptographic proof of event immutability
- **Regulatory Compliance**: Meet audit requirements
- **Tamper Detection**: Detect any unauthorized modifications

## Monitoring & Observability

### Metrics

- Event storage rate
- Event replay latency
- Snapshot creation frequency
- Read model update lag
- Event type distribution

### Logging

All event operations are logged with:
- Correlation ID for distributed tracing
- Causation ID for event chains
- Tenant ID for multi-tenancy
- Timestamp for temporal analysis

### Alerts

- High event storage latency
- Snapshot creation failures
- Read model update lag
- Event sequence gaps

## Troubleshooting

### Event Replay Issues

```python
# Check for missing events
events = await service.get_events(aggregate_id)
sequences = [e.sequence_number for e in events]
missing = set(range(1, max(sequences) + 1)) - set(sequences)
```

### Read Model Inconsistency

```python
# Rebuild read model from events
state = await service.replay_events(aggregate_id, aggregate_type)
await service.update_read_model(...)
```

### Performance Issues

```python
# Create snapshot to reduce replay time
await service.create_snapshot(aggregate_id, aggregate_type, tenant_id)
```

## Migration Guide

### From Traditional CRUD

1. Identify business transactions
2. Design events for each transaction
3. Create event handlers
4. Build read models
5. Migrate existing data as events

### Testing

```python
# Test event storage
event = await service.store_event(...)
assert event.sequence_number == 1

# Test event replay
state = await service.replay_events(aggregate_id, aggregate_type)
assert state["status"] == "completed"

# Test read model
read_model = db.query(ReadModel).filter(...).first()
assert read_model.version == 1
```

## References

- [Event Sourcing Pattern](https://martinfowler.com/eaaDev/EventSourcing.html)
- [CQRS Pattern](https://martinfowler.com/bliki/CQRS.html)
- [Kafka Event Bus](./KAFKA_EVENT_BUS.md)
- [VoiceCore Architecture](../ARCHITECTURE_V2.md)
