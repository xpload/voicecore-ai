#!/bin/bash
# VoiceCore AI 3.0 Enterprise - Istio Validation Script
# This script validates the Istio service mesh deployment

set -e

echo "=========================================="
echo "VoiceCore AI 3.0 - Istio Validation"
echo "=========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0
WARNINGS=0

print_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

print_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED++))
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED++))
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARNINGS++))
}

# Test 1: Check if Istio is installed
print_test "Checking if Istio control plane is installed..."
if kubectl get namespace istio-system &> /dev/null; then
    print_pass "Istio namespace exists"
else
    print_fail "Istio namespace not found"
fi

# Test 2: Check Istio pods
print_test "Checking Istio control plane pods..."
ISTIOD_PODS=$(kubectl get pods -n istio-system -l app=istiod --no-headers 2>/dev/null | wc -l)
if [ "$ISTIOD_PODS" -gt 0 ]; then
    READY_PODS=$(kubectl get pods -n istio-system -l app=istiod --no-headers 2>/dev/null | grep "Running" | wc -l)
    if [ "$READY_PODS" -eq "$ISTIOD_PODS" ]; then
        print_pass "All istiod pods are running ($READY_PODS/$ISTIOD_PODS)"
    else
        print_fail "Some istiod pods are not running ($READY_PODS/$ISTIOD_PODS)"
    fi
else
    print_fail "No istiod pods found"
fi

# Test 3: Check Ingress Gateway
print_test "Checking Istio Ingress Gateway..."
INGRESS_PODS=$(kubectl get pods -n istio-system -l app=istio-ingressgateway --no-headers 2>/dev/null | wc -l)
if [ "$INGRESS_PODS" -gt 0 ]; then
    READY_INGRESS=$(kubectl get pods -n istio-system -l app=istio-ingressgateway --no-headers 2>/dev/null | grep "Running" | wc -l)
    if [ "$READY_INGRESS" -eq "$INGRESS_PODS" ]; then
        print_pass "Ingress Gateway is running ($READY_INGRESS/$INGRESS_PODS)"
    else
        print_fail "Ingress Gateway pods not ready ($READY_INGRESS/$INGRESS_PODS)"
    fi
else
    print_fail "No Ingress Gateway pods found"
fi

# Test 4: Check Egress Gateway
print_test "Checking Istio Egress Gateway..."
EGRESS_PODS=$(kubectl get pods -n istio-system -l app=istio-egressgateway --no-headers 2>/dev/null | wc -l)
if [ "$EGRESS_PODS" -gt 0 ]; then
    READY_EGRESS=$(kubectl get pods -n istio-system -l app=istio-egressgateway --no-headers 2>/dev/null | grep "Running" | wc -l)
    if [ "$READY_EGRESS" -eq "$EGRESS_PODS" ]; then
        print_pass "Egress Gateway is running ($READY_EGRESS/$EGRESS_PODS)"
    else
        print_warn "Egress Gateway pods not ready ($READY_EGRESS/$EGRESS_PODS)"
    fi
else
    print_warn "No Egress Gateway pods found (optional)"
fi

# Test 5: Check namespace injection
print_test "Checking automatic sidecar injection..."
if kubectl get namespace voicecore-ai -o jsonpath='{.metadata.labels.istio-injection}' 2>/dev/null | grep -q "enabled"; then
    print_pass "Automatic sidecar injection enabled for voicecore-ai namespace"
else
    print_fail "Automatic sidecar injection not enabled for voicecore-ai namespace"
fi

# Test 6: Check for sidecars in running pods
print_test "Checking for Istio sidecars in application pods..."
if kubectl get namespace voicecore-ai &> /dev/null; then
    TOTAL_PODS=$(kubectl get pods -n voicecore-ai --no-headers 2>/dev/null | wc -l)
    if [ "$TOTAL_PODS" -gt 0 ]; then
        PODS_WITH_SIDECARS=$(kubectl get pods -n voicecore-ai -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[*].name}{"\n"}{end}' 2>/dev/null | grep "istio-proxy" | wc -l)
        if [ "$PODS_WITH_SIDECARS" -eq "$TOTAL_PODS" ]; then
            print_pass "All pods have Istio sidecars ($PODS_WITH_SIDECARS/$TOTAL_PODS)"
        elif [ "$PODS_WITH_SIDECARS" -gt 0 ]; then
            print_warn "Some pods have Istio sidecars ($PODS_WITH_SIDECARS/$TOTAL_PODS)"
        else
            print_warn "No pods with Istio sidecars found (deploy applications first)"
        fi
    else
        print_warn "No application pods found in voicecore-ai namespace"
    fi
else
    print_warn "voicecore-ai namespace not found"
fi

# Test 7: Check mTLS policies
print_test "Checking mTLS policies..."
MTLS_POLICIES=$(kubectl get peerauthentication -A --no-headers 2>/dev/null | wc -l)
if [ "$MTLS_POLICIES" -gt 0 ]; then
    print_pass "mTLS policies configured ($MTLS_POLICIES policies found)"
    
    # Check for STRICT mode
    STRICT_POLICIES=$(kubectl get peerauthentication -A -o yaml 2>/dev/null | grep "mode: STRICT" | wc -l)
    if [ "$STRICT_POLICIES" -gt 0 ]; then
        print_pass "STRICT mTLS mode enforced"
    else
        print_warn "No STRICT mTLS policies found"
    fi
else
    print_fail "No mTLS policies found"
fi

# Test 8: Check Virtual Services
print_test "Checking Virtual Services..."
VIRTUAL_SERVICES=$(kubectl get virtualservices -n voicecore-ai --no-headers 2>/dev/null | wc -l)
if [ "$VIRTUAL_SERVICES" -gt 0 ]; then
    print_pass "Virtual Services configured ($VIRTUAL_SERVICES found)"
else
    print_warn "No Virtual Services found (traffic management not configured)"
fi

# Test 9: Check Destination Rules
print_test "Checking Destination Rules (circuit breakers)..."
DEST_RULES=$(kubectl get destinationrules -n voicecore-ai --no-headers 2>/dev/null | wc -l)
if [ "$DEST_RULES" -gt 0 ]; then
    print_pass "Destination Rules configured ($DEST_RULES found)"
else
    print_warn "No Destination Rules found (circuit breakers not configured)"
fi

# Test 10: Check Gateways
print_test "Checking Istio Gateways..."
GATEWAYS=$(kubectl get gateways -n voicecore-ai --no-headers 2>/dev/null | wc -l)
if [ "$GATEWAYS" -gt 0 ]; then
    print_pass "Istio Gateways configured ($GATEWAYS found)"
else
    print_warn "No Istio Gateways found (external access not configured)"
fi

# Test 11: Check Authorization Policies
print_test "Checking Authorization Policies..."
AUTH_POLICIES=$(kubectl get authorizationpolicies -n voicecore-ai --no-headers 2>/dev/null | wc -l)
if [ "$AUTH_POLICIES" -gt 0 ]; then
    print_pass "Authorization Policies configured ($AUTH_POLICIES found)"
else
    print_warn "No Authorization Policies found"
fi

# Test 12: Verify istioctl is working
print_test "Checking istioctl installation..."
if command -v istioctl &> /dev/null; then
    print_pass "istioctl is installed"
    
    # Check version
    ISTIO_VERSION=$(istioctl version --remote=false 2>/dev/null | head -n 1)
    echo "  Version: $ISTIO_VERSION"
else
    print_warn "istioctl not found in PATH"
fi

# Test 13: Run Istio analyze
print_test "Running Istio configuration analysis..."
if command -v istioctl &> /dev/null; then
    ANALYSIS_OUTPUT=$(istioctl analyze -A 2>&1)
    if echo "$ANALYSIS_OUTPUT" | grep -q "No validation issues found"; then
        print_pass "No configuration issues found"
    else
        print_warn "Configuration issues detected:"
        echo "$ANALYSIS_OUTPUT" | head -n 10
    fi
else
    print_warn "Skipping analysis (istioctl not available)"
fi

# Test 14: Check Ingress Gateway LoadBalancer
print_test "Checking Ingress Gateway LoadBalancer..."
INGRESS_IP=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
if [ -n "$INGRESS_IP" ] && [ "$INGRESS_IP" != "null" ]; then
    print_pass "Ingress Gateway has external IP: $INGRESS_IP"
else
    INGRESS_HOSTNAME=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
    if [ -n "$INGRESS_HOSTNAME" ] && [ "$INGRESS_HOSTNAME" != "null" ]; then
        print_pass "Ingress Gateway has hostname: $INGRESS_HOSTNAME"
    else
        print_warn "Ingress Gateway LoadBalancer IP/hostname pending"
    fi
fi

# Test 15: Check certificate rotation configuration
print_test "Checking certificate rotation configuration..."
CERT_CONFIG=$(kubectl get configmap istio-ca-root-cert -n voicecore-ai 2>/dev/null)
if [ $? -eq 0 ]; then
    print_pass "Certificate rotation configuration found"
else
    print_warn "Certificate rotation configuration not found"
fi

# Summary
echo ""
echo "=========================================="
echo "Validation Summary"
echo "=========================================="
echo -e "${GREEN}Passed:${NC} $PASSED"
echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
echo -e "${RED}Failed:${NC} $FAILED"
echo ""

if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}✓ Istio service mesh is properly configured!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Deploy microservices: kubectl apply -f kubernetes/istio/microservices-deployments.yaml"
    echo "2. Monitor mesh: istioctl dashboard kiali"
    echo "3. View traces: istioctl dashboard jaeger"
    echo "4. Check status: istioctl proxy-status"
    exit 0
else
    echo -e "${RED}✗ Istio service mesh has configuration issues${NC}"
    echo ""
    echo "Please review the failed tests above and:"
    echo "1. Run: ./scripts/deploy-istio.sh"
    echo "2. Check logs: kubectl logs -n istio-system -l app=istiod"
    echo "3. Analyze config: istioctl analyze -A"
    exit 1
fi
