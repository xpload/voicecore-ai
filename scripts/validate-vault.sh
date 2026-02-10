#!/bin/bash

# Validate HashiCorp Vault deployment

set -e

echo "========================================="
echo "Validating Vault Deployment"
echo "========================================="

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

FAILED=0

# Check namespace
echo -e "${YELLOW}Checking Vault namespace...${NC}"
if kubectl get namespace vault >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Vault namespace exists${NC}"
else
    echo -e "${RED}✗ Vault namespace not found${NC}"
    FAILED=1
fi

# Check pods
echo -e "${YELLOW}Checking Vault pods...${NC}"
READY_PODS=$(kubectl get pods -n vault -l app=vault --no-headers 2>/dev/null | grep -c "Running" || echo "0")
if [ "$READY_PODS" -ge 3 ]; then
    echo -e "${GREEN}✓ All Vault pods are running ($READY_PODS/3)${NC}"
else
    echo -e "${RED}✗ Not all Vault pods are running ($READY_PODS/3)${NC}"
    FAILED=1
fi

# Check services
echo -e "${YELLOW}Checking Vault services...${NC}"
if kubectl get service vault -n vault >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Vault service exists${NC}"
else
    echo -e "${RED}✗ Vault service not found${NC}"
    FAILED=1
fi

# Check Vault status
echo -e "${YELLOW}Checking Vault status...${NC}"
VAULT_STATUS=$(kubectl exec -it vault-0 -n vault -- vault status -format=json 2>/dev/null || echo "{}")
INITIALIZED=$(echo "$VAULT_STATUS" | jq -r '.initialized // false')
SEALED=$(echo "$VAULT_STATUS" | jq -r '.sealed // true')

if [ "$INITIALIZED" = "true" ]; then
    echo -e "${GREEN}✓ Vault is initialized${NC}"
else
    echo -e "${RED}✗ Vault is not initialized${NC}"
    FAILED=1
fi

if [ "$SEALED" = "false" ]; then
    echo -e "${GREEN}✓ Vault is unsealed${NC}"
else
    echo -e "${YELLOW}⚠ Vault is sealed${NC}"
fi

# Check HA status
echo -e "${YELLOW}Checking HA status...${NC}"
HA_ENABLED=$(echo "$VAULT_STATUS" | jq -r '.ha_enabled // false')
if [ "$HA_ENABLED" = "true" ]; then
    echo -e "${GREEN}✓ HA is enabled${NC}"
else
    echo -e "${YELLOW}⚠ HA is not enabled${NC}"
fi

# Check secrets engines
echo -e "${YELLOW}Checking secrets engines...${NC}"
SECRETS_ENGINES=$(kubectl exec -it vault-0 -n vault -- vault secrets list -format=json 2>/dev/null || echo "{}")
if echo "$SECRETS_ENGINES" | jq -e '.["voicecore/"]' >/dev/null 2>&1; then
    echo -e "${GREEN}✓ VoiceCore KV secrets engine enabled${NC}"
else
    echo -e "${RED}✗ VoiceCore KV secrets engine not found${NC}"
    FAILED=1
fi

if echo "$SECRETS_ENGINES" | jq -e '.["database/"]' >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Database secrets engine enabled${NC}"
else
    echo -e "${RED}✗ Database secrets engine not found${NC}"
    FAILED=1
fi

if echo "$SECRETS_ENGINES" | jq -e '.["transit/"]' >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Transit secrets engine enabled${NC}"
else
    echo -e "${RED}✗ Transit secrets engine not found${NC}"
    FAILED=1
fi

# Check auth methods
echo -e "${YELLOW}Checking auth methods...${NC}"
AUTH_METHODS=$(kubectl exec -it vault-0 -n vault -- vault auth list -format=json 2>/dev/null || echo "{}")
if echo "$AUTH_METHODS" | jq -e '.["kubernetes/"]' >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Kubernetes auth method enabled${NC}"
else
    echo -e "${RED}✗ Kubernetes auth method not found${NC}"
    FAILED=1
fi

# Check monitoring
echo -e "${YELLOW}Checking monitoring...${NC}"
if kubectl get servicemonitor vault -n vault >/dev/null 2>&1; then
    echo -e "${GREEN}✓ ServiceMonitor configured${NC}"
else
    echo -e "${YELLOW}⚠ ServiceMonitor not found${NC}"
fi

# Summary
echo ""
echo "========================================="
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ Vault validation passed!${NC}"
    echo "========================================="
    exit 0
else
    echo -e "${RED}✗ Vault validation failed!${NC}"
    echo "========================================="
    exit 1
fi
