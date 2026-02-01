#!/usr/bin/env python3
"""
🚀 SUBIDA AUTOMÁTICA A GITHUB - DASHBOARD ENTERPRISE
Sube automáticamente los archivos actualizados a GitHub para despliegue en Railway
"""

import os
import subprocess
import sys
from datetime import datetime

def run_command(command, description):
    """Ejecutar comando y mostrar resultado"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - Exitoso")
            if result.stdout.strip():
                print(f"   {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} - Error")
            if result.stderr.strip():
                print(f"   Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ {description} - Excepción: {e}")
        return False

def main():
    """Función principal"""
    
    print("🚀 SUBIDA AUTOMÁTICA - DASHBOARD ENTERPRISE")
    print("=" * 60)
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Verificar si estamos en un repositorio git
    if not os.path.exists('.git'):
        print("❌ No se detectó repositorio Git")
        print("💡 Inicializa el repositorio primero:")
        print("   git init")
        print("   git remote add origin https://github.com/TU_USUARIO/voicecore-ai.git")
        return False
    
    # Comandos de Git
    commands = [
        ("git add .", "Agregando archivos al staging"),
        ("git commit -m \"🎨 Integrate Enterprise Dashboard - Live Update with Real-time Metrics\"", "Creando commit"),
        ("git push origin main", "Subiendo a GitHub")
    ]
    
    success = True
    for command, description in commands:
        if not run_command(command, description):
            success = False
            break
    
    if success:
        print("\n🎉 ¡DESPLIEGUE INICIADO!")
        print("=" * 40)
        print("✅ Archivos subidos a GitHub exitosamente")
        print("⏱️ Railway redesplegará automáticamente en 3-5 minutos")
        print()
        print("🔗 URLs para verificar:")
        print("  • GitHub: https://github.com/TU_USUARIO/voicecore-ai")
        print("  • Railway: https://railway.app/dashboard")
        print("  • Dashboard: https://voicecore-ai-production.up.railway.app/dashboard")
        print()
        print("📊 DASHBOARD ENTERPRISE FEATURES:")
        print("  • Métricas del sistema en tiempo real")
        print("  • Monitoreo de infraestructura Railway")
        print("  • Gráficos interactivos con Chart.js")
        print("  • Interfaz responsive y profesional")
        print("  • Auto-refresh cada 30 segundos")
        print("  • Exportación de métricas")
        print()
        print("🎯 Verifica el dashboard en 5 minutos:")
        print("   https://voicecore-ai-production.up.railway.app/dashboard")
        
    else:
        print("\n❌ Error en el despliegue")
        print("💡 Verifica tu configuración de Git y GitHub")
        print("   - git config --global user.name \"Tu Nombre\"")
        print("   - git config --global user.email \"tu@email.com\"")
        print("   - git remote -v (verificar remote)")
    
    return success

if __name__ == "__main__":
    main()