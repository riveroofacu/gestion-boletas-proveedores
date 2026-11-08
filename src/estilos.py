"""
Estilo visual de la app, tomado de la cartelería del local: negro, rojo de la marca,
letras con serifa gruesa, líneas finas de borde y un toque de madera.
"""
import base64
import html
import os

import streamlit as st

ROJO = "#AF342C"
NEGRO = "#121212"
MADERA = "#8A5A33"
PALETA_GRAFICOS = [ROJO, NEGRO, MADERA, "#D9867E", "#6B6560", "#C49A6C", "#7A1F19", "#3D3D3D", "#E3C9A8"]

CSS = """
<style>
__FUENTES__
:root { --rojo:#AF342C; --rojo-osc:#8E2922; --negro:#121212; --crema:#EBE3D6; --madera:#8A5A33;
        --madera-cl:#B07A4A; --borde:#E2DACD; --gris:#6B6560; --verde:#2F6B3A; --ambar:#B7791F; }
.stApp { background: var(--crema); }
header[data-testid="stHeader"] { background: transparent; height: 0; }
[data-testid="stToolbar"], [data-testid="stDecoration"], footer { display: none !important; }
.block-container { padding-top: 1.2rem !important; padding-bottom: 4rem !important; max-width: 760px; }

/* Encabezado tipo cartel */
.csl-head { background: var(--negro); border-radius: 6px 6px 0 0; padding: 16px 18px; position: relative;
            display: flex; align-items: center; gap: 16px; }
.csl-head::after { content: ""; position: absolute; inset: 6px; border: 1px solid #3b3b3b; border-radius: 3px;
                   pointer-events: none; }
.csl-head img { width: 64px; height: 64px; flex: none; }
.csl-kicker { font-family: 'Roboto Slab', Rockwell, Georgia, serif; letter-spacing: .26em; font-size: 11px; color: #cfc8bd;
              text-transform: uppercase; }
.csl-title { font-family: 'Alfa Slab One', Rockwell, Georgia, serif; color: #fff; font-size: 26px; line-height: 1.1; margin-top: 3px; }
.csl-bar { width: 44px; height: 4px; background: var(--rojo); border-radius: 2px; margin-top: 9px; }
.csl-wood { height: 8px; background: linear-gradient(var(--madera-cl), var(--madera)); border-radius: 0 0 6px 6px;
            margin-bottom: 18px; }

/* Portada (pantalla de la clave) */
.csl-portada { text-align: center; padding: 28px 0 8px; }
.csl-portada img { width: 132px; height: 132px; }
.csl-portada .csl-title { color: var(--negro); font-size: 30px; margin-top: 14px; }
.csl-portada .csl-kicker { color: var(--gris); margin-top: 6px; }
.csl-portada .csl-bar { margin: 12px auto 0; }

/* Títulos de sección */
.csl-sec { margin: 6px 0 14px; }
.csl-sec span { font-family: 'Alfa Slab One', Rockwell, Georgia, serif; font-size: 27px; color: var(--negro); text-transform: uppercase;
                letter-spacing: .01em; }
.csl-sec i { display: block; width: 44px; height: 4px; background: var(--rojo); margin-top: 6px; border-radius: 2px; }
.csl-sub { font-family: 'Roboto Slab', Rockwell, Georgia, serif; font-weight: 700; font-size: 13px; letter-spacing: .2em;
           text-transform: uppercase; color: var(--negro); margin: 26px 0 10px; display: flex; align-items: center; gap: 10px; }
.csl-sub::after { content: ""; flex: 1; height: 1px; background: var(--borde); }

/* Navegación */
.st-key-pagina, .st-key-pagina [data-testid="stButtonGroup"] { width: 100% !important; }
.st-key-pagina [role="radiogroup"] { width: 100%; display: flex; }
[data-testid="stButtonGroup"] button { flex: 1 1 0; min-width: 0; padding: 0 4px; font-family: 'Roboto Slab', Rockwell, Georgia, serif; font-weight: 600; font-size: 14px;
    border-radius: 4px !important; border: 1px solid var(--negro) !important; background: #fff; color: var(--negro);
    min-height: 44px; }
[data-testid="stButtonGroup"] button[kind$="Active"], [data-testid="stButtonGroup"] button[aria-checked="true"] {
    background: var(--negro) !important; color: #fff !important; box-shadow: inset 0 -4px 0 var(--rojo); }

/* Botones */
.stButton > button, .stFormSubmitButton > button { border-radius: 4px; font-family: 'Roboto Slab', Rockwell, Georgia, serif;
    font-weight: 600; min-height: 46px; padding: 0 22px; }
.stButton > button[kind="primary"], [data-testid="stBaseButton-primary"] { background: var(--rojo); border-color: var(--rojo);
    color: #fff; text-transform: uppercase; letter-spacing: .08em; width: 100%; }
.stButton > button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover { background: var(--rojo-osc);
    border-color: var(--rojo-osc); }
.stButton > button[kind="secondary"], [data-testid="stBaseButton-secondary"] { background: #fff; border: 1px solid var(--negro);
    color: var(--negro); }
.stButton > button[kind="secondary"]:hover, [data-testid="stBaseButton-secondary"]:hover { border-color: var(--rojo);
    color: var(--rojo); }
.stButton { width: 100%; }

/* Campos */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] { border-radius: 4px !important; }
[data-testid="stWidgetLabel"] p { font-weight: 600; color: #2b2723; }
[data-testid="stFileUploaderDropzone"] { background: #fff; border: 2px dashed var(--madera-cl); border-radius: 6px; }
[data-testid="stExpander"] details { background: #fff; border-radius: 6px; border-color: var(--borde); }
[data-testid="stDataFrame"] { border: 1px solid var(--borde); border-radius: 6px; overflow: hidden; }

/* Tarjeta negra (importe, totales) */
.csl-total { background: var(--negro); color: #fff; border-radius: 6px; padding: 18px 20px; position: relative;
             margin: 14px 0; }
.csl-total::after { content: ""; position: absolute; inset: 6px; border: 1px solid #3b3b3b; border-radius: 3px;
                    pointer-events: none; }
.csl-total .lbl { font-family: 'Roboto Slab', Rockwell, Georgia, serif; letter-spacing: .26em; font-size: 11px; color: #e7a49e;
                  text-transform: uppercase; }
.csl-total .val { font-family: 'Alfa Slab One', Rockwell, Georgia, serif; font-size: 32px; line-height: 1.15; margin-top: 4px; }
.csl-total .lin { font-size: 13px; color: #cfc8bd; margin-top: 10px; border-top: 1px solid #2c2c2c; padding-top: 8px; }
.csl-total .lin div { display: flex; justify-content: space-between; gap: 12px; padding: 2px 0; }

.csl-kpis { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.csl-kpis .csl-total { margin: 0; }
.csl-kpis .csl-total.rojo { background: var(--rojo); }
.csl-kpis .csl-total.rojo::after { border-color: rgba(255,255,255,.35); }
.csl-kpis .csl-total.rojo .lbl { color: #fbe1de; }
.csl-kpis .val { font-size: 25px; }
@media (max-width: 560px) { .csl-kpis { grid-template-columns: 1fr; } .csl-total .val { font-size: 27px; } }

/* Tarjetas de proveedor */
.csl-provs { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 12px; }
.csl-prov { background: #fff; border: 1px solid var(--borde); border-top: 4px solid var(--rojo); border-radius: 6px;
            padding: 12px 14px; }
.csl-prov.ok { border-top-color: var(--verde); }
.csl-prov .n { font-family: 'Roboto Slab', Rockwell, Georgia, serif; font-weight: 700; font-size: 15px; color: var(--negro); }
.csl-prov .d { font-family: 'Alfa Slab One', Rockwell, Georgia, serif; font-size: 22px; color: var(--negro); margin: 4px 0 2px; }
.csl-prov .s { font-size: 13px; color: var(--gris); }

/* Cheques */
.csl-cheque { display: flex; align-items: center; gap: 14px; background: #fff; border: 1px solid var(--borde);
              border-radius: 6px; padding: 10px 12px; margin-bottom: 8px; }
.csl-cheque .f { background: var(--negro); color: #fff; border-radius: 4px; width: 54px; text-align: center;
                 padding: 6px 0; flex: none; }
.csl-cheque .f b { font-family: 'Alfa Slab One', Rockwell, Georgia, serif; font-size: 20px; display: block; line-height: 1; }
.csl-cheque .f small { font-family: 'Roboto Slab', Rockwell, Georgia, serif; font-size: 10px; letter-spacing: .15em; text-transform: uppercase; }
.csl-cheque .f.pronto { background: var(--rojo); }
.csl-cheque .t { flex: 1; min-width: 0; }
.csl-cheque .t b { font-family: 'Roboto Slab', Rockwell, Georgia, serif; display: block; }
.csl-cheque .t span { font-size: 13px; color: var(--gris); }
.csl-cheque .m { font-family: 'Alfa Slab One', Rockwell, Georgia, serif; font-size: 17px; white-space: nowrap; }

/* Vista previa de un pago */
.csl-fila { display: flex; align-items: center; gap: 10px; background: #fff; border: 1px solid var(--borde);
            border-radius: 6px; padding: 9px 12px; margin-bottom: 6px; font-size: 14px; }
.csl-fila .t { flex: 1; }
.csl-chip { font-family: 'Roboto Slab', Rockwell, Georgia, serif; font-size: 11px; font-weight: 700; letter-spacing: .08em;
            text-transform: uppercase; padding: 3px 8px; border-radius: 3px; color: #fff; white-space: nowrap; }
.csl-chip.Pagado { background: var(--verde); } .csl-chip.Parcial { background: var(--ambar); }
.csl-chip.Pendiente { background: var(--rojo); } .csl-chip.Favor { background: var(--madera); }
/* Compras por proveedor (barras) */
.csl-barras { background: #fff; border: 1px solid var(--borde); border-radius: 6px; padding: 14px 16px 8px; }
.csl-barra { margin-bottom: 12px; }
.csl-barra .top { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; }
.csl-barra .n { font-family: 'Roboto Slab', Rockwell, Georgia, serif; font-weight: 600; font-size: 14px; }
.csl-barra .v { font-family: 'Alfa Slab One', Rockwell, Georgia, serif; font-size: 15px; white-space: nowrap; }
.csl-barra .pista { height: 10px; background: #EFE8DD; border-radius: 2px; margin-top: 5px; overflow: hidden; }
.csl-barra .relleno { height: 100%; background: var(--negro); border-radius: 2px; }
.csl-barra:first-child .relleno { background: var(--rojo); }
.csl-barra .p { font-size: 12px; color: var(--gris); margin-top: 3px; }
.csl-barras .tot { display: flex; justify-content: space-between; border-top: 1px solid var(--borde);
                   padding: 10px 0 6px; font-family: 'Roboto Slab', Rockwell, Georgia, serif; font-weight: 700; }
.csl-vacio { background: #fff; border: 1px dashed var(--borde); border-radius: 6px; padding: 14px; color: var(--gris);
             text-align: center; font-size: 14px; }
@media (min-width: 820px) { .block-container { max-width: 1180px !important; padding-left: 40px !important; padding-right: 40px !important; } }
</style>
"""

COLORES_ESTADO = {"Pagado": "#2F6B3A", "Parcial": "#B7791F", "Pendiente": ROJO}

_logo = None


def logo_b64():
    global _logo
    if _logo is None:
        ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "logo.png")
        _logo = base64.b64encode(open(ruta, "rb").read()).decode() if os.path.exists(ruta) else ""
    return _logo


def _img():
    return f'<img src="data:image/png;base64,{logo_b64()}" alt="">' if logo_b64() else ""


def _h(s):
    return html.escape(str(s))


def _md(texto):
    st.markdown(texto, unsafe_allow_html=True)


def _fuentes():
    """Las tipografías van incluidas en la app (assets/fuentes, licencia OFL) para que se vean
    igual aunque no haya internet."""
    carpeta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fuentes")
    caras = [("Alfa Slab One", 400, "alfa-slab-one-latin-400-normal.woff2")] + [
        ("Roboto Slab", w, f"roboto-slab-latin-{w}-normal.woff2") for w in (400, 600, 700)]
    css = []
    for familia, peso, archivo in caras:
        ruta = os.path.join(carpeta, archivo)
        if os.path.exists(ruta):
            datos = base64.b64encode(open(ruta, "rb").read()).decode()
            css.append(f"@font-face {{ font-family: '{familia}'; font-weight: {peso}; font-style: normal; "
                       f"font-display: swap; src: url(data:font/woff2;base64,{datos}) format('woff2'); }}")
    return "\n".join(css)


@st.cache_data
def _css():
    return CSS.replace("__FUENTES__", _fuentes())


def aplicar():
    _md(_css())


def portada():
    _md(f'<div class="csl-portada">{_img()}<div class="csl-title">Boletas de proveedores</div>'
        f'<div class="csl-kicker">Cabaña Santa Lucía · Carnicería artesanal</div><div class="csl-bar"></div></div>')


def encabezado():
    _md(f'<div class="csl-head">{_img()}<div><div class="csl-kicker">Cabaña Santa Lucía</div>'
        f'<div class="csl-title">Boletas de proveedores</div><div class="csl-bar"></div></div></div>'
        f'<div class="csl-wood"></div>')


def titulo(texto):
    _md(f'<div class="csl-sec"><span>{_h(texto)}</span><i></i></div>')


def subtitulo(texto):
    _md(f'<div class="csl-sub">{_h(texto)}</div>')


def total(etiqueta, valor, lineas=()):
    """Tarjeta negra con un monto grande. lineas: [(izquierda, derecha)]."""
    lin = "".join(f"<div><span>{_h(a)}</span><span>{_h(b)}</span></div>" for a, b in lineas)
    _md(f'<div class="csl-total"><div class="lbl">{_h(etiqueta)}</div><div class="val">{_h(valor)}</div>'
        + (f'<div class="lin">{lin}</div>' if lin else "") + "</div>")


def kpis(items):
    """items: [(etiqueta, valor, rojo?)]"""
    _md('<div class="csl-kpis">' + "".join(
        f'<div class="csl-total{" rojo" if r else ""}"><div class="lbl">{_h(e)}</div><div class="val">{_h(v)}</div></div>'
        for e, v, r in items) + "</div>")


def proveedores(tarjetas):
    """tarjetas: [(nombre, deuda_txt, detalle_txt, al_dia?)]"""
    _md('<div class="csl-provs">' + "".join(
        f'<div class="csl-prov{" ok" if ok else ""}"><div class="n">{_h(n)}</div><div class="d">{_h(d)}</div>'
        f'<div class="s">{_h(s)}</div></div>' for n, d, s, ok in tarjetas) + "</div>")


MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def cheque(fecha_iso, proveedor, detalle, monto_txt, pronto=False):
    a, m, d = fecha_iso[:10].split("-")
    _md(f'<div class="csl-cheque"><div class="f{" pronto" if pronto else ""}"><b>{int(d)}</b>'
        f'<small>{MESES[int(m) - 1]}</small></div><div class="t"><b>{_h(proveedor)}</b><span>{_h(detalle)}</span></div>'
        f'<div class="m">{_h(monto_txt)}</div></div>')


def fila(texto, estado, etiqueta=None):
    _md(f'<div class="csl-fila"><div class="t">{_h(texto)}</div>'
        f'<span class="csl-chip {_h(estado)}">{_h(etiqueta or estado)}</span></div>')


def vacio(texto):
    _md(f'<div class="csl-vacio">{_h(texto)}</div>')


def color_estado(v):
    c = COLORES_ESTADO.get(v)
    return f"color: {c}; font-weight: 700" if c else ""


MESES_LARGOS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
                "octubre", "noviembre", "diciembre"]


def nombre_mes(aaaa_mm):
    a, m = aaaa_mm.split("-")
    return f"{MESES_LARGOS[int(m) - 1].capitalize()} {a}"


def barras(filas, total_txt):
    """filas: [(nombre, monto, monto_txt)] ordenadas de mayor a menor."""
    maximo = max((m for _, m, _ in filas), default=0) or 1
    tot = sum(m for _, m, _ in filas) or 1
    cuerpo = "".join(
        f'<div class="csl-barra"><div class="top"><span class="n">{_h(n)}</span><span class="v">{_h(t)}</span></div>'
        f'<div class="pista"><div class="relleno" style="width:{max(m / maximo * 100, 1.5):.1f}%"></div></div>'
        f'<div class="p">{m / tot * 100:.0f}% del mes</div></div>' for n, m, t in filas)
    _md(f'<div class="csl-barras">{cuerpo}<div class="tot"><span>Total del mes</span><span>{_h(total_txt)}</span></div></div>')
