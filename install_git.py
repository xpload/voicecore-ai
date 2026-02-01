#!/usr/bin/env python3
"""
🔧 INSTALADOR DE GIT PARA WINDOWS
Descarga e instala Git automáticamente
"""

import os
import subprocess
import urllib.request
import sys
from pathlib import Path

def download_git():
    """Descargar Git para Windows"""
    print("📥 Descargando Git para Windows...")
    
    # URL de descarga de Git para Windows (64-bit)
    git_url = "https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe"
    git_installer = "Git-installer.exe"
    
    try:
        urllib.request.urlretrieve(git_url, git_installer)
        print(f"✅ Git descargado: {git_installer}")
        return git_installer
    except Exception as e:
        print(f"❌ Error descargando Git: {e}")
        return None

def install_git(installer_path):
    """Instalar Git silenciosamente"""
    print("🔧 Instalando Git...")
    
    try:
        # Instalación silenciosa con configuración por defecto
        cmd = f'"{installer_path}" /VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /COMPONENTS="icons,ext\\reg\\shellhere,assoc,assoc_sh"'
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Git instalado exitosamente")
            return True
        else:
            print(f"❌ Error instalando Git: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error en instalación: {e}")
        return False

def check_git_installation():
    """Verificar si Git está instalado"""
    try:
        result = subprocess.run("git --version", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Git ya está instalado: {result.stdout.strip()}")
            return True
        else:
            return False
    except:
        return False

def main():
    """Función principal"""
    
    print("🔧 INSTALADOR DE GIT PARA WINDOWS")
    print("=" * 50)
    
    # Verificar si Git ya está instalado
    if check_git_installation():
        print("🎉 Git ya está disponible")
        return True
    
    print("📋 Git no está instalado. Procediendo con la instalación...")
    
    # Descargar Git
    installer = download_git()
    if not installer:
        print("❌ No se pudo descargar Git")
        print("💡 Descarga manualmente desde: https://git-scm.com/download/win")
        return False
    
    # Instalar Git
    if install_git(installer):
        print("\n🎉 ¡Git instalado exitosamente!")
        print("💡 Reinicia PowerShell o abre una nueva ventana")
        print("   Luego ejecuta: git --version")
        
        # Limpiar archivo de instalación
        try:
            os.remove(installer)
            print(f"🧹 Archivo de instalación eliminado: {installer}")
        except:
            pass
            
        return True
    else:
        print("❌ Error en la instalación de Git")
        return False

if __name__ == "__main__":
    main()