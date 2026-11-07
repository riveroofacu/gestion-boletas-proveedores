"""Muestra la dirección para entrar desde el celular (mismo wifi que la compu)."""
import socket

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))   # no manda nada, solo averigua qué red usa la compu
    ip = s.getsockname()[0]
    s.close()
    print("\n  En esta compu:      http://localhost:8501")
    print(f"  Desde el celular:   http://{ip}:8501\n")
except OSError:
    print("\n  No se pudo averiguar la IP. En esta compu entrá a http://localhost:8501\n")
