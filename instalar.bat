@echo off
cd /d "%~dp0"
echo Instalando el sistema de boletas. Puede tardar varios minutos.
echo.
if not exist .venv (
    py -3.12 -m venv .venv 2>nul || python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install paddlepaddle==3.2.2 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
python -m pip install -r requirements.txt
if not exist config\proveedores.json copy config\proveedores.ejemplo.json config\proveedores.json
if not exist config\ajustes.json copy config\ajustes.ejemplo.json config\ajustes.json
if not exist datos mkdir datos
echo.
echo Listo. Ahora completa config\ajustes.json y abri iniciar.bat
pause
