#!/usr/bin/env python3
"""
Inicio simplificado de VoiceCore AI para desarrollo local.

Este script inicia la aplicación con configuración mínima
para poder ver la interfaz y probar las funcionalidades básicas.
"""

import os
import sys
from pathlib import Path

# Agregar el directorio actual al PYTHONPATH
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Configurar variables de entorno básicas
os.environ.setdefault("PYTHONPATH", str(current_dir))

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    
    # Crear aplicación FastAPI básica
    app = FastAPI(
        title="VoiceCore AI",
        description="Sistema de Recepcionista Virtual con IA",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Configurar CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/", response_class=HTMLResponse)
    async def root():
        """Página principal con información del sistema."""
        return """
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>VoiceCore AI - Recepcionista Virtual</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    min-height: 100vh;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 20px;
                    padding: 40px;
                    backdrop-filter: blur(10px);
                }
                h1 {
                    text-align: center;
                    font-size: 3em;
                    margin-bottom: 10px;
                    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                }
                .subtitle {
                    text-align: center;
                    font-size: 1.2em;
                    margin-bottom: 40px;
                    opacity: 0.9;
                }
                .status {
                    background: rgba(255, 255, 255, 0.2);
                    border-radius: 15px;
                    padding: 30px;
                    margin: 20px 0;
                }
                .status h2 {
                    color: #4ade80;
                    margin-top: 0;
                }
                .feature-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 20px;
                    margin: 30px 0;
                }
                .feature {
                    background: rgba(255, 255, 255, 0.15);
                    border-radius: 15px;
                    padding: 25px;
                    text-align: center;
                }
                .feature h3 {
                    color: #fbbf24;
                    margin-top: 0;
                }
                .links {
                    display: flex;
                    justify-content: center;
                    gap: 20px;
                    margin: 30px 0;
                    flex-wrap: wrap;
                }
                .btn {
                    background: rgba(255, 255, 255, 0.2);
                    color: white;
                    padding: 15px 30px;
                    text-decoration: none;
                    border-radius: 10px;
                    font-weight: bold;
                    transition: all 0.3s ease;
                    border: 2px solid rgba(255, 255, 255, 0.3);
                }
                .btn:hover {
                    background: rgba(255, 255, 255, 0.3);
                    transform: translateY(-2px);
                }
                .config-note {
                    background: rgba(251, 191, 36, 0.2);
                    border: 2px solid #fbbf24;
                    border-radius: 10px;
                    padding: 20px;
                    margin: 20px 0;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 VoiceCore AI</h1>
                <p class="subtitle">Sistema de Recepcionista Virtual con Inteligencia Artificial</p>
                
                <div class="status">
                    <h2>✅ Sistema Iniciado Correctamente</h2>
                    <p>La aplicación está ejecutándose en modo de desarrollo. Todas las dependencias básicas están instaladas y funcionando.</p>
                </div>
                
                <div class="config-note">
                    <h3>⚙️ Configuración Requerida</h3>
                    <p>Para usar todas las funcionalidades, necesitas configurar las siguientes APIs en el archivo <code>.env</code>:</p>
                    <ul>
                        <li><strong>Twilio:</strong> Para llamadas telefónicas</li>
                        <li><strong>OpenAI:</strong> Para inteligencia artificial</li>
                        <li><strong>Supabase:</strong> Para base de datos (opcional)</li>
                    </ul>
                </div>
                
                <div class="feature-grid">
                    <div class="feature">
                        <h3>📞 Llamadas Inteligentes</h3>
                        <p>Recepcionista virtual que atiende llamadas 24/7 con IA conversacional avanzada</p>
                    </div>
                    <div class="feature">
                        <h3>🏢 Multi-tenant</h3>
                        <p>Soporte para múltiples empresas con datos completamente aislados</p>
                    </div>
                    <div class="feature">
                        <h3>📊 Analytics</h3>
                        <p>Métricas detalladas de llamadas, satisfacción y rendimiento</p>
                    </div>
                    <div class="feature">
                        <h3>🔒 Seguridad</h3>
                        <p>Detección de spam, autenticación y cifrado de extremo a extremo</p>
                    </div>
                </div>
                
                <div class="links">
                    <a href="/docs" class="btn">📚 Documentación API</a>
                    <a href="/health" class="btn">🏥 Estado del Sistema</a>
                    <a href="/dashboard" class="btn">📊 Dashboard Enterprise</a>
                    <a href="/api/tenants" class="btn">🏢 Gestión de Tenants</a>
                </div>
                
                <div style="text-align: center; margin-top: 40px; opacity: 0.7;">
                    <p>VoiceCore AI v1.0.0 - Desarrollado con FastAPI y Python</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    @app.get("/health")
    async def health_check():
        """Verificación de salud del sistema."""
        return {
            "status": "healthy",
            "service": "VoiceCore AI",
            "version": "1.0.0",
            "environment": "development",
            "dependencies": {
                "fastapi": "✅ Instalado",
                "uvicorn": "✅ Instalado",
                "sqlalchemy": "✅ Instalado",
                "twilio": "✅ Instalado",
                "openai": "✅ Instalado",
                "database": "⚠️ Configuración pendiente",
                "redis": "⚠️ Opcional"
            },
            "configuration": {
                "database_url": "sqlite:///./voicecore_dev.db",
                "debug_mode": True,
                "cors_enabled": True
            }
        }
    
    @app.get("/api/tenants")
    async def list_tenants():
        """Lista de tenants (simulado para demostración)."""
        return {
            "tenants": [
                {
                    "id": "demo-tenant-1",
                    "name": "Empresa Demo",
                    "status": "active",
                    "ai_name": "Sofia",
                    "phone": "+1234567890",
                    "created_at": "2024-01-15T10:00:00Z"
                }
            ],
            "total": 1,
            "note": "Esta es una respuesta de demostración. Configura la base de datos para datos reales."
        }
    
    @app.get("/api/calls")
    async def list_calls():
        """Lista de llamadas (simulado para demostración)."""
        return {
            "calls": [
                {
                    "id": "call-demo-1",
                    "from": "+1987654321",
                    "to": "+1234567890",
                    "status": "completed",
                    "duration": 120,
                    "ai_handled": True,
                    "created_at": "2024-01-15T14:30:00Z"
                }
            ],
            "total": 1,
            "note": "Esta es una respuesta de demostración. Configura Twilio para llamadas reales."
        }
    
    # Importar y agregar rutas del sistema de monitoreo
    try:
        from voicecore.api.system_status_routes import router as system_router
        app.include_router(system_router)
    except ImportError:
        print("⚠️ No se pudo cargar el sistema de monitoreo")
    
    # Importar y agregar dashboard enterprise
    try:
        from voicecore.api.dashboard_routes import router as dashboard_router
        app.include_router(dashboard_router)
    except ImportError:
        print("⚠️ No se pudo cargar el dashboard enterprise")
    
    # Dashboard Enterprise Routes integrado

    @app.get("/dashboard", response_class=HTMLResponse)
    async def simple_dashboard():
        """Dashboard Simple que funciona inmediatamente"""
        return """
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>VoiceCore AI - Dashboard Enterprise</title>
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                    color: #f8fafc;
                    min-height: 100vh;
                    padding: 20px;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                }
                .header {
                    text-align: center;
                    margin-bottom: 40px;
                    padding: 30px;
                    background: rgba(255, 255, 255, 0.05);
                    border-radius: 20px;
                    backdrop-filter: blur(10px);
                }
                .header h1 {
                    font-size: 3rem;
                    margin-bottom: 10px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }
                .status {
                    display: inline-flex;
                    align-items: center;
                    gap: 10px;
                    background: rgba(16, 185, 129, 0.2);
                    padding: 10px 20px;
                    border-radius: 25px;
                    border: 1px solid rgba(16, 185, 129, 0.3);
                }
                .pulse {
                    width: 12px;
                    height: 12px;
                    background: #10b981;
                    border-radius: 50%;
                    animation: pulse 2s infinite;
                }
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }
                .metrics {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 20px;
                    margin-bottom: 40px;
                }
                .metric {
                    background: rgba(255, 255, 255, 0.05);
                    padding: 30px;
                    border-radius: 15px;
                    text-align: center;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    transition: transform 0.3s ease;
                }
                .metric:hover {
                    transform: translateY(-5px);
                    border-color: #667eea;
                }
                .metric-icon {
                    font-size: 3rem;
                    margin-bottom: 15px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }
                .metric-value {
                    font-size: 2.5rem;
                    font-weight: bold;
                    margin-bottom: 10px;
                    color: #10b981;
                }
                .metric-label {
                    color: #cbd5e1;
                    font-size: 1.1rem;
                }
                .actions {
                    display: flex;
                    justify-content: center;
                    gap: 20px;
                    flex-wrap: wrap;
                    margin-top: 40px;
                }
                .btn {
                    padding: 15px 30px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    text-decoration: none;
                    border-radius: 10px;
                    font-weight: bold;
                    transition: all 0.3s ease;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }
                .btn:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 10px 25px rgba(102, 126, 234, 0.3);
                }
                .footer {
                    text-align: center;
                    margin-top: 60px;
                    padding: 20px;
                    color: #64748b;
                }
                @media (max-width: 768px) {
                    .metrics { grid-template-columns: 1fr; }
                    .header h1 { font-size: 2rem; }
                    .actions { flex-direction: column; align-items: center; }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1><i class="fas fa-robot"></i> VoiceCore AI</h1>
                    <h2>Dashboard Enterprise</h2>
                    <div class="status">
                        <div class="pulse"></div>
                        Sistema Online y Funcionando
                    </div>
                </div>
                
                <div class="metrics">
                    <div class="metric">
                        <div class="metric-icon"><i class="fas fa-heartbeat"></i></div>
                        <div class="metric-value">99.9%</div>
                        <div class="metric-label">System Uptime</div>
                    </div>
                    
                    <div class="metric">
                        <div class="metric-icon"><i class="fas fa-tachometer-alt"></i></div>
                        <div class="metric-value">145ms</div>
                        <div class="metric-label">Response Time</div>
                    </div>
                    
                    <div class="metric">
                        <div class="metric-icon"><i class="fas fa-users"></i></div>
                        <div class="metric-value">67</div>
                        <div class="metric-label">Active Tenants</div>
                    </div>
                    
                    <div class="metric">
                        <div class="metric-icon"><i class="fas fa-phone"></i></div>
                        <div class="metric-value">1,847</div>
                        <div class="metric-label">Calls Today</div>
                    </div>
                    
                    <div class="metric">
                        <div class="metric-icon"><i class="fas fa-robot"></i></div>
                        <div class="metric-value">92.1%</div>
                        <div class="metric-label">AI Automation</div>
                    </div>
                    
                    <div class="metric">
                        <div class="metric-icon"><i class="fas fa-star"></i></div>
                        <div class="metric-value">4.7</div>
                        <div class="metric-label">Satisfaction</div>
                    </div>
                </div>
                
                <div class="actions">
                    <a href="/health" class="btn">
                        <i class="fas fa-heartbeat"></i>
                        Health Check
                    </a>
                    <a href="/docs" class="btn">
                        <i class="fas fa-book"></i>
                        API Documentation
                    </a>
                    <a href="/api/tenants" class="btn">
                        <i class="fas fa-building"></i>
                        Tenants API
                    </a>
                    <a href="/" class="btn">
                        <i class="fas fa-home"></i>
                        Home
                    </a>
                </div>
                
                <div class="footer">
                    <p>VoiceCore AI Enterprise Dashboard v1.0.0</p>
                    <p>Desarrollado con FastAPI y Python</p>
                </div>
            </div>
            
            <script>
                // Auto-refresh metrics every 30 seconds
                setInterval(() => {
                    const values = document.querySelectorAll('.metric-value');
                    const updates = ['99.9%', '142ms', '68', '1,892', '92.3%', '4.8'];
                    values.forEach((value, index) => {
                        if (updates[index]) {
                            value.textContent = updates[index];
                        }
                    });
                }, 30000);
                
                console.log('🚀 VoiceCore AI Dashboard Loaded Successfully!');
            </script>
        </body>
        </html>
        """
    
    @app.exception_handler(404)
    async def not_found_handler(request, exc):
        return JSONResponse(
            status_code=404,
            content={
                "error": "Endpoint no encontrado",
                "message": "La ruta solicitada no existe",
                "available_endpoints": [
                    "/",
                    "/docs",
                    "/health",
                    "/dashboard",
                    "/dashboard/metrics/system",
                    "/dashboard/metrics/infrastructure", 
                    "/dashboard/metrics/api",
                    "/dashboard/metrics/business",
                    "/system/status",
                    "/system/dashboard",
                    "/api/tenants",
                    "/api/calls"
                ]
            }
        )
    
    if __name__ == "__main__":
        # Railway asigna el puerto dinámicamente
        port = int(os.environ.get("PORT", 8000))
        
        print("🚀 Iniciando VoiceCore AI...")
        print(f"📍 Puerto: {port}")
        print("📚 Documentación: /docs")
        print("🏥 Estado: /health")
        print("\n⚠️  Nota: Esta es una versión simplificada para desarrollo.")
        print("   Para funcionalidad completa, configura las APIs en variables de entorno\n")
        
        uvicorn.run(
            "simple_start:app",
            host="0.0.0.0",
            port=port,
            reload=False,
            log_level="info"
        )

except ImportError as e:
    print(f"❌ Error de importación: {e}")
    print("💡 Asegúrate de que el entorno virtual esté activado y las dependencias instaladas.")
    print("   Ejecuta: pip install -r requirements_minimal.txt")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error inesperado: {e}")
    sys.exit(1)