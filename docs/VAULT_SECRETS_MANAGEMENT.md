# HashiCorp Vault Secrets Management

## Overview

VoiceCore AI 3.0 Enterprise uses HashiCorp Vault for centralized secrets management with zero-trust security, dynamic credentials, and automatic rotation.

## Architecture

- **High Availability**: 3-node Raft cluster
- **Auto-unseal**: AWS KMS integration
- **Dynamic Secrets**: Database credentials with TTL
- **Encryption as a Service**: Transit engine
- **PKI**: Certificate management
- **Audit Logging**: Immutable audit trails

## Secrets Engines

### 1. KV v2 (Key-Value)

Store application secrets:

```bash
# Write secret
vault kv put voicecore/config/api-keys \
  openai_key="sk-..." \
  twilio_sid="AC..." \
  stripe_key="sk_live_..."

# Read secret
vault kv get voicecore/config/api-keys

# List secrets
vault kv list voicecore/config/
```

### 2. Database Engine

Generate dynamic database credentials:

```bash
# Configure PostgreSQL
vault write database/config/postgresql \
  plugin_name=postgresql-database-plugin \
  connection_url="postgresql://{{username}}:{{password}}@postgres:5432/voicecore" \
  username="vault" \
  password="vault-password"

# Create role
vault write database/roles/voicecore-app \
  db_name=postgresql \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}';" \
  default_ttl="1h" \
  max_ttl="24h"

# Generate credentials
vault read database/creds/voicecore-app
```

### 3. Transit Engine

Encryption as a service:

```bash
# Encrypt data
vault write transit/encrypt/voicecore-key \
  plaintext=$(echo "sensitive data" | base64)

# Decrypt data
vault write transit/decrypt/voicecore-key \
  ciphertext="vault:v1:..."

# Rotate encryption key
vault write -f transit/keys/voicecore-key/rotate
```

## Python Integration

```python
import hvac
import os

class VaultService:
    def __init__(self):
        self.client = hvac.Client(url='https://vault.voicecore.ai:8200')
        self.authenticate()
    
    def authenticate(self):
        """Authenticate using Kubernetes service account"""
        with open('/var/run/secrets/kubernetes.io/serviceaccount/token') as f:
            jwt = f.read()
        
        self.client.auth.kubernetes.login(
            role='voicecore',
            jwt=jwt
        )
    
    async def get_secret(self, path: str) -> dict:
        """Get secret from Vault"""
        secret = self.client.secrets.kv.v2.read_secret_version(
            path=path,
            mount_point='voicecore'
        )
        return secret['data']['data']
    
    async def get_db_credentials(self) -> dict:
        """Get dynamic database credentials"""
        creds = self.client.secrets.database.generate_credentials(
            name='voicecore-app'
        )
        return {
            'username': creds['data']['username'],
            'password': creds['data']['password']
        }
    
    async def encrypt(self, plaintext: str) -> str:
        """Encrypt data using Transit engine"""
        encrypted = self.client.secrets.transit.encrypt_data(
            name='voicecore-key',
            plaintext=plaintext
        )
        return encrypted['data']['ciphertext']
```

## Security Best Practices

1. **Never store root token** - Rotate immediately
2. **Use dynamic secrets** - Short-lived credentials
3. **Enable audit logging** - Track all access
4. **Implement least privilege** - Minimal permissions
5. **Regular backups** - Automated snapshots
6. **Monitor metrics** - Alert on anomalies

## References

- [Vault Documentation](https://www.vaultproject.io/docs)
- [Best Practices](https://learn.hashicorp.com/tutorials/vault/production-hardening)
