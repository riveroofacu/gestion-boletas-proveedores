"""
Detalle por producto: lee de la tabla de la boleta cuántos kilos (o cajones) vino de cada producto.

Es un agregado de la segunda iteración, aparte de las reglas evaluadas en la primera ronda
(proveedor, número, fecha y total), que no cambian. Sirve para calcular el importe cuando
la boleta no lo trae.

Cómo funciona
1. Busca los encabezados de la tabla: la columna de productos ("PRODUCTO", "Mercadería",
   "Descripción") y la de kilos ("KG", "Kilos"); si hay, también la de cantidad ("CANT").
2. Con esos dos encabezados arma los ejes de la tabla, así funciona aunque la foto esté
   torcida o girada.
3. Para cada producto conocido del proveedor que aparece escrito, toma el número de la
   columna de kilos (o de cantidad, si se cobra por cajón) que está en el mismo renglón.
"""
import math
import re
import unicodedata

ENC_PRODUCTO = ("producto", "mercaderia", "descripcion")
ENC_KILOS = ("kg", "kilos", "kilo")
ENC_CANTIDAD = ("cant", "cantidad", "unidades", "unidade")
NUMERO = re.compile(r"^\d{1,4}([.,]\d{1,3})?$")


def normal(s):
    """'POLLO N°8' -> 'pollon8' ; 'Mercadería' -> 'mercaderia'."""
    s = str(s).replace("°", "").replace("º", "")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _centro(c):
    return ((c[0] + c[2]) / 2, (c[1] + c[3]) / 2)


def _numero(t):
    t = t.strip()
    if not NUMERO.match(t):
        return None
    return float(t.replace(",", "."))


def _encabezado(textos, cajas, opciones):
    for t, c in zip(textos, cajas):
        if normal(t) in opciones:
            return c
    return None


def _producto_de(texto, productos):
    """El producto cuyo nombre coincide con el comienzo del texto (el más largo)."""
    n = normal(texto)
    if not n:
        return None
    mejor = None
    for p in productos:
        q = normal(p["producto"])
        if q and n.startswith(q) and (mejor is None or len(q) > len(normal(mejor["producto"]))):
            mejor = p
    return mejor


def detalle_por_producto(l, productos):
    """l: lectura del OCR (textos y cajas). productos: [{producto, unidad}] del proveedor.
    Devuelve [{producto, unidad, cantidad}] con cantidad > 0, sumando renglones repetidos."""
    T, C = l["textos"], l["cajas"]
    h_prod = _encabezado(T, C, ENC_PRODUCTO)
    h_kg = _encabezado(T, C, ENC_KILOS)
    if h_prod is None or h_kg is None:
        return []
    h_cant = _encabezado(T, C, ENC_CANTIDAD)

    # Ejes de la tabla: u va de la columna de productos a la de kilos; v baja por los renglones
    (px, py), (kx, ky) = _centro(h_prod), _centro(h_kg)
    largo = math.hypot(kx - px, ky - py) or 1.0
    ux, uy = (kx - px) / largo, (ky - py) / largo
    vx, vy = -uy, ux
    col = lambda c: _centro(c)[0] * ux + _centro(c)[1] * uy        # posición a lo ancho
    fila = lambda c: _centro(c)[0] * vx + _centro(c)[1] * vy       # posición a lo largo
    alto = lambda c: abs((c[2] - c[0]) * vx) + abs((c[3] - c[1]) * vy)   # alto del texto
    # v tiene que apuntar hacia los renglones de la tabla (debajo del encabezado): se elige
    # el sentido donde hay más números en la columna de kilos
    cerca_kg = [c for t, c in zip(T, C) if _numero(t) is not None and abs(col(c) - col(h_kg)) <= alto(h_kg) * 3]
    if sum(fila(c) < fila(h_kg) for c in cerca_kg) > sum(fila(c) > fila(h_kg) for c in cerca_kg):
        vx, vy = -vx, -vy

    renglon = sorted(alto(c) for c in C)[len(C) // 2]               # alto típico de un renglón
    ancho_col = max(abs((h_kg[2] - h_kg[0]) * ux) + abs((h_kg[3] - h_kg[1]) * uy), renglon) * 1.5

    def columna(h):
        return [(c, _numero(t)) for t, c in zip(T, C)
                if _numero(t) is not None and abs(col(c) - col(h)) <= ancho_col and fila(c) > fila(h)]

    numeros_kg = columna(h_kg)
    numeros_cant = columna(h_cant) if h_cant is not None else []

    total = {}
    for t, c in zip(T, C):
        p = _producto_de(t, productos)
        if p is None or fila(c) <= fila(h_prod):
            continue
        candidatos = numeros_cant if (p["unidad"] != "kg" and numeros_cant) else numeros_kg
        cerca = [(abs(fila(cc) - fila(c)), v) for cc, v in candidatos]
        cerca = [x for x in cerca if x[0] <= renglon * 0.7]
        if not cerca:
            continue
        valor = min(cerca)[1]
        if valor > 0:
            total[p["producto"]] = total.get(p["producto"], 0) + valor
    unidades = {p["producto"]: p["unidad"] for p in productos}
    return [{"producto": k, "unidad": unidades[k], "cantidad": round(v, 3)} for k, v in total.items()]
