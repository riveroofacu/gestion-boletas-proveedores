"""
Segunda ronda de evaluación: prueba en el local con boletas nuevas.

Compara lo que extrajo el sistema con lo que confirmó el usuario al guardar cada boleta
y calcula las mismas métricas que la primera ronda, contra los umbrales definidos.

Uso
  python evaluar_campo.py                     todas las boletas cargadas
  python evaluar_campo.py --desde 2026-11-08  solo las cargadas desde esa fecha

Deja el detalle en datos/resultados_campo.csv
"""
import csv
import json
import os
import sys
from statistics import mean

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "src"))
import comparar  # noqa: E402
import db  # noqa: E402

UMBRALES = {"proveedor": 0.95, "impresos": 0.90, "manuscritos": 0.75,
            "completos": 0.70, "correcciones": 1.0, "segundos": 60}
CAMPOS_DATO = ["nro_comprobante", "fecha_emision", "total_pesos", "total_kg"]


def formatos_manuscritos():
    ruta = os.path.join(BASE, "config", "proveedores.json")
    if not os.path.exists(ruta):
        return set()
    with open(ruta, encoding="utf-8") as f:
        provs = json.load(f)["proveedores"]
    return {p["nombre"] for p in provs if p["formato"] == "nota_manuscrita"}


def pct(a, b):
    return f"{a}/{b} ({a / b:.0%})" if b else "-"


def cumple(ok):
    return "cumple" if ok else "NO cumple"


def main():
    desde = sys.argv[sys.argv.index("--desde") + 1] if "--desde" in sys.argv else None
    con = db.conectar(os.path.join(BASE, "datos", "boletas.db"))
    sql = "SELECT * FROM comprobantes WHERE extraido IS NOT NULL AND confirmado IS NOT NULL"
    params = ()
    if desde:
        sql += " AND creado >= ?"
        params = (desde,)
    filas = [dict(f) for f in con.execute(sql + " ORDER BY id", params)]
    if not filas:
        print("No hay boletas cargadas con la app para evaluar.")
        return

    manuscritos = formatos_manuscritos()
    detalle, por_campo = [], {k: {"ok": 0, "vacio": 0, "incorrecto": 0} for k in comparar.CAMPOS}
    imp = {"ok": 0, "n": 0}
    man = {"ok": 0, "n": 0}
    completos, correcciones, seg_ocr, seg_carga = 0, [], [], []
    det = {"ok": 0, "vacio": 0, "incorrecto": 0, "boletas": 0, "boletas_ok": 0}
    for f in filas:
        ext, conf = json.loads(f["extraido"]), json.loads(f["confirmado"])
        res = {k: comparar.resultado(k, ext.get(k), conf.get(k)) for k in comparar.CAMPOS}
        for k, r in res.items():
            if r:
                por_campo[k][r] += 1
        grupo = man if conf["proveedor"] in manuscritos else imp
        for k in CAMPOS_DATO:
            if res[k]:
                grupo["n"] += 1
                grupo["ok"] += res[k] == "ok"
        if all(r in (None, "ok") for r in res.values()):
            completos += 1
        correcciones.append(comparar.correcciones(ext, conf))
        # Detalle por producto (boletas cuyo importe salió de cantidad por precio)
        confirmados = {i["producto"]: i["cantidad"] for i in db.items_de(con, f["id"])}
        if confirmados:
            leidos = {d["producto"]: d["cantidad"] for d in ext.get("detalle") or []}
            r_det = {p: ("ok" if p in leidos and abs(leidos[p] - c) < 0.05 else
                         "vacio" if p not in leidos else "incorrecto") for p, c in confirmados.items()}
            r_det.update({p: "incorrecto" for p in leidos if p not in confirmados})
            for r in r_det.values():
                det[r] += 1
            det["boletas"] += 1
            det["boletas_ok"] += all(r == "ok" for r in r_det.values())
        if f["segundos_ocr"] is not None:
            seg_ocr.append(f["segundos_ocr"])
        if f["segundos_carga"] is not None:
            seg_carga.append(f["segundos_carga"])
        detalle.append({"id": f["id"], "proveedor": conf["proveedor"], **{k: res[k] or "" for k in comparar.CAMPOS},
                        "correcciones": correcciones[-1], "segundos_ocr": f["segundos_ocr"],
                        "segundos_carga": f["segundos_carga"]})

    n = len(filas)
    print(f"Boletas evaluadas {n}\n")
    print("Por campo (ok / vacío / incorrecto)")
    for k, c in por_campo.items():
        tot = sum(c.values())
        print(f"  {k:16} {c['ok']:3} / {c['vacio']:3} / {c['incorrecto']:3}   {pct(c['ok'], tot)}")

    prov_ok = por_campo["proveedor"]["ok"]
    print("\nUmbrales")
    print(f"  Proveedor identificado     {pct(prov_ok, n):18} {cumple(prov_ok / n >= UMBRALES['proveedor'])}")
    if imp["n"]:
        print(f"  Campos impresos            {pct(imp['ok'], imp['n']):18} {cumple(imp['ok'] / imp['n'] >= UMBRALES['impresos'])}")
    if man["n"]:
        print(f"  Campos manuscritos         {pct(man['ok'], man['n']):18} {cumple(man['ok'] / man['n'] >= UMBRALES['manuscritos'])}")
    print(f"  Comprobantes completos     {pct(completos, n):18} {cumple(completos / n >= UMBRALES['completos'])}")
    print(f"  Correcciones por boleta    {mean(correcciones):<18.2f} {cumple(mean(correcciones) <= UMBRALES['correcciones'])}")
    if seg_ocr:
        print(f"  Tiempo de lectura (prom.)  {mean(seg_ocr):<18.0f} {cumple(mean(seg_ocr) <= UMBRALES['segundos'])}")
    if seg_carga:
        menos_min = sum(s < 60 for s in seg_carga)
        print(f"  Tiempo de carga (prom.)    {mean(seg_carga):.0f} s, {pct(menos_min, len(seg_carga))} en menos de 1 minuto")

    if det["boletas"]:
        tot = det["ok"] + det["vacio"] + det["incorrecto"]
        print("\nDetalle por producto (agregado de la segunda iteración, sin umbral previo)")
        print(f"  Renglones bien leídos       {pct(det['ok'], tot)}  (vacíos {det['vacio']}, incorrectos {det['incorrecto']})")
        print(f"  Boletas con todo el detalle bien  {pct(det['boletas_ok'], det['boletas'])}")

    salida = os.path.join(BASE, "datos", "resultados_campo.csv")
    with open(salida, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(detalle[0]))
        w.writeheader()
        w.writerows(detalle)
    print(f"\nDetalle en {os.path.relpath(salida, BASE)}")


if __name__ == "__main__":
    main()
