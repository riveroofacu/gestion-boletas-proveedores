"""
Extracción de datos de comprobantes con OCR más reglas (versión 2, congelada el 6/11/2026).

Flujo:
  foto -> achicar a 2000 px -> PaddleOCR (texto + posición) -> identificar proveedor
       -> reglas del formato de ese proveedor -> normalizar -> validar

Las reglas se definen por FORMATO de comprobante, no por proveedor. Qué proveedor usa
qué formato, y con qué palabras se lo reconoce, está en config/proveedores.json, que no
se sube al repositorio (ver config/proveedores.ejemplo.json).
"""
import difflib
import glob
import json
import os
import re
import time
from datetime import date

import cv2

# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------
_ocr = None
_sin_onednn = False
# Configuración evaluada: foto a 2000 px y clasificador de orientación de renglones activado.
AJUSTE = {"lado_max": 2000, "orientacion_renglones": True}


def configurar(lado_max=None, orientacion_renglones=None):
    """Permite cambiar el tamaño de la foto y la orientación de renglones (para ganar velocidad)."""
    global _ocr
    if lado_max:
        AJUSTE["lado_max"] = int(lado_max)
    if orientacion_renglones is not None and bool(orientacion_renglones) != AJUSTE["orientacion_renglones"]:
        AJUSTE["orientacion_renglones"] = bool(orientacion_renglones)
        _ocr = None


def obtener_ocr():
    """Carga PaddleOCR una sola vez (tarda unos segundos la primera vez)."""
    global _ocr
    if _ocr is None:
        from paddleocr import PaddleOCR
        extra = {"enable_mkldnn": False} if _sin_onednn else {}
        _ocr = PaddleOCR(lang="es", use_doc_orientation_classify=False, use_doc_unwarping=False,
                         use_textline_orientation=AJUSTE["orientacion_renglones"], **extra)
    return _ocr


def _predecir(ruta):
    """Algunas versiones de PaddlePaddle para CPU (3.3.x) fallan con la aceleración oneDNN.
    Si pasa eso, se vuelve a cargar el OCR sin oneDNN (más lento, pero funciona)."""
    global _ocr, _sin_onednn
    try:
        return list(obtener_ocr().predict(ruta))
    except NotImplementedError as e:
        if _sin_onednn or "ConvertPirAttribute" not in str(e):
            raise
        print("Aviso: PaddlePaddle falló con oneDNN; se reintenta sin oneDNN (más lento).")
        _sin_onednn, _ocr = True, None
        return list(obtener_ocr().predict(ruta))


def achicar(ruta, salida, lado_max=2000):
    """Reduce la foto para que su lado más largo mida lado_max píxeles."""
    img = cv2.imread(ruta)
    if img is None:
        raise ValueError("No se pudo abrir la imagen")
    alto, ancho = img.shape[:2]
    escala = lado_max / max(alto, ancho)
    if escala < 1:
        img = cv2.resize(img, (int(ancho * escala), int(alto * escala)),
                         interpolation=cv2.INTER_AREA)
    cv2.imwrite(salida, img)
    return salida


def leer_foto(ruta, carpeta_tmp="tmp_ocr"):
    """Corre el OCR y devuelve {'textos', 'cajas', 'segundos'}. Cada caja es [x1, y1, x2, y2]."""
    os.makedirs(carpeta_tmp, exist_ok=True)
    inicio = time.time()
    chica = achicar(ruta, os.path.join(carpeta_tmp, "chica_" + os.path.basename(ruta)), AJUSTE["lado_max"])
    textos, cajas = [], []
    for res in _predecir(chica):
        res.save_to_json(carpeta_tmp)
        nombre = os.path.splitext(os.path.basename(chica))[0]
        archivo = sorted(glob.glob(os.path.join(carpeta_tmp, f"{nombre}*.json")))[-1]
        with open(archivo, encoding="utf-8") as f:
            datos = json.load(f)
        datos = datos.get("res", datos)
        textos = datos["rec_texts"]
        if "rec_boxes" in datos:
            cajas = [list(map(float, b)) for b in datos["rec_boxes"]]
        else:
            for p in datos["rec_polys"]:
                xs = [pt[0] for pt in p]
                ys = [pt[1] for pt in p]
                cajas.append([min(xs), min(ys), max(xs), max(ys)])
    return {"textos": textos, "cajas": cajas, "segundos": time.time() - inicio}


# ---------------------------------------------------------------------------
# Patrones
# ---------------------------------------------------------------------------
NUMERO       = re.compile(r"\d{4}-\d{8}")                                  # 0015-00136530
FECHA_SOLA   = re.compile(r"(?<!\d)(\d{2}/\d{2}/\d{4})(?!\d)")              # 08/09/2026 sin hora pegada
FECHA_FLEX   = re.compile(r"(?<!\d)(\d{1,2})/(\d{1,2})/(\d{4}|\d{2})(?!\d)")  # 2/9/2026, 23/09/26
KILOS        = re.compile(r"\d+[.,]\d{2}")
KILOS_V2     = re.compile(r"(?<![\d.,])\d+(?:[.,]\d{1,2})?(?![\d.,])")      # 5, 27,6, 94,00
IMPORTE      = re.compile(r"\d{1,3}(?:\.\d{3})+,\d{2}|\d+,\d{2}")
IMPORTE_V2   = re.compile(r"\d{1,3}(?:\.\d{3})+,\d{2}|\d+,\d{2}|\d+\.\d{2}(?!\d)")
NRO_CORTO    = re.compile(r"(?<![\d.,])\d{4,6}(?![\d.,])")
NRO_GENERICO = re.compile(r"(?<![\d.,/-])\d{1,8}(?![\d.,/-])")
NUM_MANO     = re.compile(r"\d[\d.,]*\d|\d")


# ---------------------------------------------------------------------------
# Funciones de apoyo
# ---------------------------------------------------------------------------
def sin_espacios(s):
    return s.lower().replace(" ", "")


def a_numero(v):
    """'$217.500,00' -> 217500.0 ; '94,00' -> 94.0 ; '67.650' -> 67650.0 ; '775200.00' -> 775200.0"""
    if v is None or str(v).strip() == "":
        return None
    v = str(v).replace("$", "").replace(" ", "").strip()
    if "," in v:
        v = v.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", v):
        v = v.replace(".", "")
    return float(v)


def primero(textos, patron):
    for t in textos:
        m = patron.search(t)
        if m:
            return m.group()
    return None


def valor_despues(textos, etiqueta, patron, ventana=3):
    """Valor con ese patrón en el mismo texto que la etiqueta o en los renglones siguientes."""
    for i, t in enumerate(textos):
        if etiqueta in t.lower():
            for candidato in [t] + textos[i + 1: i + 1 + ventana]:
                m = patron.search(candidato)
                if m:
                    return m.group()
    return None


def valor_cerca(l, etiqueta, patron, direccion="derecha"):
    """Busca la etiqueta (sin espacios ni mayúsculas) y devuelve el valor más cercano con ese
    patrón: primero en el mismo texto, si no a la derecha en el mismo renglón o justo debajo."""
    T, C = l["textos"], l["cajas"]
    e = sin_espacios(etiqueta)
    for i, t in enumerate(T):
        compacto = sin_espacios(t)
        if e not in compacto:
            continue
        m = patron.search(compacto[compacto.index(e) + len(e):])
        if m:
            return m.group()
        x1, y1, x2, y2 = C[i]
        alto = y2 - y1
        centro = (y1 + y2) / 2
        candidatos = []
        for j, (u, (a1, b1, a2, b2)) in enumerate(zip(T, C)):
            m = patron.search(u)
            if j == i or not m:
                continue
            if direccion == "derecha" and abs((b1 + b2) / 2 - centro) < 0.7 * alto and a1 > x1:
                candidatos.append((a1 - x2, m.group()))
            if (direccion == "abajo" and b1 > centro and b1 - y2 < 3 * alto
                    and a2 > x1 - alto and a1 < x2 + 2 * alto):
                candidatos.append((b1 - y2, m.group()))
        if candidatos:
            return min(candidatos)[1]
    return None


def fecha_normal(valor):
    """'5/10/2026' -> '05/10/2026' ; '23/09/26' -> '23/09/2026'"""
    if valor is None:
        return None
    m = FECHA_FLEX.search(valor)
    if not m:
        return None
    d, mes, a = m.groups()
    if len(a) == 2:
        a = "20" + a
    return f"{int(d):02d}/{int(mes):02d}/{a}"


def fecha_flexible(l, etiqueta="fecha"):
    v = valor_cerca(l, etiqueta, FECHA_FLEX, "derecha") or primero(l["textos"], FECHA_FLEX)
    return fecha_normal(v)


def fecha_despues_del_numero(textos):
    for i, t in enumerate(textos):
        if NUMERO.search(t):
            for siguiente in textos[i + 1:]:
                m = FECHA_SOLA.search(siguiente)
                if m:
                    return m.group(1)
    return None


DIAS_ATRAS, DIAS_ADELANTE = 90, 7   # una boleta se carga, como mucho, unos meses después de llegar


def fecha_razonable(f, hoy=None):
    hoy = hoy or date.today()
    return -DIAS_ADELANTE <= (hoy - f).days <= DIAS_ATRAS


def fecha_casillas(l, etiqueta="fecha", hoy=None):
    """Fecha manuscrita en casillas debajo de FECHA. Prueba primero la lectura directa y, si no da
    una fecha razonable (cercana a hoy), prueba cortar los dígitos de otras formas. Si nada da una
    fecha razonable, devuelve None: mejor un campo vacío que una fecha inventada."""
    f = _fecha_casillas(l, etiqueta, hoy)
    if f:
        d, m, a = map(int, f.split("/"))
        if fecha_razonable(date(a, m, d), hoy):
            return f
    return None


def _fecha_casillas(l, etiqueta="fecha", hoy=None):
    """Junta los números de las casillas debajo de FECHA, de izquierda a derecha."""
    T, C = l["textos"], l["cajas"]
    for i, t in enumerate(T):
        if etiqueta not in sin_espacios(t) or len(t) > 12:
            continue
        x1, y1, x2, y2 = C[i]
        alto, ancho = y2 - y1, x2 - x1
        piezas = []
        for j, (u, (a1, b1, a2, b2)) in enumerate(zip(T, C)):
            if (j != i and b1 > y1 and b1 - y2 < 4 * alto
                    and a2 > x1 - 2 * ancho and a1 < x2 + 2 * ancho):
                piezas.append((a1, u))
        numeros = re.findall(r"\d+", " ".join(u for _, u in sorted(piezas)))
        crudos = list(numeros)
        if len(numeros) == 2 and len(numeros[1]) == 4:
            numeros = [numeros[0], numeros[1][:2], numeros[1][2:]]
        elif len(numeros) == 2 and len(numeros[0]) == 4:
            numeros = [numeros[0][:2], numeros[0][2:], numeros[1]]
        if len(numeros) >= 3:
            d, m, a = numeros[0], numeros[1], numeros[2]
            if len(a) == 2:
                a = "20" + a
            if 1 <= int(d) <= 31 and 1 <= int(m) <= 12:
                try:
                    if fecha_razonable(date(int(a), int(m), int(d)), hoy):
                        return f"{int(d):02d}/{int(m):02d}/{a}"
                except ValueError:
                    pass
        # Agregado el 13/11/2026, después de la prueba en el local: con el día de un dígito
        # (5/11/26) el OCR junta casillas ("511") y lo de arriba no sabe separarlas.
        fecha = fecha_por_cortes(crudos, hoy)
        if fecha:
            return fecha
    return None


def fecha_por_cortes(numeros, hoy=None):
    """Prueba todas las formas de cortar los dígitos en día, mes y año (de 2 o 4 cifras),
    respetando dónde el OCR ya separó, y se queda con la fecha razonable más cercana a hoy.
    Devuelve dd/mm/aaaa o None."""
    hoy = hoy or date.today()
    digitos = "".join(numeros)
    cortes_ocr = set()
    pos = 0
    for n in numeros[:-1]:
        pos += len(n)
        cortes_ocr.add(pos)
    candidatas = set()
    for ld in (1, 2):
        for lm in (1, 2):
            for la in (2, 4):
                if ld + lm + la != len(digitos):
                    continue
                # un corte del OCR no puede caer en el medio del día, el mes o el año
                if any(c not in (ld, ld + lm) for c in cortes_ocr):
                    continue
                d, m, a = int(digitos[:ld]), int(digitos[ld:ld + lm]), digitos[ld + lm:]
                anio = int(a) + 2000 if la == 2 else int(a)
                try:
                    f = date(anio, m, d)
                except ValueError:
                    continue
                if fecha_razonable(f, hoy):
                    candidatas.add(f)
    if not candidatas:
        return None
    f = min(candidatas, key=lambda x: abs((hoy - x).days))
    return f.strftime("%d/%m/%Y")


def total_mano(l):
    for etiqueta in ("total$", "totals"):
        v = valor_cerca(l, etiqueta, NUM_MANO, "derecha")
        if v:
            return re.sub(r"\D", "", v)
    return None


# ---------------------------------------------------------------------------
# Reglas por formato de comprobante
# ---------------------------------------------------------------------------
def formato_remito_carnico(l):
    """Remito electrónico cárnico con el orden de lectura conocido (proveedor fijo)."""
    T = l["textos"]
    return {"nro_comprobante": valor_despues(T, "número", NUMERO) or primero(T, NUMERO),
            "fecha_emision":   fecha_despues_del_numero(T) or fecha_flexible(l, "fecha emis"),
            "total_pesos":     None,
            "total_kg":        valor_despues(T, "total kilos", KILOS)
                               or valor_cerca(l, "total kilos", KILOS_V2, "derecha")}


def formato_remito_carnico_generico(l):
    T = l["textos"]
    return {"nro_comprobante": valor_cerca(l, "número", NUMERO, "derecha") or primero(T, NUMERO),
            "fecha_emision":   fecha_flexible(l, "fecha emis"),
            "total_pesos":     None,
            "total_kg":        valor_cerca(l, "total kilos", KILOS_V2, "derecha")}


def formato_remito_con_saldo(l):
    """Remito con precios, SUB TOTAL con IVA y saldo anterior (cuenta corriente)."""
    return {"nro_comprobante": primero(l["textos"], NUMERO),
            "fecha_emision":   fecha_flexible(l, "fecha"),
            "total_pesos":     valor_cerca(l, "sub total", IMPORTE, "abajo"),
            "saldo_anterior":  valor_cerca(l, "saldo anterior", IMPORTE, "derecha"),
            "total_kg":        None}


def formato_presupuesto(l):
    return {"nro_comprobante": valor_cerca(l, "presupuesto", NRO_CORTO, "derecha"),
            "fecha_emision":   fecha_flexible(l, "fecha"),
            "total_pesos":     valor_cerca(l, "total neto", IMPORTE, "derecha"),
            "total_kg":        None}


def formato_planilla_kilos(l):
    return {"nro_comprobante": None,
            "fecha_emision":   fecha_flexible(l, "fecha"),
            "total_pesos":     None,
            "total_kg":        valor_cerca(l, "total kg", KILOS_V2, "derecha")}


def formato_nota_manuscrita(l):
    return {"nro_comprobante": None,
            "fecha_emision":   fecha_casillas(l),
            "total_pesos":     total_mano(l),
            "total_kg":        valor_cerca(l, "total kilos", KILOS_V2, "derecha")}


def formato_remito_generico(l):
    """Para proveedores sin reglas propias: número, primera fecha y el importe más grande."""
    T = l["textos"]
    nro = primero(T, NUMERO)
    if nro is None:
        for et in ("remito", "nro", "número", "numero", "n°"):
            nro = valor_cerca(l, et, NRO_GENERICO, "derecha")
            if nro:
                break
    importes = [m.group() for t in T for m in IMPORTE_V2.finditer(t)]
    return {"nro_comprobante": nro,
            "fecha_emision":   fecha_flexible(l, "fecha"),
            "total_pesos":     max(importes, key=a_numero) if importes else None,
            "total_kg":        valor_cerca(l, "total kilos", KILOS_V2, "derecha")
                               or valor_cerca(l, "total kg", KILOS_V2, "derecha")}


FORMATOS = {
    "remito_carnico":          formato_remito_carnico,
    "remito_carnico_generico": formato_remito_carnico_generico,
    "remito_con_saldo":        formato_remito_con_saldo,
    "presupuesto":             formato_presupuesto,
    "planilla_kilos":          formato_planilla_kilos,
    "nota_manuscrita":         formato_nota_manuscrita,
    "remito_generico":         formato_remito_generico,
}


# ---------------------------------------------------------------------------
# Identificación del proveedor (configurable)
# ---------------------------------------------------------------------------
def cargar_proveedores(ruta="config/proveedores.json"):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)["proveedores"]


def identificar_proveedor(textos, proveedores):
    """1) palabras clave exactas, en el orden de la configuración;
       2) pares de palabras que pueden venir en renglones separados ("Nota de" + "Pedido");
       3) nombres de una palabra aunque el OCR cambie alguna letra ("Menuaencias")."""
    todo = sin_espacios(" ".join(textos))
    for p in proveedores:
        if any(c in todo for c in p.get("palabras_clave", [])):
            return p["nombre"]
    for p in proveedores:
        for par in p.get("pares", []):
            if all(x in todo for x in par):
                return p["nombre"]
    parecidas = {w: p["nombre"] for p in proveedores for w in p.get("parecidas", [])}
    for palabra in re.findall(r"[a-záéíóúñ]+", " ".join(textos).lower()):
        m = difflib.get_close_matches(palabra, parecidas.keys(), n=1, cutoff=0.85)
        if m:
            return parecidas[m[0]]
    return None


def extraer(l, proveedores):
    """Identifica el proveedor y aplica la regla de su formato. Si no lo reconoce,
    igual sugiere datos con la regla genérica."""
    nombre = identificar_proveedor(l["textos"], proveedores)
    formato = next((p["formato"] for p in proveedores if p["nombre"] == nombre), "remito_generico")
    datos = FORMATOS[formato](l)
    datos.setdefault("saldo_anterior", None)
    datos["proveedor"] = nombre
    return datos


# ---------------------------------------------------------------------------
# Validaciones (avisos para el usuario, no bloquean)
# ---------------------------------------------------------------------------
def a_fecha(texto):
    """'08/09/2026' -> date(2026, 9, 8) o None si no es válida."""
    try:
        d, m, a = (int(x) for x in str(texto).split("/"))
        return date(a, m, d)
    except (ValueError, TypeError):
        return None


def validar(datos, hoy=None):
    hoy = hoy or date.today()
    avisos = []
    if not datos.get("proveedor"):
        avisos.append("No se reconoció el proveedor. Elegilo de la lista.")
    f = a_fecha(datos.get("fecha_emision"))
    if f is None:
        avisos.append("No se encontró una fecha válida.")
    elif f > hoy:
        avisos.append("La fecha es posterior a hoy. Revisala.")
    elif (hoy - f).days > 180:
        avisos.append("La fecha tiene más de 6 meses. Revisala.")
    if datos.get("total_pesos") is None and datos.get("total_kg") is None:
        avisos.append("No se encontró ni el importe ni los kilos.")
    return avisos
