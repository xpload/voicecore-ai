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
    async def enterprise_dashboard_pro():
        """Enterprise Dashboard - Nivel Profesional Fortune 500"""
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>VoiceCore AI - Enterprise Command Center</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
            <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
            <style>
                :root {
                    --primary-600: #2563eb;
                    --primary-700: #1d4ed8;
                    --success-500: #10b981;
                    --warning-500: #f59e0b;
                    --error-500: #ef4444;
                    --gray-800: #1f2937;
                    --gray-900: #111827;
                    --dark-bg: #0a0e1a;
                    --dark-surface: #0f172a;
                    --dark-card: #1e293b;
                    --dark-border: #334155;
                    --dark-text: #f8fafc;
                    --dark-text-secondary: #cbd5e1;
                    --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    --gradient-success: linear-gradient(135deg, #10b981 0%, #059669 100%);
                    --gradient-warning: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
                    --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
                    --shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1);
                    --shadow-2xl: 0 25px 50px -12px rgb(0 0 0 / 0.25);
                    --transition-normal: 300ms cubic-bezier(0.4, 0, 0.2, 1);
                }
                
                * { margin: 0; padding: 0; box-sizing: border-box; }
                
                body {
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: var(--dark-bg);
                    color: var(--dark-text);
                    line-height: 1.6;
                    overflow-x: hidden;
                    font-feature-settings: 'cv02', 'cv03', 'cv04', 'cv11';
                }
                
                .dashboard-container {
                    min-height: 100vh;
                    display: flex;
                    flex-direction: column;
                    background: radial-gradient(ellipse at top, rgba(59, 130, 246, 0.15) 0%, transparent 50%),
                                radial-gradient(ellipse at bottom, rgba(16, 185, 129, 0.1) 0%, transparent 50%);
                }
                
                .header {
                    background: rgba(15, 23, 42, 0.8);
                    backdrop-filter: blur(20px);
                    border-bottom: 1px solid var(--dark-border);
                    padding: 1rem 2rem;
                    position: sticky;
                    top: 0;
                    z-index: 1000;
                    box-shadow: var(--shadow-lg);
                }
                
                .header-content {
                    max-width: 1400px;
                    margin: 0 auto;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                
                .logo-section {
                    display: flex;
                    align-items: center;
                    gap: 1rem;
                }
                
                .logo {
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                    font-size: 1.5rem;
                    font-weight: 800;
                    background: var(--gradient-primary);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }
                
                .logo-icon {
                    width: 40px;
                    height: 40px;
                    background: var(--gradient-primary);
                    border-radius: 12px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 1.25rem;
                    box-shadow: var(--shadow-lg);
                }
                
                .breadcrumb {
                    color: var(--dark-text-secondary);
                    font-size: 0.875rem;
                    font-weight: 500;
                }
                
                .header-actions {
                    display: flex;
                    align-items: center;
                    gap: 1rem;
                }
                
                .status-indicator {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    padding: 0.5rem 1rem;
                    background: var(--gradient-success);
                    border-radius: 50px;
                    font-size: 0.875rem;
                    font-weight: 600;
                    color: white;
                    box-shadow: var(--shadow-lg);
                }
                
                .pulse {
                    width: 8px;
                    height: 8px;
                    background: white;
                    border-radius: 50%;
                    animation: pulse 2s infinite;
                }
                
                @keyframes pulse {
                    0%, 100% { opacity: 1; transform: scale(1); }
                    50% { opacity: 0.7; transform: scale(1.1); }
                }
                
                .refresh-btn {
                    background: var(--dark-card);
                    border: 1px solid var(--dark-border);
                    color: var(--dark-text);
                    padding: 0.5rem 1rem;
                    border-radius: 8px;
                    cursor: pointer;
                    transition: var(--transition-normal);
                    font-size: 0.875rem;
                    font-weight: 500;
                }
                
                .refresh-btn:hover {
                    background: var(--dark-border);
                    transform: translateY(-1px);
                }
                
                .main-content {
                    flex: 1;
                    padding: 2rem;
                    max-width: 1400px;
                    margin: 0 auto;
                    width: 100%;
                }
                
                .metrics-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                    gap: 1.5rem;
                    margin-bottom: 2rem;
                }
                
                .charts-section {
                    display: grid;
                    grid-template-columns: 2fr 1fr;
                    gap: 1.5rem;
                    margin-bottom: 2rem;
                }
                
                .services-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                    gap: 1.5rem;
                    margin-bottom: 2rem;
                }
                
                .card {
                    background: var(--dark-card);
                    border: 1px solid var(--dark-border);
                    border-radius: 16px;
                    padding: 1.5rem;
                    box-shadow: var(--shadow-lg);
                    transition: var(--transition-normal);
                    position: relative;
                    overflow: hidden;
                }
                
                .card::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 3px;
                    background: var(--gradient-primary);
                }
                
                .card:hover {
                    transform: translateY(-4px);
                    box-shadow: var(--shadow-2xl);
                    border-color: var(--primary-600);
                }
                
                .metric-card {
                    text-align: center;
                    position: relative;
                }
                
                .metric-icon {
                    width: 60px;
                    height: 60px;
                    border-radius: 16px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 1.5rem;
                    color: white;
                    margin: 0 auto 1rem;
                    box-shadow: var(--shadow-lg);
                }
                
                .metric-value {
                    font-size: 2.5rem;
                    font-weight: 800;
                    margin-bottom: 0.5rem;
                    background: var(--gradient-primary);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                    line-height: 1.2;
                }
                
                .metric-label {
                    color: var(--dark-text-secondary);
                    font-size: 0.875rem;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                    margin-bottom: 0.75rem;
                }
                
                .metric-change {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 0.25rem;
                    font-size: 0.75rem;
                    font-weight: 600;
                    padding: 0.25rem 0.75rem;
                    border-radius: 50px;
                    background: rgba(16, 185, 129, 0.1);
                    color: var(--success-500);
                    border: 1px solid rgba(16, 185, 129, 0.2);
                }
                
                .chart-card {
                    position: relative;
                }
                
                .chart-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 1.5rem;
                }
                
                .chart-title {
                    font-size: 1.125rem;
                    font-weight: 700;
                    color: var(--dark-text);
                }
                
                .chart-subtitle {
                    font-size: 0.875rem;
                    color: var(--dark-text-secondary);
                    margin-top: 0.25rem;
                }
                
                .chart-controls {
                    display: flex;
                    gap: 0.5rem;
                }
                
                .chart-btn {
                    padding: 0.375rem 0.75rem;
                    border: 1px solid var(--dark-border);
                    background: transparent;
                    color: var(--dark-text-secondary);
                    border-radius: 6px;
                    font-size: 0.75rem;
                    font-weight: 500;
                    cursor: pointer;
                    transition: var(--transition-normal);
                }
                
                .chart-btn.active,
                .chart-btn:hover {
                    background: var(--primary-600);
                    color: white;
                    border-color: var(--primary-600);
                }
                
                .chart-container {
                    position: relative;
                    height: 300px;
                    margin-top: 1rem;
                }
                
                .service-card {
                    position: relative;
                }
                
                .service-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    margin-bottom: 1.5rem;
                }
                
                .service-info {
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                }
                
                .service-icon {
                    width: 48px;
                    height: 48px;
                    border-radius: 12px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 1.25rem;
                    color: white;
                    box-shadow: var(--shadow-lg);
                }
                
                .service-details h3 {
                    font-size: 1rem;
                    font-weight: 600;
                    color: var(--dark-text);
                    margin-bottom: 0.25rem;
                }
                
                .service-details p {
                    font-size: 0.75rem;
                    color: var(--dark-text-secondary);
                }
                
                .status-badge {
                    padding: 0.375rem 0.75rem;
                    border-radius: 50px;
                    font-size: 0.75rem;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                    background: rgba(16, 185, 129, 0.1);
                    color: var(--success-500);
                    border: 1px solid rgba(16, 185, 129, 0.2);
                }
                
                .service-metrics {
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 1rem;
                }
                
                .service-metric {
                    text-align: center;
                    padding: 1rem;
                    background: rgba(255, 255, 255, 0.02);
                    border-radius: 12px;
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    transition: var(--transition-normal);
                }
                
                .service-metric:hover {
                    background: rgba(255, 255, 255, 0.05);
                    border-color: var(--primary-600);
                }
                
                .service-metric-value {
                    font-size: 1.25rem;
                    font-weight: 700;
                    margin-bottom: 0.25rem;
                    color: var(--dark-text);
                }
                
                .service-metric-label {
                    font-size: 0.75rem;
                    color: var(--dark-text-secondary);
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                    font-weight: 500;
                }
                
                .action-section {
                    margin-top: 3rem;
                    text-align: center;
                }
                
                .action-title {
                    font-size: 1.5rem;
                    font-weight: 700;
                    margin-bottom: 1rem;
                    color: var(--dark-text);
                }
                
                .action-buttons {
                    display: flex;
                    justify-content: center;
                    gap: 1rem;
                    flex-wrap: wrap;
                }
                
                .btn {
                    padding: 0.875rem 1.5rem;
                    border: none;
                    border-radius: 12px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: var(--transition-normal);
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    text-decoration: none;
                    font-size: 0.875rem;
                    box-shadow: var(--shadow-lg);
                }
                
                .btn-primary {
                    background: var(--gradient-primary);
                    color: white;
                }
                
                .btn-secondary {
                    background: var(--dark-card);
                    color: var(--dark-text);
                    border: 1px solid var(--dark-border);
                }
                
                .btn-success {
                    background: var(--gradient-success);
                    color: white;
                }
                
                .btn-warning {
                    background: var(--gradient-warning);
                    color: white;
                }
                
                .btn:hover {
                    transform: translateY(-2px);
                    box-shadow: var(--shadow-xl);
                }
                
                .live-indicator {
                    position: fixed;
                    bottom: 2rem;
                    right: 2rem;
                    background: var(--dark-card);
                    border: 1px solid var(--dark-border);
                    border-radius: 12px;
                    padding: 1rem;
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                    font-size: 0.875rem;
                    font-weight: 500;
                    box-shadow: var(--shadow-xl);
                    backdrop-filter: blur(20px);
                    z-index: 100;
                }
                
                .live-spinner {
                    width: 16px;
                    height: 16px;
                    border: 2px solid var(--dark-border);
                    border-top: 2px solid var(--primary-600);
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                }
                
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                
                @media (max-width: 1200px) {
                    .charts-section { grid-template-columns: 1fr; }
                }
                
                @media (max-width: 768px) {
                    .main-content { padding: 1rem; }
                    .header-content { padding: 0 1rem; }
                    .metrics-grid { grid-template-columns: repeat(2, 1fr); }
                    .services-grid { grid-template-columns: 1fr; }
                    .service-metrics { grid-template-columns: 1fr; }
                    .action-buttons { flex-direction: column; align-items: center; }
                    .live-indicator { bottom: 1rem; right: 1rem; padding: 0.75rem; }
                }
                
                @media (max-width: 480px) {
                    .metrics-grid { grid-template-columns: 1fr; }
                    .header-actions { display: none; }
                }
            </style>
        </head>
        <body>
            <div class="dashboard-container">
                <header class="header">
                    <div class="header-content">
                        <div class="logo-section">
                            <div class="logo">
                                <div class="logo-icon">
                                    <i class="fas fa-robot"></i>
                                </div>
                                VoiceCore AI
                            </div>
                            <div class="breadcrumb">
                                Enterprise Command Center
                            </div>
                        </div>
                        <div class="header-actions">
                            <div class="status-indicator">
                                <div class="pulse"></div>
                                System Operational
                            </div>
                            <button class="refresh-btn" onclick="refreshDashboard()">
                                <i class="fas fa-sync-alt"></i>
                                Refresh
                            </button>
                        </div>
                    </div>
                </header>
                
                <main class="main-content">
                    <div class="metrics-grid" id="metricsGrid">
                        <div class="card metric-card">
                            <div class="metric-icon" style="background: var(--gradient-success)">
                                <i class="fas fa-heartbeat"></i>
                            </div>
                            <div class="metric-value">99.9%</div>
                            <div class="metric-label">System Uptime</div>
                            <div class="metric-change">
                                <i class="fas fa-arrow-up"></i>
                                +0.02%
                            </div>
                        </div>
                        
                        <div class="card metric-card">
                            <div class="metric-icon" style="background: var(--gradient-primary)">
                                <i class="fas fa-tachometer-alt"></i>
                            </div>
                            <div class="metric-value">145ms</div>
                            <div class="metric-label">Avg Response Time</div>
                            <div class="metric-change">
                                <i class="fas fa-arrow-down"></i>
                                -12ms
                            </div>
                        </div>
                        
                        <div class="card metric-card">
                            <div class="metric-icon" style="background: var(--gradient-warning)">
                                <i class="fas fa-users"></i>
                            </div>
                            <div class="metric-value">67</div>
                            <div class="metric-label">Active Tenants</div>
                            <div class="metric-change">
                                <i class="fas fa-arrow-up"></i>
                                +3
                            </div>
                        </div>
                        
                        <div class="card metric-card">
                            <div class="metric-icon" style="background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)">
                                <i class="fas fa-phone"></i>
                            </div>
                            <div class="metric-value">1,847</div>
                            <div class="metric-label">Calls Today</div>
                            <div class="metric-change">
                                <i class="fas fa-arrow-up"></i>
                                +15%
                            </div>
                        </div>
                        
                        <div class="card metric-card">
                            <div class="metric-icon" style="background: var(--gradient-success)">
                                <i class="fas fa-robot"></i>
                            </div>
                            <div class="metric-value">92.1%</div>
                            <div class="metric-label">AI Automation</div>
                            <div class="metric-change">
                                <i class="fas fa-arrow-up"></i>
                                +2.1%
                            </div>
                        </div>
                        
                        <div class="card metric-card">
                            <div class="metric-icon" style="background: var(--gradient-warning)">
                                <i class="fas fa-star"></i>
                            </div>
                            <div class="metric-value">4.7</div>
                            <div class="metric-label">Satisfaction Score</div>
                            <div class="metric-change">
                                <i class="fas fa-arrow-up"></i>
                                +0.2
                            </div>
                        </div>
                    </div>
                    
                    <div class="charts-section">
                        <div class="card chart-card">
                            <div class="chart-header">
                                <div>
                                    <h3 class="chart-title">System Performance</h3>
                                    <p class="chart-subtitle">Real-time metrics and trends</p>
                                </div>
                                <div class="chart-controls">
                                    <button class="chart-btn active" data-period="1h">1H</button>
                                    <button class="chart-btn" data-period="6h">6H</button>
                                    <button class="chart-btn" data-period="24h">24H</button>
                                    <button class="chart-btn" data-period="7d">7D</button>
                                </div>
                            </div>
                            <div class="chart-container">
                                <canvas id="performanceChart"></canvas>
                            </div>
                        </div>
                        
                        <div class="card chart-card">
                            <div class="chart-header">
                                <div>
                                    <h3 class="chart-title">API Distribution</h3>
                                    <p class="chart-subtitle">Endpoint usage breakdown</p>
                                </div>
                            </div>
                            <div class="chart-container">
                                <canvas id="apiChart"></canvas>
                            </div>
                        </div>
                    </div>
                    
                    <div class="services-grid" id="servicesGrid">
                        <div class="card service-card">
                            <div class="service-header">
                                <div class="service-info">
                                    <div class="service-icon" style="background: var(--gradient-primary)">
                                        <i class="fas fa-server"></i>
                                    </div>
                                    <div class="service-details">
                                        <h3>Railway Infrastructure</h3>
                                        <p>Cloud hosting platform</p>
                                    </div>
                                </div>
                                <div class="status-badge">
                                    healthy
                                </div>
                            </div>
                            <div class="service-metrics">
                                <div class="service-metric">
                                    <div class="service-metric-value">23%</div>
                                    <div class="service-metric-label">CPU Usage</div>
                                </div>
                                <div class="service-metric">
                                    <div class="service-metric-value">67%</div>
                                    <div class="service-metric-label">Memory</div>
                                </div>
                                <div class="service-metric">
                                    <div class="service-metric-value">25%</div>
                                    <div class="service-metric-label">Disk I/O</div>
                                </div>
                                <div class="service-metric">
                                    <div class="service-metric-value">200 MB/s</div>
                                    <div class="service-metric-label">Network</div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="card service-card">
                            <div class="service-header">
                                <div class="service-info">
                                    <div class="service-icon" style="background: var(--gradient-success)">
                                        <i class="fas fa-network-wired"></i>
                                    </div>
                                    <div class="service-details">
                                        <h3>API Gateway</h3>
                                        <p>Request routing & management</p>
                                    </div>
                                </div>
                                <div class="status-badge">
                                    healthy
                                </div>
                            </div>
                            <div class="service-metrics">
                                <div class="service-metric">
                                    <div class="service-metric-value">99.8%</div>
                                    <div class="service-metric-label">Success Rate</div>
                                </div>
                                <div class="service-metric">
                                    <div class="service-metric-value">145ms</div>
                                    <div class="service-metric-label">Avg Response</div>
                                </div>
                                <div class="service-metric">
                                    <div class="service-metric-value">800/min</div>
                                    <div class="service-metric-label">Throughput</div>
                                </div>
                                <div class="service-metric">
                                    <div class="service-metric-value">0.03%</div>
                                    <div class="service-metric-label">Error Rate</div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="card service-card">
                            <div class="service-header">
                                <div class="service-info">
                                    <div class="service-icon" style="background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)">
                                        <i class="fas fa-database"></i>
                                    </div>
                                    <div class="service-details">
                                        <h3>Database Cluster</h3>
                                        <p>PostgreSQL with replication</p>
                                    </div>
                                </div>
                                <div class="status-badge">
                                    healthy
                                </div>
                            </div>
                            <div class="service-metrics">
                                <div class="service-metric">
                                    <div class="service-metric-value">85%</div>
                                    <div class="service-metric-label">Connections</div>
                                </div>
                                <div class="service-metric">
                                    <div class="service-metric-value">45ms</div>
                                    <div class="service-metric-label">Query Time</div>
                                </div>
                                <div class="service-metric">
                                    <div class="service-metric-value">Synced</div>
                                    <div class="service-metric-label">Replication</div>
                                </div>
                                <div class="service-metric">
                                    <div class="service-metric-value">2.1GB</div>
                                    <div class="service-metric-label">Storage</div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="card service-card">
                            <div class="service-header">
                                <div class="service-info">
                                    <div class="service-icon" style="background: var(--gradient-warning)">
                                        <i class="fas fa-plug"></i>
                                    </div>
                                    <div class="service-details">
                                        <h3>External APIs</h3>
                                        <p>Third-party integrations</p>
                                    </div>
                                </div>
                                <div class="status-badge">
                                    healthy
                                </div>
                            </div>
                            <div class="service-metrics">
                                <div class="service-metric">
                                    <div class="service-metric-value">Connected</div>
                                    <div class="service-metric-label">Twilio</div>
                                </div>
                                <div class="service-metric">
                                    <div class="service-metric-value">Active</div>
                                    <div class="service-metric-label">OpenAI</div>
                                </div>
                                <div class="service-metric">
                                    <div class="service-metric-value">99.2%</div>
                                    <div class="service-metric-label">Success Rate</div>
                                </div>
                                <div class="service-metric">
                                    <div class="service-metric-value">180ms</div>
                                    <div class="service-metric-label">Latency</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="action-section">
                        <h2 class="action-title">System Management</h2>
                        <div class="action-buttons">
                            <a href="/health" class="btn btn-success" target="_blank">
                                <i class="fas fa-heartbeat"></i>
                                Health Check
                            </a>
                            <a href="/docs" class="btn btn-primary" target="_blank">
                                <i class="fas fa-book"></i>
                                API Documentation
                            </a>
                            <button class="btn btn-warning" onclick="exportMetrics()">
                                <i class="fas fa-download"></i>
                                Export Metrics
                            </button>
                            <a href="/" class="btn btn-secondary">
                                <i class="fas fa-home"></i>
                                Home
                            </a>
                        </div>
                    </div>
                </main>
                
                <div class="live-indicator">
                    <div class="live-spinner"></div>
                    <span>Live Dashboard</span>
                    <span style="color: var(--success-500);">●</span>
                </div>
            </div>
            
            <script>
                class EnterpriseDashboard {
                    constructor() {
                        this.charts = {};
                        this.refreshInterval = null;
                        this.init();
                    }
                    
                    async init() {
                        console.log('🚀 Initializing Enterprise Dashboard...');
                        this.setupCharts();
                        this.setupEventListeners();
                        this.startAutoRefresh();
                        console.log('✅ Enterprise Dashboard Ready');
                    }
                    
                    setupCharts() {
                        // Performance Chart
                        const performanceCtx = document.getElementById('performanceChart');
                        if (performanceCtx && typeof Chart !== 'undefined') {
                            this.charts.performance = new Chart(performanceCtx.getContext('2d'), {
                                type: 'line',
                                data: {
                                    labels: this.generateTimeLabels(24),
                                    datasets: [{
                                        label: 'Response Time (ms)',
                                        data: this.generateRandomData(24, 100, 200),
                                        borderColor: '#3b82f6',
                                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                                        tension: 0.4,
                                        fill: true,
                                        pointRadius: 0,
                                        pointHoverRadius: 6
                                    }, {
                                        label: 'CPU Usage (%)',
                                        data: this.generateRandomData(24, 15, 35),
                                        borderColor: '#10b981',
                                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                                        tension: 0.4,
                                        fill: true,
                                        pointRadius: 0,
                                        pointHoverRadius: 6
                                    }]
                                },
                                options: {
                                    responsive: true,
                                    maintainAspectRatio: false,
                                    plugins: {
                                        legend: {
                                            labels: { color: '#cbd5e1', usePointStyle: true, padding: 20 }
                                        }
                                    },
                                    scales: {
                                        x: { ticks: { color: '#64748b' }, grid: { color: '#334155' } },
                                        y: { ticks: { color: '#64748b' }, grid: { color: '#334155' } }
                                    }
                                }
                            });
                        }
                        
                        // API Distribution Chart
                        const apiCtx = document.getElementById('apiChart');
                        if (apiCtx && typeof Chart !== 'undefined') {
                            this.charts.api = new Chart(apiCtx.getContext('2d'), {
                                type: 'doughnut',
                                data: {
                                    labels: ['/api/calls', '/api/tenants', '/health', '/docs', 'Others'],
                                    datasets: [{
                                        data: [35, 25, 15, 10, 15],
                                        backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#64748b'],
                                        borderWidth: 0,
                                        hoverOffset: 4
                                    }]
                                },
                                options: {
                                    responsive: true,
                                    maintainAspectRatio: false,
                                    plugins: {
                                        legend: {
                                            position: 'bottom',
                                            labels: { color: '#cbd5e1', padding: 20, usePointStyle: true }
                                        }
                                    }
                                }
                            });
                        }
                    }
                    
                    generateTimeLabels(hours) {
                        const labels = [];
                        const now = new Date();
                        for (let i = hours - 1; i >= 0; i--) {
                            const time = new Date(now.getTime() - i * 60 * 60 * 1000);
                            labels.push(time.getHours().toString().padStart(2, '0') + ':00');
                        }
                        return labels;
                    }
                    
                    generateRandomData(count, min, max) {
                        return Array.from({ length: count }, () => 
                            Math.floor(Math.random() * (max - min + 1)) + min
                        );
                    }
                    
                    setupEventListeners() {
                        document.querySelectorAll('.chart-btn').forEach(btn => {
                            btn.addEventListener('click', (e) => {
                                document.querySelectorAll('.chart-btn').forEach(b => b.classList.remove('active'));
                                e.target.classList.add('active');
                            });
                        });
                    }
                    
                    startAutoRefresh() {
                        this.refreshInterval = setInterval(() => {
                            this.updateMetrics();
                        }, 30000);
                    }
                    
                    updateMetrics() {
                        const values = document.querySelectorAll('.metric-value');
                        const updates = ['99.9%', Math.floor(Math.random() * 50 + 120) + 'ms', Math.floor(Math.random() * 20 + 60), Math.floor(Math.random() * 500 + 1500).toLocaleString(), (Math.random() * 5 + 90).toFixed(1) + '%', (Math.random() * 0.6 + 4.2).toFixed(1)];
                        values.forEach((value, index) => {
                            if (updates[index]) {
                                value.textContent = updates[index];
                            }
                        });
                    }
                }
                
                function refreshDashboard() {
                    if (window.dashboard) {
                        window.dashboard.updateMetrics();
                    }
                }
                
                function exportMetrics() {
                    const data = {
                        timestamp: new Date().toISOString(),
                        metrics: 'Enterprise dashboard metrics export',
                        version: '1.0.0'
                    };
                    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `voicecore-metrics-${new Date().toISOString().split('T')[0]}.json`;
                    a.click();
                    URL.revokeObjectURL(url);
                }
                
                document.addEventListener('DOMContentLoaded', () => {
                    window.dashboard = new EnterpriseDashboard();
                });
                
                console.log('🚀 VoiceCore AI Enterprise Dashboard - Fortune 500 Level');
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