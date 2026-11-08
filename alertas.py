"""
Avisos por Telegram: cheques que se cobran en los próximos días y deuda por proveedor.

Uso
  python alertas.py            manda el aviso del día (una sola vez por día)
  python alertas.py --forzar   lo manda aunque ya se haya mandado hoy
  python alertas.py --chat-id  muestra el chat_id de quien le escribió al bot (para configurarlo)
  python alertas.py --esperar  queda abierto y manda el aviso todos los días a la hora_aviso
                               de config/ajustes.json (8 por defecto); lo usa iniciar.bat

El token del bot y el chat_id van en config/ajustes.json (no se sube al repositorio).
"""
import json
import os
import sys
import time
from datetime import date, datetime

import requests

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "src"))
import db  # noqa: E402

RUTA_AJUSTES = os.path.join(BASE, "config", "ajustes.json")
RUTA_DB = os.path.join(BASE, "datos", "boletas.db")
RUTA_ULTIMO = os.path.join(BASE, "datos", "ultimo_aviso.txt")


def cargar_ajustes():
    if not os.path.exists(RUTA_AJUSTES):
        return {}
    with open(RUTA_AJUSTES, encoding="utf-8") as f:
        return json.load(f)


def pesos(x):
    return "$ " + f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def dd_mm(iso):
    a, m, d = iso.split("-")
    return f"{d}/{m}"


def armar_mensaje(con, dias=7, hoy=None):
    hoy = hoy or date.today()
    renglones = [f"Boletas - aviso del {hoy.strftime('%d/%m/%Y')}", ""]
    proximos = db.cheques_proximos(con, dias, hoy)
    if proximos:
        renglones.append(f"Cheques que se cobran en los próximos {dias} días")
        for c in proximos:
            nro = f" (Nº {c['nro_cheque']})" if c["nro_cheque"] else ""
            renglones.append(f"• {dd_mm(c['fecha_cobro'])} {c['proveedor']} {pesos(c['monto'])}{nro}")
        renglones.append(f"Total {pesos(sum(c['monto'] for c in proximos))}")
    else:
        renglones.append(f"No hay cheques para cobrar en los próximos {dias} días.")
    deuda = [d for d in db.deuda_por_proveedor(con) if abs(d["deuda"]) > db.TOL]
    if deuda:
        renglones += ["", "Deuda por proveedor"]
        for d in deuda:
            renglones.append(f"• {d['proveedor']} {pesos(d['deuda'])}")
        renglones.append(f"Total {pesos(sum(d['deuda'] for d in deuda))}")
    return "\n".join(renglones)


def enviar(token, chat_id, texto):
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      data={"chat_id": chat_id, "text": texto}, timeout=20)
    r.raise_for_status()


def mostrar_chat_id(token):
    r = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=20)
    r.raise_for_status()
    vistos = {}
    for u in r.json().get("result", []):
        msg = u.get("message") or u.get("edited_message") or {}
        chat = msg.get("chat", {})
        if chat:
            vistos[chat["id"]] = chat.get("first_name") or chat.get("title") or ""
    if not vistos:
        print("No hay mensajes. Mandale cualquier mensaje al bot desde Telegram y volvé a correr esto.")
    for cid, nombre in vistos.items():
        print(f"chat_id {cid}  ({nombre})")


def esperar():
    """Revisa cada 10 minutos y manda el aviso una vez por día, desde la hora_aviso."""
    print("Avisos de Telegram activos. Se mandan una vez por día.")
    while True:
        hora = int(cargar_ajustes().get("hora_aviso", 8))
        if datetime.now().hour >= hora:
            try:
                main(silencioso=True)
            except Exception as e:   # un error (sin internet, etc.) no corta la espera
                print(datetime.now().strftime("%d/%m %H:%M"), "No se pudo mandar el aviso:", e)
        time.sleep(600)


def main(silencioso=False):
    aj = cargar_ajustes()
    token, chat_id = aj.get("telegram_token"), aj.get("telegram_chat_id")
    if not token:
        print("Falta telegram_token en config/ajustes.json. No se manda el aviso.")
        return
    if "--chat-id" in sys.argv:
        mostrar_chat_id(token)
        return
    if not chat_id:
        print("Falta telegram_chat_id en config/ajustes.json. Corré: python alertas.py --chat-id")
        return
    hoy = date.today().isoformat()
    if "--forzar" not in sys.argv and os.path.exists(RUTA_ULTIMO):
        with open(RUTA_ULTIMO) as f:
            if f.read().strip() == hoy:
                if not silencioso:
                    print("El aviso de hoy ya se mandó.")
                return
    os.makedirs(os.path.dirname(RUTA_DB), exist_ok=True)
    con = db.conectar(RUTA_DB)
    try:
        enviar(token, chat_id, armar_mensaje(con, int(aj.get("dias_aviso", 7))))
    except requests.RequestException as e:
        print("No se pudo mandar el aviso (¿hay internet?):", e)
        return
    with open(RUTA_ULTIMO, "w") as f:
        f.write(hoy)
    print(datetime.now().strftime("%d/%m %H:%M"), "Aviso enviado.")


if __name__ == "__main__":
    if "--esperar" in sys.argv:
        esperar()
    else:
        main()
