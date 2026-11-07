"""
Comparación entre lo que extrajo el sistema y lo que confirmó el usuario.
Usa las mismas reglas que la evaluación en Colab: el número se compara sin espacios,
la fecha como fecha y los montos con una tolerancia de un centavo.
"""
import re
from datetime import date

CAMPOS = ["proveedor", "nro_comprobante", "fecha_emision", "total_pesos", "total_kg"]


def a_numero(v):
    """'204.367,85' -> 204367.85 ; '94,00' -> 94.0 ; None o '' -> None."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(" ", "")
    if "," in s or re.fullmatch(r"\d{1,3}(\.\d{3})+", s):   # 1.234,56 o 1.234 (miles)
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def a_fecha(v):
    if v is None or v == "":
        return None
    if isinstance(v, date):
        return v
    s = str(v).strip()
    try:
        if "-" in s:                       # 2026-09-08
            a, m, d = (int(x) for x in s.split("-"))
        else:                              # 08/09/2026 o 8/9/26
            d, m, a = (int(x) for x in s.split("/"))
            if a < 100:
                a += 2000
        return date(a, m, d)
    except (ValueError, TypeError):
        return None


def normalizar(campo, v):
    if campo in ("total_pesos", "total_kg"):
        return a_numero(v)
    if campo == "fecha_emision":
        return a_fecha(v)
    if v is None:
        return None
    s = str(v).strip().replace(" ", "").lower()
    return s or None


def iguales(campo, a, b):
    a, b = normalizar(campo, a), normalizar(campo, b)
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, float):
        return abs(a - b) < 0.01
    return a == b


def resultado(campo, extraido, confirmado):
    """'ok', 'vacio' (no lo encontró) o 'incorrecto'. None si el campo no aplica
    (no estaba en la boleta y el sistema tampoco propuso nada)."""
    e, c = normalizar(campo, extraido), normalizar(campo, confirmado)
    if c is None and e is None:
        return None
    if iguales(campo, extraido, confirmado):
        return "ok"
    return "vacio" if e is None else "incorrecto"


def correcciones(extraido, confirmado):
    """Cantidad de campos que el usuario tuvo que cambiar o completar."""
    return sum(1 for k in CAMPOS
               if resultado(k, extraido.get(k), confirmado.get(k)) in ("vacio", "incorrecto"))
