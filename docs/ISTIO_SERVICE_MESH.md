# Istio Service Mesh - VoiceCore AI 3.0 Enterprise

## Overview

VoiceCore AI 3.0 Enterprise Edition uses Istio service mesh to provide enterprise-grade traffic management, security, and observability for all microservices. This document describes the Istio deployment, configuration, and operational procedures.

## Architecture

### Istio Components

1. **Pilot (istiod)** - Traffic management and service discovery
   - Dynamic service routing
   - Load balancing
   - Traffic splitting for canary deployments
   - Fault injection for testing

2. **Citadel (integrated into istiod)** - Certificate and key management
   - Automatic mTLS certificate generation
   - Certificate rotation (90-day lifetime)
   - Service identity management
   - SPIFFE-compliant identities

3. **Mixer (deprecated, functionality moved to Envoy)** - Policy enforcement and telemetry
   - Rate limiting
   - Access control
   - Metrics collection
   - Distributed tracing

4. **Envoy Proxy** - Sidecar proxy for each service
   - Automatic mTLS encryption
   - Circuit breaking
   - Retry logic
   - Load balancing
   - Metrics and trace collection

### Service Mesh Topology

```
┌─────────────────────────────────────────────────────────────┐
│                    Istio Control Plane                       │
│  ┌──────────┐  ┌──────────┐  ┌─────────────────────────┐   │
│  │  Pilot   │  │ Citadel  │  │  Ingress/Egress Gateway │   │
│  │ (istiod) │  │ (istiod) │  │                         │   │
│  └──────────┘  └──────────┘  └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Configuration & Certificates
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Plane (Services)                     │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Gateway    │  │ Tenant Svc   │  │  Call Svc    │     │
│  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │     │
│  │ │  Envoy   │ │  │ │  Envoy   │ │  │ │  Envoy   │ │     │
│  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │     │
│  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │     │
│  │ │   App    │ │  │ │   App    │ │  │ │   App    │ │     │
│  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  All traffic encrypted with mTLS                            │
└─────────────────────────────────────────────────────────────┘
```

## Deployment

### Prerequisites

- Kubernetes cluster (1.24+)
- kubectl configured
- Cluster admin permissions
- At least 4 CPU cores and 8GB RAM available

### Installation Steps

#### Option 1: Using Deployment Script (Recommended)

**Linux/macOS:**
```bash
chmod +x scripts/deploy-istio.sh
./scripts/deploy-istio.sh
```

**Windows (PowerShell):**
```powershell
.\scripts\deploy-istio.ps1
```

#### Option 2: Manual Installation

1. **Install istioctl:**
```bash
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.20.0 sh -
export PATH="$PWD/istio-1.20.0/bin:$PATH"
```

2. **Create namespaces:**
```bash
kubectl apply -f kubernetes/istio/namespace-injection.yaml
```

3. **Install Istio control plane:**
```bash
istioctl install -f kubernetes/istio/istio-installation.yaml -y
```

4. **Apply mTLS policies:**
```bash
kubectl apply -f kubernetes/istio/mtls-policy.yaml
```

5. **Apply traffic management rules:**
```bash
kubectl apply -f kubernetes/istio/traffic-management.yaml
```

6. **Configure certificate rotation:**
```bash
kubectl apply -f kubernetes/istio/certificate-rotation.yaml
```

### Verification

1. **Check Istio installation:**
```bash
kubectl get pods -n istio-system
```

Expected output:
```
NAME                                    READY   STATUS    RESTARTS   AGE
istiod-xxxxx                           1/1     Running   0          5m
istio-ingressgateway-xxxxx             1/1     Running   0          5m
istio-egressgateway-xxxxx              1/1     Running   0          5m
```

2. **Verify sidecar injection:**
```bash
kubectl get pods -n voicecore-ai -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[*].name}{"\n"}{end}'
```

Each pod should have an `istio-proxy` container.

3. **Check mTLS status:**
```bash
istioctl authn tls-check
```

All services should show `STRICT` mTLS mode.

4. **View mesh status:**
```bash
istioctl proxy-status
```

## Configuration

### Mutual TLS (mTLS)

#### Global mTLS Policy

Strict mTLS is enforced across the entire mesh:

```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default-mtls-strict
  namespace: istio-system
spec:
  mtls:
    mode: STRICT
```

#### Certificate Lifecycle

- **Certificate Lifetime:** 90 days
- **Rotation Window:** 24 hours before expiry
- **Grace Period:** 10% of certificate lifetime (9 days)
- **Automatic Rotation:** Enabled by default

#### Certificate Monitoring

Monitor certificate expiration:
```bash
kubectl exec -n voicecore-ai <pod-name> -c istio-proxy -- \
  openssl s_client -connect localhost:15000 -showcerts 2>/dev/null | \
  openssl x509 -noout -dates
```

### Traffic Management

#### Circuit Breakers

Circuit breakers are configured for all services to prevent cascading failures:

**Example Configuration:**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: call-service-circuit-breaker
spec:
  host: call-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 200
      http:
        http1MaxPendingRequests: 100
        http2MaxRequests: 200
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

**Parameters:**
- `maxConnections`: Maximum TCP connections
- `http1MaxPendingRequests`: Maximum pending HTTP/1.1 requests
- `http2MaxRequests`: Maximum concurrent HTTP/2 requests
- `consecutiveErrors`: Errors before ejection
- `baseEjectionTime`: Minimum ejection duration
- `maxEjectionPercent`: Maximum percentage of hosts that can be ejected

#### Retry Policies

Automatic retries are configured for transient failures:

```yaml
retries:
  attempts: 3
  perTryTimeout: 10s
  retryOn: 5xx,reset,connect-failure,refused-stream
```

**Retry Conditions:**
- `5xx`: Server errors
- `reset`: Connection reset
- `connect-failure`: Connection failures
- `refused-stream`: Stream refused

#### Timeouts

Service-specific timeouts:
- **Tenant Service:** 30s
- **Call Service:** 60s
- **AI Service:** 120s (longer for AI processing)
- **CRM Service:** 30s
- **Analytics Service:** 60s
- **Integration Service:** 45s
- **Billing Service:** 30s

### Load Balancing

Load balancing algorithms per service:
- **LEAST_REQUEST:** Gateway, Tenant, Call, CRM, Integration, Billing
- **ROUND_ROBIN:** AI, Analytics

## Operations

### Monitoring

#### Kiali Dashboard

View service mesh topology and traffic flow:
```bash
istioctl dashboard kiali
```

Access at: http://localhost:20001

#### Jaeger Tracing

View distributed traces:
```bash
istioctl dashboard jaeger
```

Access at: http://localhost:16686

#### Prometheus Metrics

View Istio metrics:
```bash
istioctl dashboard prometheus
```

Access at: http://localhost:9090

#### Grafana Dashboards

View pre-built Istio dashboards:
```bash
istioctl dashboard grafana
```

Access at: http://localhost:3000

### Troubleshooting

#### Check Proxy Configuration

View Envoy configuration for a pod:
```bash
istioctl proxy-config all <pod-name> -n voicecore-ai
```

#### View Proxy Logs

Check Envoy proxy logs:
```bash
kubectl logs <pod-name> -n voicecore-ai -c istio-proxy
```

#### Debug mTLS Issues

Check mTLS configuration:
```bash
istioctl authn tls-check <pod-name>.<namespace>
```

#### Analyze Traffic

Capture traffic for debugging:
```bash
istioctl dashboard envoy <pod-name>.<namespace>
```

#### Common Issues

**Issue: Sidecar not injected**
- Solution: Ensure namespace has `istio-injection: enabled` label
```bash
kubectl label namespace voicecore-ai istio-injection=enabled
kubectl rollout restart deployment -n voicecore-ai
```

**Issue: mTLS connection failures**
- Solution: Verify PeerAuthentication policies
```bash
kubectl get peerauthentication -A
istioctl authn tls-check
```

**Issue: Circuit breaker triggering**
- Solution: Check service health and adjust thresholds
```bash
kubectl logs <pod-name> -n voicecore-ai -c istio-proxy | grep "upstream_rq_pending_overflow"
```

### Upgrades

#### Upgrade Istio

1. **Download new version:**
```bash
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.21.0 sh -
```

2. **Check upgrade compatibility:**
```bash
istioctl x precheck
```

3. **Perform canary upgrade:**
```bash
istioctl install -f kubernetes/istio/istio-installation.yaml --revision 1-21-0
```

4. **Migrate workloads:**
```bash
kubectl label namespace voicecore-ai istio.io/rev=1-21-0 --overwrite
kubectl rollout restart deployment -n voicecore-ai
```

5. **Verify upgrade:**
```bash
istioctl proxy-status
```

6. **Remove old version:**
```bash
istioctl x uninstall --revision 1-20-0
```

## Security

### Zero Trust Architecture

Istio implements zero-trust security:

1. **Service Identity:** Every service has a SPIFFE identity
2. **Mutual Authentication:** All services authenticate each other
3. **Encryption:** All traffic encrypted with mTLS
4. **Authorization:** Fine-grained access control policies
5. **Audit:** Complete audit trail of all communications

### Authorization Policies

Example authorization policy:
```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: allow-authenticated
  namespace: voicecore-ai
spec:
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/*"]
```

### Best Practices

1. **Always use STRICT mTLS mode**
2. **Implement least-privilege authorization policies**
3. **Monitor certificate expiration**
4. **Enable access logging for audit**
5. **Use egress gateway for external traffic**
6. **Implement rate limiting for public endpoints**
7. **Regular security audits with `istioctl analyze`**

## Performance Tuning

### Resource Allocation

**Control Plane:**
- Pilot: 2-5 replicas, 500m-2000m CPU, 2-4GB RAM
- Ingress Gateway: 2-10 replicas (auto-scaled)
- Egress Gateway: 2 replicas

**Data Plane (Sidecars):**
- Requests: 100m CPU, 128Mi RAM
- Limits: 2000m CPU, 1024Mi RAM

### Optimization Tips

1. **Reduce trace sampling in production** (currently 100% for enterprise observability)
2. **Use connection pooling** to reduce overhead
3. **Enable HTTP/2** for better performance
4. **Tune circuit breaker thresholds** based on service capacity
5. **Use local rate limiting** for high-traffic services

## Compliance

### Requirements Satisfied

- **Requirement 1.1:** Istio service mesh implemented ✓
- **Requirement 1.2:** Automatic mTLS encryption ✓
- **Requirement 1.3:** Circuit breakers and retry policies ✓
- **Requirement 1.4:** Distributed tracing (Jaeger integration) ✓
- **Requirement 1.5:** Canary deployment support ✓
- **Requirement 1.6:** Zero-trust security policies ✓
- **Requirement 1.7:** Rate limiting and quota management ✓

## References

- [Istio Documentation](https://istio.io/latest/docs/)
- [Istio Security Best Practices](https://istio.io/latest/docs/ops/best-practices/security/)
- [Istio Performance and Scalability](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/)
- [SPIFFE Specification](https://spiffe.io/docs/latest/spiffe-about/overview/)

## Support

For issues or questions:
1. Check Istio logs: `kubectl logs -n istio-system -l app=istiod`
2. Run diagnostics: `istioctl analyze -A`
3. View mesh status: `istioctl proxy-status`
4. Consult Istio documentation: https://istio.io/latest/docs/
