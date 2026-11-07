"""
Compara el tiempo de lectura y los datos extraídos con distintos ajustes del OCR,
para elegir el más rápido que siga leyendo bien en la compu donde se va a usar.

Uso: poner fotos en la carpeta fotos_prueba y correr probar_velocidad.bat
     (o: python probar_velocidad.py foto1.jpg foto2.jpg ...)
Conviene usar fotos del conjunto de DESARROLLO, no las de prueba.
"""
import glob
import os
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "src"))
import extraccion  # noqa: E402

AJUSTES = [
    ("A  2000 px, con orientación (el evaluado)", 2000, True),
    ("B  1600 px, con orientación", 1600, True),
    ("C  1280 px, con orientación", 1280, True),
    ("D  1280 px, sin orientación", 1280, False),
]
CAMPOS = ["proveedor", "nro_comprobante", "fecha_emision", "total_pesos", "total_kg"]


_salida = []


def mostrar(texto=""):
    print(texto, flush=True)
    _salida.append(texto)


def main():
    fotos = sys.argv[1:] or sorted(glob.glob(os.path.join(BASE, "fotos_prueba", "*.jp*g"))
                                   + glob.glob(os.path.join(BASE, "fotos_prueba", "*.png")))
    if not fotos:
        mostrar("No hay fotos. Poné algunas en la carpeta fotos_prueba.")
        return
    provs = extraccion.cargar_proveedores(os.path.join(BASE, "config", "proveedores.json"))
    tmp = os.path.join(BASE, "datos", "tmp_velocidad")
    resumen = []
    for nombre, lado, orient in AJUSTES:
        mostrar(f"\n=== {nombre} ===")
        extraccion.configurar(lado, orient)
        extraccion.obtener_ocr()            # carga el modelo antes de medir
        tiempos = []
        for f in fotos:
            t0 = time.time()
            l = extraccion.leer_foto(f, tmp)
            d = extraccion.extraer(l, provs)
            tiempos.append(time.time() - t0)
            datos = "  ".join(f"{k}={d.get(k)}" for k in CAMPOS if d.get(k) is not None)
            mostrar(f"{os.path.basename(f):28} {tiempos[-1]:5.0f} s   {datos}")
        resumen.append((nombre, sum(tiempos) / len(tiempos)))
    mostrar("\nPromedio por foto")
    for nombre, prom in resumen:
        mostrar(f"  {nombre:45} {prom:5.0f} s")
    mostrar("\nElegí el más rápido que haya leído bien los mismos datos que A y pasalo a config/ajustes.json")
    with open(os.path.join(BASE, "resultado_velocidad.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(_salida) + "\n")


if __name__ == "__main__":
    main()
