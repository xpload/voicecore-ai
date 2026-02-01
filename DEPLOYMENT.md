# VoiceCore AI - Production Deployment Guide

This document provides comprehensive instructions for deploying VoiceCore AI to production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Configuration](#configuration)
6. [Monitoring and Logging](#monitoring-and-logging)
7. [Security](#security)
8. [Backup and Recovery](#backup-and-recovery)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **CPU**: Minimum 4 cores, recommended 8+ cores
- **Memory**: Minimum 8GB RAM, recommended 16GB+ RAM
- **Storage**: Minimum 100GB SSD, recommended 500GB+ SSD
- **Network**: Stable internet connection with low latency

### Software Requirements

- Docker 20.10+ and Docker Compose 2.0+
- OR Kubernetes 1.20+ with kubectl configured
- SSL certificates for HTTPS
- Domain name with DNS configured

### External Services

- **Supabase**: PostgreSQL database with RLS enabled
- **Twilio**: Voice API account with phone numbers
- **OpenAI**: API account with Realtime API access
- **Redis**: For caching and session storage (can be self-hosted)

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/voicecore-ai.git
cd voicecore-ai
```

### 2. Configure Environment Variables

Copy the production environment template:

```bash
cp .env.production.example .env.production
```

Edit `.env.production` with your actual values:

```bash
# Required: Update these values
SECRET_KEY=your-super-secret-key-change-this-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-this

# Database (Supabase)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
DATABASE_URL=postgresql://postgres:password@your-supabase-db-host:5432/postgres

# Twilio
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_WEBHOOK_URL=https://your-domain.com/api/v1/webhooks/twilio

# OpenAI
OPENAI_API_KEY=your-openai-api-key

# Domain and CORS
ALLOWED_ORIGINS=https://your-domain.com,https://admin.your-domain.com
```

### 3. SSL Certificates

Place your SSL certificates in the `nginx/ssl/` directory:

```bash
mkdir -p nginx/ssl
cp your-certificate.crt nginx/ssl/voicecore.crt
cp your-private-key.key nginx/ssl/voicecore.key
```

Or generate self-signed certificates for testing:

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/voicecore.key \
  -out nginx/ssl/voicecore.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=your-domain.com"
```

## Docker Deployment

### Quick Start

Use the deployment script for automated deployment:

```bash
# Linux/macOS
chmod +x scripts/deploy.sh
./scripts/deploy.sh deploy

# Windows PowerShell
.\scripts\setup-production.ps1 -Action deploy
```

### Manual Deployment

1. **Build and start services:**

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

2. **Run database migrations:**

```bash
docker-compose -f docker-compose.prod.yml exec voicecore alembic upgrade head
```

3. **Verify deployment:**

```bash
curl -f http://localhost:8000/health
```

### Service Management

```bash
# View logs
docker-compose -f docker-compose.prod.yml logs -f voicecore

# Restart services
docker-compose -f docker-compose.prod.yml restart

# Scale services
docker-compose -f docker-compose.prod.yml up -d --scale voicecore=3

# Stop services
docker-compose -f docker-compose.prod.yml down
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (EKS, GKE, AKS, or self-managed)
- kubectl configured to access your cluster
- Ingress controller (nginx-ingress recommended)
- cert-manager for SSL certificates (optional)

### Deployment Steps

1. **Create namespace:**

```bash
kubectl apply -f kubernetes/namespace.yaml
```

2. **Configure secrets:**

Edit `kubernetes/secrets.yaml` with base64-encoded values:

```bash
echo -n "your-secret-value" | base64
```

Apply secrets:

```bash
kubectl apply -f kubernetes/secrets.yaml
```

3. **Deploy application:**

```bash
# Using individual manifests
kubectl apply -f kubernetes/

# Or using Kustomize
kubectl apply -k kubernetes/
```

4. **Verify deployment:**

```bash
kubectl get pods -n voicecore-ai
kubectl get services -n voicecore-ai
kubectl get ingress -n voicecore-ai
```

5. **Run database migrations:**

```bash
kubectl exec -n voicecore-ai deployment/voicecore-api -- alembic upgrade head
```

### Scaling

```bash
# Manual scaling
kubectl scale deployment voicecore-api --replicas=5 -n voicecore-ai

# Auto-scaling is configured via HPA (kubernetes/hpa.yaml)
kubectl get hpa -n voicecore-ai
```

## Configuration

### Database Setup

1. **Create Supabase project** and configure RLS policies
2. **Run initial migrations:**

```sql
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Run Alembic migrations
-- This is handled automatically by the deployment scripts
```

### Twilio Configuration

1. **Configure webhook URLs** in Twilio Console:
   - Voice webhook: `https://your-domain.com/api/v1/webhooks/twilio/voice`
   - Status callback: `https://your-domain.com/api/v1/webhooks/twilio/status`

2. **Purchase phone numbers** and assign to your application

### OpenAI Configuration

1. **Ensure API access** to GPT-4 and Realtime API
2. **Configure usage limits** and monitoring

## Monitoring and Logging

### Prometheus and Grafana

The Docker Compose setup includes Prometheus and Grafana:

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

### Application Metrics

VoiceCore AI exposes metrics at `/metrics` endpoint:

```bash
curl http://localhost:8000/metrics
```

### Log Aggregation

Logs are collected using structured logging (JSON format):

```bash
# View application logs
docker-compose -f docker-compose.prod.yml logs -f voicecore

# In Kubernetes
kubectl logs -f deployment/voicecore-api -n voicecore-ai
```

### Health Checks

- **Application health**: `/health`
- **System diagnostics**: `/api/v1/system/health`
- **Component status**: `/api/v1/system/diagnostics`

## Security

### Network Security

- All external communication uses HTTPS/TLS
- Internal service communication within Docker/K8s network
- Rate limiting configured at nginx and application level

### Authentication

- JWT-based authentication for API access
- Webhook signature verification for Twilio
- API key authentication for external integrations

### Data Protection

- Row-Level Security (RLS) in PostgreSQL
- Encryption at rest and in transit
- No storage of sensitive PII data
- Audit logging for all operations

### Security Headers

Nginx is configured with security headers:

```
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000
Content-Security-Policy: [configured policy]
```

## Backup and Recovery

### Automated Backups

The deployment script includes backup functionality:

```bash
# Create backup
./scripts/deploy.sh backup

# Windows
.\scripts\setup-production.ps1 -Action backup
```

### Manual Backup

```bash
# Database backup (if using local PostgreSQL)
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U voicecore voicecore > backup.sql

# Redis backup
docker-compose -f docker-compose.prod.yml exec redis redis-cli BGSAVE
```

### Disaster Recovery

```bash
# Rollback to previous version
./scripts/deploy.sh rollback

# Windows
.\scripts\setup-production.ps1 -Action rollback
```

## Troubleshooting

### Common Issues

1. **Service won't start:**
   - Check environment variables
   - Verify external service connectivity
   - Check Docker/K8s resource limits

2. **Database connection issues:**
   - Verify Supabase credentials
   - Check network connectivity
   - Ensure RLS policies are configured

3. **Twilio webhook failures:**
   - Verify webhook URLs are accessible
   - Check webhook signature validation
   - Ensure proper SSL certificate

4. **High memory usage:**
   - Monitor application metrics
   - Check for memory leaks
   - Adjust resource limits

### Debugging Commands

```bash
# Check service status
docker-compose -f docker-compose.prod.yml ps

# View detailed logs
docker-compose -f docker-compose.prod.yml logs --tail=100 voicecore

# Check system resources
docker stats

# Test external connectivity
curl -v https://api.openai.com/v1/models
curl -v https://api.twilio.com/2010-04-01/Accounts.json
```

### Performance Tuning

1. **Database optimization:**
   - Configure connection pooling
   - Optimize queries and indexes
   - Monitor slow query log

2. **Redis optimization:**
   - Configure memory limits
   - Enable persistence if needed
   - Monitor memory usage

3. **Application tuning:**
   - Adjust worker processes
   - Configure connection limits
   - Enable caching where appropriate

### Support

For additional support:

1. Check application logs and metrics
2. Review system diagnostics endpoint
3. Consult the error handling system
4. Contact support with correlation IDs

## Production Checklist

Before going live:

- [ ] SSL certificates configured and valid
- [ ] Environment variables properly set
- [ ] Database migrations completed
- [ ] External services configured (Twilio, OpenAI)
- [ ] Monitoring and alerting set up
- [ ] Backup strategy implemented
- [ ] Security review completed
- [ ] Load testing performed
- [ ] Disaster recovery plan tested
- [ ] Documentation updated
- [ ] Team trained on operations

## Maintenance

### Regular Tasks

- Monitor system health and performance
- Review and rotate secrets regularly
- Update dependencies and security patches
- Backup verification and testing
- Capacity planning and scaling
- Log rotation and cleanup

### Updates

```bash
# Update to new version
git pull origin main
./scripts/deploy.sh deploy

# Rollback if needed
./scripts/deploy.sh rollback
```

The deployment system supports zero-downtime rolling updates with automatic health checks and rollback capabilities.