# VIP Caller Management System

The VIP Caller Management System in VoiceCore AI provides comprehensive premium customer experience through intelligent caller identification, priority routing, and special handling rules.

## Overview

The VIP system automatically identifies premium callers and applies special handling rules to ensure exceptional service quality. It integrates seamlessly with the call routing system to provide priority treatment based on customer value and preferences.

## Key Features

### 1. VIP Caller Identification
- **Automatic Recognition**: Identifies VIP callers by phone number lookup
- **Privacy Compliant**: Phone numbers are hashed for security
- **Multi-Number Support**: Primary and alternative phone numbers
- **Real-time Lookup**: Instant identification during call routing

### 2. Priority Levels
- **Diamond**: Highest priority (immediate transfer, <15s wait)
- **Platinum**: High priority (dedicated agents, <30s wait)
- **Gold**: Standard VIP (priority queue, <60s wait)
- **Silver**: Basic VIP (enhanced service)
- **Standard**: Default VIP level

### 3. Special Handling Rules
- **Immediate Transfer**: Direct routing to available agents
- **Dedicated Agent**: Routing to preferred agents
- **Priority Queue**: Jump to front of call queues
- **Custom Greeting**: Personalized welcome messages
- **Extended Hours**: Service outside normal hours
- **Callback Priority**: Preferred callback scheduling

### 4. Escalation Management
- **Automatic Escalation**: Based on wait time and queue position
- **Rule-Based**: Configurable escalation conditions
- **Multi-Channel Notifications**: Email, SMS, internal alerts
- **Time-Based Rules**: Different rules for business hours

## API Endpoints

### VIP Caller Management

#### Create VIP Caller
```http
POST /api/v1/vip/
Content-Type: application/json

{
  "phone_number": "+1234567890",
  "caller_name": "John Doe",
  "company_name": "Acme Corp",
  "vip_level": "GOLD",
  "status": "ACTIVE",
  "handling_rules": ["PRIORITY_QUEUE", "CUSTOM_GREETING"],
  "custom_greeting": "Hello Mr. Doe, thank you for calling.",
  "max_wait_time": 30,
  "callback_priority": 1,
  "email": "john.doe@acme.com",
  "account_number": "ACC123456",
  "account_value": 50000.0,
  "notes": "High-value customer",
  "tags": ["premium", "enterprise"]
}
```

#### List VIP Callers
```http
GET /api/v1/vip/?skip=0&limit=100&vip_level=GOLD&status=ACTIVE&search=John
```

#### Get VIP Caller
```http
GET /api/v1/vip/{vip_id}
```

#### Update VIP Caller
```http
PUT /api/v1/vip/{vip_id}
Content-Type: application/json

{
  "vip_level": "PLATINUM",
  "notes": "Upgraded to Platinum level",
  "handling_rules": ["IMMEDIATE_TRANSFER", "DEDICATED_AGENT"]
}
```

#### Delete VIP Caller
```http
DELETE /api/v1/vip/{vip_id}
```

### VIP Operations

#### Identify VIP Caller
```http
POST /api/v1/vip/identify?phone_number=+1234567890
```

Response:
```json
{
  "is_vip": true,
  "vip_caller": {
    "id": "uuid",
    "caller_name": "John Doe",
    "vip_level": "GOLD",
    "handling_rules": ["PRIORITY_QUEUE"]
  },
  "routing_priority": 85
}
```

#### Check Escalation Rules
```http
POST /api/v1/vip/{vip_id}/escalation-check?wait_time=120&queue_position=3
```

Response:
```json
{
  "should_escalate": true,
  "triggered_rules": [
    {
      "rule_id": "uuid",
      "rule_name": "VIP Wait Time Rule",
      "escalation_type": "manager",
      "notification_emails": ["manager@company.com"]
    }
  ]
}
```

### Analytics

#### VIP Analytics
```http
GET /api/v1/vip/{vip_id}/analytics?start_date=2024-01-01&end_date=2024-01-31
```

#### Overview Analytics
```http
GET /api/v1/vip/analytics/overview?start_date=2024-01-01&end_date=2024-01-31
```

### Bulk Operations

#### Bulk Import
```http
POST /api/v1/vip/bulk-import
Content-Type: application/json

{
  "vip_callers": [
    {
      "phone_number": "+1234567890",
      "caller_name": "John Doe",
      "vip_level": "GOLD"
    },
    {
      "phone_number": "+1234567891",
      "caller_name": "Jane Smith",
      "vip_level": "PLATINUM"
    }
  ]
}
```

## Integration with Call Routing

The VIP system integrates seamlessly with the call routing service:

### 1. Automatic VIP Detection
```python
# During call routing, VIP status is automatically checked
vip_caller = await vip_service.identify_vip_caller(tenant_id, caller_number)
is_vip = vip_caller is not None
```

### 2. Priority Calculation
```python
# VIP priority affects routing decisions
if is_vip and vip_caller:
    priority = await vip_service.get_vip_routing_priority(tenant_id, vip_caller)
    # Priority score influences queue position and agent selection
```

### 3. Special Routing Rules
```python
# VIP handling rules modify routing behavior
if vip_caller.has_handling_rule(VIPHandlingRule.IMMEDIATE_TRANSFER):
    # Route directly to preferred agent if available
    
if vip_caller.has_handling_rule(VIPHandlingRule.DEDICATED_AGENT):
    # Wait for preferred agent even if others are available
```

## Database Schema

### VIP Caller Table
```sql
CREATE TABLE vip_caller (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    phone_number VARCHAR(255) NOT NULL, -- Hashed for privacy
    caller_name VARCHAR(255) NOT NULL,
    company_name VARCHAR(255),
    vip_level vippriority NOT NULL DEFAULT 'STANDARD',
    status vipstatus NOT NULL DEFAULT 'ACTIVE',
    preferred_agent_id UUID,
    preferred_department_id UUID,
    handling_rules JSON NOT NULL DEFAULT '[]',
    custom_greeting TEXT,
    max_wait_time INTEGER NOT NULL DEFAULT 60,
    callback_priority INTEGER NOT NULL DEFAULT 1,
    account_value FLOAT,
    total_calls INTEGER NOT NULL DEFAULT 0,
    satisfaction_score FLOAT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
```

### VIP Call History Table
```sql
CREATE TABLE vip_call_history (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    vip_caller_id UUID NOT NULL,
    call_id UUID NOT NULL,
    vip_level_at_call vippriority NOT NULL,
    handling_rules_applied JSON NOT NULL DEFAULT '[]',
    wait_time_seconds INTEGER NOT NULL DEFAULT 0,
    escalation_triggered BOOLEAN NOT NULL DEFAULT FALSE,
    satisfaction_rating INTEGER,
    service_quality_score FLOAT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);
```

### VIP Escalation Rules Table
```sql
CREATE TABLE vip_escalation_rule (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    vip_levels JSON NOT NULL DEFAULT '[]',
    max_wait_time INTEGER,
    max_queue_position INTEGER,
    escalation_type VARCHAR(50) NOT NULL,
    notification_emails JSON NOT NULL DEFAULT '[]',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    priority INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);
```

## Configuration Examples

### Basic VIP Setup
```python
# Create a Gold VIP with priority queue
vip_data = {
    "phone_number": "+1234567890",
    "caller_name": "John Doe",
    "vip_level": "GOLD",
    "handling_rules": ["PRIORITY_QUEUE"],
    "max_wait_time": 60
}
```

### Premium VIP with Dedicated Agent
```python
# Create a Platinum VIP with dedicated agent
vip_data = {
    "phone_number": "+1234567890",
    "caller_name": "Sarah Johnson",
    "vip_level": "PLATINUM",
    "handling_rules": ["DEDICATED_AGENT", "CUSTOM_GREETING"],
    "preferred_agent_id": "agent-uuid",
    "custom_greeting": "Good day Ms. Johnson, connecting you to your account manager.",
    "max_wait_time": 30
}
```

### Diamond VIP with Immediate Transfer
```python
# Create a Diamond VIP with immediate transfer
vip_data = {
    "phone_number": "+1234567890",
    "caller_name": "Michael Chen",
    "vip_level": "DIAMOND",
    "handling_rules": ["IMMEDIATE_TRANSFER", "CUSTOM_GREETING"],
    "custom_greeting": "Hello Mr. Chen, transferring you immediately.",
    "max_wait_time": 15,
    "account_value": 500000.0
}
```

## Best Practices

### 1. VIP Level Assignment
- **Diamond**: C-level executives, major accounts (>$500K value)
- **Platinum**: Key decision makers, high-value accounts (>$100K value)
- **Gold**: Important customers, loyal clients (>$50K value)
- **Silver**: Regular customers with good history (>$10K value)
- **Standard**: New or basic VIP designation

### 2. Handling Rules Selection
- Use **Immediate Transfer** sparingly for highest-value customers
- **Dedicated Agent** for customers requiring relationship continuity
- **Priority Queue** for most VIP customers to balance service and resources
- **Custom Greeting** to personalize the experience

### 3. Escalation Rules
- Set conservative wait times for higher VIP levels
- Configure multiple escalation tiers (agent → supervisor → manager)
- Include relevant stakeholders in notification lists
- Test escalation rules regularly

### 4. Analytics and Monitoring
- Monitor VIP satisfaction scores regularly
- Track escalation rates by VIP level
- Analyze wait times and service quality
- Review and adjust VIP levels based on account value changes

## Security and Privacy

### 1. Phone Number Hashing
- All phone numbers are hashed using secure algorithms
- Original numbers are never stored in the database
- Lookup is performed using hashed values

### 2. Data Encryption
- Sensitive VIP data is encrypted at rest
- API communications use TLS encryption
- Access logs are maintained for audit purposes

### 3. Access Control
- VIP data access is restricted by tenant isolation
- Role-based permissions for VIP management
- Audit trails for all VIP data modifications

## Troubleshooting

### Common Issues

#### VIP Not Identified
- Verify phone number format and hashing
- Check VIP status (must be ACTIVE)
- Confirm validity dates
- Review tenant isolation settings

#### Escalation Not Triggering
- Verify escalation rule is active
- Check VIP level matches rule criteria
- Confirm time-based conditions
- Review rule priority ordering

#### Routing Issues
- Check preferred agent availability
- Verify department assignments
- Review handling rule configuration
- Monitor queue capacity limits

### Debugging Tools

#### VIP Identification Test
```bash
curl -X POST "http://localhost:8000/api/v1/vip/identify?phone_number=+1234567890" \
  -H "Authorization: Bearer <token>"
```

#### Analytics Review
```bash
curl -X GET "http://localhost:8000/api/v1/vip/analytics/overview" \
  -H "Authorization: Bearer <token>"
```

## Performance Considerations

### 1. Database Optimization
- Index on tenant_id + phone_number for fast VIP lookup
- Partition call history by date for better performance
- Regular cleanup of old escalation rule triggers

### 2. Caching Strategy
- Cache frequently accessed VIP data
- Implement cache invalidation on updates
- Use Redis for session-based VIP context

### 3. Scalability
- Horizontal scaling of VIP service instances
- Database read replicas for analytics queries
- Asynchronous processing for bulk operations

## Monitoring and Alerts

### Key Metrics
- VIP identification rate
- Average wait time by VIP level
- Escalation trigger frequency
- Customer satisfaction scores
- Service quality metrics

### Alerting Rules
- High escalation rates (>5% for Diamond VIPs)
- Long wait times exceeding VIP thresholds
- Failed VIP identifications
- Service quality score drops

This comprehensive VIP management system ensures that premium customers receive exceptional service while maintaining operational efficiency and scalability.