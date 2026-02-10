# HashiCorp Vault Deployment for VoiceCore AI 3.0

This directory contains Kubernetes manifests for deploying HashiCorp Vault with High Availability configuration for VoiceCore AI 3.0 Enterprise Edition.

## Architecture

- **High Availability**: 3-node Raft cluster
- **Auto-unseal**: AWS KMS integration
- **Storage**: Persistent volumes with encryption
- **Security**: mTLS, zero-trust policies
- **Monitoring**: Prometheus metrics and Grafana dashboards

## Prerequisites

- Kubernetes cluster 1.24+
- kubectl configured
- Helm 3.x
- Istio service mesh (optional)
- AWS KMS key for auto-unseal

## Quick Start

### Deploy Vault

```bash
# Linux/Mac
./scripts/deploy-vault.sh

# Windows
.\scripts\deploy-vault.ps1
```

### Validate Deployment

```bash
./scripts/validate-vault.sh
```

## Manual Deployment

### 1. Create Namespace

```bash
kubectl apply -f vault-namespace.yaml
```

### 2. Create Storage

```bash
kubectl apply -f vault-storage.yaml
```

### 3. Create RBAC

```bash
kubectl apply -f vault-rbac.yaml
```

### 4. Generate TLS Certificates

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout vault-tls.key \
  -out vault-tls.crt \
  -subj "/CN=vault.voicecore.ai/O=VoiceCore"

kubectl create secret tls vault-tls \
  --cert=vault-tls.crt \
  --key=vault-tls.key \
  -n vault
```

### 5. Deploy Vault

```bash
kubectl apply -f vault-config.yaml
kubectl apply -f vault-policies.yaml
kubectl apply -f vault-statefulset.yaml
kubectl apply -f vault-services.yaml
```

### 6. Initialize Vault

```bash
kubectl apply -f vault-init-job.yaml
```

### 7. Get Root Token

```bash
kubectl get secret vault-init-keys -n vault \
  -o jsonpath='{.data.vault-init\.json}' | base64 -d | jq -r '.root_token'
```

## Configuration

### Secrets Engines

- **KV v2** (`voicecore/`): Application secrets
- **Database** (`database/`): Dynamic database credentials
- **Transit** (`transit/`): Encryption as a service
- **PKI** (`pki/`): Certificate management

### Auth Methods

- **Kubernetes**: Service account authentication
- **Token**: Root and service tokens

### Policies

- `admin-policy`: Full access
- `voicecore-policy`: Application access
- `database-admin-policy`: Database management
- `kubernetes-auth-policy`: K8s authentication
- `secrets-rotation-policy`: Secret rotation

## Usage

### Access Vault UI

```bash
# Port forward
kubectl port-forward -n vault svc/vault-ui 8200:8200

# Open browser
open https://localhost:8200
```

### Login with Root Token

```bash
export VAULT_TOKEN=$(kubectl get secret vault-init-keys -n vault \
  -o jsonpath='{.data.vault-init\.json}' | base64 -d | jq -r '.root_token')

kubectl exec -it vault-0 -n vault -- vault login $VAULT_TOKEN
```

### Store a Secret

```bash
kubectl exec -it vault-0 -n vault -- \
  vault kv put voicecore/config/database \
  username=admin \
  password=secret123
```

### Read a Secret

```bash
kubectl exec -it vault-0 -n vault -- \
  vault kv get voicecore/config/database
```

### Create Dynamic Database Credentials

```bash
# Configure database connection
kubectl exec -it vault-0 -n vault -- \
  vault write database/config/postgresql \
  plugin_name=postgresql-database-plugin \
  allowed_roles="voicecore-role" \
  connection_url="postgresql://{{username}}:{{password}}@postgres:5432/voicecore" \
  username="vault" \
  password="vault-password"

# Create role
kubectl exec -it vault-0 -n vault -- \
  vault write database/roles/voicecore-role \
  db_name=postgresql \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}';" \
  default_ttl="1h" \
  max_ttl="24h"

# Generate credentials
kubectl exec -it vault-0 -n vault -- \
  vault read database/creds/voicecore-role
```

### Encrypt/Decrypt Data

```bash
# Encrypt
kubectl exec -it vault-0 -n vault -- \
  vault write transit/encrypt/voicecore-key \
  plaintext=$(echo "sensitive data" | base64)

# Decrypt
kubectl exec -it vault-0 -n vault -- \
  vault write transit/decrypt/voicecore-key \
  ciphertext="vault:v1:..."
```

## Monitoring

### Prometheus Metrics

Vault exposes metrics at `/v1/sys/metrics?format=prometheus`

### Grafana Dashboard

Import the dashboard from `vault-monitoring.yaml`

### Alerts

- VaultSealed: Vault is sealed
- VaultDown: Vault is down
- VaultLeadershipLost: Lost leadership
- VaultHighMemoryUsage: Memory usage > 90%

## Backup and Recovery

### Backup Raft Data

```bash
kubectl exec -it vault-0 -n vault -- \
  vault operator raft snapshot save /tmp/vault-backup.snap

kubectl cp vault/vault-0:/tmp/vault-backup.snap ./vault-backup.snap
```

### Restore from Backup

```bash
kubectl cp ./vault-backup.snap vault/vault-0:/tmp/vault-backup.snap

kubectl exec -it vault-0 -n vault -- \
  vault operator raft snapshot restore /tmp/vault-backup.snap
```

## Troubleshooting

### Vault is Sealed

```bash
# Get unseal keys
kubectl get secret vault-init-keys -n vault \
  -o jsonpath='{.data.vault-init\.json}' | base64 -d | jq -r '.unseal_keys_b64[]'

# Unseal (need 3 keys)
kubectl exec -it vault-0 -n vault -- vault operator unseal <key1>
kubectl exec -it vault-0 -n vault -- vault operator unseal <key2>
kubectl exec -it vault-0 -n vault -- vault operator unseal <key3>
```

### Check Vault Status

```bash
kubectl exec -it vault-0 -n vault -- vault status
```

### View Logs

```bash
kubectl logs -f vault-0 -n vault
```

### Check Raft Peers

```bash
kubectl exec -it vault-0 -n vault -- vault operator raft list-peers
```

## Security Best Practices

1. **Rotate Root Token**: Rotate immediately after setup
2. **Enable Audit Logging**: Monitor all access
3. **Use Dynamic Secrets**: Never store static credentials
4. **Implement Least Privilege**: Minimal policy permissions
5. **Regular Backups**: Automated snapshot schedule
6. **Monitor Metrics**: Set up alerts for anomalies
7. **Seal on Breach**: Seal Vault if compromise detected

## Integration with VoiceCore

VoiceCore services authenticate using Kubernetes service accounts:

```python
import hvac

# Initialize Vault client
client = hvac.Client(url='https://vault.voicecore.ai:8200')

# Authenticate with Kubernetes
with open('/var/run/secrets/kubernetes.io/serviceaccount/token') as f:
    jwt = f.read()

client.auth.kubernetes.login(
    role='voicecore',
    jwt=jwt
)

# Read secrets
secret = client.secrets.kv.v2.read_secret_version(
    path='config/database',
    mount_point='voicecore'
)

print(secret['data']['data'])
```

## References

- [Vault Documentation](https://www.vaultproject.io/docs)
- [Vault on Kubernetes](https://www.vaultproject.io/docs/platform/k8s)
- [Vault HA with Raft](https://www.vaultproject.io/docs/configuration/storage/raft)
