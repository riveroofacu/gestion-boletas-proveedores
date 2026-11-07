@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
echo Revisando avisos de Telegram...
python alertas.py
python src\ip_local.py
echo No cierres esta ventana mientras uses el sistema.
streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
pause
