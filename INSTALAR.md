# Instalación y uso

El sistema corre en una notebook con Windows, que hace de servidor, y se usa desde el navegador del celular del negocio o de la misma notebook. Para entrar desde el celular se usa Tailscale, una red privada gratuita, así que funciona desde cualquier lugar sin publicar el sistema en internet.

Se necesita internet para Tailscale, para mandar los avisos de Telegram y para bajar los modelos de lectura la primera vez.

## 1. Lo que hace falta

- Windows de 64 bits con un procesador con AVX (prácticamente cualquiera desde 2015). Se recomiendan 8 GB de RAM.
- Python 3.12 instalado (al instalarlo, marcar "Add Python to PATH").
- Unos 3 GB libres en el disco.
- La notebook **enchufada**. Con batería la lectura tarda varias veces más.

## 2. Instalar (una sola vez)

1. Descargar el repositorio (botón verde **Code** en GitHub, **Download ZIP**) y descomprimirlo en una carpeta.
2. Hacer doble clic en `instalar.bat`. Tarda varios minutos.
3. Abrir `config\ajustes.json` con el Bloc de notas y poner una clave en `"clave"`.
4. Completar `config\proveedores.json` (nombre, formato y palabras con las que se reconoce cada proveedor) y `config\precios_iniciales.csv` (precios de cada producto). Hay ejemplos en la misma carpeta.
5. Para que el sistema se abra solo al prender la notebook, crear un acceso directo de `iniciar.bat` y moverlo a la carpeta Inicio de Windows (se abre escribiendo `shell:startup` en Ejecutar, Windows + R).
6. En **Panel de control, Opciones de energía, Elegir el comportamiento del cierre de la tapa**, poner "No hacer nada" cuando está enchufada. Así el sistema sigue andando con la notebook cerrada.

## 3. Abrir el sistema

Si se hizo el paso 5, se abre solo al prender la notebook (tarda un poco). Si no, doble clic en `iniciar.bat`. La primera vez Windows pregunta por el firewall: permitir en **redes privadas**.

Se abren dos ventanas, la del sistema y la de los avisos de Telegram. No hay que cerrarlas. En la notebook se entra a `http://localhost:8501`.

La primera boleta tarda más porque se cargan los modelos de lectura.

## 4. Entrar desde el celular

1. Instalar [Tailscale](https://tailscale.com) en la notebook y en el celular, e iniciar sesión con la misma cuenta en los dos.
2. En el celular, abrir el navegador y entrar a `http://IP:8501`, donde IP es la dirección que muestra Tailscale para la notebook (empieza con 100).
3. Agregar la página a la pantalla de inicio para que quede como una app más. En el iPhone es **Compartir, Agregar a pantalla de inicio**.
4. Escribir la clave. La notebook tiene que estar prendida y con Tailscale activo.

## 5. Avisos por Telegram

1. En Telegram, buscar **@BotFather**, mandarle `/newbot` y seguir los pasos. Al final responde con un **token**.
2. Pegar el token en `config\ajustes.json`, en `"telegram_token"`. El token no se comparte ni se sube al repositorio.
3. Desde el Telegram de quien va a recibir los avisos, buscar el bot y mandarle cualquier mensaje.
4. En la carpeta del sistema, abrir una terminal y correr
   ```
   .venv\Scripts\activate
   python alertas.py --chat-id
   ```
   Copiar el número que aparece en `"telegram_chat_id"`.
5. Probar con `python alertas.py --forzar`. Tiene que llegar un mensaje.

Desde ahí el aviso sale solo una vez por día, a partir de `hora_aviso` (8 por defecto), con los cheques de los próximos `dias_aviso` días (7 por defecto) y la deuda por proveedor. También hay un botón en el Panel para mandarlo en el momento.

## 6. Uso

- **Cargar** sacar la foto o elegirla de la galería, esperar la lectura (unos 25 segundos), revisar proveedor, número, fecha, kilos y la cantidad de cada producto, y guardar. Si la boleta no trae importe, se calcula con el precio vigente de cada producto. Si un producto no tiene precio, se carga en ese momento.
- **Pagos** elegir el proveedor y las boletas que se pagan, en el orden en que se cancelan. Si el monto no alcanza, la última queda con pago parcial; si sobra, queda saldo a favor para las próximas.
- **Panel** deuda por proveedor, cheques a cobrar, compras por mes y listado de boletas con su foto.
- **Precios** precio de cada producto por proveedor, por kilo o por cajón, con la fecha desde la que vale.

## 7. Si algo no anda

- **La página no abre en el celular** revisar que la notebook esté prendida, con Tailscale activo y con la ventana del sistema abierta.
- **La lectura tarda mucho más de 30 segundos** enchufar la notebook.
- **No llegó el aviso del día** revisar que la notebook tenga internet, o mandarlo desde el Panel.

## 8. Prueba en el local (segunda ronda de evaluación)

Cada boleta que se carga guarda lo que leyó el sistema, lo que confirmó el usuario y cuánto tardó. Para ver los resultados

```
.venv\Scripts\activate
python evaluar_campo.py --desde 2026-11-08
```

## 9. Copias de seguridad

Todo queda en la carpeta `datos` (base `boletas.db` y fotos). Conviene copiarla cada tanto a un pendrive o a Drive. Esa carpeta no se sube a GitHub.
