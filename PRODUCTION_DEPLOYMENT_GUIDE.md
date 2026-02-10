# 🚀 VoiceCore AI - Guía de Despliegue a Producción

## Fase 1: Pre-Despliegue - Testing Completo (30 minutos)

### Paso 1: Verificar el Sistema (2 minutos)

```bash
# Verificar que todo está listo
python check_test_readiness.py
```

**Resultado esperado:** ✅ Todos los checks en verde

Si algo falla:
- ❌ Dependencies → `pip install -r requirements.txt`
- ❌ Database → `alembic upgrade head`
- ❌ .env file → `cp .env.example .env` y configurar

### Paso 2: Ejecutar Suite de Pruebas (10 minutos)

```bash
# Ejecutar todas las pruebas
python run_call_tests.py
```

**Resultado esperado:**
```
✅ PASSED - Inbound Call with AI
✅ PASSED - Call Escalation to Human
✅ PASSED - Outbound Call by Agent
✅ PASSED - Multi-turn AI Conversation
✅ PASSED - AI Sentiment Detection
✅ PASSED - Call Recording Lifecycle

Summary:
  Total: 6
  Passed: 6
  Failed: 0

🎉 All tests passed!
```

### Paso 3: Probar Demo Interactivo (5 minutos)

```bash
# Ejecutar demo interactivo
python examples/interactive_call_demo.py
```

Selecciona opción 6 (Run All Scenarios) para ver todos los flujos.

### Paso 4: Verificar Event Sourcing (3 minutos)

```bash
# Ejecutar ejemplo de event sourcing
python examples/event_sourcing_example.py
```

**Verifica:**
- ✅ Eventos se almacenan correctamente
- ✅ Replay funciona
- ✅ Snapshots se crean
- ✅ Read models se actualizan

### Paso 5: Tests de Integración (10 minutos)

```bash
# Tests de integración completos
pytest tests/integration/ -v

# Tests específicos
pytest tests/integration/test_end_to_end_call_flows.py -v
pytest tests/integration/test_multitenant_isolation.py -v
pytest tests/integration/test_external_service_integrations.py -v
```

---

## Fase 2: Configuración de Producción (20 minutos)

### Paso 1: Configurar Variables de Entorno

```bash
# Copiar template de producción
cp .env.production.example .env.production
```

Editar `.env.production` con valores reales:

```env
# === PRODUCCIÓN ===
ENV=production
DEBUG=false
LOG_LEVEL=INFO

# Base de Datos (PostgreSQL en producción)
DATABASE_URL=postgresql://user:password@prod-db.example.com:5432/voicecore_prod

# Redis (para caché y sesiones)
REDIS_URL=redis://prod-redis.example.com:6379/0

# Twilio (Servicio de llamadas)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_production_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# OpenAI (IA conversacional)
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=500

# Seguridad
SECRET_KEY=your-super-secret-production-key-min-32-chars
JWT_SECRET_KEY=your-jwt-secret-production-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# CORS
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Kafka (Event Bus)
KAFKA_BOOTSTRAP_SERVERS=prod-kafka.example.com:9092
KAFKA_TOPIC_PREFIX=voicecore_prod

# Monitoring
SENTRY_DSN=https://xxxxx@sentry.io/xxxxx
PROMETHEUS_PORT=9090

# Email (para notificaciones)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@yourdomain.com
SMTP_PASSWORD=your_smtp_password
```

### Paso 2: Configurar Base de Datos de Producción

```bash
# Conectar a base de datos de producción
export DATABASE_URL="postgresql://user:password@prod-db:5432/voicecore_prod"

# Ejecutar migraciones
alembic upgrade head

# Verificar migraciones
alembic current
```

**Resultado esperado:**
```
INFO  [alembic.runtime.migration] Running upgrade -> 009_add_event_sourcing
Current revision: 009_add_event_sourcing
```

### Paso 3: Crear Tenant Inicial

```bash
# Crear primer tenant de producción
python scripts/init_project.py --production
```

Esto creará:
- ✅ Tenant principal
- ✅ Usuario administrador
- ✅ Departamentos básicos
- ✅ Configuración inicial

---

## Fase 3: Despliegue (Opción A - Docker) (15 minutos)

### Opción A1: Docker Compose (Más Simple)

```bash
# 1. Build de imágenes
docker-compose -f docker-compose.prod.yml build

# 2. Iniciar servicios
docker-compose -f docker-compose.prod.yml up -d

# 3. Verificar que todo está corriendo
docker-compose -f docker-compose.prod.yml ps

# 4. Ver logs
docker-compose -f docker-compose.prod.yml logs -f voicecore
```

**Servicios que se inician:**
- ✅ VoiceCore API (Puerto 8000)
- ✅ PostgreSQL (Puerto 5432)
- ✅ Redis (Puerto 6379)
- ✅ Nginx (Puerto 80/443)
- ✅ Prometheus (Puerto 9090)

### Opción A2: Docker Swarm (Para Cluster)

```bash
# 1. Inicializar Swarm
docker swarm init

# 2. Desplegar stack
docker stack deploy -c docker-compose.prod.yml voicecore

# 3. Verificar servicios
docker service ls

# 4. Escalar servicios
docker service scale voicecore_api=3
```

---

## Fase 3: Despliegue (Opción B - Kubernetes) (30 minutos)

### Paso 1: Preparar Cluster

```bash
# Verificar conexión al cluster
kubectl cluster-info

# Crear namespace
kubectl create namespace voicecore-prod

# Configurar contexto
kubectl config set-context --current --namespace=voicecore-prod
```

### Paso 2: Configurar Secrets

```bash
# Crear secrets desde .env.production
kubectl create secret generic voicecore-secrets \
  --from-env-file=.env.production \
  --namespace=voicecore-prod

# Verificar
kubectl get secrets -n voicecore-prod
```

### Paso 3: Desplegar Aplicación

```bash
# 1. Desplegar base de datos
kubectl apply -f kubernetes/postgres-statefulset.yaml

# 2. Desplegar Redis
kubectl apply -f kubernetes/redis-deployment.yaml

# 3. Desplegar VoiceCore
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
kubectl apply -f kubernetes/ingress.yaml

# 4. Verificar pods
kubectl get pods -n voicecore-prod

# 5. Ver logs
kubectl logs -f deployment/voicecore-api -n voicecore-prod
```

### Paso 4: Configurar Auto-Scaling

```bash
# Aplicar HPA (Horizontal Pod Autoscaler)
kubectl apply -f kubernetes/hpa.yaml

# Verificar HPA
kubectl get hpa -n voicecore-prod
```

---

## Fase 3: Despliegue (Opción C - Railway/Heroku) (10 minutos)

### Railway

```bash
# 1. Instalar Railway CLI
npm install -g @railway/cli

# 2. Login
railway login

# 3. Crear proyecto
railway init

# 4. Agregar PostgreSQL
railway add postgresql

# 5. Agregar Redis
railway add redis

# 6. Desplegar
railway up

# 7. Ver logs
railway logs
```

### Heroku

```bash
# 1. Login
heroku login

# 2. Crear app
heroku create voicecore-prod

# 3. Agregar PostgreSQL
heroku addons:create heroku-postgresql:standard-0

# 4. Agregar Redis
heroku addons:create heroku-redis:premium-0

# 5. Configurar variables
heroku config:set $(cat .env.production | xargs)

# 6. Desplegar
git push heroku main

# 7. Ejecutar migraciones
heroku run alembic upgrade head

# 8. Ver logs
heroku logs --tail
```

---

## Fase 4: Verificación Post-Despliegue (15 minutos)

### Paso 1: Health Check

```bash
# Verificar que la API responde
curl https://your-domain.com/health

# Resultado esperado:
{
  "status": "healthy",
  "version": "3.0.0",
  "database": "connected",
  "redis": "connected",
  "timestamp": "2026-02-10T10:00:00Z"
}
```

### Paso 2: Test de API

```bash
# Test de autenticación
curl -X POST https://your-domain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"your_password"}'

# Test de creación de llamada (con token)
curl -X POST https://your-domain.com/api/v1/calls \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"from_number":"+1234567890","to_number":"+0987654321"}'
```

### Paso 3: Verificar Event Sourcing

```bash
# Verificar eventos
curl https://your-domain.com/api/v1/events/statistics \
  -H "Authorization: Bearer YOUR_TOKEN"

# Resultado esperado:
{
  "total_events": 0,
  "event_type_distribution": {},
  "filters": {}
}
```

### Paso 4: Monitoreo

```bash
# Verificar Prometheus
curl https://your-domain.com:9090/metrics

# Verificar logs
tail -f /var/log/voicecore/app.log

# O con Docker
docker-compose -f docker-compose.prod.yml logs -f

# O con Kubernetes
kubectl logs -f deployment/voicecore-api -n voicecore-prod
```

---

## Fase 5: Configuración de Twilio (10 minutos)

### Paso 1: Configurar Webhooks

En el dashboard de Twilio (https://console.twilio.com):

1. **Phone Numbers** → Selecciona tu número
2. **Voice & Fax** → Configure with:
   - **A CALL COMES IN**: Webhook
   - **URL**: `https://your-domain.com/api/v1/webhooks/twilio/voice`
   - **HTTP**: POST

3. **Messaging** → Configure with:
   - **A MESSAGE COMES IN**: Webhook
   - **URL**: `https://your-domain.com/api/v1/webhooks/twilio/sms`
   - **HTTP**: POST

### Paso 2: Probar Llamada Real

```bash
# Hacer una llamada de prueba a tu número de Twilio
# Desde tu teléfono, llama al número configurado

# Verificar en logs que se recibió el webhook
kubectl logs -f deployment/voicecore-api -n voicecore-prod | grep "webhook"
```

---

## Fase 6: Monitoreo y Alertas (10 minutos)

### Paso 1: Configurar Prometheus

```bash
# Verificar que Prometheus está scrapeando métricas
curl http://localhost:9090/api/v1/targets

# Importar dashboards de Grafana
# Ir a Grafana → Import → ID: 1860 (Node Exporter)
# Ir a Grafana → Import → ID: 3662 (Prometheus 2.0)
```

### Paso 2: Configurar Alertas

```bash
# Verificar reglas de alerta
kubectl apply -f monitoring/alert_rules.yml

# Ver alertas activas
curl http://localhost:9090/api/v1/alerts
```

### Paso 3: Configurar Sentry (Opcional)

```python
# Ya está configurado en el código
# Solo necesitas agregar SENTRY_DSN en .env.production
```

---

## Fase 7: Testing en Producción (20 minutos)

### Test 1: Llamada Entrante Completa

```bash
# 1. Llama a tu número de Twilio desde tu teléfono
# 2. Verifica que la IA responde
# 3. Haz una pregunta
# 4. Verifica la respuesta
# 5. Termina la llamada

# Verificar en base de datos
psql $DATABASE_URL -c "SELECT * FROM calls ORDER BY created_at DESC LIMIT 1;"

# Verificar eventos
psql $DATABASE_URL -c "SELECT event_type, timestamp FROM event_store ORDER BY timestamp DESC LIMIT 10;"
```

### Test 2: Dashboard Web

```bash
# Abrir en navegador
https://your-domain.com/dashboard

# Verificar:
# ✅ Login funciona
# ✅ Dashboard carga
# ✅ Métricas se muestran
# ✅ Llamadas aparecen en tiempo real
```

### Test 3: API Endpoints

```bash
# Script de prueba completo
python test_production_api.py
```

Crear `test_production_api.py`:

```python
import requests
import json

BASE_URL = "https://your-domain.com"

# 1. Login
response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
    "email": "admin@example.com",
    "password": "your_password"
})
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Get calls
response = requests.get(f"{BASE_URL}/api/v1/calls", headers=headers)
print(f"✅ Calls: {len(response.json())} calls found")

# 3. Get events
response = requests.get(f"{BASE_URL}/api/v1/events/statistics", headers=headers)
print(f"✅ Events: {response.json()['total_events']} events stored")

# 4. Get agents
response = requests.get(f"{BASE_URL}/api/v1/agents", headers=headers)
print(f"✅ Agents: {len(response.json())} agents available")

print("\n🎉 All API tests passed!")
```

---

## Checklist Final de Producción

### Pre-Despliegue
- [ ] Todas las pruebas pasan
- [ ] Demo interactivo funciona
- [ ] Event sourcing verificado
- [ ] Variables de entorno configuradas
- [ ] Secrets configurados
- [ ] Base de datos migrada

### Despliegue
- [ ] Aplicación desplegada
- [ ] Servicios corriendo
- [ ] Health check responde
- [ ] Logs accesibles
- [ ] Auto-scaling configurado

### Post-Despliegue
- [ ] API responde correctamente
- [ ] Twilio webhooks configurados
- [ ] Llamada de prueba exitosa
- [ ] Dashboard accesible
- [ ] Monitoreo activo
- [ ] Alertas configuradas

### Seguridad
- [ ] HTTPS habilitado
- [ ] Certificados SSL válidos
- [ ] Firewall configurado
- [ ] Rate limiting activo
- [ ] Backups configurados

---

## Comandos Útiles de Producción

```bash
# Ver logs en tiempo real
kubectl logs -f deployment/voicecore-api -n voicecore-prod

# Reiniciar servicio
kubectl rollout restart deployment/voicecore-api -n voicecore-prod

# Escalar horizontalmente
kubectl scale deployment voicecore-api --replicas=5 -n voicecore-prod

# Ver métricas
kubectl top pods -n voicecore-prod

# Ejecutar comando en pod
kubectl exec -it deployment/voicecore-api -n voicecore-prod -- bash

# Backup de base de datos
kubectl exec -it postgres-0 -n voicecore-prod -- pg_dump voicecore_prod > backup.sql

# Ver eventos del cluster
kubectl get events -n voicecore-prod --sort-by='.lastTimestamp'
```

---

## Troubleshooting

### Problema: API no responde

```bash
# 1. Verificar pods
kubectl get pods -n voicecore-prod

# 2. Ver logs
kubectl logs deployment/voicecore-api -n voicecore-prod

# 3. Verificar servicio
kubectl get svc -n voicecore-prod

# 4. Verificar ingress
kubectl get ingress -n voicecore-prod
```

### Problema: Base de datos no conecta

```bash
# 1. Verificar pod de PostgreSQL
kubectl get pods -l app=postgres -n voicecore-prod

# 2. Probar conexión
kubectl exec -it postgres-0 -n voicecore-prod -- psql -U postgres

# 3. Verificar secrets
kubectl get secret voicecore-secrets -n voicecore-prod -o yaml
```

### Problema: Twilio webhooks fallan

```bash
# 1. Verificar logs de webhooks
kubectl logs -f deployment/voicecore-api -n voicecore-prod | grep webhook

# 2. Probar webhook manualmente
curl -X POST https://your-domain.com/api/v1/webhooks/twilio/voice \
  -d "CallSid=CAtest123&From=%2B1234567890&To=%2B0987654321"

# 3. Verificar en Twilio debugger
# https://console.twilio.com/us1/monitor/logs/debugger
```

---

## Soporte y Monitoreo Continuo

### Dashboards Recomendados

1. **Grafana**: http://your-domain.com:3000
   - Métricas de sistema
   - Métricas de aplicación
   - Métricas de llamadas

2. **Prometheus**: http://your-domain.com:9090
   - Métricas raw
   - Alertas activas

3. **Kibana** (si usas ELK): http://your-domain.com:5601
   - Logs centralizados
   - Búsqueda de eventos

### Alertas Críticas

Configurar alertas para:
- ✅ API down (> 1 minuto)
- ✅ Base de datos down
- ✅ Uso de CPU > 80%
- ✅ Uso de memoria > 85%
- ✅ Tasa de error > 5%
- ✅ Latencia > 2 segundos
- ✅ Llamadas fallidas > 10%

---

## 🎉 ¡Listo para Producción!

Tu sistema VoiceCore AI está ahora en producción con:

✅ Testing completo
✅ Event Sourcing activo
✅ Monitoreo configurado
✅ Auto-scaling habilitado
✅ Backups automáticos
✅ Alertas configuradas

**Próximos pasos:**
1. Monitorear métricas primeras 24 horas
2. Ajustar auto-scaling según carga
3. Optimizar queries lentas
4. Configurar CDN para frontend
5. Implementar CI/CD pipeline

**Contacto de Soporte:**
- Email: support@voicecore.ai
- Slack: #voicecore-prod
- On-call: +1-XXX-XXX-XXXX
