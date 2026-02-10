# Getting Started with VoiceCore AI 2.0 🚀

This guide will help you get VoiceCore AI 2.0 up and running on your local machine or deploy it to production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Configuration](#configuration)
4. [Development Setup](#development-setup)
5. [Testing](#testing)
6. [Deployment](#deployment)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

- **Docker** (20.10+) - [Install Docker](https://docs.docker.com/get-docker/)
- **Docker Compose** (2.0+) - [Install Docker Compose](https://docs.docker.com/compose/install/)
- **Git** - [Install Git](https://git-scm.com/downloads)

### Optional (for local development)

- **Node.js** (20+) - [Install Node.js](https://nodejs.org/)
- **Python** (3.11+) - [Install Python](https://www.python.org/downloads/)
- **PostgreSQL** (15+) - [Install PostgreSQL](https://www.postgresql.org/download/)
- **Redis** (7+) - [Install Redis](https://redis.io/download)

### External Services (Optional)

- **OpenAI API Key** - [Get API Key](https://platform.openai.com/api-keys)
- **Twilio Account** - [Sign up](https://www.twilio.com/try-twilio)
- **Stripe Account** - [Sign up](https://dashboard.stripe.com/register)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/voicecore-ai-2.0.git
cd voicecore-ai-2.0
```

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.v2.example .env

# Edit .env with your configuration
# At minimum, set:
# - OPENAI_API_KEY (for AI features)
# - TWILIO credentials (for phone calls)
# - STRIPE keys (for billing)
```

### 3. Start the Platform

**Option A: Using the startup script (Recommended)**

```bash
python start_voicecore_v2.py
```

**Option B: Using Docker Compose directly**

```bash
docker-compose -f docker-compose.microservices.yml up -d
```

### 4. Access the Application

Once all services are running:

- **Frontend**: http://localhost:3000
- **API Gateway**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Configuration

### Environment Variables

The `.env` file contains all configuration options. Here are the most important ones:

#### Database Configuration

```env
DATABASE_URL=postgresql://voicecore:voicecore_secure_password@postgres:5432/voicecore_v2
```

#### AI Configuration

```env
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-4
OPENAI_TEMPERATURE=0.7
```

#### Twilio Configuration (for phone calls)

```env
TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890
```

#### Stripe Configuration (for billing)

```env
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key_here
```

#### Security Configuration

```env
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
ENABLE_MFA=true
SESSION_TIMEOUT_MINUTES=30
```

### Feature Flags

Enable or disable features:

```env
ENABLE_WEBRTC=true
ENABLE_VIDEO_CALLS=true
ENABLE_SCREEN_SHARING=true
ENABLE_REAL_TIME_TRANSLATION=true
ENABLE_SENTIMENT_ANALYSIS=true
ENABLE_VOICE_CLONING=false
```

## Development Setup

### Backend Development

Each microservice can be developed independently:

```bash
# Navigate to a service
cd services/tenant-service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the service
python main.py
```

### Frontend Development

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Testing

### Running All Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=voicecore --cov-report=html

# Run specific test file
pytest tests/test_ai_properties.py
```

### Property-Based Tests

```bash
# Run only property-based tests
pytest -m property

# Run with verbose output
pytest -v -m property

# Run specific property test
pytest tests/test_ai_properties.py::test_multi_language_support
```

### Unit Tests

```bash
# Run only unit tests
pytest -m unit

# Run integration tests
pytest -m integration
```

### Frontend Tests

```bash
cd frontend

# Run tests
npm test

# Run tests with coverage
npm test -- --coverage

# Run E2E tests
npm run test:e2e
```

## Deployment

### Docker Compose (Simple Deployment)

```bash
# Build and start all services
docker-compose -f docker-compose.microservices.yml up -d --build

# View logs
docker-compose -f docker-compose.microservices.yml logs -f

# Stop services
docker-compose -f docker-compose.microservices.yml down

# Stop and remove volumes
docker-compose -f docker-compose.microservices.yml down -v
```

### Kubernetes Deployment

```bash
# Create namespace
kubectl create namespace voicecore-v2

# Apply configurations
kubectl apply -f kubernetes/

# Check deployment status
kubectl get pods -n voicecore-v2

# View logs
kubectl logs -f deployment/gateway -n voicecore-v2

# Scale deployment
kubectl scale deployment/gateway --replicas=3 -n voicecore-v2
```

### Production Checklist

Before deploying to production:

- [ ] Change all default passwords and secrets
- [ ] Configure proper CORS origins
- [ ] Enable HTTPS/TLS
- [ ] Set up monitoring and alerting
- [ ] Configure backup strategy
- [ ] Enable audit logging
- [ ] Review security settings
- [ ] Set up CDN for static assets
- [ ] Configure auto-scaling
- [ ] Test disaster recovery procedures

## Troubleshooting

### Services Won't Start

**Problem**: Docker containers fail to start

**Solutions**:
1. Check Docker is running: `docker ps`
2. Check logs: `docker-compose -f docker-compose.microservices.yml logs`
3. Verify .env file exists and is configured
4. Check port conflicts: `netstat -an | grep LISTEN`

### Database Connection Errors

**Problem**: Services can't connect to PostgreSQL

**Solutions**:
1. Verify PostgreSQL is running: `docker ps | grep postgres`
2. Check DATABASE_URL in .env
3. Verify database exists: `docker exec -it <postgres-container> psql -U voicecore -d voicecore_v2`
4. Check network connectivity: `docker network ls`

### API Gateway Returns 503

**Problem**: Gateway shows services as unhealthy

**Solutions**:
1. Check individual service health: `curl http://localhost:8001/health`
2. Verify all services are running: `docker ps`
3. Check service logs: `docker logs <service-container>`
4. Restart services: `docker-compose -f docker-compose.microservices.yml restart`

### Frontend Can't Connect to Backend

**Problem**: Frontend shows connection errors

**Solutions**:
1. Verify API Gateway is running: `curl http://localhost:8000/health`
2. Check REACT_APP_API_URL in frontend/.env
3. Verify CORS settings in gateway
4. Check browser console for errors

### OpenAI API Errors

**Problem**: AI service fails with API errors

**Solutions**:
1. Verify OPENAI_API_KEY is set correctly
2. Check API key has sufficient credits
3. Verify model name is correct (gpt-4, gpt-3.5-turbo, etc.)
4. Check rate limits

### Performance Issues

**Problem**: System is slow or unresponsive

**Solutions**:
1. Check resource usage: `docker stats`
2. Verify Redis is running and accessible
3. Check database query performance
4. Review logs for errors or warnings
5. Consider scaling services

### Common Error Messages

#### "Port already in use"

```bash
# Find process using port
lsof -i :8000  # On Linux/Mac
netstat -ano | findstr :8000  # On Windows

# Kill process or change port in docker-compose.yml
```

#### "Cannot connect to Docker daemon"

```bash
# Start Docker daemon
sudo systemctl start docker  # On Linux
# Or start Docker Desktop on Windows/Mac
```

#### "Permission denied"

```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker
```

## Getting Help

### Documentation

- **README**: [README_V2.md](README_V2.md)
- **Requirements**: [.kiro/specs/voicecore-ai-2.0/requirements.md](.kiro/specs/voicecore-ai-2.0/requirements.md)
- **Design**: [.kiro/specs/voicecore-ai-2.0/design.md](.kiro/specs/voicecore-ai-2.0/design.md)
- **Tasks**: [.kiro/specs/voicecore-ai-2.0/tasks.md](.kiro/specs/voicecore-ai-2.0/tasks.md)

### Support Channels

- **Email**: support@voicecore.ai
- **Slack**: https://voicecore.slack.com
- **GitHub Issues**: https://github.com/your-org/voicecore-ai-2.0/issues

### Useful Commands

```bash
# View all running containers
docker ps

# View all containers (including stopped)
docker ps -a

# View logs for specific service
docker logs <container-name>

# Follow logs in real-time
docker logs -f <container-name>

# Execute command in container
docker exec -it <container-name> bash

# Restart specific service
docker-compose -f docker-compose.microservices.yml restart <service-name>

# Rebuild specific service
docker-compose -f docker-compose.microservices.yml up -d --build <service-name>

# Remove all containers and volumes
docker-compose -f docker-compose.microservices.yml down -v

# Check service health
curl http://localhost:8000/services
```

## Next Steps

Once you have VoiceCore AI 2.0 running:

1. **Explore the API**: Visit http://localhost:8000/docs
2. **Configure AI Personalities**: Set up custom AI behaviors for your tenants
3. **Set up Integrations**: Connect Salesforce, Slack, or other external services
4. **Customize the Frontend**: Modify React components to match your brand
5. **Add Custom Features**: Extend the platform with your own microservices
6. **Deploy to Production**: Follow the production deployment checklist

## Additional Resources

- **Docker Documentation**: https://docs.docker.com/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **React Documentation**: https://react.dev/
- **PostgreSQL Documentation**: https://www.postgresql.org/docs/
- **Redis Documentation**: https://redis.io/documentation
- **Kubernetes Documentation**: https://kubernetes.io/docs/

---

**Happy Building! 🚀**
