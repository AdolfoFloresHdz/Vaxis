@echo off
echo.
echo  =========================================
echo    VAXIS — Instalador automatico
echo  =========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python no esta instalado.
    echo  Descargalo en: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo  Instalando dependencias...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo  ERROR: Algo fallo durante la instalacion.
    echo  Intenta correr como Administrador.
    pause
    exit /b 1
)

echo.
echo  Todo listo!
echo  Ahora corre: python vaxis.py
echo.
pause
