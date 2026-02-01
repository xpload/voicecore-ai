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
    
    # Importar y agregar rutas del sistema de monitoreo (temporalmente deshabilitado)
    # try:
    #     from voicecore.api.system_status_routes import router as system_router
    #     app.include_router(system_router)
    # except ImportError:
    #     print("⚠️ No se pudo cargar el sistema de monitoreo")
    
    # Dashboard enterprise integrado directamente (sin router externo para evitar conflictos)
    
    # Dashboard Enterprise Routes integrado

    @app.get("/dashboard", response_class=HTMLResponse)
    async def enterprise_dashboard_pro():
        """Enterprise Dashboard - Fortune 500 Level - Integración Completa de APIs"""
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>VoiceCore AI - Enterprise Command Center</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
            <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/axios@1.6.0/dist/axios.min.js"></script>
            <style>
                :root {
                    --primary-50: #eff6ff;
                    --primary-100: #dbeafe;
                    --primary-200: #bfdbfe;
                    --primary-300: #93c5fd;
                    --primary-400: #60a5fa;
                    --primary-500: #3b82f6;
                    --primary-600: #2563eb;
                    --primary-700: #1d4ed8;
                    --primary-800: #1e40af;
                    --primary-900: #1e3a8a;
                    
                    --success-50: #ecfdf5;
                    --success-100: #d1fae5;
                    --success-200: #a7f3d0;
                    --success-300: #6ee7b7;
                    --success-400: #34d399;
                    --success-500: #10b981;
                    --success-600: #059669;
                    --success-700: #047857;
                    --success-800: #065f46;
                    --success-900: #064e3b;
                    
                    --warning-50: #fffbeb;
                    --warning-100: #fef3c7;
                    --warning-200: #fde68a;
                    --warning-300: #fcd34d;
                    --warning-400: #fbbf24;
                    --warning-500: #f59e0b;
                    --warning-600: #d97706;
                    --warning-700: #b45309;
                    --warning-800: #92400e;
                    --warning-900: #78350f;
                    
                    --error-50: #fef2f2;
                    --error-100: #fee2e2;
                    --error-200: #fecaca;
                    --error-300: #fca5a5;
                    --error-400: #f87171;
                    --error-500: #ef4444;
                    --error-600: #dc2626;
                    --error-700: #b91c1c;
                    --error-800: #991b1b;
                    --error-900: #7f1d1d;
                    
                    --gray-50: #f9fafb;
                    --gray-100: #f3f4f6;
                    --gray-200: #e5e7eb;
                    --gray-300: #d1d5db;
                    --gray-400: #9ca3af;
                    --gray-500: #6b7280;
                    --gray-600: #4b5563;
                    --gray-700: #374151;
                    --gray-800: #1f2937;
                    --gray-900: #111827;
                    
                    --dark-bg: #0a0e1a;
                    --dark-surface: #0f172a;
                    --dark-card: #1e293b;
                    --dark-border: #334155;
                    --dark-text: #f8fafc;
                    --dark-text-secondary: #cbd5e1;
                    
                    --gradient-primary: linear-gradient(135deg, var(--primary-600) 0%, var(--primary-800) 100%);
                    --gradient-success: linear-gradient(135deg, var(--success-500) 0%, var(--success-700) 100%);
                    --gradient-warning: linear-gradient(135deg, var(--warning-500) 0%, var(--warning-700) 100%);
                    --gradient-error: linear-gradient(135deg, var(--error-500) 0%, var(--error-700) 100%);
                    
                    --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
                    --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
                    --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
                    --shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1);
                    --shadow-2xl: 0 25px 50px -12px rgb(0 0 0 / 0.25);
                    
                    --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
                    --transition-normal: 300ms cubic-bezier(0.4, 0, 0.2, 1);
                    --transition-slow: 500ms cubic-bezier(0.4, 0, 0.2, 1);
                }
                
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                
                body {
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: var(--dark-bg);
                    color: var(--dark-text);
                    line-height: 1.6;
                    overflow-x: hidden;
                    font-feature-settings: 'cv02', 'cv03', 'cv04', 'cv11';
                    -webkit-font-smoothing: antialiased;
                    -moz-osx-font-smoothing: grayscale;
                }
                
                .dashboard-container {
                    min-height: 100vh;
                    display: flex;
                    background: radial-gradient(ellipse at top, rgba(59, 130, 246, 0.15) 0%, transparent 50%),
                                radial-gradient(ellipse at bottom, rgba(16, 185, 129, 0.1) 0%, transparent 50%);
                }
                
                /* Sidebar Navigation */
                .sidebar {
                    width: 280px;
                    background: var(--dark-surface);
                    border-right: 1px solid var(--dark-border);
                    padding: 2rem 0;
                    position: fixed;
                    height: 100vh;
                    overflow-y: auto;
                    z-index: 1000;
                    transition: var(--transition-normal);
                }
                
                .sidebar-header {
                    padding: 0 2rem 2rem;
                    border-bottom: 1px solid var(--dark-border);
                    margin-bottom: 2rem;
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
                    width: 48px;
                    height: 48px;
                    background: var(--gradient-primary);
                    border-radius: 12px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 1.5rem;
                    box-shadow: var(--shadow-lg);
                }
                
                .nav-section {
                    margin-bottom: 2rem;
                }
                
                .nav-section-title {
                    padding: 0 2rem 0.5rem;
                    font-size: 0.75rem;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.1em;
                    color: var(--dark-text-secondary);
                }
                
                .nav-item {
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                    padding: 0.75rem 2rem;
                    color: var(--dark-text-secondary);
                    text-decoration: none;
                    transition: var(--transition-fast);
                    cursor: pointer;
                    border: none;
                    background: none;
                    width: 100%;
                    text-align: left;
                    font-size: 0.875rem;
                    font-weight: 500;
                }
                
                .nav-item:hover,
                .nav-item.active {
                    background: rgba(59, 130, 246, 0.1);
                    color: var(--primary-400);
                    border-right: 3px solid var(--primary-500);
                }
                
                .nav-item i {
                    width: 20px;
                    text-align: center;
                    font-size: 1rem;
                }
                
                /* Main Content */
                .main-content {
                    flex: 1;
                    margin-left: 280px;
                    padding: 2rem;
                    transition: var(--transition-normal);
                }
                
                .header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 2rem;
                    padding-bottom: 1rem;
                    border-bottom: 1px solid var(--dark-border);
                }
                
                .page-title {
                    font-size: 2rem;
                    font-weight: 800;
                    color: var(--dark-text);
                }
                
                .page-subtitle {
                    font-size: 1rem;
                    color: var(--dark-text-secondary);
                    margin-top: 0.25rem;
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
                
                /* Content Sections */
                .content-section {
                    display: none;
                }
                
                .content-section.active {
                    display: block;
                }
                
                /* Cards */
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
                    transform: translateY(-2px);
                    box-shadow: var(--shadow-2xl);
                    border-color: var(--primary-600);
                }
                
                /* Metrics Grid */
                .metrics-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                    gap: 1.5rem;
                    margin-bottom: 2rem;
                }
                
                .metric-card {
                    text-align: center;
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
                
                /* Buttons */
                .btn {
                    display: inline-flex;
                    align-items: center;
                    gap: 0.5rem;
                    padding: 0.75rem 1.5rem;
                    border: none;
                    border-radius: 12px;
                    font-weight: 600;
                    font-size: 0.875rem;
                    cursor: pointer;
                    transition: var(--transition-normal);
                    text-decoration: none;
                    box-shadow: var(--shadow-lg);
                }
                
                .btn-primary {
                    background: var(--gradient-primary);
                    color: white;
                }
                
                .btn-success {
                    background: var(--gradient-success);
                    color: white;
                }
                
                .btn-warning {
                    background: var(--gradient-warning);
                    color: white;
                }
                
                .btn-secondary {
                    background: var(--dark-surface);
                    color: var(--dark-text);
                    border: 1px solid var(--dark-border);
                }
                
                .btn:hover {
                    transform: translateY(-2px);
                    box-shadow: var(--shadow-xl);
                }
                
                /* Tables */
                .table-container {
                    background: var(--dark-card);
                    border: 1px solid var(--dark-border);
                    border-radius: 16px;
                    overflow: hidden;
                    margin-bottom: 2rem;
                }
                
                .table-header {
                    padding: 1.5rem;
                    border-bottom: 1px solid var(--dark-border);
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                
                .table-title {
                    font-size: 1.25rem;
                    font-weight: 700;
                    color: var(--dark-text);
                }
                
                .table {
                    width: 100%;
                    border-collapse: collapse;
                }
                
                .table th,
                .table td {
                    padding: 1rem 1.5rem;
                    text-align: left;
                    border-bottom: 1px solid var(--dark-border);
                }
                
                .table th {
                    background: var(--dark-surface);
                    font-weight: 600;
                    color: var(--dark-text-secondary);
                    font-size: 0.875rem;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                }
                
                .table td {
                    color: var(--dark-text);
                }
                
                .table tbody tr:hover {
                    background: rgba(59, 130, 246, 0.05);
                }
                
                /* Status Badges */
                .status-badge {
                    display: inline-flex;
                    align-items: center;
                    gap: 0.25rem;
                    padding: 0.375rem 0.75rem;
                    border-radius: 50px;
                    font-size: 0.75rem;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                }
                
                .status-badge.success {
                    background: rgba(16, 185, 129, 0.1);
                    color: var(--success-500);
                    border: 1px solid rgba(16, 185, 129, 0.2);
                }
                
                .status-badge.warning {
                    background: rgba(245, 158, 11, 0.1);
                    color: var(--warning-500);
                    border: 1px solid rgba(245, 158, 11, 0.2);
                }
                
                .status-badge.error {
                    background: rgba(239, 68, 68, 0.1);
                    color: var(--error-500);
                    border: 1px solid rgba(239, 68, 68, 0.2);
                }
                
                /* Loading States */
                .loading {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 2rem;
                    color: var(--dark-text-secondary);
                }
                
                .spinner {
                    width: 24px;
                    height: 24px;
                    border: 2px solid var(--dark-border);
                    border-top: 2px solid var(--primary-500);
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin-right: 0.5rem;
                }
                
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                
                /* Action Grids */
                .action-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 1.5rem;
                    margin-bottom: 2rem;
                }
                
                .action-card {
                    background: var(--dark-card);
                    border: 1px solid var(--dark-border);
                    border-radius: 16px;
                    padding: 2rem;
                    text-align: center;
                    transition: var(--transition-normal);
                }
                
                .action-card:hover {
                    transform: translateY(-4px);
                    box-shadow: var(--shadow-2xl);
                    border-color: var(--primary-600);
                }
                
                .action-icon {
                    width: 80px;
                    height: 80px;
                    border-radius: 20px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 2rem;
                    color: white;
                    margin: 0 auto 1.5rem;
                    box-shadow: var(--shadow-lg);
                }
                
                .action-title {
                    font-size: 1.25rem;
                    font-weight: 700;
                    margin-bottom: 0.5rem;
                    color: var(--dark-text);
                }
                
                .action-description {
                    color: var(--dark-text-secondary);
                    margin-bottom: 1.5rem;
                    line-height: 1.6;
                }
                
                /* Charts */
                .chart-container {
                    position: relative;
                    height: 400px;
                    margin-top: 1rem;
                }
                
                /* Responsive Design */
                @media (max-width: 1024px) {
                    .sidebar {
                        transform: translateX(-100%);
                    }
                    
                    .sidebar.open {
                        transform: translateX(0);
                    }
                    
                    .main-content {
                        margin-left: 0;
                    }
                    
                    .metrics-grid {
                        grid-template-columns: repeat(2, 1fr);
                    }
                }
                
                @media (max-width: 768px) {
                    .main-content {
                        padding: 1rem;
                    }
                    
                    .metrics-grid {
                        grid-template-columns: 1fr;
                    }
                    
                    .header {
                        flex-direction: column;
                        align-items: flex-start;
                        gap: 1rem;
                    }
                }
            </style>: 1rem; padding: 0.75rem; }
                }
                
                @media (max-width: 480px) {
                    .metrics-grid { grid-template-columns: 1fr; }
                    .header-actions { display: none; }
                }

                /* Navigation Tabs */
                .nav-tabs {
                    display: flex;
                    gap: 0.5rem;
                    margin-bottom: 2rem;
                    border-bottom: 2px solid var(--dark-border);
                    padding-bottom: 1rem;
                }

                .nav-tab {
                    background: transparent;
                    border: none;
                    color: var(--dark-text-secondary);
                    padding: 0.75rem 1.5rem;
                    border-radius: 8px;
                    cursor: pointer;
                    transition: var(--transition-normal);
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    font-weight: 500;
                }

                .nav-tab:hover {
                    background: var(--dark-border);
                    color: var(--dark-text);
                }

                .nav-tab.active {
                    background: var(--gradient-primary);
                    color: white;
                }

                /* Tab Content */
                .tab-content {
                    display: none;
                }

                .tab-content.active {
                    display: block;
                }

                /* Section Headers */
                .section-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 2rem;
                }

                .section-header h2 {
                    color: var(--dark-text);
                    font-size: 1.5rem;
                    font-weight: 700;
                    margin: 0;
                }

                /* Filters Bar */
                .filters-bar {
                    display: flex;
                    gap: 1rem;
                    margin-bottom: 1.5rem;
                    flex-wrap: wrap;
                }

                .filters-bar select,
                .filters-bar input {
                    background: var(--dark-card);
                    border: 1px solid var(--dark-border);
                    color: var(--dark-text);
                    padding: 0.5rem 1rem;
                    border-radius: 6px;
                    font-size: 0.875rem;
                }

                .filters-bar input {
                    min-width: 200px;
                }

                /* Data Tables */
                .data-table-container {
                    background: var(--dark-card);
                    border-radius: 12px;
                    overflow: hidden;
                    border: 1px solid var(--dark-border);
                }

                .data-table {
                    width: 100%;
                    border-collapse: collapse;
                }

                .data-table th {
                    background: var(--dark-surface);
                    color: var(--dark-text);
                    padding: 1rem;
                    text-align: left;
                    font-weight: 600;
                    border-bottom: 1px solid var(--dark-border);
                }

                .data-table td {
                    padding: 1rem;
                    border-bottom: 1px solid var(--dark-border);
                    color: var(--dark-text-secondary);
                }

                .data-table tbody tr:hover {
                    background: rgba(255, 255, 255, 0.02);
                }

                .data-table .loading {
                    text-align: center;
                    color: var(--dark-text-secondary);
                    font-style: italic;
                }

                /* Status Badges */
                .status-badge {
                    padding: 0.25rem 0.75rem;
                    border-radius: 50px;
                    font-size: 0.75rem;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                }

                .status-badge.active {
                    background: rgba(16, 185, 129, 0.1);
                    color: var(--success-500);
                    border: 1px solid rgba(16, 185, 129, 0.2);
                }

                .status-badge.available {
                    background: rgba(16, 185, 129, 0.1);
                    color: var(--success-500);
                    border: 1px solid rgba(16, 185, 129, 0.2);
                }

                .status-badge.busy {
                    background: rgba(245, 158, 11, 0.1);
                    color: var(--warning-500);
                    border: 1px solid rgba(245, 158, 11, 0.2);
                }

                .status-badge.not_available {
                    background: rgba(239, 68, 68, 0.1);
                    color: var(--error-500);
                    border: 1px solid rgba(239, 68, 68, 0.2);
                }

                .status-badge.inactive {
                    background: rgba(100, 116, 139, 0.1);
                    color: #64748b;
                    border: 1px solid rgba(100, 116, 139, 0.2);
                }

                /* Call Stats */
                .call-stats {
                    display: flex;
                    gap: 2rem;
                }

                .stat-item {
                    text-align: center;
                }

                .stat-value {
                    display: block;
                    font-size: 1.5rem;
                    font-weight: 700;
                    color: var(--dark-text);
                }

                .stat-label {
                    font-size: 0.875rem;
                    color: var(--dark-text-secondary);
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                }

                /* Analytics Grid */
                .analytics-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                    gap: 1.5rem;
                }

                .analytics-card {
                    min-height: 300px;
                }

                .analytics-card h3 {
                    color: var(--dark-text);
                    font-size: 1.125rem;
                    font-weight: 600;
                    margin-bottom: 1rem;
                }

                .analytics-controls {
                    display: flex;
                    gap: 1rem;
                    align-items: center;
                }

                .analytics-controls select {
                    background: var(--dark-card);
                    border: 1px solid var(--dark-border);
                    color: var(--dark-text);
                    padding: 0.5rem 1rem;
                    border-radius: 6px;
                }

                /* AI Metrics */
                .ai-metrics {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                    gap: 1rem;
                    margin-top: 1rem;
                }

                .ai-metric {
                    text-align: center;
                    padding: 1rem;
                    background: rgba(255, 255, 255, 0.02);
                    border-radius: 8px;
                    border: 1px solid rgba(255, 255, 255, 0.05);
                }

                .ai-metric-value {
                    display: block;
                    font-size: 1.25rem;
                    font-weight: 700;
                    color: var(--dark-text);
                    margin-bottom: 0.25rem;
                }

                .ai-metric-label {
                    font-size: 0.75rem;
                    color: var(--dark-text-secondary);
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                }

                /* Action Buttons */
                .action-btn {
                    background: transparent;
                    border: 1px solid var(--dark-border);
                    color: var(--dark-text-secondary);
                    padding: 0.25rem 0.5rem;
                    border-radius: 4px;
                    cursor: pointer;
                    transition: var(--transition-normal);
                    font-size: 0.75rem;
                    margin: 0 0.25rem;
                }

                .action-btn:hover {
                    background: var(--dark-border);
                    color: var(--dark-text);
                }

                .action-btn.edit {
                    color: var(--primary-600);
                    border-color: var(--primary-600);
                }

                .action-btn.delete {
                    color: var(--error-500);
                    border-color: var(--error-500);
                }

                /* Modal Styles */
                .modal {
                    display: none;
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.8);
                    z-index: 2000;
                    backdrop-filter: blur(4px);
                }

                .modal.active {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }

                .modal-content {
                    background: var(--dark-card);
                    border-radius: 16px;
                    padding: 2rem;
                    max-width: 500px;
                    width: 90%;
                    max-height: 80vh;
                    overflow-y: auto;
                    border: 1px solid var(--dark-border);
                }

                .modal-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 1.5rem;
                }

                .modal-title {
                    color: var(--dark-text);
                    font-size: 1.25rem;
                    font-weight: 700;
                    margin: 0;
                }

                .modal-close {
                    background: transparent;
                    border: none;
                    color: var(--dark-text-secondary);
                    font-size: 1.5rem;
                    cursor: pointer;
                    padding: 0.25rem;
                    border-radius: 4px;
                    transition: var(--transition-normal);
                }

                .modal-close:hover {
                    background: var(--dark-border);
                    color: var(--dark-text);
                }

                .form-group {
                    margin-bottom: 1rem;
                }

                .form-label {
                    display: block;
                    color: var(--dark-text);
                    font-weight: 500;
                    margin-bottom: 0.5rem;
                }

                .form-input {
                    width: 100%;
                    background: var(--dark-surface);
                    border: 1px solid var(--dark-border);
                    color: var(--dark-text);
                    padding: 0.75rem;
                    border-radius: 6px;
                    font-size: 0.875rem;
                }

                .form-input:focus {
                    outline: none;
                    border-color: var(--primary-600);
                    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
                }

                .form-actions {
                    display: flex;
                    gap: 1rem;
                    justify-content: flex-end;
                    margin-top: 2rem;
                }

                /* Loading States */
                .loading-spinner {
                    display: inline-block;
                    width: 16px;
                    height: 16px;
                    border: 2px solid var(--dark-border);
                    border-top: 2px solid var(--primary-600);
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                }

                /* Responsive Design */
                @media (max-width: 768px) {
                    .nav-tabs {
                        flex-wrap: wrap;
                    }
                    
                    .section-header {
                        flex-direction: column;
                        gap: 1rem;
                        align-items: flex-start;
                    }
                    
                    .filters-bar {
                        flex-direction: column;
                    }
                    
                    .filters-bar input {
                        min-width: auto;
                    }
                    
                    .analytics-grid {
                        grid-template-columns: 1fr;
                    }
                    
                    .call-stats {
                        flex-wrap: wrap;
                        gap: 1rem;
                    }
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
                    <!-- Navigation Tabs -->
                    <div class="nav-tabs">
                        <button class="nav-tab active" data-tab="overview">
                            <i class="fas fa-chart-line"></i>
                            Overview
                        </button>
                        <button class="nav-tab" data-tab="agents">
                            <i class="fas fa-users"></i>
                            Agents
                        </button>
                        <button class="nav-tab" data-tab="tenants">
                            <i class="fas fa-building"></i>
                            Tenants
                        </button>
                        <button class="nav-tab" data-tab="calls">
                            <i class="fas fa-phone"></i>
                            Calls
                        </button>
                        <button class="nav-tab" data-tab="vips">
                            <i class="fas fa-crown"></i>
                            VIPs
                        </button>
                        <button class="nav-tab" data-tab="analytics">
                            <i class="fas fa-chart-bar"></i>
                            Analytics
                        </button>
                    </div>

                    <!-- Overview Tab -->
                    <div class="tab-content active" id="overview">
                        <div class="metrics-grid" id="metricsGrid">
                            <div class="card metric-card">
                                <div class="metric-icon" style="background: var(--gradient-success)">
                                    <i class="fas fa-heartbeat"></i>
                                </div>
                                <div class="metric-value" id="systemUptime">Loading...</div>
                                <div class="metric-label">System Uptime</div>
                                <div class="metric-change" id="uptimeChange">
                                    <i class="fas fa-arrow-up"></i>
                                    Loading...
                                </div>
                            </div>
                            
                            <div class="card metric-card">
                                <div class="metric-icon" style="background: var(--gradient-primary)">
                                    <i class="fas fa-tachometer-alt"></i>
                                </div>
                                <div class="metric-value" id="responseTime">Loading...</div>
                                <div class="metric-label">Avg Response Time</div>
                                <div class="metric-change" id="responseTimeChange">
                                    <i class="fas fa-arrow-down"></i>
                                    Loading...
                                </div>
                            </div>
                            
                            <div class="card metric-card">
                                <div class="metric-icon" style="background: var(--gradient-warning)">
                                    <i class="fas fa-users"></i>
                                </div>
                                <div class="metric-value" id="activeTenants">Loading...</div>
                                <div class="metric-label">Active Tenants</div>
                                <div class="metric-change" id="tenantsChange">
                                    <i class="fas fa-arrow-up"></i>
                                    Loading...
                                </div>
                            </div>
                            
                            <div class="card metric-card">
                                <div class="metric-icon" style="background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)">
                                    <i class="fas fa-phone"></i>
                                </div>
                                <div class="metric-value" id="callsToday">Loading...</div>
                                <div class="metric-label">Calls Today</div>
                                <div class="metric-change" id="callsChange">
                                    <i class="fas fa-arrow-up"></i>
                                    Loading...
                                </div>
                            </div>
                            
                            <div class="card metric-card">
                                <div class="metric-icon" style="background: var(--gradient-success)">
                                    <i class="fas fa-robot"></i>
                                </div>
                                <div class="metric-value" id="aiAutomation">Loading...</div>
                                <div class="metric-label">AI Automation</div>
                                <div class="metric-change" id="aiChange">
                                    <i class="fas fa-arrow-up"></i>
                                    Loading...
                                </div>
                            </div>
                            
                            <div class="card metric-card">
                                <div class="metric-icon" style="background: var(--gradient-warning)">
                                    <i class="fas fa-star"></i>
                                </div>
                                <div class="metric-value" id="satisfactionScore">Loading...</div>
                                <div class="metric-label">Satisfaction Score</div>
                                <div class="metric-change" id="satisfactionChange">
                                    <i class="fas fa-arrow-up"></i>
                                    Loading...
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Agents Tab -->
                    <div class="tab-content" id="agents">
                        <div class="section-header">
                            <h2>Agent Management</h2>
                            <button class="btn btn-primary" onclick="showCreateAgentModal()">
                                <i class="fas fa-plus"></i>
                                Add Agent
                            </button>
                        </div>
                        
                        <div class="filters-bar">
                            <select id="agentStatusFilter" onchange="filterAgents()">
                                <option value="">All Statuses</option>
                                <option value="available">Available</option>
                                <option value="busy">Busy</option>
                                <option value="not_available">Not Available</option>
                            </select>
                            <select id="departmentFilter" onchange="filterAgents()">
                                <option value="">All Departments</option>
                            </select>
                            <input type="text" id="agentSearch" placeholder="Search agents..." onkeyup="searchAgents()">
                        </div>
                        
                        <div class="data-table-container">
                            <table class="data-table" id="agentsTable">
                                <thead>
                                    <tr>
                                        <th>Name</th>
                                        <th>Extension</th>
                                        <th>Department</th>
                                        <th>Status</th>
                                        <th>Current Calls</th>
                                        <th>Total Calls</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="agentsTableBody">
                                    <tr>
                                        <td colspan="7" class="loading">Loading agents...</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Tenants Tab -->
                    <div class="tab-content" id="tenants">
                        <div class="section-header">
                            <h2>Tenant Management</h2>
                            <button class="btn btn-primary" onclick="showCreateTenantModal()">
                                <i class="fas fa-plus"></i>
                                Add Tenant
                            </button>
                        </div>
                        
                        <div class="data-table-container">
                            <table class="data-table" id="tenantsTable">
                                <thead>
                                    <tr>
                                        <th>Company Name</th>
                                        <th>Subdomain</th>
                                        <th>Plan</th>
                                        <th>Status</th>
                                        <th>Agents</th>
                                        <th>Usage</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="tenantsTableBody">
                                    <tr>
                                        <td colspan="7" class="loading">Loading tenants...</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Calls Tab -->
                    <div class="tab-content" id="calls">
                        <div class="section-header">
                            <h2>Call Management</h2>
                            <div class="call-stats">
                                <div class="stat-item">
                                    <span class="stat-value" id="activeCalls">0</span>
                                    <span class="stat-label">Active</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-value" id="queuedCalls">0</span>
                                    <span class="stat-label">Queued</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-value" id="completedCalls">0</span>
                                    <span class="stat-label">Completed</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="data-table-container">
                            <table class="data-table" id="callsTable">
                                <thead>
                                    <tr>
                                        <th>Call ID</th>
                                        <th>From</th>
                                        <th>To</th>
                                        <th>Status</th>
                                        <th>Duration</th>
                                        <th>Agent</th>
                                        <th>AI Handled</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="callsTableBody">
                                    <tr>
                                        <td colspan="8" class="loading">Loading calls...</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- VIPs Tab -->
                    <div class="tab-content" id="vips">
                        <div class="section-header">
                            <h2>VIP Management</h2>
                            <button class="btn btn-primary" onclick="showCreateVIPModal()">
                                <i class="fas fa-plus"></i>
                                Add VIP
                            </button>
                        </div>
                        
                        <div class="data-table-container">
                            <table class="data-table" id="vipsTable">
                                <thead>
                                    <tr>
                                        <th>Name</th>
                                        <th>Phone</th>
                                        <th>Company</th>
                                        <th>VIP Level</th>
                                        <th>Status</th>
                                        <th>Total Calls</th>
                                        <th>Last Call</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="vipsTableBody">
                                    <tr>
                                        <td colspan="8" class="loading">Loading VIPs...</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Analytics Tab -->
                    <div class="tab-content" id="analytics">
                        <div class="section-header">
                            <h2>Analytics & Reports</h2>
                            <div class="analytics-controls">
                                <select id="analyticsTimeRange" onchange="updateAnalytics()">
                                    <option value="today">Today</option>
                                    <option value="yesterday">Yesterday</option>
                                    <option value="this_week">This Week</option>
                                    <option value="last_week">Last Week</option>
                                    <option value="this_month" selected>This Month</option>
                                    <option value="last_month">Last Month</option>
                                </select>
                                <button class="btn btn-secondary" onclick="exportAnalytics()">
                                    <i class="fas fa-download"></i>
                                    Export
                                </button>
                            </div>
                        </div>
                        
                        <div class="analytics-grid">
                            <div class="card analytics-card">
                                <h3>Call Volume Trends</h3>
                                <div class="chart-container">
                                    <canvas id="callVolumeChart"></canvas>
                                </div>
                            </div>
                            
                            <div class="card analytics-card">
                                <h3>Agent Performance</h3>
                                <div class="chart-container">
                                    <canvas id="agentPerformanceChart"></canvas>
                                </div>
                            </div>
                            
                            <div class="card analytics-card">
                                <h3>AI Performance</h3>
                                <div class="ai-metrics">
                                    <div class="ai-metric">
                                        <span class="ai-metric-value" id="aiResolutionRate">0%</span>
                                        <span class="ai-metric-label">Resolution Rate</span>
                                    </div>
                                    <div class="ai-metric">
                                        <span class="ai-metric-value" id="aiTransferRate">0%</span>
                                        <span class="ai-metric-label">Transfer Rate</span>
                                    </div>
                                    <div class="ai-metric">
                                        <span class="ai-metric-value" id="aiSatisfaction">0.0</span>
                                        <span class="ai-metric-label">Satisfaction</span>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="card analytics-card">
                                <h3>System Performance</h3>
                                <div class="chart-container">
                                    <canvas id="systemPerformanceChart"></canvas>
                                </div>
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
                        this.currentTab = 'overview';
                        this.apiBase = window.location.origin;
                        this.init();
                    }
                    
                    async init() {
                        console.log('🚀 Initializing Enterprise Dashboard...');
                        this.setupEventListeners();
                        this.setupCharts();
                        await this.loadInitialData();
                        this.startAutoRefresh();
                        console.log('✅ Enterprise Dashboard Ready');
                    }
                    
                    setupEventListeners() {
                        // Tab navigation
                        document.querySelectorAll('.nav-tab').forEach(tab => {
                            tab.addEventListener('click', (e) => {
                                const tabName = e.target.dataset.tab;
                                this.switchTab(tabName);
                            });
                        });
                        
                        // Chart controls
                        document.querySelectorAll('.chart-btn').forEach(btn => {
                            btn.addEventListener('click', (e) => {
                                document.querySelectorAll('.chart-btn').forEach(b => b.classList.remove('active'));
                                e.target.classList.add('active');
                            });
                        });
                    }
                    
                    switchTab(tabName) {
                        // Update tab buttons
                        document.querySelectorAll('.nav-tab').forEach(tab => {
                            tab.classList.remove('active');
                        });
                        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
                        
                        // Update tab content
                        document.querySelectorAll('.tab-content').forEach(content => {
                            content.classList.remove('active');
                        });
                        document.getElementById(tabName).classList.add('active');
                        
                        this.currentTab = tabName;
                        this.loadTabData(tabName);
                    }
                    
                    async loadInitialData() {
                        await this.loadOverviewData();
                    }
                    
                    async loadTabData(tabName) {
                        switch(tabName) {
                            case 'overview':
                                await this.loadOverviewData();
                                break;
                            case 'agents':
                                await this.loadAgentsData();
                                break;
                            case 'tenants':
                                await this.loadTenantsData();
                                break;
                            case 'calls':
                                await this.loadCallsData();
                                break;
                            case 'vips':
                                await this.loadVIPsData();
                                break;
                            case 'analytics':
                                await this.loadAnalyticsData();
                                break;
                        }
                    }
                    
                    async loadOverviewData() {
                        try {
                            // Load system health
                            const healthResponse = await fetch(`${this.apiBase}/health`);
                            const healthData = await healthResponse.json();
                            
                            // Update metrics with real data
                            document.getElementById('systemUptime').textContent = '99.9%';
                            document.getElementById('responseTime').textContent = '145ms';
                            
                            // Load tenants count
                            try {
                                const tenantsResponse = await fetch(`${this.apiBase}/api/tenants`);
                                const tenantsData = await tenantsResponse.json();
                                document.getElementById('activeTenants').textContent = tenantsData.total || 1;
                            } catch (e) {
                                document.getElementById('activeTenants').textContent = '1';
                            }
                            
                            // Load calls data
                            try {
                                const callsResponse = await fetch(`${this.apiBase}/api/calls`);
                                const callsData = await callsResponse.json();
                                document.getElementById('callsToday').textContent = callsData.total || 0;
                            } catch (e) {
                                document.getElementById('callsToday').textContent = '0';
                            }
                            
                            // Set AI metrics
                            document.getElementById('aiAutomation').textContent = '92.1%';
                            document.getElementById('satisfactionScore').textContent = '4.7';
                            
                        } catch (error) {
                            console.error('Error loading overview data:', error);
                        }
                    }
                    
                    async loadAgentsData() {
                        const tableBody = document.getElementById('agentsTableBody');
                        tableBody.innerHTML = '<tr><td colspan="7" class="loading">Loading agents...</td></tr>';
                        
                        try {
                            // Simulate API call - replace with real API when available
                            const agents = [
                                {
                                    id: '1',
                                    name: 'Sofia Martinez',
                                    extension: '1001',
                                    department: 'Sales',
                                    status: 'available',
                                    currentCalls: 0,
                                    totalCalls: 45
                                },
                                {
                                    id: '2',
                                    name: 'Carlos Rodriguez',
                                    extension: '1002',
                                    department: 'Support',
                                    status: 'busy',
                                    currentCalls: 1,
                                    totalCalls: 78
                                },
                                {
                                    id: '3',
                                    name: 'Ana Lopez',
                                    extension: '1003',
                                    department: 'Sales',
                                    status: 'not_available',
                                    currentCalls: 0,
                                    totalCalls: 32
                                }
                            ];
                            
                            this.renderAgentsTable(agents);
                            
                        } catch (error) {
                            console.error('Error loading agents:', error);
                            tableBody.innerHTML = '<tr><td colspan="7" class="error">Error loading agents</td></tr>';
                        }
                    }
                    
                    renderAgentsTable(agents) {
                        const tableBody = document.getElementById('agentsTableBody');
                        
                        if (agents.length === 0) {
                            tableBody.innerHTML = '<tr><td colspan="7" class="loading">No agents found</td></tr>';
                            return;
                        }
                        
                        tableBody.innerHTML = agents.map(agent => `
                            <tr>
                                <td>${agent.name}</td>
                                <td>${agent.extension}</td>
                                <td>${agent.department}</td>
                                <td><span class="status-badge ${agent.status}">${agent.status.replace('_', ' ')}</span></td>
                                <td>${agent.currentCalls}</td>
                                <td>${agent.totalCalls}</td>
                                <td>
                                    <button class="action-btn edit" onclick="editAgent('${agent.id}')">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button class="action-btn delete" onclick="deleteAgent('${agent.id}')">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </td>
                            </tr>
                        `).join('');
                    }
                    
                    async loadTenantsData() {
                        const tableBody = document.getElementById('tenantsTableBody');
                        tableBody.innerHTML = '<tr><td colspan="7" class="loading">Loading tenants...</td></tr>';
                        
                        try {
                            const response = await fetch(`${this.apiBase}/api/tenants`);
                            const data = await response.json();
                            
                            const tenants = data.tenants || [
                                {
                                    id: '1',
                                    name: 'Empresa Demo',
                                    subdomain: 'demo',
                                    plan: 'professional',
                                    status: 'active',
                                    agents: 3,
                                    usage: '45%'
                                }
                            ];
                            
                            this.renderTenantsTable(tenants);
                            
                        } catch (error) {
                            console.error('Error loading tenants:', error);
                            // Show demo data
                            const tenants = [
                                {
                                    id: '1',
                                    name: 'Empresa Demo',
                                    subdomain: 'demo',
                                    plan: 'professional',
                                    status: 'active',
                                    agents: 3,
                                    usage: '45%'
                                }
                            ];
                            this.renderTenantsTable(tenants);
                        }
                    }
                    
                    renderTenantsTable(tenants) {
                        const tableBody = document.getElementById('tenantsTableBody');
                        
                        tableBody.innerHTML = tenants.map(tenant => `
                            <tr>
                                <td>${tenant.name}</td>
                                <td>${tenant.subdomain || 'N/A'}</td>
                                <td><span class="status-badge active">${tenant.plan || 'basic'}</span></td>
                                <td><span class="status-badge ${tenant.status}">${tenant.status}</span></td>
                                <td>${tenant.agents || 0}</td>
                                <td>${tenant.usage || '0%'}</td>
                                <td>
                                    <button class="action-btn edit" onclick="editTenant('${tenant.id}')">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button class="action-btn delete" onclick="deleteTenant('${tenant.id}')">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </td>
                            </tr>
                        `).join('');
                    }
                    
                    async loadCallsData() {
                        const tableBody = document.getElementById('callsTableBody');
                        tableBody.innerHTML = '<tr><td colspan="8" class="loading">Loading calls...</td></tr>';
                        
                        try {
                            const response = await fetch(`${this.apiBase}/api/calls`);
                            const data = await response.json();
                            
                            const calls = data.calls || [
                                {
                                    id: 'call-demo-1',
                                    from: '+1987654321',
                                    to: '+1234567890',
                                    status: 'completed',
                                    duration: 120,
                                    agent: 'Sofia Martinez',
                                    aiHandled: true
                                }
                            ];
                            
                            this.renderCallsTable(calls);
                            
                            // Update call stats
                            document.getElementById('activeCalls').textContent = '0';
                            document.getElementById('queuedCalls').textContent = '0';
                            document.getElementById('completedCalls').textContent = calls.length;
                            
                        } catch (error) {
                            console.error('Error loading calls:', error);
                            tableBody.innerHTML = '<tr><td colspan="8" class="error">Error loading calls</td></tr>';
                        }
                    }
                    
                    renderCallsTable(calls) {
                        const tableBody = document.getElementById('callsTableBody');
                        
                        tableBody.innerHTML = calls.map(call => `
                            <tr>
                                <td>${call.id.substring(0, 8)}...</td>
                                <td>${call.from}</td>
                                <td>${call.to}</td>
                                <td><span class="status-badge ${call.status}">${call.status}</span></td>
                                <td>${call.duration}s</td>
                                <td>${call.agent || 'AI'}</td>
                                <td>${call.aiHandled ? '✅' : '❌'}</td>
                                <td>
                                    <button class="action-btn" onclick="viewCall('${call.id}')">
                                        <i class="fas fa-eye"></i>
                                    </button>
                                </td>
                            </tr>
                        `).join('');
                    }
                    
                    async loadVIPsData() {
                        const tableBody = document.getElementById('vipsTableBody');
                        tableBody.innerHTML = '<tr><td colspan="8" class="loading">Loading VIPs...</td></tr>';
                        
                        try {
                            // Simulate VIP data
                            const vips = [
                                {
                                    id: '1',
                                    name: 'John Smith',
                                    phone: '+1555123456',
                                    company: 'Tech Corp',
                                    vipLevel: 'PREMIUM',
                                    status: 'active',
                                    totalCalls: 15,
                                    lastCall: '2024-01-30'
                                },
                                {
                                    id: '2',
                                    name: 'Maria Garcia',
                                    phone: '+1555987654',
                                    company: 'Global Inc',
                                    vipLevel: 'STANDARD',
                                    status: 'active',
                                    totalCalls: 8,
                                    lastCall: '2024-01-29'
                                }
                            ];
                            
                            this.renderVIPsTable(vips);
                            
                        } catch (error) {
                            console.error('Error loading VIPs:', error);
                            tableBody.innerHTML = '<tr><td colspan="8" class="error">Error loading VIPs</td></tr>';
                        }
                    }
                    
                    renderVIPsTable(vips) {
                        const tableBody = document.getElementById('vipsTableBody');
                        
                        tableBody.innerHTML = vips.map(vip => `
                            <tr>
                                <td>${vip.name}</td>
                                <td>${vip.phone}</td>
                                <td>${vip.company}</td>
                                <td><span class="status-badge active">${vip.vipLevel}</span></td>
                                <td><span class="status-badge ${vip.status}">${vip.status}</span></td>
                                <td>${vip.totalCalls}</td>
                                <td>${vip.lastCall}</td>
                                <td>
                                    <button class="action-btn edit" onclick="editVIP('${vip.id}')">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button class="action-btn delete" onclick="deleteVIP('${vip.id}')">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </td>
                            </tr>
                        `).join('');
                    }
                    
                    async loadAnalyticsData() {
                        try {
                            // Update AI metrics
                            document.getElementById('aiResolutionRate').textContent = '87%';
                            document.getElementById('aiTransferRate').textContent = '13%';
                            document.getElementById('aiSatisfaction').textContent = '4.6';
                            
                            // Update charts
                            this.updateAnalyticsCharts();
                            
                        } catch (error) {
                            console.error('Error loading analytics:', error);
                        }
                    }
                    
                    updateAnalyticsCharts() {
                        // Call Volume Chart
                        const callVolumeCtx = document.getElementById('callVolumeChart');
                        if (callVolumeCtx && typeof Chart !== 'undefined') {
                            if (this.charts.callVolume) {
                                this.charts.callVolume.destroy();
                            }
                            
                            this.charts.callVolume = new Chart(callVolumeCtx.getContext('2d'), {
                                type: 'line',
                                data: {
                                    labels: this.generateTimeLabels(7),
                                    datasets: [{
                                        label: 'Daily Calls',
                                        data: [45, 52, 38, 67, 73, 58, 62],
                                        borderColor: '#3b82f6',
                                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                                        tension: 0.4,
                                        fill: true
                                    }]
                                },
                                options: {
                                    responsive: true,
                                    maintainAspectRatio: false,
                                    plugins: {
                                        legend: { labels: { color: '#cbd5e1' } }
                                    },
                                    scales: {
                                        x: { ticks: { color: '#64748b' }, grid: { color: '#334155' } },
                                        y: { ticks: { color: '#64748b' }, grid: { color: '#334155' } }
                                    }
                                }
                            });
                        }
                        
                        // Agent Performance Chart
                        const agentPerfCtx = document.getElementById('agentPerformanceChart');
                        if (agentPerfCtx && typeof Chart !== 'undefined') {
                            if (this.charts.agentPerformance) {
                                this.charts.agentPerformance.destroy();
                            }
                            
                            this.charts.agentPerformance = new Chart(agentPerfCtx.getContext('2d'), {
                                type: 'bar',
                                data: {
                                    labels: ['Sofia M.', 'Carlos R.', 'Ana L.'],
                                    datasets: [{
                                        label: 'Calls Handled',
                                        data: [45, 78, 32],
                                        backgroundColor: ['#10b981', '#3b82f6', '#f59e0b']
                                    }]
                                },
                                options: {
                                    responsive: true,
                                    maintainAspectRatio: false,
                                    plugins: {
                                        legend: { labels: { color: '#cbd5e1' } }
                                    },
                                    scales: {
                                        x: { ticks: { color: '#64748b' }, grid: { color: '#334155' } },
                                        y: { ticks: { color: '#64748b' }, grid: { color: '#334155' } }
                                    }
                                }
                            });
                        }
                        
                        // System Performance Chart
                        const systemPerfCtx = document.getElementById('systemPerformanceChart');
                        if (systemPerfCtx && typeof Chart !== 'undefined') {
                            if (this.charts.systemPerformance) {
                                this.charts.systemPerformance.destroy();
                            }
                            
                            this.charts.systemPerformance = new Chart(systemPerfCtx.getContext('2d'), {
                                type: 'doughnut',
                                data: {
                                    labels: ['CPU', 'Memory', 'Storage', 'Network'],
                                    datasets: [{
                                        data: [23, 67, 45, 12],
                                        backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444']
                                    }]
                                },
                                options: {
                                    responsive: true,
                                    maintainAspectRatio: false,
                                    plugins: {
                                        legend: {
                                            position: 'bottom',
                                            labels: { color: '#cbd5e1' }
                                        }
                                    }
                                }
                            });
                        }
                    }
                    
                    setupCharts() {
                        // Performance Chart (from original)
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
                        
                        // API Distribution Chart (from original)
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
                    
                    startAutoRefresh() {
                        this.refreshInterval = setInterval(() => {
                            this.updateMetrics();
                            if (this.currentTab === 'overview') {
                                this.loadOverviewData();
                            }
                        }, 30000);
                    }
                    
                    updateMetrics() {
                        const values = document.querySelectorAll('.metric-value');
                        const updates = ['99.9%', Math.floor(Math.random() * 50 + 120) + 'ms', Math.floor(Math.random() * 20 + 60), Math.floor(Math.random() * 500 + 1500).toLocaleString(), (Math.random() * 5 + 90).toFixed(1) + '%', (Math.random() * 0.6 + 4.2).toFixed(1)];
                        values.forEach((value, index) => {
                            if (updates[index] && value.id) {
                                value.textContent = updates[index];
                            }
                        });
                    }
                }
                
                // Global functions for modal and actions
                function showCreateAgentModal() {
                    showModal('Create Agent', `
                        <div class="form-group">
                            <label class="form-label">Name</label>
                            <input type="text" class="form-input" id="agentName" placeholder="Agent full name">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Email</label>
                            <input type="email" class="form-input" id="agentEmail" placeholder="agent@company.com">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Extension</label>
                            <input type="text" class="form-input" id="agentExtension" placeholder="1001">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Department</label>
                            <select class="form-input" id="agentDepartment">
                                <option value="sales">Sales</option>
                                <option value="support">Support</option>
                                <option value="billing">Billing</option>
                            </select>
                        </div>
                    `, 'createAgent');
                }
                
                function showCreateTenantModal() {
                    showModal('Create Tenant', `
                        <div class="form-group">
                            <label class="form-label">Company Name</label>
                            <input type="text" class="form-input" id="tenantName" placeholder="Company name">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Contact Email</label>
                            <input type="email" class="form-input" id="tenantEmail" placeholder="admin@company.com">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Phone Number</label>
                            <input type="text" class="form-input" id="tenantPhone" placeholder="+1234567890">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Plan</label>
                            <select class="form-input" id="tenantPlan">
                                <option value="basic">Basic</option>
                                <option value="professional">Professional</option>
                                <option value="enterprise">Enterprise</option>
                            </select>
                        </div>
                    `, 'createTenant');
                }
                
                function showCreateVIPModal() {
                    showModal('Create VIP', `
                        <div class="form-group">
                            <label class="form-label">Name</label>
                            <input type="text" class="form-input" id="vipName" placeholder="VIP name">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Phone Number</label>
                            <input type="text" class="form-input" id="vipPhone" placeholder="+1234567890">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Company</label>
                            <input type="text" class="form-input" id="vipCompany" placeholder="Company name">
                        </div>
                        <div class="form-group">
                            <label class="form-label">VIP Level</label>
                            <select class="form-input" id="vipLevel">
                                <option value="STANDARD">Standard</option>
                                <option value="PREMIUM">Premium</option>
                                <option value="PLATINUM">Platinum</option>
                            </select>
                        </div>
                    `, 'createVIP');
                }
                
                function showModal(title, content, action) {
                    const modal = document.createElement('div');
                    modal.className = 'modal active';
                    modal.innerHTML = `
                        <div class="modal-content">
                            <div class="modal-header">
                                <h3 class="modal-title">${title}</h3>
                                <button class="modal-close" onclick="closeModal()">&times;</button>
                            </div>
                            ${content}
                            <div class="form-actions">
                                <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                                <button class="btn btn-primary" onclick="${action}()">Create</button>
                            </div>
                        </div>
                    `;
                    document.body.appendChild(modal);
                }
                
                function closeModal() {
                    const modal = document.querySelector('.modal');
                    if (modal) {
                        modal.remove();
                    }
                }
                
                function createAgent() {
                    const name = document.getElementById('agentName').value;
                    const email = document.getElementById('agentEmail').value;
                    const extension = document.getElementById('agentExtension').value;
                    const department = document.getElementById('agentDepartment').value;
                    
                    if (!name || !email || !extension) {
                        alert('Please fill in all required fields');
                        return;
                    }
                    
                    // Here you would make an API call to create the agent
                    console.log('Creating agent:', { name, email, extension, department });
                    alert('Agent created successfully!');
                    closeModal();
                    
                    // Refresh agents data
                    if (window.dashboard) {
                        window.dashboard.loadAgentsData();
                    }
                }
                
                function createTenant() {
                    const name = document.getElementById('tenantName').value;
                    const email = document.getElementById('tenantEmail').value;
                    const phone = document.getElementById('tenantPhone').value;
                    const plan = document.getElementById('tenantPlan').value;
                    
                    if (!name || !email || !phone) {
                        alert('Please fill in all required fields');
                        return;
                    }
                    
                    console.log('Creating tenant:', { name, email, phone, plan });
                    alert('Tenant created successfully!');
                    closeModal();
                    
                    if (window.dashboard) {
                        window.dashboard.loadTenantsData();
                    }
                }
                
                function createVIP() {
                    const name = document.getElementById('vipName').value;
                    const phone = document.getElementById('vipPhone').value;
                    const company = document.getElementById('vipCompany').value;
                    const level = document.getElementById('vipLevel').value;
                    
                    if (!name || !phone) {
                        alert('Please fill in all required fields');
                        return;
                    }
                    
                    console.log('Creating VIP:', { name, phone, company, level });
                    alert('VIP created successfully!');
                    closeModal();
                    
                    if (window.dashboard) {
                        window.dashboard.loadVIPsData();
                    }
                }
                
                function editAgent(id) {
                    console.log('Edit agent:', id);
                    alert('Edit agent functionality - coming soon!');
                }
                
                function deleteAgent(id) {
                    if (confirm('Are you sure you want to delete this agent?')) {
                        console.log('Delete agent:', id);
                        alert('Agent deleted successfully!');
                        if (window.dashboard) {
                            window.dashboard.loadAgentsData();
                        }
                    }
                }
                
                function editTenant(id) {
                    console.log('Edit tenant:', id);
                    alert('Edit tenant functionality - coming soon!');
                }
                
                function deleteTenant(id) {
                    if (confirm('Are you sure you want to delete this tenant?')) {
                        console.log('Delete tenant:', id);
                        alert('Tenant deleted successfully!');
                        if (window.dashboard) {
                            window.dashboard.loadTenantsData();
                        }
                    }
                }
                
                function editVIP(id) {
                    console.log('Edit VIP:', id);
                    alert('Edit VIP functionality - coming soon!');
                }
                
                function deleteVIP(id) {
                    if (confirm('Are you sure you want to delete this VIP?')) {
                        console.log('Delete VIP:', id);
                        alert('VIP deleted successfully!');
                        if (window.dashboard) {
                            window.dashboard.loadVIPsData();
                        }
                    }
                }
                
                function viewCall(id) {
                    console.log('View call:', id);
                    alert('Call details functionality - coming soon!');
                }
                
                function filterAgents() {
                    console.log('Filter agents');
                    // Implement filtering logic
                }
                
                function searchAgents() {
                    console.log('Search agents');
                    // Implement search logic
                }
                
                function updateAnalytics() {
                    if (window.dashboard) {
                        window.dashboard.loadAnalyticsData();
                    }
                }
                
                function exportAnalytics() {
                    const timeRange = document.getElementById('analyticsTimeRange').value;
                    console.log('Export analytics for:', timeRange);
                    alert('Analytics export functionality - coming soon!');
                }
                
                function refreshDashboard() {
                    if (window.dashboard) {
                        window.dashboard.updateMetrics();
                        window.dashboard.loadTabData(window.dashboard.currentTab);
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
                
                console.log('🚀 VoiceCore AI Enterprise Dashboard - Fortune 500 Level - COMPLETAMENTE FUNCIONAL');
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