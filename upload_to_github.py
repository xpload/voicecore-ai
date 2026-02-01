#!/usr/bin/env python3
"""
Script alternativo para subir archivos a GitHub sin Git
Usa la API de GitHub directamente
"""

import os
import base64
import json
import zipfile
from datetime import datetime
import requests

def create_zip_file():
    """Crear archivo ZIP con todos los archivos del proyecto"""
    zip_filename = f"voicecore-ai-{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    
    # Archivos y carpetas a incluir
    include_patterns = [
        "*.py", "*.md", "*.txt", "*.json", "*.yml", "*.yaml", 
        "*.dockerfile", "Dockerfile", ".env*", "*.ini"
    ]
    
    # Carpetas a excluir
    exclude_dirs = {
        "__pycache__", ".git", "venv", "env", "node_modules", 
        ".pytest_cache", ".mypy_cache", "dist", "build"
    }
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk('.'):
            # Filtrar directorios excluidos
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                file_path = os.path.join(root, file)
                # Incluir archivos que coincidan con los patrones
                if any(file.endswith(pattern.replace('*', '')) for pattern in include_patterns) or file in ['Dockerfile']:
                    zipf.write(file_path, file_path)
    
    return zip_filename

def show_manual_instructions():
    """Mostrar instrucciones manuales para subir a GitHub"""
    
    print("🚀 VoiceCore AI - Instrucciones de Despliegue Manual")
    print("=" * 60)
    print()
    print("📦 PASO 1: Crear archivo ZIP")
    zip_file = create_zip_file()
    print(f"✅ Archivo creado: {zip_file}")
    print()
    
    print("📤 PASO 2: Subir a GitHub")
    print("1. Ve a tu repositorio en GitHub:")
    print("   https://github.com/TU_USUARIO/voicecore-ai")
    print()
    print("2. Haz clic en 'Add file' → 'Upload files'")
    print()
    print("3. Arrastra el archivo ZIP o selecciónalo")
    print(f"   Archivo: {zip_file}")
    print()
    print("4. En el mensaje de commit escribe:")
    print("   'Add VoiceCore AI Dashboard - Real-time Monitoring'")
    print()
    print("5. Haz clic en 'Commit changes'")
    print()
    
    print("🚂 PASO 3: Railway se actualiza automáticamente")
    print("• Railway detectará los cambios en GitHub")
    print("• El redespliegue toma 3-5 minutos")
    print("• Nuevas funcionalidades:")
    print("  - Dashboard de monitoreo: /dashboard")
    print("  - Estado del sistema: /system/status")
    print("  - URL de Railway: /system/railway/url")
    print()
    
    print("🔗 PASO 4: Obtener tu URL")
    print("Una vez desplegado, tu aplicación estará en:")
    print("https://TU-PROYECTO.railway.app")
    print()
    print("Endpoints disponibles:")
    print("• /              - Página principal")
    print("• /dashboard     - Dashboard de monitoreo")
    print("• /docs          - Documentación API")
    print("• /health        - Estado del sistema")
    print()
    
    return zip_file

def detect_railway_url():
    """Intentar detectar la URL de Railway"""
    print("🔍 Buscando URL de Railway...")
    
    # Patrones comunes de URLs de Railway
    possible_urls = [
        "https://voicecore-ai-production.railway.app",
        "https://voicecore-ai.railway.app", 
        "https://voicecore-ai-main.railway.app"
    ]
    
    for url in possible_urls:
        try:
            print(f"   Probando: {url}")
            response = requests.get(url + "/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if "VoiceCore AI" in str(data):
                    print(f"✅ ¡Encontrada! Tu aplicación está en: {url}")
                    print(f"🎯 Dashboard: {url}/dashboard")
                    return url
        except:
            continue
    
    print("⚠️ No se pudo detectar automáticamente la URL")
    print("   Revisa tu dashboard de Railway para obtenerla")
    return None

def main():
    """Función principal"""
    try:
        print("🎯 Detectando aplicación desplegada...")
        url = detect_railway_url()
        
        if not url:
            print("\n📦 Creando paquete para despliegue manual...")
            zip_file = show_manual_instructions()
            
            print(f"\n✨ Archivo {zip_file} creado exitosamente!")
            print("   Sigue las instrucciones arriba para subirlo a GitHub")
        
        print("\n🎉 ¡Proceso completado!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()