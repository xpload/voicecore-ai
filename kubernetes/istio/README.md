# Istio Service Mesh Configuration

This directory contains all Istio service mesh configuration files for VoiceCore AI 3.0 Enterprise Edition.

## Quick Start

### Deploy Istio

**Linux/macOS:**
```bash
chmod +x ../../scripts/deploy-istio.sh
../../scripts/deploy-istio.sh
```

**Windows:**
```powershell
..\..\scripts\deploy-istio.ps1
```

### Verify Installation

```bash
# Check Istio pods
kubectl get pods -n istio-system

# Check sidecar injection
kubectl get pods -n voicecore-ai

# Verify mTLS
istioctl authn tls-check

# View mesh status
istioctl proxy-status
```

## Files

### Core Configuration

- **`istio-installation.yaml`** - IstioOperator configuration for control plane
  - Pilot (traffic management)
  - Citadel (certificate management)
  - Ingress/Egress gateways
  - Resource limits and auto-scaling

- **`namespace-injection.yaml`** - Namespace configuration with automatic sidecar injection
  - voicecore-ai namespace
  - observability namespace
  - istio-system namespace

- **`mtls-policy.yaml`** - Mutual TLS configuration
  - Global STRICT mTLS enforcement
  - Service-specific mTLS policies
  - Authorization policies

- **`traffic-management.yaml`** - Traffic management rules
  - Gateway configuration
  - Virtual services for routing
  - Destination rules with circuit breakers
  - Retry policies and timeouts
  - Load balancing strategies

- **`certificate-rotation.yaml`** - Certificate lifecycle management
  - 90-day certificate lifetime
  - Automatic rotation policies
  - Certificate monitoring
  - Expiration alerts

- **`microservices-deployments.yaml`** - Updated microservice deployments
  - Istio-compatible labels and annotations
  - Sidecar injection enabled
  - Prometheus metrics scraping
  - Health checks

## Architecture

```
┌─────────────────────────────────────┐
│     Istio Control Plane             │
│  ┌──────────┐  ┌──────────────┐    │
│  │  Pilot   │  │   Citadel    │    │
│  │ (istiod) │  │   (istiod)   │    │
│  └──────────┘  └──────────────┘    │
│  ┌──────────────────────────────┐  │
│  │  Ingress/Egress Gateways     │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
              │
              │ mTLS + Config
              ▼
┌─────────────────────────────────────┐
│        Microservices                │
│  ┌────────┐  ┌────────┐  ┌────────┐│
│  │Gateway │  │Tenant  │  │ Call   ││
│  │+Envoy  │  │+Envoy  │  │+Envoy  ││
│  └────────┘  └────────┘  └────────┘│
│  ┌────────┐  ┌────────┐  ┌────────┐│
│  │  AI    │  │  CRM   │  │Analytics││
│  │+Envoy  │  │+Envoy  │  │+Envoy  ││
│  └────────┘  └────────┘  └────────┘│
│  ┌────────┐  ┌────────┐            │
│  │Integr. │  │Billing │            │
│  │+Envoy  │  │+Envoy  │            │
│  └────────┘  └────────┘            │
└─────────────────────────────────────┘
```

## Features

### Security
- ✅ Automatic mTLS encryption between all services
- ✅ Certificate rotation (90-day lifetime)
- ✅ Zero-trust security policies
- ✅ Service-to-service authorization
- ✅ SPIFFE-compliant identities

### Traffic Management
- ✅ Circuit breakers for all services
- ✅ Automatic retries with exponential backoff
- ✅ Request timeouts
- ✅ Load balancing (LEAST_REQUEST, ROUND_ROBIN)
- ✅ Traffic splitting for canary deployments

### Observability
- ✅ Distributed tracing (100% sampling)
- ✅ Prometheus metrics collection
- ✅ Access logging (JSON format)
- ✅ Service dependency mapping
- ✅ Real-time traffic visualization

## Configuration Details

### mTLS Settings

- **Mode:** STRICT (enforced globally)
- **Certificate Lifetime:** 90 days
- **Rotation Window:** 24 hours before expiry
- **Grace Period:** 9 days (10% of lifetime)

### Circuit Breaker Settings

| Service | Max Connections | Max Pending | Consecutive Errors | Ejection Time |
|---------|----------------|-------------|-------------------|---------------|
| Gateway | 500 | 250 | 5 | 30s |
| Tenant | 100 | 50 | 5 | 30s |
| Call | 200 | 100 | 5 | 30s |
| AI | 150 | 75 | 3 | 60s |
| CRM | 100 | 50 | 5 | 30s |
| Analytics | 150 | 75 | 5 | 30s |
| Integration | 100 | 50 | 5 | 30s |
| Billing | 100 | 50 | 5 | 30s |

### Timeout Settings

| Service | Timeout | Retry Attempts | Per-Try Timeout |
|---------|---------|----------------|-----------------|
| Tenant | 30s | 3 | 10s |
| Call | 60s | 3 | 20s |
| AI | 120s | 2 | 60s |
| CRM | 30s | 3 | 10s |
| Analytics | 60s | 2 | 30s |
| Integration | 45s | 3 | 15s |
| Billing | 30s | 3 | 10s |

## Monitoring

### Dashboards

```bash
# Kiali - Service mesh visualization
istioctl dashboard kiali

# Jaeger - Distributed tracing
istioctl dashboard jaeger

# Prometheus - Metrics
istioctl dashboard prometheus

# Grafana - Dashboards
istioctl dashboard grafana
```

### Metrics

Key metrics to monitor:
- `istio_requests_total` - Total requests
- `istio_request_duration_milliseconds` - Request latency
- `istio_tcp_connections_opened_total` - TCP connections
- `pilot_xds_pushes` - Configuration updates
- `citadel_server_root_cert_expiry_timestamp` - Certificate expiration

### Alerts

Monitor for:
- Certificate expiration (< 7 days)
- Circuit breaker activation
- High error rates (> 5%)
- High latency (p99 > 1s)
- Pod restarts

## Troubleshooting

### Common Commands

```bash
# Check Istio installation
istioctl verify-install

# Analyze configuration
istioctl analyze -A

# View proxy configuration
istioctl proxy-config all <pod-name> -n voicecore-ai

# Check mTLS status
istioctl authn tls-check <pod-name>.<namespace>

# View proxy logs
kubectl logs <pod-name> -n voicecore-ai -c istio-proxy

# Debug traffic
istioctl dashboard envoy <pod-name>.<namespace>
```

### Common Issues

**Sidecar not injected:**
```bash
kubectl label namespace voicecore-ai istio-injection=enabled
kubectl rollout restart deployment -n voicecore-ai
```

**mTLS errors:**
```bash
istioctl authn tls-check
kubectl get peerauthentication -A
```

**Circuit breaker triggering:**
```bash
kubectl logs <pod-name> -c istio-proxy | grep "upstream_rq_pending_overflow"
```

## Upgrade

```bash
# Download new version
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.21.0 sh -

# Check compatibility
istioctl x precheck

# Canary upgrade
istioctl install -f istio-installation.yaml --revision 1-21-0

# Migrate workloads
kubectl label namespace voicecore-ai istio.io/rev=1-21-0 --overwrite
kubectl rollout restart deployment -n voicecore-ai

# Verify
istioctl proxy-status

# Remove old version
istioctl x uninstall --revision 1-20-0
```

## Requirements Satisfied

This configuration satisfies the following VoiceCore AI 3.0 Enterprise requirements:

- ✅ **1.1** - Istio service mesh implementation
- ✅ **1.2** - Automatic mTLS encryption
- ✅ **1.3** - Circuit breakers and retry policies
- ✅ **1.4** - Distributed tracing with sub-millisecond precision
- ✅ **1.5** - Canary deployment support
- ✅ **1.6** - Zero-trust security policies
- ✅ **1.7** - Rate limiting and quota management

## Documentation

For detailed documentation, see:
- [Istio Service Mesh Guide](../../docs/ISTIO_SERVICE_MESH.md)
- [Istio Official Documentation](https://istio.io/latest/docs/)

## Support

For issues:
1. Check logs: `kubectl logs -n istio-system -l app=istiod`
2. Run diagnostics: `istioctl analyze -A`
3. View status: `istioctl proxy-status`
4. Consult docs: https://istio.io/latest/docs/
