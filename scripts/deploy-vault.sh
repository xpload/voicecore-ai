#!/bin/bash

# Deploy HashiCorp Vault for VoiceCore AI 3.0 Enterprise
# This script deploys Vault with HA configuration

set -e

echo "========================================="
echo "Deploying HashiCorp Vault"
echo "========================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"
command -v kubectl >/dev/null 2>&1 || { echo -e "${RED}kubectl is required${NC}"; exit 1; }
command -v helm >/dev/null 2>&1 || { echo -e "${RED}helm is required${NC}"; exit 1; }

# Create namespace
echo -e "${GREEN}Creating Vault namespace...${NC}"
kubectl apply -f kubernetes/vault/vault-namespace.yaml

# Create storage resources
echo -e "${GREEN}Creating storage resources...${NC}"
kubectl apply -f kubernetes/vault/vault-storage.yaml

# Create RBAC resources
echo -e "${GREEN}Creating RBAC resources...${NC}"
kubectl apply -f kubernetes/vault/vault-rbac.yaml

# Generate TLS certificates
echo -e "${GREEN}Generating TLS certificates...${NC}"
if ! kubectl get secret vault-tls -n vault >/dev/null 2>&1; then
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /tmp/vault-tls.key \
    -out /tmp/vault-tls.crt \
    -subj "/CN=vault.voicecore.ai/O=VoiceCore"
  
  kubectl create secret tls vault-tls \
    --cert=/tmp/vault-tls.crt \
    --key=/tmp/vault-tls.key \
    -n vault
  
  rm /tmp/vault-tls.key /tmp/vault-tls.crt
fi

# Apply configuration
echo -e "${GREEN}Applying Vault configuration...${NC}"
kubectl apply -f kubernetes/vault/vault-config.yaml
kubectl apply -f kubernetes/vault/vault-policies.yaml

# Deploy Vault StatefulSet
echo -e "${GREEN}Deploying Vault StatefulSet...${NC}"
kubectl apply -f kubernetes/vault/vault-statefulset.yaml

# Create services
echo -e "${GREEN}Creating Vault services...${NC}"
kubectl apply -f kubernetes/vault/vault-services.yaml

# Wait for Vault pods
echo -e "${YELLOW}Waiting for Vault pods to be ready...${NC}"
kubectl wait --for=condition=ready pod -l app=vault -n vault --timeout=300s

# Initialize Vault
echo -e "${GREEN}Initializing Vault...${NC}"
kubectl apply -f kubernetes/vault/vault-init-job.yaml

# Wait for initialization
echo -e "${YELLOW}Waiting for Vault initialization...${NC}"
kubectl wait --for=condition=complete job/vault-init -n vault --timeout=300s

# Apply monitoring
echo -e "${GREEN}Setting up monitoring...${NC}"
kubectl apply -f kubernetes/vault/vault-monitoring.yaml

# Apply ingress
echo -e "${GREEN}Configuring ingress...${NC}"
kubectl apply -f kubernetes/vault/vault-ingress.yaml

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Vault deployment complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Vault UI: https://vault.voicecore.ai"
echo ""
echo "To get the root token:"
echo "kubectl get secret vault-init-keys -n vault -o jsonpath='{.data.vault-init\.json}' | base64 -d | jq -r '.root_token'"
echo ""
echo "To unseal Vault manually (if needed):"
echo "kubectl exec -it vault-0 -n vault -- vault operator unseal"
