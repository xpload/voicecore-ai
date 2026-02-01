#!/usr/bin/env python3
"""
🔗 CONECTAR CON GITHUB - SCRIPT INTERACTIVO
Te ayuda a conectar tu repositorio local con GitHub paso a paso
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
    
    print("🔗 CONECTAR CON GITHUB - SCRIPT INTERACTIVO")
    print("=" * 60)
    print()
    
    print("📋 INSTRUCCIONES:")
    print("1. Ve a: https://github.com/new")
    print("2. Nombre: voicecore-ai")
    print("3. NO marques ninguna casilla")
    print("4. Crea el repositorio")
    print()
    
    # Pedir URL del repositorio
    print("🔗 Después de crear el repositorio, GitHub te mostrará una URL como:")
    print("   https://github.com/TU_USUARIO/voicecore-ai.git")
    print()
    
    while True:
        repo_url = input("📝 Pega aquí la URL de tu repositorio: ").strip()
        
        if not repo_url:
            print("❌ Por favor ingresa la URL del repositorio")
            continue
            
        if not repo_url.startswith("https://github.com/"):
            print("❌ La URL debe empezar con https://github.com/")
            continue
            
        if not repo_url.endswith(".git"):
            repo_url += ".git"
            
        break
    
    print(f"\n🎯 Conectando con: {repo_url}")
    print()
    
    # Verificar si ya hay un remote
    result = subprocess.run("git remote -v", shell=True, capture_output=True, text=True)
    if "origin" in result.stdout:
        print("🔄 Removiendo remote existente...")
        run_command("git remote remove origin", "Removiendo remote anterior")
    
    # Agregar remote
    if run_command(f'git remote add origin "{repo_url}"', "Agregando remote de GitHub"):
        
        # Hacer push
        if run_command("git push -u origin main", "Subiendo código a GitHub"):
            
            print("\n🎉 ¡CÓDIGO SUBIDO EXITOSAMENTE!")
            print("=" * 50)
            
            # Extraer usuario y repo de la URL
            parts = repo_url.replace("https://github.com/", "").replace(".git", "").split("/")
            if len(parts) == 2:
                usuario, repo = parts
                
                print(f"✅ Repositorio: https://github.com/{usuario}/{repo}")
                print()
                print("🚀 PRÓXIMO PASO - RAILWAY:")
                print("=" * 30)
                print("1. Ve a: https://railway.app/dashboard")
                print("2. New Project → Deploy from GitHub repo")
                print(f"3. Selecciona: {repo}")
                print("4. ¡Espera 3-5 minutos!")
                print()
                print("🎨 DASHBOARD ENTERPRISE ESTARÁ EN:")
                print(f"   https://tu-app.up.railway.app/dashboard")
                print()
                print("🎉 ¡FELICIDADES! Tu aplicación estará online en minutos")
                
        else:
            print("\n❌ Error subiendo a GitHub")
            print("💡 Verifica que:")
            print("   - Estés logueado en GitHub")
            print("   - La URL del repositorio sea correcta")
            print("   - Tengas permisos de escritura")
    
    else:
        print("\n❌ Error conectando con GitHub")
        print("💡 Verifica que la URL del repositorio sea correcta")

if __name__ == "__main__":
    main()