# Deploy HashiCorp Vault for VoiceCore AI 3.0 Enterprise
# PowerShell deployment script

$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Green
Write-Host "Deploying HashiCorp Vault" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow
if (!(Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Host "kubectl is required" -ForegroundColor Red
    exit 1
}
if (!(Get-Command helm -ErrorAction SilentlyContinue)) {
    Write-Host "helm is required" -ForegroundColor Red
    exit 1
}

# Create namespace
Write-Host "Creating Vault namespace..." -ForegroundColor Green
kubectl apply -f kubernetes/vault/vault-namespace.yaml

# Create storage resources
Write-Host "Creating storage resources..." -ForegroundColor Green
kubectl apply -f kubernetes/vault/vault-storage.yaml

# Create RBAC resources
Write-Host "Creating RBAC resources..." -ForegroundColor Green
kubectl apply -f kubernetes/vault/vault-rbac.yaml

# Generate TLS certificates
Write-Host "Generating TLS certificates..." -ForegroundColor Green
$secretExists = kubectl get secret vault-tls -n vault 2>$null
if (!$secretExists) {
    # Generate self-signed certificate
    $cert = New-SelfSignedCertificate `
        -DnsName "vault.voicecore.ai" `
        -CertStoreLocation "cert:\CurrentUser\My" `
        -NotAfter (Get-Date).AddYears(1)
    
    $certPath = "cert:\CurrentUser\My\$($cert.Thumbprint)"
    $certBytes = (Get-Item $certPath).Export("Pfx", "temp")
    [System.IO.File]::WriteAllBytes("$env:TEMP\vault.pfx", $certBytes)
    
    # Extract key and cert
    openssl pkcs12 -in "$env:TEMP\vault.pfx" -nocerts -nodes -out "$env:TEMP\vault-tls.key" -passin pass:temp
    openssl pkcs12 -in "$env:TEMP\vault.pfx" -clcerts -nokeys -out "$env:TEMP\vault-tls.crt" -passin pass:temp
    
    kubectl create secret tls vault-tls `
        --cert="$env:TEMP\vault-tls.crt" `
        --key="$env:TEMP\vault-tls.key" `
        -n vault
    
    Remove-Item "$env:TEMP\vault.pfx", "$env:TEMP\vault-tls.key", "$env:TEMP\vault-tls.crt"
}

# Apply configuration
Write-Host "Applying Vault configuration..." -ForegroundColor Green
kubectl apply -f kubernetes/vault/vault-config.yaml
kubectl apply -f kubernetes/vault/vault-policies.yaml

# Deploy Vault StatefulSet
Write-Host "Deploying Vault StatefulSet..." -ForegroundColor Green
kubectl apply -f kubernetes/vault/vault-statefulset.yaml

# Create services
Write-Host "Creating Vault services..." -ForegroundColor Green
kubectl apply -f kubernetes/vault/vault-services.yaml

# Wait for Vault pods
Write-Host "Waiting for Vault pods to be ready..." -ForegroundColor Yellow
kubectl wait --for=condition=ready pod -l app=vault -n vault --timeout=300s

# Initialize Vault
Write-Host "Initializing Vault..." -ForegroundColor Green
kubectl apply -f kubernetes/vault/vault-init-job.yaml

# Wait for initialization
Write-Host "Waiting for Vault initialization..." -ForegroundColor Yellow
kubectl wait --for=condition=complete job/vault-init -n vault --timeout=300s

# Apply monitoring
Write-Host "Setting up monitoring..." -ForegroundColor Green
kubectl apply -f kubernetes/vault/vault-monitoring.yaml

# Apply ingress
Write-Host "Configuring ingress..." -ForegroundColor Green
kubectl apply -f kubernetes/vault/vault-ingress.yaml

Write-Host "=========================================" -ForegroundColor Green
Write-Host "Vault deployment complete!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Vault UI: https://vault.voicecore.ai"
Write-Host ""
Write-Host "To get the root token:"
Write-Host "kubectl get secret vault-init-keys -n vault -o jsonpath='{.data.vault-init\.json}' | base64 -d | jq -r '.root_token'"
