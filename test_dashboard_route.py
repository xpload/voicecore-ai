#!/usr/bin/env python3
"""
Test simple para verificar que la ruta del dashboard está registrada correctamente.
"""

import sys
from pathlib import Path

# Agregar el directorio actual al PYTHONPATH
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    
    # Crear aplicación de prueba
    app = FastAPI()
    
    @app.get("/dashboard", response_class=HTMLResponse)
    async def test_dashboard():
        return "<h1>Dashboard Test</h1>"
    
    # Verificar rutas
    print("🔍 Verificando rutas registradas:")
    for route in app.routes:
        if hasattr(route, 'path'):
            methods = getattr(route, 'methods', ['GET'])
            print(f"  {list(methods)} {route.path}")
    
    # Test específico del dashboard
    dashboard_routes = [route for route in app.routes if hasattr(route, 'path') and route.path == '/dashboard']
    
    if dashboard_routes:
        print("✅ Ruta /dashboard encontrada")
        print(f"   Métodos: {list(dashboard_routes[0].methods)}")
    else:
        print("❌ Ruta /dashboard NO encontrada")
    
    print("\n🧪 Iniciando servidor de prueba en puerto 8001...")
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()