#!/usr/bin/env python3
"""
🚀 VoiceCore AI - Deployment Completo a Railway
Script automatizado para desplegar desde cero
"""

import os
import subprocess
import sys
import time
import json
from pathlib import Path

class RailwayDeployer:
    def __init__(self):
        self.project_name = "voicecore-ai-production"
        self.github_repo = "xpload/voicecore-ai"
        self.errors = []
        
    def print_header(self, text):
        """Imprimir encabezado"""
        print("\n" + "=" * 60)
        print(f"🚀 {text}")
        print("=" * 60 + "\n")
    
    def print_step(self, step, text):
        """Imprimir paso"""
        print(f"\n[{step}] {text}")
    
    def print_success(self, text):
        """Imprimir éxito"""
        print(f"✅ {text}")
    
    def print_error(self, text):
        """Imprimir error"""
        print(f"❌ {text}")
        self.errors.append(text)
    
    def print_info(self, text):
        """Imprimir información"""
        print(f"ℹ️  {text}")
    
    def run_command(self, command, description, capture=True):
        """Ejecutar comando"""
        try:
            if capture:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                return result.returncode == 0, result.stdout, result.stderr
            else:
                result = subprocess.run(command, shell=True, timeout=60)
                return result.returncode == 0, "", ""
        except subprocess.TimeoutExpired:
            self.print_error(f"{description} - Timeout")
            return False, "", "Timeout"
        except Exception as e:
            self.print_error(f"{description} - Error: {e}")
            return False, "", str(e)
    
    def check_git(self):
        """Verificar Git"""
        self.print_step(1, "Verificando Git...")
        
        success, stdout, stderr = self.run_command("git --version", "Git check")
        if success:
            self.print_success(f"Git instalado: {stdout.strip()}")
            return True
        else:
            self.print_error("Git no está instalado")
            return False
    
    def check_github_repo(self):
        """Verificar repositorio GitHub"""
        self.print_step(2, "Verificando repositorio GitHub...")
        
        success, stdout, stderr = self.run_command("git remote -v", "Git remote check")
        if success and "github.com" in stdout:
            self.print_success("Repositorio GitHub configurado")
            print(f"   {stdout.strip()}")
            return True
        else:
            self.print_error("Repositorio GitHub no configurado")
            return False
    
    def ensure_code_pushed(self):
        """Asegurar que el código está en GitHub"""
        self.print_step(3, "Verificando código en GitHub...")
        
        # Verificar status
        success, stdout, stderr = self.run_command("git status --porcelain", "Git status")
        
        if stdout.strip():
            self.print_info("Hay cambios sin commitear")
            
            # Add all
            self.print_info("Agregando archivos...")
            success, _, _ = self.run_command("git add .", "Git add")
            
            # Commit
            self.print_info("Creando commit...")
            commit_msg = "Deploy: VoiceCore AI 3.0 Enterprise to Railway"
            success, _, _ = self.run_command(f'git commit -m "{commit_msg}"', "Git commit")
            
            # Push
            self.print_info("Subiendo a GitHub...")
            success, stdout, stderr = self.run_command("git push origin main", "Git push")
            
            if not success:
                # Try master
                success, _, _ = self.run_command("git push origin master", "Git push master")
            
            if success:
                self.print_success("Código subido a GitHub")
                return True
            else:
                self.print_error("Error al subir código a GitHub")
                return False
        else:
            self.print_success("Código ya está en GitHub")
            return True
    
    def create_railway_instructions(self):
        """Crear instrucciones para Railway"""
        self.print_header("INSTRUCCIONES PARA RAILWAY")
        
        print("""
🎯 PASOS PARA DESPLEGAR EN RAILWAY:

1️⃣  CREAR PROYECTO EN RAILWAY
   • Ve a: https://railway.app/new
   • Click en "Deploy from GitHub repo"
   • Selecciona: xpload/voicecore-ai
   • Click en "Deploy Now"

2️⃣  AGREGAR POSTGRESQL
   • En tu proyecto, click "+ New"
   • Selecciona "Database"
   • Selecciona "PostgreSQL"
   • Railway configurará DATABASE_URL automáticamente

3️⃣  CONFIGURAR VARIABLES DE ENTORNO
   • Click en tu servicio "voicecore-ai"
   • Ve a "Variables"
   • Agrega estas variables:

   SECRET_KEY=voicecore-production-secret-key-2024-change-this-in-production-12345678901234567890
   JWT_SECRET_KEY=voicecore-jwt-secret-key-2024-change-this-in-production-12345678901234567890
   DEBUG=false
   LOG_LEVEL=INFO
   
   # Opcionales (para funcionalidad completa):
   TWILIO_ACCOUNT_SID=tu-twilio-sid
   TWILIO_AUTH_TOKEN=tu-twilio-token
   TWILIO_PHONE_NUMBER=+1234567890
   OPENAI_API_KEY=sk-tu-openai-key

4️⃣  ESPERAR DEPLOYMENT (2-5 minutos)
   • Railway construirá y desplegará automáticamente
   • Verás los logs en tiempo real

5️⃣  OBTENER URL
   • Ve a "Settings" → "Domains"
   • Click "Generate Domain"
   • Copia tu URL: https://voicecore-ai-production-xxxx.railway.app

6️⃣  EJECUTAR MIGRACIONES
   • En Railway, ve a tu servicio
   • Click en "..." → "Run Command"
   • Ejecuta: alembic upgrade head

7️⃣  VERIFICAR DEPLOYMENT
   • Abre: https://tu-url.railway.app/health
   • Deberías ver: {"status":"healthy"}

8️⃣  PROBAR APLICACIÓN
   • API Docs: https://tu-url.railway.app/docs
   • Dashboard: https://tu-url.railway.app/dashboard
   • Event Sourcing: https://tu-url.railway.app/api/v1/events/statistics

═══════════════════════════════════════════════════════════════

🔗 ENLACES RÁPIDOS:

• Railway Dashboard: https://railway.app/dashboard
• Crear Proyecto: https://railway.app/new
• GitHub Repo: https://github.com/xpload/voicecore-ai
• Documentación Railway: https://docs.railway.app

═══════════════════════════════════════════════════════════════

⚡ TIPS IMPORTANTES:

1. DATABASE_URL se configura automáticamente al agregar PostgreSQL
2. No necesitas Railway CLI para esto
3. El deployment es automático desde GitHub
4. Puedes ver logs en tiempo real en Railway
5. Si algo falla, revisa los logs en Railway dashboard

═══════════════════════════════════════════════════════════════
""")
    
    def create_env_production_file(self):
        """Crear archivo .env.production con valores correctos"""
        self.print_step(4, "Creando archivo .env.production...")
        
        env_content = """# VoiceCore AI - Production Environment Variables
# Configuración para Railway

# Application Settings
APP_NAME=VoiceCore AI
APP_VERSION=3.0.0
DEBUG=false
LOG_LEVEL=INFO
SECRET_KEY=voicecore-production-secret-key-2024-change-this-in-production-12345678901234567890

# Server Settings (Railway configura PORT automáticamente)
HOST=0.0.0.0
PORT=8000
RELOAD=false

# Database Configuration (Railway configura DATABASE_URL automáticamente)
# DATABASE_URL se configura automáticamente al agregar PostgreSQL en Railway

# Security Settings
JWT_SECRET_KEY=voicecore-jwt-secret-key-2024-change-this-in-production-12345678901234567890
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
BCRYPT_ROUNDS=12

# CORS Settings
ALLOWED_ORIGINS=["https://voicecore-ai-production.railway.app","https://voicecore-ai-production-*.railway.app"]

# Twilio Configuration (Opcional - configurar cuando tengas cuenta)
# TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# TWILIO_AUTH_TOKEN=tu_auth_token
# TWILIO_PHONE_NUMBER=+1234567890
# TWILIO_WEBHOOK_URL=https://tu-url.railway.app/api/webhooks/twilio

# OpenAI Configuration (Opcional - configurar cuando tengas cuenta)
# OPENAI_API_KEY=sk-proj-tu_clave_api
OPENAI_MODEL=gpt-4o-mini
OPENAI_REALTIME_MODEL=gpt-4o-realtime-preview-2024-10-01

# Redis Configuration (Opcional)
# REDIS_URL=redis://redis:6379

# File Storage
STORAGE_BUCKET=voicecore-recordings-prod
MAX_FILE_SIZE_MB=100

# Rate Limiting
RATE_LIMIT_CALLS_PER_MINUTE=100
RATE_LIMIT_BURST=20

# WebSocket Configuration
WEBSOCKET_HEARTBEAT_INTERVAL=30
WEBSOCKET_TIMEOUT=60

# Call Configuration
MAX_CONCURRENT_CALLS_PER_TENANT=2000
CALL_TIMEOUT_SECONDS=3600
AI_RESPONSE_TIMEOUT_MS=1500

# Spam Detection
SPAM_DETECTION_THRESHOLD=0.8
SPAM_CHALLENGE_ENABLED=true

# Monitoring & Logging
LOG_FORMAT=json
ENABLE_METRICS=true

# Sentry (Opcional)
# SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
"""
        
        try:
            with open(".env.production", "w") as f:
                f.write(env_content)
            self.print_success("Archivo .env.production creado")
            return True
        except Exception as e:
            self.print_error(f"Error al crear .env.production: {e}")
            return False
    
    def create_railway_json(self):
        """Crear railway.json con configuración"""
        self.print_step(5, "Creando railway.json...")
        
        railway_config = {
            "$schema": "https://railway.app/railway.schema.json",
            "build": {
                "builder": "NIXPACKS",
                "buildCommand": "pip install -r requirements.txt"
            },
            "deploy": {
                "startCommand": "uvicorn voicecore.main:app --host 0.0.0.0 --port $PORT",
                "restartPolicyType": "ON_FAILURE",
                "restartPolicyMaxRetries": 10
            }
        }
        
        try:
            with open("railway.json", "w") as f:
                json.dump(railway_config, f, indent=2)
            self.print_success("Archivo railway.json creado")
            return True
        except Exception as e:
            self.print_error(f"Error al crear railway.json: {e}")
            return False
    
    def verify_files(self):
        """Verificar archivos necesarios"""
        self.print_step(6, "Verificando archivos necesarios...")
        
        required_files = [
            "Procfile",
            "railway.toml",
            "requirements.txt",
            "voicecore/main.py",
            "voicecore/config.py",
            "voicecore/database.py"
        ]
        
        all_exist = True
        for file in required_files:
            if os.path.exists(file):
                self.print_success(f"✓ {file}")
            else:
                self.print_error(f"✗ {file} - NO EXISTE")
                all_exist = False
        
        return all_exist
    
    def create_readme_deployment(self):
        """Crear README de deployment"""
        self.print_step(7, "Creando README_DEPLOYMENT.md...")
        
        readme_content = """# 🚀 VoiceCore AI 3.0 - Deployment a Railway

## ✅ Estado Actual

Tu código está listo para desplegar a Railway.

## 📋 Archivos Configurados

- ✅ `Procfile` - Comando de inicio
- ✅ `railway.toml` - Configuración de Railway
- ✅ `railway.json` - Configuración adicional
- ✅ `requirements.txt` - Dependencias Python
- ✅ `.env.production` - Variables de entorno de producción
- ✅ Código subido a GitHub

## 🎯 Próximos Pasos

### 1. Crear Proyecto en Railway

Ve a: **https://railway.app/new**

1. Click en "Deploy from GitHub repo"
2. Autoriza Railway a acceder a GitHub
3. Selecciona el repositorio: `xpload/voicecore-ai`
4. Click en "Deploy Now"

### 2. Agregar PostgreSQL

1. En tu proyecto de Railway, click "+ New"
2. Selecciona "Database"
3. Selecciona "PostgreSQL"
4. Railway configurará `DATABASE_URL` automáticamente

### 3. Configurar Variables de Entorno

En Railway, ve a tu servicio → "Variables" y agrega:

```
SECRET_KEY=voicecore-production-secret-key-2024-change-this-in-production-12345678901234567890
JWT_SECRET_KEY=voicecore-jwt-secret-key-2024-change-this-in-production-12345678901234567890
DEBUG=false
LOG_LEVEL=INFO
```

**Opcionales (para funcionalidad completa):**

```
TWILIO_ACCOUNT_SID=tu-twilio-sid
TWILIO_AUTH_TOKEN=tu-twilio-token
TWILIO_PHONE_NUMBER=+1234567890
OPENAI_API_KEY=sk-tu-openai-key
```

### 4. Esperar Deployment

Railway desplegará automáticamente en 2-5 minutos.

### 5. Obtener URL

1. Ve a "Settings" → "Domains"
2. Click "Generate Domain"
3. Copia tu URL

### 6. Ejecutar Migraciones

En Railway:
1. Click en tu servicio
2. Click "..." → "Run Command"
3. Ejecuta: `alembic upgrade head`

### 7. Verificar

Abre: `https://tu-url.railway.app/health`

Deberías ver:
```json
{
  "status": "healthy",
  "service": "VoiceCore AI",
  "version": "3.0.0"
}
```

## 🔗 Enlaces Útiles

- **Railway Dashboard**: https://railway.app/dashboard
- **GitHub Repo**: https://github.com/xpload/voicecore-ai
- **Documentación**: https://docs.railway.app

## 🆘 Troubleshooting

### Error: "Application failed to respond"

1. Verifica que `DATABASE_URL` esté configurada
2. Verifica que `SECRET_KEY` esté configurada
3. Revisa los logs en Railway dashboard

### Error: "ModuleNotFoundError"

1. Verifica que `requirements.txt` esté completo
2. Redespliega el proyecto

### Error: "Database connection failed"

1. Verifica que PostgreSQL esté agregado
2. Verifica que `DATABASE_URL` esté configurada automáticamente

## 📊 Funcionalidades Disponibles

Una vez desplegado, tendrás acceso a:

- **API REST**: `/docs` - Documentación interactiva
- **Health Check**: `/health` - Estado del sistema
- **Event Sourcing**: `/api/v1/events/statistics` - Estadísticas de eventos
- **Dashboard**: `/dashboard` - Panel de control
- **WebSocket**: `/ws` - Conexiones en tiempo real

## 🎉 ¡Listo!

Tu aplicación VoiceCore AI 3.0 Enterprise estará online y lista para usar.
"""
        
        try:
            with open("README_DEPLOYMENT.md", "w") as f:
                f.write(readme_content)
            self.print_success("README_DEPLOYMENT.md creado")
            return True
        except Exception as e:
            self.print_error(f"Error al crear README: {e}")
            return False
    
    def run(self):
        """Ejecutar deployment completo"""
        self.print_header("VOICECORE AI 3.0 - DEPLOYMENT A RAILWAY")
        
        # Verificar Git
        if not self.check_git():
            return False
        
        # Verificar GitHub
        if not self.check_github_repo():
            return False
        
        # Asegurar código en GitHub
        if not self.ensure_code_pushed():
            return False
        
        # Crear archivos de configuración
        self.create_env_production_file()
        self.create_railway_json()
        
        # Verificar archivos
        if not self.verify_files():
            self.print_error("Faltan archivos necesarios")
            return False
        
        # Crear README
        self.create_readme_deployment()
        
        # Commit y push de archivos nuevos
        self.print_step(8, "Subiendo archivos de configuración...")
        self.run_command("git add .env.production railway.json README_DEPLOYMENT.md", "Git add")
        self.run_command('git commit -m "Add Railway deployment configuration"', "Git commit")
        success, _, _ = self.run_command("git push origin main", "Git push")
        
        if not success:
            self.run_command("git push origin master", "Git push master")
        
        # Mostrar instrucciones
        self.create_railway_instructions()
        
        # Resumen final
        self.print_header("RESUMEN")
        
        if self.errors:
            print("\n⚠️  Se encontraron algunos errores:")
            for error in self.errors:
                print(f"   • {error}")
        
        print("\n✅ PREPARACIÓN COMPLETADA")
        print("\n📋 Archivos listos:")
        print("   • Procfile")
        print("   • railway.toml")
        print("   • railway.json")
        print("   • .env.production")
        print("   • requirements.txt")
        print("   • README_DEPLOYMENT.md")
        
        print("\n🚀 PRÓXIMO PASO:")
        print("   Ve a: https://railway.app/new")
        print("   Y sigue las instrucciones arriba")
        
        print("\n📚 Documentación completa en: README_DEPLOYMENT.md")
        
        return True

def main():
    """Función principal"""
    deployer = RailwayDeployer()
    success = deployer.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
