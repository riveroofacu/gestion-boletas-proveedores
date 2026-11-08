"""
Sistema de Gestión Inteligente de Boletas de Proveedores - Cabaña Santa Lucía.

Se abre con iniciar.bat (o: streamlit run app.py --server.address 0.0.0.0).
Desde el celular, conectado al wifi del local, se entra a http://IP-DE-LA-COMPU:8501
"""
import hashlib
import os
import shutil
import sys
import time
import traceback
from datetime import date, timedelta

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "src"))
import comparar  # noqa: E402
import db  # noqa: E402
import detalle  # noqa: E402
import extraccion  # noqa: E402
import alertas  # noqa: E402

CARPETA_DATOS = os.path.join(BASE, "datos")
CARPETA_FOTOS = os.path.join(CARPETA_DATOS, "fotos")
CARPETA_TMP = os.path.join(CARPETA_DATOS, "tmp")
RUTA_PROVEEDORES = os.path.join(BASE, "config", "proveedores.json")
for c in (CARPETA_FOTOS, CARPETA_TMP):
    os.makedirs(c, exist_ok=True)

OTRO_PROVEEDOR = "Otro (no está en la lista)"
NUEVO_PRODUCTO = "Otro producto"

st.set_page_config(page_title="Boletas - Cabaña Santa Lucía", page_icon="🧾", layout="centered")
# Streamlit marca la página como inglés y Chrome la "traduce" al castellano, cambiando textos
# ("Media res" -> "Res. media"). Se marca como castellano y sin traducción.
components.html("""<script>
const d = window.parent.document.documentElement; d.lang = "es"; d.setAttribute("translate", "no");
d.classList.add("notranslate");
</script>""", height=0)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def pesos(x):
    if x is None:
        return "-"
    return "$ " + f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def num(x):
    return f"{x:g}".replace(".", ",")


def dmy(iso):
    if not iso:
        return ""
    a, m, d = str(iso)[:10].split("-")
    return f"{d}/{m}/{a}"


@st.cache_resource
def conexion():
    c = db.conectar(os.path.join(CARPETA_DATOS, "boletas.db"))
    db.importar_precios(c, os.path.join(BASE, "config", "precios_iniciales.csv"))
    return c


def proveedores_config():
    if os.path.exists(RUTA_PROVEEDORES):
        return extraccion.cargar_proveedores(RUTA_PROVEEDORES)
    return []


def nombres_proveedores(con):
    nombres = [p["nombre"] for p in proveedores_config()]
    usados = [f["proveedor"] for f in con.execute("SELECT DISTINCT proveedor FROM comprobantes ORDER BY proveedor")]
    return nombres + [n for n in usados if n not in nombres]


# ---------------------------------------------------------------------------
# Acceso con clave
# ---------------------------------------------------------------------------
ajustes = alertas.cargar_ajustes()
if ajustes.get("clave") and not st.session_state.get("adentro"):
    st.title("Boletas de proveedores")
    clave = st.text_input("Clave", type="password")
    if st.button("Entrar", type="primary"):
        if clave == ajustes["clave"]:
            st.session_state.adentro = True
            st.rerun()
        else:
            st.error("Clave incorrecta.")
    st.stop()

con = conexion()


@st.cache_resource(show_spinner="Preparando el lector de boletas (solo la primera vez)...")
def lector_listo():
    """Carga el OCR al abrir la app, así la primera boleta no tarda de más."""
    extraccion.configurar(ajustes.get("lado_max"), ajustes.get("orientacion_renglones"))
    try:
        extraccion.obtener_ocr()
    except Exception:
        traceback.print_exc()
    return True


lector_listo()
pagina = st.segmented_control("Sección", ["Cargar boleta", "Pagos", "Panel", "Precios"],
                              default="Cargar boleta", label_visibility="collapsed", key="pagina")
pagina = pagina or "Cargar boleta"

if st.session_state.get("mensaje"):
    st.success(st.session_state.pop("mensaje"))


# ---------------------------------------------------------------------------
# Cargar boleta
# ---------------------------------------------------------------------------
def pagina_cargar():
    st.header("Cargar boleta")
    n = st.session_state.get("n_subida", 0)
    foto = st.file_uploader("Sacale una foto a la boleta o elegila de la galería",
                            type=["jpg", "jpeg", "png"], key=f"foto_{n}")
    if not foto:
        st.caption("Consejo: foto derecha, con buena luz y la boleta entera.")
        return

    datos_foto = foto.getvalue()
    clave = hashlib.md5(datos_foto).hexdigest()[:12]
    if st.session_state.get("lectura", {}).get("clave") != clave:
        t0 = time.time()
        ruta = os.path.join(CARPETA_TMP, f"{clave}.jpg")
        with open(ruta, "wb") as f:
            f.write(datos_foto)
        with st.spinner("Leyendo la boleta... puede tardar hasta un minuto"):
            try:
                lectura = extraccion.leer_foto(ruta, CARPETA_TMP)
                ext = extraccion.extraer(lectura, proveedores_config())
                seg = lectura["segundos"]
                ocr = {"textos": lectura["textos"], "cajas": lectura["cajas"]}
            except Exception as e:   # si falla el OCR, igual se puede cargar a mano
                traceback.print_exc()
                st.warning(f"No se pudo leer la foto automáticamente ({e}). Completá los datos a mano.")
                ext = {k: None for k in comparar.CAMPOS}
                ext["saldo_anterior"] = None
                seg = None
                ocr = None
        st.session_state.lectura = {"clave": clave, "ruta": ruta, "ext": ext, "seg_ocr": seg, "t0": t0,
                                    "ocr": ocr}

    lec = st.session_state.lectura
    ext = lec["ext"]
    with st.expander("Ver la foto"):
        st.image(datos_foto, width="stretch")
    if lec["seg_ocr"] is not None:
        st.caption(f"Lectura automática en {lec['seg_ocr']:.0f} s. Revisá los datos y corregí lo que haga falta.")
    for aviso in extraccion.validar(ext):
        st.warning(aviso)

    k = lec["clave"]
    nombres = nombres_proveedores(con)
    opciones = nombres + [OTRO_PROVEEDOR]
    idx = opciones.index(ext["proveedor"]) if ext.get("proveedor") in opciones else len(opciones) - 1
    prov = st.selectbox("Proveedor", opciones, index=idx, key=f"prov_{k}")
    if prov == OTRO_PROVEEDOR:
        prov = st.text_input("Nombre del proveedor", key=f"prov_nuevo_{k}").strip()

    col1, col2 = st.columns(2)
    nro = col1.text_input("Número de comprobante", value=ext.get("nro_comprobante") or "", key=f"nro_{k}").strip()
    fecha = col2.date_input("Fecha", value=comparar.a_fecha(ext.get("fecha_emision")),
                            format="DD/MM/YYYY", key=f"fecha_{k}")
    kilos = col1.number_input("Kilos (si figuran)", min_value=0.0, step=0.1, format="%.2f",
                              value=comparar.a_numero(ext.get("total_kg")), key=f"kg_{k}")
    impreso = col2.number_input("Importe impreso (si figura)", min_value=0.0, step=100.0, format="%.2f",
                                value=comparar.a_numero(ext.get("total_pesos")), key=f"imp_{k}")
    saldo_ant = None
    if ext.get("saldo_anterior") is not None:
        saldo_ant = st.number_input("Saldo anterior que figura en la boleta", min_value=0.0, format="%.2f",
                                    value=comparar.a_numero(ext.get("saldo_anterior")), key=f"saldo_{k}")

    if prov and nro and db.existe_comprobante(con, prov, nro):
        st.error(f"Ya hay un comprobante Nº {nro} de {prov} cargado. Fijate que no sea repetido.")
    if fecha and fecha > date.today():
        st.warning("La fecha es posterior a hoy.")

    # Importe: el impreso, o cantidad por precio de cada producto
    importe, items, precios_a_guardar, detalle_leido = None, [], [], []
    if impreso:
        importe = impreso
    elif prov:
        a_mano = st.checkbox("Cargar el importe total a mano", key=f"a_mano_{k}")
        if a_mano:
            importe = st.number_input("Importe total", min_value=0.0, step=100.0, format="%.2f", value=None,
                                      key=f"imp_mano_{k}")
        else:
            importe, items, precios_a_guardar, detalle_leido = tabla_productos(
                prov, fecha or date.today(), kilos, k, lec.get("ocr"))

    if importe:
        st.subheader(f"Importe {pesos(importe)}")
    if saldo_ant is not None and prov:
        deuda = next((d["deuda"] for d in db.deuda_por_proveedor(con) if d["proveedor"] == prov), 0.0)
        if abs(deuda - saldo_ant) > 1:
            st.info(f"Control: la boleta dice saldo anterior {pesos(saldo_ant)} y en el sistema la deuda "
                    f"con {prov} es {pesos(deuda)}. Puede ser por boletas o pagos que todavía no se cargaron.")

    faltan = [n for n, v in (("proveedor", prov), ("fecha", fecha), ("importe", importe)) if not v]
    if st.button("Guardar boleta", type="primary", disabled=bool(faltan)):
        confirmado = {"proveedor": prov, "nro_comprobante": nro or None, "fecha_emision": fecha.isoformat(),
                      "total_pesos": impreso or None, "total_kg": kilos or None}
        for pr in precios_a_guardar:
            db.guardar_precio(con, prov, pr["producto"], pr["precio"], fecha, pr["unidad"])
        unico = items[0] if len(items) == 1 else None
        cid = db.guardar_comprobante(
            con, prov, nro, fecha, importe, total_kg=kilos or None,
            producto=unico["producto"] if unico else ("Varios" if items else None),
            precio_kg=unico["precio"] if unico else None, saldo_anterior=saldo_ant, items=items,
            extraido={**ext, "detalle": detalle_leido}, confirmado=confirmado, campos_corregidos=comparar.correcciones(ext, confirmado),
            segundos_ocr=lec["seg_ocr"], segundos_carga=round(time.time() - lec["t0"], 1))
        destino = os.path.join(CARPETA_FOTOS, f"{cid}.jpg")
        shutil.move(lec["ruta"], destino)
        con.execute("UPDATE comprobantes SET foto=? WHERE id=?", (os.path.relpath(destino, BASE), cid))
        con.commit()
        st.session_state.pop("lectura", None)
        st.session_state.n_subida = n + 1
        st.session_state.mensaje = f"Boleta de {prov} por {pesos(importe)} guardada."
        st.rerun()
    if faltan:
        st.caption("Falta completar " + ", ".join(faltan) + ".")


def tabla_productos(prov, fecha, kilos, k, ocr=None):
    """Un casillero por producto del proveedor con la cantidad que trae la boleta; el importe se calcula
    con el precio vigente a la fecha de la boleta. Las cantidades se leen de la tabla de la boleta
    cuando se puede (detalle.py). Devuelve (importe, items, precios_a_guardar, detalle_leido)."""
    vigentes = db.precios_vigentes(con, prov, fecha)
    detalle_leido = detalle.detalle_por_producto(ocr, vigentes) if ocr else []
    leidos = {d["producto"]: d["cantidad"] for d in detalle_leido}
    # Producto que se completa solo con los kilos leídos: el que más se repite en las boletas de ese
    # proveedor; si todavía no hay boletas, el habitual de config/proveedores.json (si tiene uno).
    habitual = next((p.get("producto_habitual") for p in proveedores_config() if p["nombre"] == prov), None)
    frecuente = (db.producto_frecuente(con, prov) or habitual
                 or (vigentes[0]["producto"] if len(vigentes) == 1 else None))
    st.markdown("**Productos de la boleta**")
    if leidos:
        st.caption("Las cantidades se leyeron de la boleta. Revisalas y corregí lo que haga falta.")
    else:
        st.caption("Poné la cantidad de cada producto que vino y dejá vacío el resto.")
    cantidades = {}
    for i, v in enumerate(vigentes):
        precio_txt = f"{pesos(v['precio'])} por {v['unidad']}" if v["precio"] else "sin precio"
        if leidos:
            previo = leidos.get(v["producto"])
        else:
            previo = kilos if (kilos and v["producto"] == frecuente and v["unidad"] == "kg") else None
        cantidades[v["producto"]] = st.number_input(
            f"{v['producto']} · {precio_txt}", min_value=0.0, format="%.2f", value=previo,
            step=0.1 if v["unidad"] == "kg" else 1.0, key=f"cant_{k}_{prov}_{i}")

    precios = {v["producto"]: v["precio"] for v in vigentes}
    unidades = {v["producto"]: v["unidad"] for v in vigentes}
    guardar = []
    with st.expander("Cambió un precio o falta un producto"):
        cual = st.selectbox("Producto", list(precios) + [NUEVO_PRODUCTO], key=f"cambio_prod_{k}_{prov}")
        if cual == NUEVO_PRODUCTO:
            cual = st.text_input("Nombre del producto", key=f"cambio_nombre_{k}_{prov}").strip()
            unidades[cual] = st.selectbox("Se cobra por", ["kg", "cajón", "unidad"], key=f"cambio_unidad_{k}_{prov}")
            cantidades[cual] = st.number_input("Cantidad", min_value=0.0, format="%.2f", value=None,
                                               key=f"cambio_cant_{k}_{prov}")
        nuevo = st.number_input("Precio nuevo", min_value=0.0, step=100.0, format="%.2f", value=None,
                                key=f"cambio_precio_{k}_{prov}")
        st.caption("El precio se guarda desde la fecha de esta boleta; las boletas anteriores no cambian.")
        if cual and nuevo:
            precios[cual] = nuevo
            guardar.append({"producto": cual, "unidad": unidades[cual], "precio": nuevo})

    items, sin_precio = [], []
    for prod, cant in cantidades.items():
        if not prod or not cant:
            continue
        if not precios.get(prod):
            sin_precio.append(prod)
            continue
        items.append({"producto": prod, "unidad": unidades[prod], "cantidad": cant, "precio": precios[prod]})
    if sin_precio:
        st.warning("Falta el precio de " + ", ".join(sin_precio) + ". Cargalo en «Cambió un precio o falta un producto».")
    # Algunas planillas suman en el total también los cajones, así que se acepta cualquiera de las dos sumas
    kg_items = sum(i["cantidad"] for i in items if i["unidad"] == "kg")
    todo = sum(i["cantidad"] for i in items)
    if kilos and items and abs(kg_items - kilos) > 0.05 and abs(todo - kilos) > 0.05:
        st.warning(f"Los kilos de los productos suman {num(kg_items)} y la boleta dice {num(kilos)} en total. Revisalo.")
    if not items or sin_precio:
        return None, items, guardar, detalle_leido
    for i in items:
        st.caption(f"{i['producto']} {num(i['cantidad'])} {i['unidad']} × {pesos(i['precio'])} = {pesos(i['cantidad'] * i['precio'])}")
    return round(sum(i["cantidad"] * i["precio"] for i in items), 2), items, guardar, detalle_leido


# ---------------------------------------------------------------------------
# Pagos
# ---------------------------------------------------------------------------
def pagina_pagos():
    st.header("Registrar pago")
    con_deuda = [d["proveedor"] for d in db.deuda_por_proveedor(con) if d["deuda"] > db.TOL]
    if not con_deuda:
        st.info("No hay boletas pendientes de pago.")
    else:
        prov = st.selectbox("Proveedor", con_deuda)
        pend = db.pendientes(con, prov)
        por_id = {c["id"]: c for c in pend}
        etiqueta = lambda cid: (f"{dmy(por_id[cid]['fecha'])} · Nº {por_id[cid]['nro'] or 's/n'} · "
                                f"debe {pesos(por_id[cid]['saldo'])}")
        np_ = st.session_state.get("n_pago", 0)
        elegidos = st.multiselect("Boletas que paga (en el orden en que se cancelan)", list(por_id),
                                  format_func=etiqueta, placeholder="Elegí las boletas", key=f"eleg_{np_}")
        total = sum(por_id[c]["saldo"] for c in elegidos)
        favor = db.saldo_a_favor(con, prov)
        if favor > db.TOL:
            st.info(f"Hay {pesos(favor)} a favor de pagos anteriores. Se usan primero.")
        st.caption(f"Total de las boletas elegidas {pesos(total)}")

        medio = st.radio("Medio de pago", ["Cheque", "Transferencia", "Efectivo"], horizontal=True, key=f"medio_{np_}")
        col1, col2 = st.columns(2)
        monto = col1.number_input("Monto", min_value=0.0, step=1000.0, format="%.2f",
                                  value=float(max(round(total - favor, 2), 0.0)), key=f"monto_{np_}_{prov}_{total}")
        fecha_pago = col2.date_input("Fecha del pago", value=date.today(), format="DD/MM/YYYY")
        nro_cheque, fecha_cobro = None, None
        if medio == "Cheque":
            nro_cheque = col1.text_input("Número de cheque", key=f"cheque_{np_}").strip()
            fecha_cobro = col2.date_input("Fecha de cobro", value=date.today() + timedelta(days=60),
                                          format="DD/MM/YYYY")

        # Vista previa de cómo queda
        disponible = monto + favor
        for cid in elegidos:
            s = por_id[cid]["saldo"]
            if disponible >= s - db.TOL:
                st.write(f"✔ Nº {por_id[cid]['nro'] or 's/n'} queda pagada")
            elif disponible > db.TOL:
                st.write(f"◐ Nº {por_id[cid]['nro'] or 's/n'} queda debiendo {pesos(s - disponible)}")
            else:
                st.write(f"✘ Nº {por_id[cid]['nro'] or 's/n'} no alcanza a cubrirse")
            disponible = max(disponible - s, 0)
        if disponible > db.TOL:
            st.write(f"Quedan {pesos(disponible)} a favor para próximas boletas")

        if st.button("Registrar pago", type="primary", disabled=monto <= 0 and (not elegidos or favor <= db.TOL)):
            if monto > 0:
                db.registrar_pago(con, prov, medio, monto, fecha_pago, elegidos, nro_cheque, fecha_cobro)
                st.session_state.mensaje = f"Pago de {pesos(monto)} a {prov} registrado."
            else:
                db.usar_saldo_a_favor(con, prov, elegidos)
                st.session_state.mensaje = "Se aplicó el saldo a favor."
            st.session_state.n_pago = np_ + 1
            st.rerun()

    st.subheader("Últimos pagos")
    pg = db.pagos(con)
    if pg:
        df = pd.DataFrame(pg)
        df["Fecha"] = df["fecha_pago"].map(dmy)
        df["Cobro"] = df["fecha_cobro"].map(dmy)
        df["Monto"] = df["monto"].map(pesos)
        df["A favor"] = (df["monto"] - df["asignado"]).map(lambda x: pesos(x) if x > db.TOL else "")
        st.dataframe(df[["Fecha", "proveedor", "medio", "Monto", "nro_cheque", "Cobro", "A favor"]]
                     .rename(columns={"proveedor": "Proveedor", "medio": "Medio", "nro_cheque": "Cheque Nº"}),
                     hide_index=True)


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------
def pagina_panel():
    st.header("Panel")
    deuda = db.deuda_por_proveedor(con)
    total = sum(d["deuda"] for d in deuda)
    dias = int(ajustes.get("dias_aviso", 7))
    prox = db.cheques_proximos(con, dias)
    c1, c2 = st.columns(2)
    c1.metric("Deuda total", pesos(total))
    c2.metric(f"Cheques próximos {dias} días", pesos(sum(c["monto"] for c in prox)))

    st.subheader("Deuda por proveedor")
    if deuda:
        df = pd.DataFrame(deuda)
        df["Deuda"] = df["deuda"].map(pesos)
        df["A favor"] = df["a_favor"].map(lambda x: pesos(x) if x > db.TOL else "")
        st.dataframe(df[["proveedor", "comprobantes", "A favor", "Deuda"]]
                     .rename(columns={"proveedor": "Proveedor", "comprobantes": "Boletas impagas"}),
                     hide_index=True)
    else:
        st.write("Sin deuda.")

    st.subheader("Cheques a cobrar")
    ch = db.cheques(con, desde=date.today())
    if ch:
        df = pd.DataFrame(ch)
        df["Cobro"] = df["fecha_cobro"].map(dmy)
        df["Monto"] = df["monto"].map(pesos)
        st.dataframe(df[["Cobro", "proveedor", "Monto", "nro_cheque"]]
                     .rename(columns={"proveedor": "Proveedor", "nro_cheque": "Cheque Nº"}), hide_index=True)
    else:
        st.write("No hay cheques pendientes de cobro.")

    st.subheader("Boletas")
    comps = db.comprobantes(con)
    if comps:
        df = pd.DataFrame(comps)
        provs = ["Todos"] + sorted(df["proveedor"].unique())
        c1, c2 = st.columns(2)
        f_prov = c1.selectbox("Proveedor", provs)
        f_est = c2.selectbox("Estado", ["Todas", "Pendiente", "Parcial", "Pagado"])
        if f_prov != "Todos":
            df = df[df["proveedor"] == f_prov]
        if f_est != "Todas":
            df = df[df["estado"] == f_est]
        vista = pd.DataFrame({"Id": df["id"], "Fecha": df["fecha"].map(dmy), "Proveedor": df["proveedor"],
                              "Nº": df["nro"].fillna(""), "Kilos": df["total_kg"].map(lambda x: "" if pd.isna(x) else f"{x:g}"), "Importe": df["importe"].map(pesos),
                              "Debe": df["saldo"].map(pesos), "Estado": df["estado"]})
        st.dataframe(vista, hide_index=True)
        with st.expander("Ver foto o borrar una boleta cargada por error"):
            cid = st.selectbox("Boleta", list(df["id"]),
                               format_func=lambda i: vista.set_index("Id").loc[i, ["Fecha", "Proveedor", "Nº"]]
                               .astype(str).str.cat(sep=" · "))
            fila = next(c for c in comps if c["id"] == cid)
            its = db.items_de(con, cid)
            if its:
                st.dataframe(pd.DataFrame([{"Producto": i["producto"], "Cantidad": f"{i['cantidad']:g} {i['unidad']}",
                                            "Precio": pesos(i["precio"]), "Subtotal": pesos(i["cantidad"] * i["precio"])}
                                           for i in its]), hide_index=True)
            if fila["foto"] and os.path.exists(os.path.join(BASE, fila["foto"])):
                st.image(os.path.join(BASE, fila["foto"]), width="stretch")
            if st.button("Borrar esta boleta"):
                if db.borrar_comprobante(con, cid):
                    st.session_state.mensaje = "Boleta borrada."
                    st.rerun()
                else:
                    st.error("No se puede borrar porque tiene pagos asignados.")

        st.subheader("Compras por mes")
        gm = pd.DataFrame(db.gastos_por_mes(con))
        st.bar_chart(gm.pivot(index="mes", columns="proveedor", values="total").fillna(0))

    if ajustes.get("telegram_token") and ajustes.get("telegram_chat_id"):
        if st.button("Mandar aviso por Telegram ahora"):
            try:
                alertas.enviar(ajustes["telegram_token"], ajustes["telegram_chat_id"], alertas.armar_mensaje(con, dias))
                st.success("Aviso enviado.")
            except Exception as e:
                st.error(f"No se pudo mandar: {e}")


# ---------------------------------------------------------------------------
# Precios
# ---------------------------------------------------------------------------
def pagina_precios():
    st.header("Precios")
    st.caption("Se usan para calcular el importe de las boletas que solo traen kilos o cajones. "
               "Cuando cambia un precio se carga uno nuevo con la fecha desde la que vale; el anterior queda "
               "para las boletas viejas.")
    lp = db.lista_precios(con)
    if lp:
        df = pd.DataFrame(lp)
        vigentes = df.sort_values("vigente_desde").groupby(["proveedor", "producto"], as_index=False).last()
        vigentes["Precio"] = vigentes["precio_kg"].map(pesos) + " / " + vigentes["unidad"]
        vigentes["Desde"] = vigentes["vigente_desde"].map(dmy)
        st.dataframe(vigentes[["proveedor", "producto", "Precio", "Desde"]]
                     .rename(columns={"proveedor": "Proveedor", "producto": "Producto"}), hide_index=True)

    st.subheader("Cargar o actualizar un precio")
    prov = st.selectbox("Proveedor", nombres_proveedores(con), key="precio_prov")
    prods = db.productos(con, prov) if prov else []
    prod = st.selectbox("Producto", prods + [NUEVO_PRODUCTO], key="precio_prod")
    if prod == NUEVO_PRODUCTO:
        prod = st.text_input("Nombre del producto", key="precio_prod_nuevo").strip()
    c1, c2, c3 = st.columns(3)
    unidad = c1.selectbox("Por", ["kg", "cajón", "unidad"],
                          index=["kg", "cajón", "unidad"].index(db.unidad_de(con, prov, prod))
                          if prod and db.unidad_de(con, prov, prod) in ("kg", "cajón", "unidad") else 0)
    precio = c2.number_input("Precio", min_value=0.0, step=100.0, format="%.2f", value=None)
    desde = c3.date_input("Vale desde", value=date.today(), format="DD/MM/YYYY")
    if st.button("Guardar precio", type="primary", disabled=not (prov and prod and precio)):
        db.guardar_precio(con, prov, prod, precio, desde, unidad)
        st.session_state.mensaje = f"Precio de {prod} ({prov}) guardado."
        st.rerun()


{"Cargar boleta": pagina_cargar, "Pagos": pagina_pagos,
 "Panel": pagina_panel, "Precios": pagina_precios}[pagina]()
