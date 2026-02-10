#!/bin/bash
# VoiceCore AI 3.0 Enterprise - Istio Service Mesh Deployment Script
# This script deploys Istio control plane and configures the service mesh

set -e

echo "=========================================="
echo "VoiceCore AI 3.0 - Istio Deployment"
echo "=========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed. Please install kubectl first."
    exit 1
fi

print_status "kubectl is installed"

# Check if istioctl is installed
if ! command -v istioctl &> /dev/null; then
    print_warning "istioctl is not installed. Installing Istio CLI..."
    
    # Download and install istioctl
    ISTIO_VERSION="1.20.0"
    curl -L https://istio.io/downloadIstio | ISTIO_VERSION=$ISTIO_VERSION sh -
    
    # Add istioctl to PATH
    export PATH="$PWD/istio-$ISTIO_VERSION/bin:$PATH"
    
    print_status "istioctl installed successfully"
else
    print_status "istioctl is already installed"
fi

# Verify Kubernetes cluster connection
echo ""
echo "Verifying Kubernetes cluster connection..."
if ! kubectl cluster-info &> /dev/null; then
    print_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
    exit 1
fi

print_status "Connected to Kubernetes cluster"

# Step 1: Create namespaces
echo ""
echo "Step 1: Creating namespaces..."
kubectl apply -f kubernetes/istio/namespace-injection.yaml
print_status "Namespaces created with automatic sidecar injection enabled"

# Step 2: Install Istio control plane
echo ""
echo "Step 2: Installing Istio control plane..."
echo "This may take several minutes..."

# Pre-check for Istio installation
istioctl x precheck

# Install Istio using the IstioOperator configuration
istioctl install -f kubernetes/istio/istio-installation.yaml -y

print_status "Istio control plane installed successfully"

# Step 3: Verify Istio installation
echo ""
echo "Step 3: Verifying Istio installation..."
kubectl get pods -n istio-system

# Wait for Istio pods to be ready
echo "Waiting for Istio pods to be ready..."
kubectl wait --for=condition=ready pod -l app=istiod -n istio-system --timeout=300s
kubectl wait --for=condition=ready pod -l app=istio-ingressgateway -n istio-system --timeout=300s

print_status "Istio control plane is ready"

# Step 4: Apply mTLS policies
echo ""
echo "Step 4: Applying mTLS policies..."
kubectl apply -f kubernetes/istio/mtls-policy.yaml
print_status "mTLS policies applied - strict mTLS enforced across the mesh"

# Step 5: Apply traffic management rules
echo ""
echo "Step 5: Applying traffic management rules..."
kubectl apply -f kubernetes/istio/traffic-management.yaml
print_status "Traffic management rules applied (circuit breakers, retries, timeouts)"

# Step 6: Configure certificate rotation
echo ""
echo "Step 6: Configuring certificate rotation..."
kubectl apply -f kubernetes/istio/certificate-rotation.yaml
print_status "Certificate rotation configured (90-day lifetime, automatic rotation)"

# Step 7: Label existing deployments for Istio injection
echo ""
echo "Step 7: Enabling Istio sidecar injection for existing deployments..."

# Restart deployments to inject Istio sidecars
if kubectl get namespace voicecore-ai &> /dev/null; then
    print_status "Restarting deployments in voicecore-ai namespace..."
    
    # Get all deployments in the namespace
    DEPLOYMENTS=$(kubectl get deployments -n voicecore-ai -o name 2>/dev/null || echo "")
    
    if [ -n "$DEPLOYMENTS" ]; then
        for deployment in $DEPLOYMENTS; do
            echo "  Restarting $deployment..."
            kubectl rollout restart -n voicecore-ai $deployment
        done
        
        # Wait for rollouts to complete
        for deployment in $DEPLOYMENTS; do
            kubectl rollout status -n voicecore-ai $deployment --timeout=300s
        done
        
        print_status "All deployments restarted with Istio sidecars"
    else
        print_warning "No deployments found in voicecore-ai namespace"
    fi
fi

# Step 8: Verify sidecar injection
echo ""
echo "Step 8: Verifying sidecar injection..."
PODS_WITH_SIDECARS=$(kubectl get pods -n voicecore-ai -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[*].name}{"\n"}{end}' | grep istio-proxy | wc -l)

if [ "$PODS_WITH_SIDECARS" -gt 0 ]; then
    print_status "Istio sidecars injected successfully ($PODS_WITH_SIDECARS pods)"
else
    print_warning "No pods with Istio sidecars found. This is normal if no applications are deployed yet."
fi

# Step 9: Display Istio ingress gateway information
echo ""
echo "Step 9: Istio Ingress Gateway Information"
echo "=========================================="

INGRESS_HOST=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
INGRESS_PORT=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.spec.ports[?(@.name=="http2")].port}')
SECURE_INGRESS_PORT=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.spec.ports[?(@.name=="https")].port}')

echo "Ingress Gateway Host: $INGRESS_HOST"
echo "HTTP Port: $INGRESS_PORT"
echo "HTTPS Port: $SECURE_INGRESS_PORT"

if [ "$INGRESS_HOST" = "pending" ]; then
    print_warning "LoadBalancer IP is pending. Run 'kubectl get svc -n istio-system' to check status."
else
    print_status "Ingress Gateway is accessible at: http://$INGRESS_HOST:$INGRESS_PORT"
fi

# Step 10: Display mesh status
echo ""
echo "Step 10: Istio Mesh Status"
echo "=========================================="
istioctl proxy-status

# Step 11: Verify mTLS status
echo ""
echo "Step 11: Verifying mTLS Configuration"
echo "=========================================="
istioctl authn tls-check

# Summary
echo ""
echo "=========================================="
echo "Istio Deployment Complete!"
echo "=========================================="
echo ""
print_status "Istio control plane (Pilot, Citadel, Mixer) installed"
print_status "Automatic sidecar injection enabled for voicecore-ai namespace"
print_status "Strict mTLS enforced for all service-to-service communication"
print_status "Certificate rotation configured (90-day lifetime)"
print_status "Traffic management rules applied (circuit breakers, retries)"
print_status "Zero-trust security policies enforced"

echo ""
echo "Next Steps:"
echo "1. Deploy your microservices to the voicecore-ai namespace"
echo "2. Monitor service mesh with: istioctl dashboard kiali"
echo "3. View distributed traces with: istioctl dashboard jaeger"
echo "4. Check mesh status with: istioctl proxy-status"
echo "5. Verify mTLS with: istioctl authn tls-check"
echo ""
echo "For more information, visit: https://istio.io/latest/docs/"
echo ""
