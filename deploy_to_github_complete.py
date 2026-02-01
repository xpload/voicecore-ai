#!/usr/bin/env python3
"""
🚀 DESPLIEGUE COMPLETO A GITHUB + RAILWAY
Script completo para subir el dashboard enterprise a GitHub y desplegarlo en Railway
"""

import os
import subprocess
import sys
from datetime import datetime

def run_command(command, description, show_output=True):
    """Ejecutar comando y mostrar resultado"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - Exitoso")
            if show_output and result.stdout.strip():
                print(f"   {result.stdout.strip()}")
            return True, result.stdout
        else:
            print(f"❌ {description} - Error")
            if result.stderr.strip():
                print(f"   Error: {result.stderr.strip()}")
            return False, result.stderr
    except Exception as e:
        print(f"❌ {description} - Excepción: {e}")
        return False, str(e)

def check_git():
    """Verificar si Git está disponible"""
    success, output = run_command("git --version", "Verificando Git", False)
    return success

def setup_git_config():
    """Configurar Git si no está configurado"""
    print("🔧 Configurando Git...")
    
    # Verificar configuración actual
    success, name = run_command("git config --global user.name", "Verificando nombre de usuario", False)
    success2, email = run_command("git config --global user.email", "Verificando email", False)
    
    if not success or not name.strip():
        print("📝 Configurando nombre de usuario...")
        run_command('git config --global user.name "VoiceCore Developer"', "Configurando nombre")
    
    if not success2 or not email.strip():
        print("📧 Configurando email...")
        run_command('git config --global user.email "developer@voicecore.ai"', "Configurando email")

def create_gitignore():
    """Crear archivo .gitignore"""
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/

# Environment Variables
.env
.env.local
.env.production

# IDE
.vscode/
.idea/
*.swp
*.swo

# Logs
*.log
logs/

# Database
*.db
*.sqlite
*.sqlite3

# OS
.DS_Store
Thumbs.db

# Temporary files
*.tmp
*.temp

# Deployment
*.zip
Git-installer.exe
"""
    
    with open('.gitignore', 'w', encoding='utf-8') as f:
        f.write(gitignore_content)
    
    print("✅ Archivo .gitignore creado")

def main():
    """Función principal"""
    
    print("🚀 DESPLIEGUE COMPLETO - VOICECORE AI DASHBOARD")
    print("=" * 60)
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Verificar Git
    if not check_git():
        print("❌ Git no está disponible")
        print("💡 Pasos para continuar:")
        print("   1. Cierra esta ventana de PowerShell")
        print("   2. Abre una nueva ventana de PowerShell")
        print("   3. Navega a: cd C:\\Users\\LUIS\\Desktop\\voicecore-ai")
        print("   4. Ejecuta: python deploy_to_github_complete.py")
        return False
    
    # Configurar Git
    setup_git_config()
    
    # Crear .gitignore
    create_gitignore()
    
    # Inicializar repositorio
    if not os.path.exists('.git'):
        success, _ = run_command("git init", "Inicializando repositorio Git")
        if not success:
            return False
    
    # Agregar archivos
    success, _ = run_command("git add .", "Agregando archivos")
    if not success:
        return False
    
    # Crear commit inicial
    commit_msg = "🎨 VoiceCore AI - Enterprise Dashboard with Real-time Monitoring"
    success, _ = run_command(f'git commit -m "{commit_msg}"', "Creando commit inicial")
    if not success:
        # Puede fallar si no hay cambios, continuar
        pass
    
    # Configurar rama principal
    run_command("git branch -M main", "Configurando rama principal")
    
    print("\n🎯 CONFIGURACIÓN DE GITHUB:")
    print("=" * 40)
    print("Para completar el despliegue, necesitas:")
    print()
    print("1. 🌐 Crear repositorio en GitHub:")
    print("   • Ve a: https://github.com/new")
    print("   • Nombre: voicecore-ai")
    print("   • Descripción: VoiceCore AI - Enterprise Virtual Receptionist")
    print("   • Público o Privado (tu elección)")
    print("   • NO inicialices con README, .gitignore o licencia")
    print()
    print("2. 🔗 Conectar repositorio local:")
    print("   • Copia la URL del repositorio (ej: https://github.com/TU_USUARIO/voicecore-ai.git)")
    print("   • Ejecuta: git remote add origin https://github.com/TU_USUARIO/voicecore-ai.git")
    print("   • Ejecuta: git push -u origin main")
    print()
    print("3. 🚀 Conectar con Railway:")
    print("   • Ve a: https://railway.app/dashboard")
    print("   • New Project → Deploy from GitHub repo")
    print("   • Selecciona: voicecore-ai")
    print("   • Railway detectará automáticamente el Dockerfile")
    print()
    print("🎉 RESULTADO FINAL:")
    print("   Dashboard Enterprise: https://TU-APP.up.railway.app/dashboard")
    print()
    print("📋 ARCHIVOS PREPARADOS:")
    print("   ✅ simple_start.py - Con dashboard integrado")
    print("   ✅ Dockerfile - Para Railway")
    print("   ✅ requirements_minimal.txt - Dependencias")
    print("   ✅ .gitignore - Archivos a ignorar")
    print("   ✅ Repositorio Git inicializado")
    
    return True

if __name__ == "__main__":
    main()