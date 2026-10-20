# Sistema de Gestión Inteligente de Boletas de Proveedores

Trabajo final de la Práctica Profesionalizante III, Técnico Superior en Ciencia de Datos e Inteligencia Artificial (IES21).

- **Autor** Facundo Rivero
- **Tutor académico** Gustavo Marcelo Macarone
- **Organización comitente** Cabaña Santa Lucía (carnicería, Córdoba)

## El problema

Los pagos a proveedores del negocio se registran a mano en cuadernos y los comprobantes se guardan en papel. Cada proveedor usa un formato distinto (remitos electrónicos, planillas de kilos, presupuestos, notas de pedido escritas a mano) y varios no traen el monto, solo los kilos. No hay un lugar donde ver cuánto se le debe a cada proveedor ni qué cheques se cobran en los próximos días.

## La propuesta

Un sistema que, a partir de una foto del comprobante tomada con el celular, extraiga automáticamente el proveedor, el número, la fecha y el total o los kilos, los guarde en una base de datos y avise antes de los vencimientos.

La extracción es híbrida y se van a comparar dos enfoques sobre el mismo conjunto de fotos.

1. **OCR más reglas por proveedor.** PaddleOCR o EasyOCR para leer el texto y reglas propias de cada formato para encontrar los campos.
2. **Modelo de visión y lenguaje abierto** (por ejemplo Qwen2.5-VL en su versión chica), que recibe la imagen y devuelve los campos directamente. Se espera que maneje mejor la escritura a mano.

En los dos casos se aplican validaciones (suma de renglones igual al total, formato de fecha, kilos por precio acordado) y el usuario confirma los datos antes de usarlos.

Todo el proyecto usa herramientas gratuitas.

| Parte | Herramienta |
| --- | --- |
| Lenguaje | Python |
| Desarrollo y pruebas | Google Colab |
| Mejora de imagen | OpenCV |
| Lectura de texto | PaddleOCR o EasyOCR |
| Modelo alternativo | Modelo de visión y lenguaje abierto |
| Base de datos | SQLite |
| Interfaz y panel | Streamlit |
| Alertas | Correo electrónico o bot de Telegram |

## Metodología

Scrum para organizar el trabajo en sprints y CRISP-DM para el ciclo de vida de los datos.

| Sprint | Cierre | Objetivo |
| --- | --- | --- |
| 1 | 19/10 | Propuesta de solución |
| 2 | 26/10 | Datos preparados |
| 3 | 2/11 | Modelo entrenado y evaluado |
| 4 | 16/11 | Despliegue e informe final |

## Datos

El dataset tiene 53 fotos de comprobantes reales de los proveedores, sacadas con un iPhone 12 y etiquetadas a mano en una planilla de referencia. Se dividieron por sorteo con semilla fija en 15 fotos de desarrollo y 38 de prueba.

Las fotos y la planilla **no se suben a este repositorio** porque contienen datos de terceros (CUIT, nombres, condiciones comerciales). Se guardan en una carpeta privada.

## Estructura del repositorio

```
notebooks/   notebooks de Colab (preparación de datos, pruebas de extracción)
src/         código del sistema
```

## Estado

- [x] Propuesta de solución
- [x] Dataset de fotos y planilla de referencia
- [ ] Análisis exploratorio y preprocesamiento
- [ ] Comparación OCR más reglas frente a modelo de visión
- [ ] Base de datos, panel y alertas
