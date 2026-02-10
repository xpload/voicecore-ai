# VoiceCore AI 2.0 - Architecture Documentation

## System Architecture Overview

VoiceCore AI 2.0 is built on a modern microservices architecture designed for scalability, reliability, and maintainability.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Web App    │  │  Mobile App  │  │ API Clients  │          │
│  │  (React 18)  │  │   (Future)   │  │   (REST)     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         EDGE LAYER                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Global CDN  │  │Load Balancer │  │     WAF      │          │
│  │   (Future)   │  │   (Nginx)    │  │   (Future)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API GATEWAY LAYER                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              API Gateway (Port 8000)                      │   │
│  │  • Request Routing                                        │   │
│  │  • Load Balancing                                         │   │
│  │  • Health Monitoring                                      │   │
│  │  • Service Discovery                                      │   │
│  │  • Authentication (Future)                                │   │
│  │  • Rate Limiting (Future)                                 │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MICROSERVICES LAYER                           │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Tenant     │  │     Call     │  │      AI      │          │
│  │   Service    │  │   Service    │  │   Service    │          │
│  │  Port 8001   │  │  Port 8002   │  │  Port 8003   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │     CRM      │  │  Analytics   │  │ Integration  │          │
│  │   Service    │  │   Service    │  │   Service    │          │
│  │  Port 8004   │  │  Port 8005   │  │  Port 8006   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐                                               │
│  │   Billing    │                                               │
│  │   Service    │                                               │
│  │  Port 8007   │                                               │
│  └──────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  PostgreSQL  │  │    Redis     │  │ Elasticsearch│          │
│  │   Cluster    │  │   Cluster    │  │   (Future)   │          │
│  │  Port 5432   │  │  Port 6379   │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐                                               │
│  │    S3/Blob   │                                               │
│  │   Storage    │                                               │
│  │   (Future)   │                                               │
│  └──────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   EXTERNAL SERVICES                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   OpenAI     │  │    Twilio    │  │    Stripe    │          │
│  │    GPT-4     │  │  Voice/SMS   │  │   Payments   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Salesforce  │  │    Slack     │  │   HubSpot    │          │
│  │     CRM      │  │Notifications │  │  Marketing   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

## Microservices Details

### 1. API Gateway (Port 8000)

**Responsibilities**:
- Central entry point for all client requests
- Route requests to appropriate microservices
- Load balancing across service instances
- Health monitoring and service discovery
- Future: Authentication, rate limiting, request validation

**Technology**: FastAPI, Python 3.11+

**Key Features**:
- Dynamic service routing
- Health check aggregation
- Request/response logging
- Error handling and retry logic

### 2. Tenant Service (Port 8001)

**Responsibilities**:
- Multi-tenant organization management
- Tenant configuration and settings
- Subscription tier management
- Resource allocation and limits

**Technology**: FastAPI, SQLAlchemy, PostgreSQL

**Database Tables**:
- tenants
- users
- tenant_settings

### 3. Call Service (Port 8002)

**Responsibilities**:
- Call routing and management
- WebRTC gateway integration
- Call session tracking
- Call recording and transcription
- Queue management

**Technology**: FastAPI, Twilio SDK, WebRTC

**Database Tables**:
- call_sessions
- call_logs
- transcripts
- call_queues

### 4. AI Service (Port 8003)

**Responsibilities**:
- GPT-4 integration and conversation management
- AI personality configuration
- Sentiment analysis
- Language detection and translation
- Response caching

**Technology**: FastAPI, OpenAI SDK, Redis

**Database Tables**:
- ai_personalities
- conversation_history
- training_data

### 5. CRM Service (Port 8004)

**Responsibilities**:
- Customer contact management
- Lead tracking and scoring
- Interaction history
- Sales pipeline management

**Technology**: FastAPI, SQLAlchemy, PostgreSQL

**Database Tables**:
- crm_contacts
- leads
- interactions
- pipeline_stages

### 6. Analytics Service (Port 8005)

**Responsibilities**:
- Business intelligence and reporting
- Real-time metrics calculation
- Data aggregation and analysis
- Custom report generation

**Technology**: FastAPI, Pandas, NumPy

**Database Tables**:
- call_analytics
- business_metrics
- custom_reports

### 7. Integration Service (Port 8006)

**Responsibilities**:
- External API integrations
- Webhook management
- OAuth/SAML authentication
- Data synchronization

**Technology**: FastAPI, httpx

**Integrations**:
- Salesforce
- HubSpot
- Slack
- Microsoft Teams
- Google Workspace
- Zapier

### 8. Billing Service (Port 8007)

**Responsibilities**:
- Usage tracking and metering
- Subscription management
- Payment processing
- Invoice generation

**Technology**: FastAPI, Stripe SDK

**Database Tables**:
- billing_usage
- subscriptions
- invoices
- payments

## Data Flow Examples

### Example 1: Incoming Phone Call

```
1. Phone Call → Twilio → Call Service
2. Call Service → AI Service (Get AI personality)
3. AI Service → OpenAI GPT-4 (Generate response)
4. AI Service → Call Service (Return response)
5. Call Service → Twilio (Play response)
6. Call Service → Analytics Service (Log metrics)
7. Call Service → CRM Service (Update contact)
```

### Example 2: Dashboard Data Request

```
1. React App → API Gateway
2. API Gateway → Analytics Service
3. Analytics Service → PostgreSQL (Query data)
4. Analytics Service → Redis (Check cache)
5. Analytics Service → API Gateway (Return data)
6. API Gateway → React App (Display data)
```

### Example 3: CRM Contact Creation

```
1. React App → API Gateway
2. API Gateway → CRM Service
3. CRM Service → PostgreSQL (Create contact)
4. CRM Service → Integration Service (Sync to Salesforce)
5. Integration Service → Salesforce API
6. CRM Service → API Gateway (Return success)
7. API Gateway → React App (Update UI)
```

## Database Architecture

### Multi-Tenant Isolation

```sql
-- Row Level Security (RLS) ensures tenant isolation
CREATE POLICY tenant_isolation_policy ON users
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

-- All queries automatically filtered by tenant_id
SELECT * FROM users;  -- Only returns current tenant's users
```

### Database Schema Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      TENANT DOMAIN                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   tenants    │  │    users     │  │ai_personalities│         │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                       CALL DOMAIN                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │call_sessions │  │  call_logs   │  │ transcripts  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        CRM DOMAIN                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │crm_contacts  │  │    leads     │  │interactions  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    ANALYTICS DOMAIN                              │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │call_analytics│  │business_metrics│                           │
│  └──────────────┘  └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     BILLING DOMAIN                               │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │billing_usage │  │ audit_logs   │                             │
│  └──────────────┘  └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

## Security Architecture

### Authentication Flow

```
1. User Login → API Gateway
2. API Gateway → Tenant Service (Verify credentials)
3. Tenant Service → PostgreSQL (Check user)
4. Tenant Service → Generate JWT token
5. API Gateway → Return JWT to client
6. Client → Include JWT in all subsequent requests
7. API Gateway → Verify JWT on each request
```

### Authorization Layers

1. **Network Level**: Firewall, VPC, Security Groups
2. **Application Level**: JWT tokens, API keys
3. **Service Level**: Inter-service authentication
4. **Database Level**: Row Level Security (RLS)
5. **Audit Level**: Comprehensive logging

## Scalability Strategy

### Horizontal Scaling

```
┌─────────────────────────────────────────────────────────────────┐
│                    KUBERNETES CLUSTER                            │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Ingress Controller                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                      API Gateway                          │   │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐         │   │
│  │  │ Pod 1  │  │ Pod 2  │  │ Pod 3  │  │ Pod N  │         │   │
│  │  └────────┘  └────────┘  └────────┘  └────────┘         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   Microservices Layer                     │   │
│  │  Each service can scale independently                     │   │
│  │  ┌────────┐  ┌────────┐  ┌────────┐                      │   │
│  │  │Service │  │Service │  │Service │  ...                 │   │
│  │  │ Pod 1  │  │ Pod 2  │  │ Pod 3  │                      │   │
│  │  └────────┘  └────────┘  └────────┘                      │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Auto-Scaling Configuration

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: gateway-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: gateway
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## Caching Strategy

### Redis Cache Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                       REDIS CACHE                                │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Session Cache (TTL: 30 min)                  │   │
│  │  • User sessions                                          │   │
│  │  • Authentication tokens                                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              AI Response Cache (TTL: 1 hour)              │   │
│  │  • Common AI responses                                    │   │
│  │  • Conversation context                                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │            Analytics Cache (TTL: 5 min)                   │   │
│  │  • Dashboard metrics                                      │   │
│  │  • Real-time statistics                                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Configuration Cache (TTL: 1 day)             │   │
│  │  • Tenant settings                                        │   │
│  │  • AI personalities                                       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Monitoring and Observability

### Metrics Collection

```
┌─────────────────────────────────────────────────────────────────┐
│                    MONITORING STACK                              │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Prometheus  │  │    Grafana   │  │  AlertManager│          │
│  │   (Metrics)  │  │(Visualization)│  │   (Alerts)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │    Jaeger    │  │      ELK     │                             │
│  │   (Tracing)  │  │   (Logging)  │                             │
│  └──────────────┘  └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

### Health Check Endpoints

All services expose:
- `/health` - Basic health status
- `/health/ready` - Readiness probe
- `/health/live` - Liveness probe
- `/metrics` - Prometheus metrics

## Deployment Architecture

### Development Environment

```
Docker Compose
├── API Gateway
├── 7 Microservices
├── PostgreSQL
├── Redis
└── React Frontend
```

### Production Environment

```
Kubernetes Cluster
├── Ingress (Load Balancer)
├── API Gateway (2-10 replicas)
├── Microservices (2-10 replicas each)
├── PostgreSQL (HA Cluster)
├── Redis (Cluster Mode)
└── CDN (Static Assets)
```

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 18 + TypeScript | Modern web interface |
| **API Gateway** | FastAPI + Python | Request routing |
| **Microservices** | FastAPI + Python | Business logic |
| **Database** | PostgreSQL 15 | Primary data store |
| **Cache** | Redis 7 | Session & data caching |
| **AI** | OpenAI GPT-4 | Conversation AI |
| **Voice** | Twilio | Phone calls |
| **Payments** | Stripe | Billing |
| **Containers** | Docker | Containerization |
| **Orchestration** | Kubernetes | Container management |
| **Monitoring** | Prometheus + Grafana | Metrics & visualization |
| **Logging** | ELK Stack | Centralized logging |
| **Tracing** | Jaeger | Distributed tracing |

---

**Last Updated**: February 7, 2026  
**Version**: 2.0.0  
**Status**: Architecture Implemented ✅
