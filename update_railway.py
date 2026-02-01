#!/usr/bin/env python3
"""
Script para actualizar automáticamente VoiceCore AI en Railway
Sube los cambios a GitHub y Railway se actualiza automáticamente
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
            print(f"✅ {description} - Completado")
            if result.stdout.strip():
                print(f"   📝 {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} - Error")
            print(f"   🚨 {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ {description} - Excepción: {e}")
        return False

def main():
    """Función principal para actualizar Railway"""
    
    print("🚀 VoiceCore AI - Actualizador Automático para Railway")
    print("=" * 60)
    
    # Verificar si estamos en un repositorio git
    if not os.path.exists(".git"):
        print("❌ No se detectó repositorio Git. Inicializando...")
        if not run_command("git init", "Inicializar repositorio Git"):
            return False
    
    # Agregar todos los archivos
    if not run_command("git add .", "Agregar archivos al repositorio"):
        return False
    
    # Crear commit con timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_message = f"Update VoiceCore AI - Dashboard de Monitoreo - {timestamp}"
    
    if not run_command(f'git commit -m "{commit_message}"', "Crear commit"):
        print("ℹ️ No hay cambios para commitear o ya están commiteados")
    
    # Verificar si hay remote origin
    result = subprocess.run("git remote -v", shell=True, capture_output=True, text=True)
    if "origin" not in result.stdout:
        print("⚠️ No se detectó remote origin.")
        print("   Configura tu repositorio GitHub primero:")
        print("   git remote add origin https://github.com/TU_USUARIO/voicecore-ai.git")
        return False
    
    # Push a GitHub (Railway se actualiza automáticamente)
    if not run_command("git push origin main", "Subir cambios a GitHub"):
        # Intentar con master si main falla
        if not run_command("git push origin master", "Subir cambios a GitHub (master)"):
            print("❌ Error al subir cambios. Verifica tu configuración de GitHub.")
            return False
    
    print("\n🎉 ¡Actualización completada!")
    print("📡 Railway detectará los cambios automáticamente y redesplegará la aplicación.")
    print("⏱️ El proceso de despliegue toma aproximadamente 2-5 minutos.")
    print("\n🔗 Nuevas funcionalidades agregadas:")
    print("   • Dashboard de monitoreo en tiempo real: /dashboard")
    print("   • API de estado del sistema: /system/status")
    print("   • Verificación de conexiones y saldos")
    print("\n📊 Una vez desplegado, visita tu URL de Railway + /dashboard")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Actualización cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)