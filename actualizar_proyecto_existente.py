#!/usr/bin/env python3
"""
🔄 ACTUALIZAR PROYECTO EXISTENTE EN RAILWAY
Actualiza tu proyecto existente con el nuevo dashboard enterprise
"""

import subprocess
import sys

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
    
    print("🔄 ACTUALIZAR PROYECTO EXISTENTE - VOICECORE AI")
    print("=" * 60)
    print()
    
    print("📋 SITUACIÓN ACTUAL:")
    print("✅ Ya tienes el proyecto en Railway")
    print("✅ Dashboard enterprise integrado localmente")
    print("🎯 Necesitamos actualizar el proyecto online")
    print()
    
    # Opciones para el usuario
    print("🔗 ¿Cuál es la URL de tu repositorio en GitHub?")
    print("   (La que usaste cuando creaste el proyecto)")
    print()
    print("💡 Ejemplos:")
    print("   - https://github.com/tu-usuario/voicecore-ai")
    print("   - https://github.com/tu-usuario/voicecore-ai.git")
    print()
    
    while True:
        repo_url = input("📝 Ingresa la URL de tu repositorio GitHub: ").strip()
        
        if not repo_url:
            print("❌ Por favor ingresa la URL del repositorio")
            continue
            
        if not repo_url.startswith("https://github.com/"):
            print("❌ La URL debe empezar con https://github.com/")
            continue
            
        if not repo_url.endswith(".git"):
            repo_url += ".git"
            
        break
    
    print(f"\n🎯 Conectando con repositorio existente: {repo_url}")
    print()
    
    # Verificar si ya hay un remote
    result = subprocess.run("git remote -v", shell=True, capture_output=True, text=True)
    if "origin" in result.stdout:
        print("🔄 Removiendo remote existente...")
        run_command("git remote remove origin", "Removiendo remote anterior")
    
    # Agregar remote
    if run_command(f'git remote add origin "{repo_url}"', "Conectando con repositorio GitHub"):
        
        # Hacer push forzado para actualizar
        print("🔄 Actualizando repositorio con dashboard enterprise...")
        if run_command("git push -f origin main", "Actualizando código en GitHub"):
            
            print("\n🎉 ¡PROYECTO ACTUALIZADO EXITOSAMENTE!")
            print("=" * 50)
            
            # Extraer usuario y repo de la URL
            parts = repo_url.replace("https://github.com/", "").replace(".git", "").split("/")
            if len(parts) == 2:
                usuario, repo = parts
                
                print(f"✅ Repositorio actualizado: https://github.com/{usuario}/{repo}")
                print()
                print("🚀 RAILWAY SE ACTUALIZARÁ AUTOMÁTICAMENTE:")
                print("=" * 45)
                print("⏱️ Railway detectará los cambios en 2-3 minutos")
                print("🔄 El despliegue tomará otros 3-5 minutos")
                print("📊 Total: 5-8 minutos para ver el dashboard")
                print()
                print("🎨 DASHBOARD ENTERPRISE ESTARÁ EN:")
                print("   https://voicecore-ai-production.up.railway.app/dashboard")
                print()
                print("🔍 VERIFICAR PROGRESO:")
                print("   • Railway Dashboard: https://railway.app/dashboard")
                print("   • Busca tu proyecto 'voicecore-ai'")
                print("   • Ve la pestaña 'Deployments'")
                print()
                print("🎉 ¡DASHBOARD ENTERPRISE ACTUALIZADO!")
                print("   Espera 5-8 minutos y verifica la URL del dashboard")
                
        else:
            print("\n❌ Error actualizando GitHub")
            print("💡 Posibles soluciones:")
            print("   - Verifica que estés logueado en GitHub")
            print("   - Asegúrate de tener permisos de escritura")
            print("   - Intenta: git push --force-with-lease origin main")
    
    else:
        print("\n❌ Error conectando con GitHub")
        print("💡 Verifica que la URL del repositorio sea correcta")

if __name__ == "__main__":
    main()