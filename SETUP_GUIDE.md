# 🚀 VoiceCore AI - Guía Completa de Configuración y Despliegue

Esta guía te llevará paso a paso para ejecutar VoiceCore AI localmente, configurar las APIs externas y desplegarlo en producción.

## 📋 Prerrequisitos

### Software Requerido
- **Python 3.11+** - [Descargar aquí](https://www.python.org/downloads/)
- **PostgreSQL 14+** - [Descargar aquí](https://www.postgresql.org/download/)
- **Redis 6+** - [Descargar aquí](https://redis.io/download)
- **Docker & Docker Compose** - [Descargar aquí](https://www.docker.com/get-started)
- **Git** - [Descargar aquí](https://git-scm.com/downloads)

### Cuentas de Servicios Externos
- **Supabase** - [Crear cuenta](https://supabase.com)
- **Twilio** - [Crear cuenta](https://www.twilio.com/try-twilio)
- **OpenAI** - [Crear cuenta](https://platform.openai.com)

## 🔧 Configuración Inicial

### 1. Instalar Python y Dependencias

```bash
# Verificar Python
python --version  # Debe ser 3.11+

# Instalar pip si no está disponible
python -m ensurepip --upgrade

# Instalar virtualenv
pip install virtualenv
```

### 2. Configurar el Proyecto

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Windows:
venv\Scripts\activate
# En macOS/Linux:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

## 🔑 Configuración de APIs Externas

### 1. Configurar Supabase

1. **Crear proyecto en Supabase:**
   - Ve a [supabase.com](https://supabase.com)
   - Crea una nueva cuenta o inicia sesión
   - Crea un nuevo proyecto
   - Anota la URL y la clave anónima

2. **Configurar base de datos:**
   - En el dashboard de Supabase, ve a "SQL Editor"
   - Ejecuta las migraciones de Alembic (ver sección de base de datos)

### 2. Configurar Twilio

1. **Obtener credenciales:**
   - Ve a [console.twilio.com](https://console.twilio.com)
   - Crea una cuenta o inicia sesión
   - Ve a "Account" > "API keys & tokens"
   - Copia tu Account SID y Auth Token

2. **Comprar número de teléfono:**
   - Ve a "Phone Numbers" > "Manage" > "Buy a number"
   - Compra un número con capacidades de voz
   - Anota el número comprado

3. **Configurar webhooks:**
   - En la configuración del número, establece:
   - Voice webhook: `https://tu-dominio.com/api/webhooks/twilio/voice`
   - Status callback: `https://tu-dominio.com/api/webhooks/twilio/status`

### 3. Configurar OpenAI

1. **Obtener API Key:**
   - Ve a [platform.openai.com](https://platform.openai.com)
   - Crea una cuenta o inicia sesión
   - Ve a "API Keys" y crea una nueva clave
   - Copia la clave API

2. **Configurar límites de uso:**
   - Ve a "Usage" y establece límites de gasto
   - Recomendado: $50-100/mes para pruebas

## 📝 Configuración de Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto:

```bash
# Configuración de Base de Datos
DATABASE_URL=postgresql://usuario:password@localhost:5432/voicecore_ai
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=tu_clave_anonima_de_supabase
SUPABASE_SERVICE_KEY=tu_clave_de_servicio_de_supabase

# Configuración de Twilio
TWILIO_ACCOUNT_SID=tu_account_sid_de_twilio
TWILIO_AUTH_TOKEN=tu_auth_token_de_twilio
TWILIO_PHONE_NUMBER=+1234567890

# Configuración de OpenAI
OPENAI_API_KEY=sk-tu_clave_api_de_openai
OPENAI_ORGANIZATION=tu_organizacion_opcional

# Configuración de Seguridad
SECRET_KEY=tu_clave_secreta_muy_segura_de_al_menos_32_caracteres
JWT_SECRET_KEY=otra_clave_secreta_para_jwt_tokens

# Configuración de Redis
REDIS_URL=redis://localhost:6379/0

# Configuración de la Aplicación
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Configuración de WebRTC
WEBRTC_STUN_SERVERS=stun:stun.l.google.com:19302
WEBRTC_TURN_SERVERS=turn:tu-servidor-turn.com:3478

# Configuración de Monitoreo
SENTRY_DSN=tu_dsn_de_sentry_opcional
PROMETHEUS_ENABLED=true
```

## 🗄️ Configuración de Base de Datos

### 1. Configurar PostgreSQL Local (Opcional)

```bash
# Instalar PostgreSQL
# Windows: Descargar desde postgresql.org
# macOS: brew install postgresql
# Ubuntu: sudo apt-get install postgresql

# Crear base de datos
createdb voicecore_ai

# Crear usuario
psql -c "CREATE USER voicecore_user WITH PASSWORD 'tu_password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE voicecore_ai TO voicecore_user;"
```

### 2. Ejecutar Migraciones

```bash
# Inicializar Alembic (solo primera vez)
alembic upgrade head

# Verificar migraciones
alembic current
alembic history
```

## 🏃‍♂️ Ejecutar el Proyecto Localmente

### 1. Método Rápido con Script

```bash
# Ejecutar script de inicio rápido
python quick_start.py
```

### 2. Método Manual

```bash
# Activar entorno virtual
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Ejecutar migraciones
alembic upgrade head

# Iniciar Redis (en otra terminal)
redis-server

# Iniciar la aplicación
uvicorn voicecore.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Método con Docker

```bash
# Construir y ejecutar con Docker Compose
docker-compose up --build

# Solo para desarrollo
docker-compose -f docker-compose.yml up
```

## 🌐 Acceder a la Interfaz

Una vez que el servidor esté ejecutándose, puedes acceder a:

### APIs y Documentación
- **API Principal:** http://localhost:8000
- **Documentación Swagger:** http://localhost:8000/docs
- **Documentación ReDoc:** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/health

### Paneles de Administración
- **Super Admin:** http://localhost:8000/admin
- **Tenant Admin:** http://localhost:8000/tenant-admin
- **Analytics Dashboard:** http://localhost:8000/analytics

### WebSocket y Tiempo Real
- **WebSocket Endpoint:** ws://localhost:8000/ws
- **Agent Status:** ws://localhost:8000/ws/agents
- **Call Events:** ws://localhost:8000/ws/calls

## 🧪 Probar la Funcionalidad

### 1. Crear un Tenant de Prueba

```bash
curl -X POST "http://localhost:8000/api/tenants" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Mi Empresa de Prueba",
    "domain": "miempresa.com",
    "phone_number": "+1234567890",
    "ai_name": "Sofia",
    "ai_voice": "alloy",
    "business_hours_start": "09:00",
    "business_hours_end": "17:00",
    "timezone": "UTC"
  }'
```

### 2. Crear Agentes

```bash
curl -X POST "http://localhost:8000/api/agents" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Juan Pérez",
    "email": "juan@miempresa.com",
    "extension": "101",
    "department": "customer_service",
    "tenant_id": "tu_tenant_id"
  }'
```

### 3. Probar Llamada de Prueba

```bash
curl -X POST "http://localhost:8000/api/webhooks/twilio/voice" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "From=+1987654321&To=+1234567890&CallSid=CA123456789"
```

## 🚀 Despliegue en Producción

### 1. Despliegue con Docker

```bash
# Construir imagen de producción
docker build -t voicecore-ai:latest .

# Ejecutar en producción
docker-compose -f docker-compose.prod.yml up -d
```

### 2. Despliegue en Kubernetes

```bash
# Aplicar configuraciones
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/secrets.yaml
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
kubectl apply -f kubernetes/ingress.yaml

# Verificar despliegue
kubectl get pods -n voicecore-ai
kubectl get services -n voicecore-ai
```

### 3. Despliegue en la Nube

#### AWS (usando ECS)
```bash
# Configurar AWS CLI
aws configure

# Ejecutar script de despliegue
./scripts/deploy.sh aws
```

#### Google Cloud (usando GKE)
```bash
# Configurar gcloud
gcloud auth login
gcloud config set project tu-proyecto

# Ejecutar script de despliegue
./scripts/deploy.sh gcp
```

#### Azure (usando AKS)
```bash
# Configurar Azure CLI
az login

# Ejecutar script de despliegue
./scripts/deploy.sh azure
```

## 🔧 Configuración de Producción

### 1. Variables de Entorno de Producción

```bash
# Configuración de seguridad
SECRET_KEY=clave_super_segura_de_produccion_64_caracteres_minimo
JWT_SECRET_KEY=otra_clave_super_segura_para_jwt_tokens

# Base de datos de producción
DATABASE_URL=postgresql://usuario:password@db-host:5432/voicecore_prod
SUPABASE_URL=https://tu-proyecto-prod.supabase.co

# APIs de producción
TWILIO_ACCOUNT_SID=tu_sid_de_produccion
OPENAI_API_KEY=tu_clave_de_produccion

# Configuración de aplicación
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING

# Dominio de producción
CORS_ORIGINS=https://tu-dominio.com,https://admin.tu-dominio.com
```

### 2. Configurar HTTPS

```bash
# Usando Let's Encrypt con Certbot
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d tu-dominio.com -d api.tu-dominio.com
```

### 3. Configurar Monitoreo

```bash
# Iniciar Prometheus y Grafana
docker-compose -f monitoring/docker-compose.yml up -d

# Acceder a dashboards
# Prometheus: http://tu-dominio.com:9090
# Grafana: http://tu-dominio.com:3000 (admin/admin)
```

## 📊 Monitoreo y Logs

### 1. Ver Logs en Tiempo Real

```bash
# Logs de la aplicación
docker-compose logs -f voicecore-ai

# Logs específicos
docker-compose logs -f voicecore-ai | grep ERROR
```

### 2. Métricas de Rendimiento

```bash
# Verificar salud del sistema
curl http://localhost:8000/health

# Métricas de Prometheus
curl http://localhost:8000/metrics
```

## 🔒 Seguridad en Producción

### 1. Configurar Firewall

```bash
# Permitir solo puertos necesarios
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

### 2. Configurar Rate Limiting

```bash
# Configurar en nginx.conf
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req zone=api burst=20 nodelay;
```

## 🆘 Solución de Problemas

### Problemas Comunes

1. **Error de conexión a base de datos:**
   ```bash
   # Verificar conexión
   psql $DATABASE_URL -c "SELECT 1;"
   ```

2. **Error de API de Twilio:**
   ```bash
   # Verificar credenciales
   curl -X GET "https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID.json" \
     -u "$TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN"
   ```

3. **Error de API de OpenAI:**
   ```bash
   # Verificar clave
   curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     "https://api.openai.com/v1/models"
   ```

### Logs de Debug

```bash
# Habilitar logs detallados
export LOG_LEVEL=DEBUG
export DEBUG=true

# Reiniciar aplicación
uvicorn voicecore.main:app --reload --log-level debug
```

## 📞 Configuración de Números de Teléfono

### 1. Configurar Webhooks en Twilio

En la consola de Twilio, para cada número:

1. **Voice Configuration:**
   - Webhook: `https://tu-dominio.com/api/webhooks/twilio/voice`
   - HTTP Method: POST

2. **Messaging Configuration:**
   - Webhook: `https://tu-dominio.com/api/webhooks/twilio/sms`
   - HTTP Method: POST

3. **Status Callbacks:**
   - Status Callback URL: `https://tu-dominio.com/api/webhooks/twilio/status`

### 2. Probar Configuración

```bash
# Hacer una llamada de prueba
curl -X POST "https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID/Calls.json" \
  -u "$TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN" \
  -d "From=$TWILIO_PHONE_NUMBER" \
  -d "To=+1234567890" \
  -d "Url=https://tu-dominio.com/api/webhooks/twilio/voice"
```

## 🎯 Próximos Pasos

1. **Configurar dominio personalizado**
2. **Configurar SSL/TLS**
3. **Configurar backups automáticos**
4. **Configurar alertas de monitoreo**
5. **Entrenar al equipo en el uso del sistema**
6. **Configurar integración con CRM existente**

## 📚 Recursos Adicionales

- [Documentación de Twilio](https://www.twilio.com/docs)
- [Documentación de OpenAI](https://platform.openai.com/docs)
- [Documentación de Supabase](https://supabase.com/docs)
- [Documentación de FastAPI](https://fastapi.tiangolo.com)

---

¿Necesitas ayuda con algún paso específico? ¡Estoy aquí para ayudarte! 🚀