@echo off
rem ==============================================================
rem  Five - el UNICO archivo que necesitas abrir.
rem  Si falta algo, instala todo primero (setup.bat) y luego abre Five.
rem ==============================================================
cd /d "%~dp0"
title Five

call :findpython
if not defined PY goto setup
%PY% -c "import pynput, pystray, PIL" >nul 2>&1 || goto setup
goto launch

:setup
call "%~dp0setup.bat" auto || exit /b 1
set "PATH=%LOCALAPPDATA%\Programs\Python\Launcher;%LOCALAPPDATA%\Programs\Python\Python312;%PATH%"
call :findpython

:launch
rem pythonw.exe runs Five without a black console window
for /f "delims=" %%i in ('%PY% -c "import sys; print(sys.executable)"') do set "PYEXE=%%i"
set "PYW=%PYEXE:python.exe=pythonw.exe%"
if not exist "%PYW%" set "PYW=%PYEXE%"
start "" "%PYW%" "%~dp0five.py"

echo.
echo   Five esta corriendo (busca el icono "5" junto al reloj).
echo   Presiona Ctrl+Alt+5 en cualquier momento.
echo.
echo   Esta ventana se cierra sola...
timeout /t 6 >nul
exit /b 0

:findpython
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3" && exit /b 0
python --version >nul 2>&1 && set "PY=python" && exit /b 0
exit /b 0
