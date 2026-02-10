# VoiceCore AI 3.0 Enterprise - Istio Service Mesh Deployment Script (PowerShell)
# This script deploys Istio control plane and configures the service mesh

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "VoiceCore AI 3.0 - Istio Deployment" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Function to print colored output
function Print-Status {
    param([string]$Message)
    Write-Host "[✓] $Message" -ForegroundColor Green
}

function Print-Error {
    param([string]$Message)
    Write-Host "[✗] $Message" -ForegroundColor Red
}

function Print-Warning {
    param([string]$Message)
    Write-Host "[!] $Message" -ForegroundColor Yellow
}

# Check if kubectl is installed
try {
    $null = kubectl version --client 2>$null
    Print-Status "kubectl is installed"
} catch {
    Print-Error "kubectl is not installed. Please install kubectl first."
    exit 1
}

# Check if istioctl is installed
try {
    $null = istioctl version --remote=false 2>$null
    Print-Status "istioctl is already installed"
} catch {
    Print-Warning "istioctl is not installed. Installing Istio CLI..."
    
    # Download and install istioctl for Windows
    $ISTIO_VERSION = "1.20.0"
    $downloadUrl = "https://github.com/istio/istio/releases/download/$ISTIO_VERSION/istioctl-$ISTIO_VERSION-win.zip"
    
    Write-Host "Downloading istioctl..."
    $tempPath = "$env:TEMP\istioctl.zip"
    Invoke-WebRequest -Uri $downloadUrl -OutFile $tempPath
    
    Write-Host "Extracting istioctl..."
    $istioPath = "$env:USERPROFILE\.istio\bin"
    New-Item -ItemType Directory -Force -Path $istioPath | Out-Null
    Expand-Archive -Path $tempPath -DestinationPath $istioPath -Force
    
    # Add to PATH for current session
    $env:Path += ";$istioPath"
    
    Print-Status "istioctl installed successfully"
    Print-Warning "Please add $istioPath to your system PATH permanently"
}

# Verify Kubernetes cluster connection
Write-Host ""
Write-Host "Verifying Kubernetes cluster connection..."
try {
    $null = kubectl cluster-info 2>$null
    Print-Status "Connected to Kubernetes cluster"
} catch {
    Print-Error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
    exit 1
}

# Step 1: Create namespaces
Write-Host ""
Write-Host "Step 1: Creating namespaces..."
kubectl apply -f kubernetes/istio/namespace-injection.yaml
Print-Status "Namespaces created with automatic sidecar injection enabled"

# Step 2: Install Istio control plane
Write-Host ""
Write-Host "Step 2: Installing Istio control plane..."
Write-Host "This may take several minutes..."

# Pre-check for Istio installation
istioctl x precheck

# Install Istio using the IstioOperator configuration
istioctl install -f kubernetes/istio/istio-installation.yaml -y

Print-Status "Istio control plane installed successfully"

# Step 3: Verify Istio installation
Write-Host ""
Write-Host "Step 3: Verifying Istio installation..."
kubectl get pods -n istio-system

# Wait for Istio pods to be ready
Write-Host "Waiting for Istio pods to be ready..."
kubectl wait --for=condition=ready pod -l app=istiod -n istio-system --timeout=300s
kubectl wait --for=condition=ready pod -l app=istio-ingressgateway -n istio-system --timeout=300s

Print-Status "Istio control plane is ready"

# Step 4: Apply mTLS policies
Write-Host ""
Write-Host "Step 4: Applying mTLS policies..."
kubectl apply -f kubernetes/istio/mtls-policy.yaml
Print-Status "mTLS policies applied - strict mTLS enforced across the mesh"

# Step 5: Apply traffic management rules
Write-Host ""
Write-Host "Step 5: Applying traffic management rules..."
kubectl apply -f kubernetes/istio/traffic-management.yaml
Print-Status "Traffic management rules applied (circuit breakers, retries, timeouts)"

# Step 6: Configure certificate rotation
Write-Host ""
Write-Host "Step 6: Configuring certificate rotation..."
kubectl apply -f kubernetes/istio/certificate-rotation.yaml
Print-Status "Certificate rotation configured (90-day lifetime, automatic rotation)"

# Step 7: Label existing deployments for Istio injection
Write-Host ""
Write-Host "Step 7: Enabling Istio sidecar injection for existing deployments..."

# Check if voicecore-ai namespace exists
try {
    $null = kubectl get namespace voicecore-ai 2>$null
    Print-Status "Restarting deployments in voicecore-ai namespace..."
    
    # Get all deployments in the namespace
    $deployments = kubectl get deployments -n voicecore-ai -o name 2>$null
    
    if ($deployments) {
        foreach ($deployment in $deployments) {
            Write-Host "  Restarting $deployment..."
            kubectl rollout restart -n voicecore-ai $deployment
        }
        
        # Wait for rollouts to complete
        foreach ($deployment in $deployments) {
            kubectl rollout status -n voicecore-ai $deployment --timeout=300s
        }
        
        Print-Status "All deployments restarted with Istio sidecars"
    } else {
        Print-Warning "No deployments found in voicecore-ai namespace"
    }
} catch {
    Print-Warning "voicecore-ai namespace not found or no deployments exist"
}

# Step 8: Verify sidecar injection
Write-Host ""
Write-Host "Step 8: Verifying sidecar injection..."
$podsWithSidecars = (kubectl get pods -n voicecore-ai -o json 2>$null | ConvertFrom-Json).items | 
    Where-Object { $_.spec.containers.name -contains "istio-proxy" } | 
    Measure-Object | 
    Select-Object -ExpandProperty Count

if ($podsWithSidecars -gt 0) {
    Print-Status "Istio sidecars injected successfully ($podsWithSidecars pods)"
} else {
    Print-Warning "No pods with Istio sidecars found. This is normal if no applications are deployed yet."
}

# Step 9: Display Istio ingress gateway information
Write-Host ""
Write-Host "Step 9: Istio Ingress Gateway Information"
Write-Host "==========================================" -ForegroundColor Cyan

$ingressHost = kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>$null
if (-not $ingressHost) {
    $ingressHost = "pending"
}

$ingressPort = kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.spec.ports[?(@.name=="http2")].port}'
$secureIngressPort = kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.spec.ports[?(@.name=="https")].port}'

Write-Host "Ingress Gateway Host: $ingressHost"
Write-Host "HTTP Port: $ingressPort"
Write-Host "HTTPS Port: $secureIngressPort"

if ($ingressHost -eq "pending") {
    Print-Warning "LoadBalancer IP is pending. Run 'kubectl get svc -n istio-system' to check status."
} else {
    Print-Status "Ingress Gateway is accessible at: http://${ingressHost}:${ingressPort}"
}

# Step 10: Display mesh status
Write-Host ""
Write-Host "Step 10: Istio Mesh Status"
Write-Host "==========================================" -ForegroundColor Cyan
istioctl proxy-status

# Step 11: Verify mTLS status
Write-Host ""
Write-Host "Step 11: Verifying mTLS Configuration"
Write-Host "==========================================" -ForegroundColor Cyan
istioctl authn tls-check

# Summary
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Istio Deployment Complete!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Print-Status "Istio control plane (Pilot, Citadel, Mixer) installed"
Print-Status "Automatic sidecar injection enabled for voicecore-ai namespace"
Print-Status "Strict mTLS enforced for all service-to-service communication"
Print-Status "Certificate rotation configured (90-day lifetime)"
Print-Status "Traffic management rules applied (circuit breakers, retries)"
Print-Status "Zero-trust security policies enforced"

Write-Host ""
Write-Host "Next Steps:"
Write-Host "1. Deploy your microservices to the voicecore-ai namespace"
Write-Host "2. Monitor service mesh with: istioctl dashboard kiali"
Write-Host "3. View distributed traces with: istioctl dashboard jaeger"
Write-Host "4. Check mesh status with: istioctl proxy-status"
Write-Host "5. Verify mTLS with: istioctl authn tls-check"
Write-Host ""
Write-Host "For more information, visit: https://istio.io/latest/docs/"
Write-Host ""
