"""
Base de datos SQLite del sistema: comprobantes, precios por kilo, pagos y cheques.

La deuda se lleva por comprobante. Cada pago se asigna a los comprobantes que el usuario
elige; si el monto no alcanza, el último queda con pago parcial, y si sobra, queda como
saldo a favor que se usa en los próximos pagos de ese proveedor.

Las fechas se guardan como texto AAAA-MM-DD.
"""
import json
import sqlite3
from datetime import date, datetime, timedelta

TABLAS = """
CREATE TABLE IF NOT EXISTS precios (
    id            INTEGER PRIMARY KEY,
    proveedor     TEXT NOT NULL,
    producto      TEXT NOT NULL,
    precio_kg     REAL NOT NULL,
    vigente_desde TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS comprobantes (
    id                INTEGER PRIMARY KEY,
    proveedor         TEXT NOT NULL,
    nro               TEXT,
    fecha             TEXT NOT NULL,
    total_kg          REAL,
    producto          TEXT,
    precio_kg         REAL,
    importe           REAL NOT NULL,
    saldo_anterior    REAL,
    foto              TEXT,
    extraido          TEXT,      -- lo que propuso el sistema (JSON), para medir correcciones
    confirmado        TEXT,      -- lo que dice la boleta según el usuario (JSON), mismos campos
    campos_corregidos INTEGER,
    segundos_ocr      REAL,
    segundos_carga    REAL,      -- desde que se subió la foto hasta que se guardó
    creado            TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pagos (
    id          INTEGER PRIMARY KEY,
    proveedor   TEXT NOT NULL,
    medio       TEXT NOT NULL,   -- Cheque / Transferencia / Efectivo
    monto       REAL NOT NULL,
    fecha_pago  TEXT NOT NULL,
    nro_cheque  TEXT,
    fecha_cobro TEXT,
    creado      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS aplicaciones (
    pago_id        INTEGER NOT NULL REFERENCES pagos(id),
    comprobante_id INTEGER NOT NULL REFERENCES comprobantes(id),
    monto          REAL NOT NULL
);
"""

TOL = 0.005  # tolerancia para comparar montos en pesos


def conectar(ruta="datos/boletas.db"):
    con = sqlite3.connect(ruta, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.executescript(TABLAS)
    return con


def iso(d):
    return d.isoformat() if isinstance(d, (date, datetime)) else d


def _json(d):
    return json.dumps(d, ensure_ascii=False, default=str) if d else None


def ahora():
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Precios
# ---------------------------------------------------------------------------
def guardar_precio(con, proveedor, producto, precio_kg, vigente_desde):
    con.execute("INSERT INTO precios (proveedor, producto, precio_kg, vigente_desde) VALUES (?,?,?,?)",
                (proveedor, producto.strip(), float(precio_kg), iso(vigente_desde)))
    con.commit()


def importar_precios(con, ruta_csv):
    """Carga los precios iniciales desde un CSV, solo si la tabla todavía está vacía."""
    import csv
    import os
    if not os.path.exists(ruta_csv) or con.execute("SELECT 1 FROM precios LIMIT 1").fetchone():
        return 0
    with open(ruta_csv, encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    for r in filas:
        guardar_precio(con, r["proveedor"], r["producto"], float(r["precio_kg"]), r["vigente_desde"])
    return len(filas)


def productos(con, proveedor):
    filas = con.execute("SELECT DISTINCT producto FROM precios WHERE proveedor=? ORDER BY producto",
                        (proveedor,)).fetchall()
    return [f["producto"] for f in filas]


def precio_vigente(con, proveedor, producto, fecha):
    """Último precio cargado para ese producto con vigencia hasta la fecha del comprobante.
    Si la boleta es anterior a todos los precios cargados, se usa el más viejo que haya."""
    f = con.execute("""SELECT precio_kg FROM precios
                       WHERE proveedor=? AND producto=? AND vigente_desde<=?
                       ORDER BY vigente_desde DESC, id DESC LIMIT 1""",
                    (proveedor, producto, iso(fecha))).fetchone()
    if f is None:
        f = con.execute("""SELECT precio_kg FROM precios WHERE proveedor=? AND producto=?
                           ORDER BY vigente_desde, id LIMIT 1""", (proveedor, producto)).fetchone()
    return f["precio_kg"] if f else None


def lista_precios(con):
    return [dict(f) for f in con.execute(
        "SELECT proveedor, producto, precio_kg, vigente_desde FROM precios ORDER BY proveedor, producto, vigente_desde")]


# ---------------------------------------------------------------------------
# Comprobantes
# ---------------------------------------------------------------------------
def existe_comprobante(con, proveedor, nro):
    if not nro:
        return False
    return con.execute("SELECT 1 FROM comprobantes WHERE proveedor=? AND nro=?",
                       (proveedor, nro)).fetchone() is not None


def guardar_comprobante(con, proveedor, nro, fecha, importe, total_kg=None, producto=None,
                        precio_kg=None, saldo_anterior=None, foto=None, extraido=None,
                        confirmado=None, campos_corregidos=None, segundos_ocr=None, segundos_carga=None):
    cur = con.execute(
        """INSERT INTO comprobantes (proveedor, nro, fecha, total_kg, producto, precio_kg, importe,
               saldo_anterior, foto, extraido, confirmado, campos_corregidos, segundos_ocr, segundos_carga, creado)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (proveedor, nro or None, iso(fecha), total_kg, producto, precio_kg, float(importe),
         saldo_anterior, foto, _json(extraido), _json(confirmado),
         campos_corregidos, segundos_ocr, segundos_carga, ahora()))
    con.commit()
    return cur.lastrowid


def comprobantes(con, proveedor=None):
    sql = """SELECT c.*, COALESCE((SELECT SUM(a.monto) FROM aplicaciones a WHERE a.comprobante_id=c.id), 0) AS pagado
             FROM comprobantes c"""
    params = ()
    if proveedor:
        sql += " WHERE c.proveedor=?"
        params = (proveedor,)
    sql += " ORDER BY c.fecha, c.id"
    filas = []
    for f in con.execute(sql, params):
        d = dict(f)
        d["saldo"] = round(d["importe"] - d["pagado"], 2)
        d["estado"] = "Pagado" if d["saldo"] <= TOL else ("Parcial" if d["pagado"] > TOL else "Pendiente")
        filas.append(d)
    return filas


def borrar_comprobante(con, cid):
    """Solo si no tiene pagos asignados (para corregir una carga equivocada)."""
    if con.execute("SELECT 1 FROM aplicaciones WHERE comprobante_id=?", (cid,)).fetchone():
        return False
    con.execute("DELETE FROM comprobantes WHERE id=?", (cid,))
    con.commit()
    return True


def pendientes(con, proveedor):
    return [c for c in comprobantes(con, proveedor) if c["saldo"] > TOL]


# ---------------------------------------------------------------------------
# Pagos
# ---------------------------------------------------------------------------
def _disponible_por_pago(con, proveedor):
    """Pagos anteriores de ese proveedor que todavía tienen plata sin asignar (saldo a favor)."""
    filas = con.execute(
        """SELECT p.id, p.monto - COALESCE((SELECT SUM(a.monto) FROM aplicaciones a WHERE a.pago_id=p.id), 0) AS libre
           FROM pagos p WHERE p.proveedor=? ORDER BY p.fecha_pago, p.id""", (proveedor,)).fetchall()
    return [[f["id"], f["libre"]] for f in filas if f["libre"] > TOL]


def saldo_a_favor(con, proveedor):
    return round(sum(libre for _, libre in _disponible_por_pago(con, proveedor)), 2)


def registrar_pago(con, proveedor, medio, monto, fecha_pago, ids_comprobantes,
                   nro_cheque=None, fecha_cobro=None):
    """Guarda el pago y lo asigna a los comprobantes elegidos, en el orden recibido.
    Primero se usa el saldo a favor que hubiera de pagos anteriores."""
    cur = con.execute(
        """INSERT INTO pagos (proveedor, medio, monto, fecha_pago, nro_cheque, fecha_cobro, creado)
           VALUES (?,?,?,?,?,?,?)""",
        (proveedor, medio, float(monto), iso(fecha_pago), nro_cheque or None, iso(fecha_cobro), ahora()))
    _asignar(con, proveedor, ids_comprobantes)
    con.commit()
    return cur.lastrowid


def usar_saldo_a_favor(con, proveedor, ids_comprobantes):
    """Cancela comprobantes con plata que sobró de pagos anteriores, sin registrar un pago nuevo."""
    _asignar(con, proveedor, ids_comprobantes)
    con.commit()


def _asignar(con, proveedor, ids_comprobantes):
    fondos = _disponible_por_pago(con, proveedor)   # el pago más nuevo queda al final
    saldos = {c["id"]: c["saldo"] for c in pendientes(con, proveedor)}
    for cid in ids_comprobantes:
        falta = saldos.get(cid, 0)
        while falta > TOL and fondos:
            pago_id, libre = fondos[0]
            usar = min(falta, libre)
            con.execute("INSERT INTO aplicaciones (pago_id, comprobante_id, monto) VALUES (?,?,?)",
                        (pago_id, cid, round(usar, 2)))
            falta -= usar
            fondos[0][1] -= usar
            if fondos[0][1] <= TOL:
                fondos.pop(0)


def pagos(con):
    filas = con.execute(
        """SELECT p.*, COALESCE((SELECT SUM(a.monto) FROM aplicaciones a WHERE a.pago_id=p.id), 0) AS asignado
           FROM pagos p ORDER BY p.fecha_pago DESC, p.id DESC""").fetchall()
    return [dict(f) for f in filas]


def cheques(con, desde=None, hasta=None):
    sql = "SELECT * FROM pagos WHERE medio='Cheque'"
    params = []
    if desde:
        sql += " AND fecha_cobro>=?"
        params.append(iso(desde))
    if hasta:
        sql += " AND fecha_cobro<=?"
        params.append(iso(hasta))
    sql += " ORDER BY fecha_cobro"
    return [dict(f) for f in con.execute(sql, params)]


def cheques_proximos(con, dias, hoy=None):
    hoy = hoy or date.today()
    return cheques(con, hoy, hoy + timedelta(days=dias))


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------
def deuda_por_proveedor(con):
    deuda = {}
    for c in comprobantes(con):
        if c["saldo"] > TOL:
            d = deuda.setdefault(c["proveedor"], {"proveedor": c["proveedor"], "comprobantes": 0,
                                                  "deuda": 0.0, "a_favor": 0.0})
            d["comprobantes"] += 1
            d["deuda"] += c["saldo"]
    provs = {f["proveedor"] for f in con.execute("SELECT DISTINCT proveedor FROM pagos")}
    for p in provs:
        favor = saldo_a_favor(con, p)
        if favor > TOL:
            d = deuda.setdefault(p, {"proveedor": p, "comprobantes": 0, "deuda": 0.0, "a_favor": 0.0})
            d["deuda"] -= favor
            d["a_favor"] = favor
    return sorted(deuda.values(), key=lambda d: -d["deuda"])


def gastos_por_mes(con):
    return [dict(f) for f in con.execute(
        """SELECT substr(fecha, 1, 7) AS mes, proveedor, SUM(importe) AS total
           FROM comprobantes GROUP BY mes, proveedor ORDER BY mes""")]
