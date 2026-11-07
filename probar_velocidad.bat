@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
if not exist fotos_prueba mkdir fotos_prueba
python probar_velocidad.py
echo.
echo El resultado quedo guardado en resultado_velocidad.txt
pause
