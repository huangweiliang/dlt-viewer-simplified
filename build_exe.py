"""
Build script to create standalone executable for DLT Viewer
Run this script to generate the .exe file
"""
import subprocess
import sys
import os

def install_pyinstaller():
    """Install PyInstaller if not already installed"""
    try:
        import PyInstaller
        print("PyInstaller is already installed")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("PyInstaller installed successfully")

def build_executable():
    """Build the executable using PyInstaller"""
    print("\nBuilding executable...")
    
    # Check if icon file exists
    icon_file = "app_icon.ico"
    if os.path.exists(icon_file):
        icon_param = f"--icon={icon_file}"
        print(f"Using icon: {icon_file}")
    else:
        icon_param = "--icon=NONE"
        print("No icon file found (app_icon.ico). Using default icon.")
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--name=DLT-Viewer-SoC",
        "--onefile",
        "--windowed",
        icon_param,
        "--add-data=search_history.json;.",
        "main.py"
    ]
    
    try:
        subprocess.check_call(cmd)
        print("\n" + "="*60)
        print("BUILD SUCCESSFUL!")
        print("="*60)
        print("\nExecutable location:")
        print("  dist\\DLT-Viewer-SoC.exe")
        print("\nYou can copy this .exe file to any Windows PC")
        print("No Python installation required on target PC")
        print("="*60)
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("="*60)
    print("DLT Viewer - Executable Builder")
    print("="*60)
    
    install_pyinstaller()
    build_executable()
