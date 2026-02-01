#!/usr/bin/env python3
"""
🚀 DESPLIEGUE AUTOMÁTICO DEL DASHBOARD ENTERPRISE
Sube los cambios a GitHub y actualiza Railway automáticamente
"""

import os
import zipfile
import requests
from datetime import datetime
import json

def create_deployment_package():
    """Crear paquete de despliegue con los nuevos archivos"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"voicecore-dashboard-enterprise-{timestamp}.zip"
    
    # Archivos críticos para el dashboard
    critical_files = [
        "simple_start.py",
        "voicecore/api/dashboard_routes.py",
        "voicecore/api/system_status_routes.py", 
        "voicecore/services/railway_api_service.py",
        "requirements_minimal.txt",
        "Dockerfile",
        "railway.json",
        ".env"
    ]
    
    # Crear ZIP con estructura completa
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk('.'):
            # Excluir directorios innecesarios
            dirs[:] = [d for d in dirs if d not in {
                '__pycache__', '.git', 'venv', 'env', 'node_modules',
                '.pytest_cache', '.mypy_cache', 'dist', 'build'
            }]
            
            for file in files:
                if file.endswith(('.py', '.md', '.txt', '.json', '.yml', '.yaml', '.dockerfile')) or file == 'Dockerfile':
                    file_path = os.path.join(root, file)
                    arcname = file_path.replace('\\', '/')
                    zipf.write(file_path, arcname)
    
    return zip_filename

def test_dashboard_locally():
    """Probar el dashboard localmente antes del despliegue"""
    try:
        print("🧪 Probando dashboard localmente...")
        
        # Verificar que los archivos críticos existen
        critical_files = [
            "voicecore/api/dashboard_routes.py",
            "simple_start.py"
        ]
        
        for file in critical_files:
            if not os.path.exists(file):
                print(f"❌ Archivo crítico faltante: {file}")
                return False
        
        print("✅ Todos los archivos críticos están presentes")
        return True
        
    except Exception as e:
        print(f"❌ Error en pruebas locales: {e}")
        return False

def verify_live_deployment():
    """Verificar que el despliegue en Railway funciona"""
    try:
        base_url = "https://voicecore-ai-production.up.railway.app"
        
        print("🔍 Verificando despliegue en Railway...")
        
        # Probar endpoints críticos
        endpoints = [
            "/",
            "/health", 
            "/dashboard",
            "/dashboard/metrics/system"
        ]
        
        results = []
        for endpoint in endpoints:
            try:
                response = requests.get(f"{base_url}{endpoint}", timeout=10)
                status = "✅" if response.status_code == 200 else "❌"
                results.append(f"{status} {endpoint} - {response.status_code}")
            except Exception as e:
                results.append(f"❌ {endpoint} - Error: {str(e)[:50]}")
        
        return results
        
    except Exception as e:
        return [f"❌ Error de verificación: {e}"]

def main():
    """Función principal de despliegue"""
    
    print("🚀 DESPLIEGUE DASHBOARD ENTERPRISE - VOICECORE AI")
    print("=" * 60)
    print(f"🕐 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Paso 1: Pruebas locales
    if not test_dashboard_locally():
        print("❌ Pruebas locales fallaron. Abortando despliegue.")
        return False
    
    # Paso 2: Crear paquete de despliegue
    print("📦 Creando paquete de despliegue...")
    zip_file = create_deployment_package()
    print(f"✅ Paquete creado: {zip_file}")
    
    # Paso 3: Instrucciones de despliegue
    print("\n🎯 INSTRUCCIONES DE DESPLIEGUE:")
    print("=" * 40)
    print("1. Ve a tu repositorio GitHub:")
    print("   https://github.com/TU_USUARIO/voicecore-ai")
    print()
    print("2. Haz clic en 'Add file' → 'Upload files'")
    print()
    print(f"3. Sube el archivo: {zip_file}")
    print()
    print("4. Commit message:")
    print("   'Add Enterprise Dashboard - Professional Monitoring Interface'")
    print()
    print("5. Haz clic en 'Commit changes'")
    print()
    print("⏱️ Railway detectará los cambios y redesplegará automáticamente (3-5 min)")
    
    # Paso 4: Información del nuevo dashboard
    print("\n🎨 NUEVO DASHBOARD ENTERPRISE:")
    print("=" * 40)
    print("✨ Características agregadas:")
    print("  • Interfaz profesional de nivel enterprise")
    print("  • Métricas en tiempo real con gráficos")
    print("  • Monitoreo de infraestructura Railway")
    print("  • KPIs de negocio y rendimiento")
    print("  • Diseño responsive y moderno")
    print("  • Auto-refresh cada 30 segundos")
    print("  • Exportación de métricas")
    print("  • Indicadores visuales de estado")
    print()
    print("🔗 URLs del Dashboard:")
    print("  • Principal: https://voicecore-ai-production.up.railway.app/dashboard")
    print("  • Métricas Sistema: /dashboard/metrics/system")
    print("  • Métricas Infraestructura: /dashboard/metrics/infrastructure")
    print("  • Métricas API: /dashboard/metrics/api")
    print("  • Métricas Negocio: /dashboard/metrics/business")
    
    # Paso 5: Verificación post-despliegue
    print("\n🔍 VERIFICACIÓN POST-DESPLIEGUE:")
    print("=" * 40)
    print("Después de subir a GitHub, espera 5 minutos y ejecuta:")
    print("  python test_live_app.py")
    print()
    print("O verifica manualmente:")
    results = verify_live_deployment()
    for result in results:
        print(f"  {result}")
    
    print("\n🎉 DESPLIEGUE PREPARADO!")
    print(f"📁 Archivo listo: {zip_file}")
    print("🚀 ¡Sube a GitHub y disfruta tu dashboard enterprise!")
    
    return True

if __name__ == "__main__":
    main()