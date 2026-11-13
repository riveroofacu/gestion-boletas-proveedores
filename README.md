# Sistema de Gestión Inteligente de Boletas de Proveedores

Trabajo final de la Práctica Profesionalizante III, Técnico Superior en Ciencia de Datos e Inteligencia Artificial (IES21).

- **Autor** Facundo Rivero
- **Tutor académico** Gustavo Marcelo Macarone
- **Organización comitente** Cabaña Santa Lucía (carnicería, Córdoba)

## El problema

Los pagos a proveedores del negocio se anotaban a mano en dos cuadernos y los comprobantes se guardaban en papel. Cada proveedor usa un formato distinto (remitos electrónicos, planillas de kilos, presupuestos, notas de pedido escritas a mano) y varios no traen el importe, solo los kilos. No había un lugar donde ver cuánto se le debe a cada proveedor ni qué cheques se cobran en los próximos días.

## Qué hace el sistema

- **Lee la boleta desde una foto** sacada con el celular y propone proveedor, número, fecha, kilos e importe. El usuario revisa y confirma.
- **Calcula el importe** de las boletas que solo traen kilos o cajones, leyendo la cantidad de cada producto y usando el precio vigente de cada uno.
- **Registra pagos y cheques** indicando qué boletas cubre cada uno, con pagos parciales y saldo a favor.
- **Muestra un panel** con la deuda por proveedor, los cheques a cobrar y las compras por mes.
- **Avisa todos los días por Telegram** qué cheques se cobran en los próximos 7 días y cuánto se le debe a cada proveedor.
- Se usa desde el celular, desde cualquier lugar, con contraseña.

## Cómo lee las boletas

1. La foto se achica a 2000 píxeles de lado con OpenCV.
2. PaddleOCR lee el texto y su posición en la imagen.
3. El proveedor se reconoce por palabras clave del comprobante.
4. Reglas escritas para cada formato buscan cada dato por su posición, por ejemplo el número que está al lado de "Total kilos".
5. Si la boleta no trae importe, se lee la tabla de productos renglón por renglón.
6. El usuario revisa todo antes de guardar.

No se entrenó ningún modelo. Se usan modelos ya entrenados y reglas propias, porque con 53 fotos no alcanza para entrenar uno.

## Evaluación

Se armó un dataset de 53 fotos de comprobantes reales, etiquetadas a mano, y se dividieron por sorteo en 15 de desarrollo y 38 de prueba. Se compararon dos enfoques sobre las mismas 38 fotos de prueba, con umbrales fijados antes de procesarlas.

| Métrica | OCR más reglas | Qwen3-VL-4B (visión y lenguaje) |
| --- | --- | --- |
| Campos correctos | 173/197 (88%) | 162/197 (82%) |
| Proveedor identificado | 94,7% | 89% |
| Comprobantes completos | 63% | 47% |
| Correcciones por comprobante | 0,63 | 0,92 |
| Campos con un valor incorrecto | 2 | 17 |
| Precisión, recall y F1 (todos los campos) | 0,98 / 0,84 / 0,91 | 0,88 / 0,84 / 0,86 |
| Tiempo por foto | 41 s sin GPU | 17 s con GPU |

Se eligió **OCR más reglas**. Es más exacto, casi nunca devuelve un dato equivocado (cuando falla deja el campo vacío) y funciona sin placa de video. El modelo de visión inventó valores que parecían válidos, como kilos en comprobantes que no los tienen.

Ninguno de los dos enfoques confundió un proveedor con otro. Cuando fallan, dejan el comprobante sin identificar.

### Segunda ronda, prueba en el local

Con los errores de la primera ronda se corrigieron las reglas de forma general. La versión corregida se probó en el local del 9 al 12 de noviembre de 2026 con **18 boletas nuevas** de cinco proveedores. El sistema guarda lo que leyó y lo que confirmó el usuario, y `evaluar_campo.py` calcula las métricas. Las reglas no se tocaron durante la prueba.

| Métrica | Umbral | Segunda ronda |
| --- | --- | --- |
| Proveedor identificado | 95% | 18/18 (100%) |
| Campos de boletas impresas | 90% | 33/33 (100%) |
| Campos de notas manuscritas | 75% | 11/19 (58%) |
| Comprobantes completos | 70% | 11/18 (61%) |
| Correcciones por boleta | 1 como máximo | 0,44 |
| Tiempo de lectura | 60 s como máximo | 27 s en promedio |
| Carga con la revisión del usuario | menos de 1 minuto | mediana 53 s |

Las boletas impresas salieron todas completas. Los errores se concentran en las notas escritas a mano, sobre todo en la fecha.

## Herramientas

Todo es gratuito.

| Parte | Herramienta |
| --- | --- |
| Lenguaje | Python |
| Desarrollo y evaluación | Google Colab |
| Lectura de texto | PaddleOCR (PP-OCRv6) |
| Modelo comparado | Qwen3-VL-4B-Instruct |
| Preparación de la foto | OpenCV |
| Base de datos | SQLite |
| Aplicación y panel | Streamlit |
| Avisos | Bot de Telegram |
| Acceso desde el celular | Tailscale |

## Estructura del repositorio

```
app.py                  aplicación (carga de boletas, pagos, panel y precios)
alertas.py              aviso diario por Telegram
evaluar_campo.py        métricas de la prueba en el local
probar_velocidad.py     comparación de ajustes de velocidad del OCR
src/extraccion.py       lectura de la foto y reglas por formato
src/detalle.py          lectura de la cantidad de cada producto
src/db.py               base de datos, pagos y deuda
src/comparar.py         comparación entre lo leído y lo confirmado
src/estilos.py          diseño de la aplicación
config/                 ejemplos de configuración (los archivos reales no se suben)
assets/                 logo y tipografías (licencia OFL)
notebooks/              notebooks de Colab
instalar.bat            instalación en Windows
iniciar.bat             abre el sistema
```

## Instalación

Los pasos están en [INSTALAR.md](INSTALAR.md). La computadora necesita Windows de 64 bits, un procesador con AVX (prácticamente cualquiera desde 2015) y al menos 8 GB de RAM recomendados. Tiene que estar enchufada, porque con batería la lectura tarda varias veces más.

## Datos y privacidad

Las fotos de los comprobantes, la planilla de referencia, la lista real de proveedores, los precios y la base de datos **no se suben a este repositorio**, porque contienen datos de terceros (CUIT, nombres, condiciones comerciales). Las fotos se guardan en una carpeta privada y la base queda solo en la computadora donde corre el sistema.

## Estado

- [x] Relevamiento y propuesta de solución
- [x] Dataset de 53 fotos etiquetado
- [x] Comparación OCR más reglas frente a modelo de visión
- [x] Aplicación con carga de boletas, pagos, panel y avisos
- [x] Prueba de uso en el local y resultados de la segunda ronda
