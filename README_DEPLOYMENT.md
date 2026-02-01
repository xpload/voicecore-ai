# 🚀 Guía de Despliegue - VoiceCore AI en Railway

## 📋 Pasos para Desplegar en Railway

### 1. Preparar el Repositorio en GitHub

1. **Crear repositorio en GitHub:**
   - Ve a [github.com](https://github.com) y crea una cuenta si no tienes
   - Haz clic en "New repository"
   - Nombre: `voicecore-ai`
   - Descripción: `Sistema de Recepcionista Virtual con IA`
   - Público o Privado (tu elección)
   - **NO** marques "Initialize with README"
   - Haz clic en "Create repository"

2. **Subir código a GitHub:**
   ```bash
   # En tu terminal, dentro de la carpeta del proyecto:
   git init
   git add .
   git commit -m "Initial commit - VoiceCore AI"
   git branch -M main
   git remote add origin https://github.com/TU_USUARIO/voicecore-ai.git
   git push -u origin main
   ```

### 2. Configurar Railway

1. **Crear cuenta en Railway:**
   - Ve a [railway.app](https://railway.app)
   - Haz clic en "Start a New Project"
   - Conecta con tu cuenta de GitHub

2. **Crear nuevo proyecto:**
   - Selecciona "Deploy from GitHub repo"
   - Busca y selecciona tu repositorio `voicecore-ai`
   - Railway detectará automáticamente el `Dockerfile`

3. **Configurar variables de entorno:**
   En el dashboard de Railway, ve a la pestaña "Variables" y agrega:
   
   ```
   DATABASE_URL=postgresql://postgres:password@postgres:5432/voicecore
   SECRET_KEY=tu_clave_secreta_super_segura_aqui_12345678901234567890
   JWT_SECRET_KEY=tu_jwt_clave_super_segura_aqui_12345678901234567890
   DEBUG=false
   LOG_LEVEL=INFO
   PORT=8000
   ```

4. **Agregar base de datos PostgreSQL:**
   - En tu proyecto de Railway, haz clic en "New Service"
   - Selecciona "Database" → "PostgreSQL"
   - Railway creará automáticamente la base de datos
   - La variable `DATABASE_URL` se configurará automáticamente

### 3. Configurar APIs Externas (Opcional)

Para funcionalidad completa, agrega estas variables en Railway:

#### Twilio (Para llamadas telefónicas):
```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=tu_auth_token_de_twilio
TWILIO_PHONE_NUMBER=+1234567890
```

#### OpenAI (Para IA):
```
OPENAI_API_KEY=sk-proj-tu_clave_api_de_openai_aqui
```

### 4. Desplegar

1. **Despliegue automático:**
   - Railway desplegará automáticamente cuando hagas push a GitHub
   - El primer despliegue puede tomar 5-10 minutos

2. **Verificar despliegue:**
   - Ve a la pestaña "Deployments" en Railway
   - Cuando esté listo, verás un enlace como: `https://tu-app.railway.app`

### 5. Probar la Aplicación

1. **Acceder a la aplicación:**
   - Haz clic en el enlace de tu aplicación
   - Deberías ver la página principal de VoiceCore AI

2. **Verificar endpoints:**
   - `/` - Página principal
   - `/docs` - Documentación de la API
   - `/health` - Estado del sistema

## 🔧 Solución de Problemas

### Error de Build
Si el build falla:
1. Revisa los logs en Railway
2. Verifica que `requirements_minimal.txt` esté correcto
3. Asegúrate de que `simple_start.py` esté en la raíz

### Error de Base de Datos
Si hay problemas con la DB:
1. Verifica que PostgreSQL esté agregado al proyecto
2. Revisa que `DATABASE_URL` esté configurada
3. Los modelos se crearán automáticamente al iniciar

### Error de Puerto
Railway asigna el puerto automáticamente:
- La aplicación debe usar `PORT` de las variables de entorno
- `simple_start.py` ya está configurado para esto

## 📞 Configuración de Producción

### Para usar llamadas reales:
1. Crea cuenta en [Twilio](https://twilio.com)
2. Obtén un número de teléfono
3. Configura webhooks apuntando a tu URL de Railway
4. Agrega las credenciales en Railway

### Para usar IA real:
1. Crea cuenta en [OpenAI](https://openai.com)
2. Genera una API key
3. Agrega la key en Railway

## 🎉 ¡Listo!

Tu aplicación VoiceCore AI estará disponible en:
`https://tu-proyecto.railway.app`

### Funcionalidades disponibles:
- ✅ Interfaz web completa
- ✅ API REST documentada
- ✅ Base de datos PostgreSQL
- ✅ Escalado automático
- ✅ HTTPS incluido
- ⚠️ Llamadas telefónicas (requiere Twilio)
- ⚠️ IA conversacional (requiere OpenAI)

¡Tu recepcionista virtual con IA está lista para recibir visitantes! 🤖📞