@echo off
rem ==============================================================
rem  Five - instalacion. Instala las 3 librerias que Five necesita.
rem  (Solo usa internet aqui, para descargar las librerias.)
rem ==============================================================
cd /d "%~dp0"
title Five - instalacion
echo.
echo   Instalando Five...
echo.

call :findpython
if not defined PY (
    echo   No encontre Python en este computador. Intentando instalarlo con winget...
    winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
    set "PATH=%LOCALAPPDATA%\Programs\Python\Launcher;%LOCALAPPDATA%\Programs\Python\Python312;%PATH%"
    call :findpython
)
if not defined PY (
    echo.
    echo   ERROR: no pude encontrar ni instalar Python.
    echo   1. Abre https://www.python.org/downloads/ y descarga Python.
    echo   2. Al instalar, marca la casilla "Add python.exe to PATH".
    echo   3. Vuelve a hacer doble clic en run.bat
    echo.
    pause
    exit /b 1
)

echo   Python encontrado. Descargando librerias: pynput, pystray, pillow...
%PY% -m pip install --user --disable-pip-version-check --upgrade pynput pystray pillow
if errorlevel 1 (
    echo.
    echo   ERROR: no se pudieron instalar las librerias. Revisa tu conexion a internet
    echo   y vuelve a intentarlo.
    pause
    exit /b 1
)

echo.
echo   Instalacion completa.
if /i not "%~1"=="auto" pause
exit /b 0

:findpython
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3" && exit /b 0
python --version >nul 2>&1 && set "PY=python" && exit /b 0
exit /b 0
