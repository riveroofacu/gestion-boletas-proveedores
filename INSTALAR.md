# Instalación y uso

El sistema corre en una compu con Windows (la del local) y se usa desde esa compu o desde el celular conectado al mismo wifi. No necesita internet para cargar boletas; solo para mandar los avisos de Telegram y para bajar los modelos de lectura la primera vez.

## 1. Lo que hace falta

- Windows 10 u 11 con Python 3.12 instalado (al instalarlo, marcar "Add Python to PATH").
- Unos 3 GB libres en el disco y 4 GB de RAM o más.

## 2. Instalar

1. Descargar el repositorio (botón verde **Code** en GitHub, **Download ZIP**) y descomprimirlo en una carpeta, por ejemplo `C:\boletas`.
2. Hacer doble clic en `instalar.bat`. Tarda varios minutos.
3. Abrir `config\ajustes.json` con el Bloc de notas y poner una clave en `"clave"`.
4. Abrir `config\proveedores.json` y completar los proveedores reales (nombre, formato y palabras con las que se los reconoce). Hay un ejemplo en `config\proveedores.ejemplo.json`.

## 3. Abrir el sistema

1. Doble clic en `iniciar.bat`. La primera vez Windows pregunta por el firewall: permitir en **redes privadas**.
2. La ventana muestra dos direcciones. En la compu se entra a `http://localhost:8501`. Desde el celular, conectado al wifi del local, a la otra (por ejemplo `http://192.168.0.15:8501`).
3. No cerrar la ventana negra mientras se usa el sistema.

La primera boleta tarda más porque se cargan los modelos de lectura.

## 4. Avisos por Telegram

1. En el celular, instalar Telegram y buscar **@BotFather**. Mandarle `/newbot`, elegir un nombre (por ejemplo "Boletas Cabaña") y un usuario que termine en `bot`. BotFather responde con un **token**.
2. Pegar el token en `config\ajustes.json`, en `"telegram_token"`.
3. Desde el Telegram de quien va a recibir los avisos, buscar el bot recién creado y mandarle cualquier mensaje.
4. En la carpeta del sistema, abrir una terminal y correr
   ```
   .venv\Scripts\activate
   python alertas.py --chat-id
   ```
   Copiar el número que aparece en `"telegram_chat_id"`.
5. Probar con `python alertas.py --forzar`. Tiene que llegar un mensaje.

Desde ahí, cada vez que se abre `iniciar.bat` se manda el aviso del día (una vez por día) con los cheques que se cobran en los próximos días y la deuda por proveedor. `dias_aviso` en `ajustes.json` define cuántos días mirar. También hay un botón en el Panel para mandarlo en el momento.

## 5. Uso

- **Cargar boleta** sacar la foto, esperar la lectura, revisar los datos y guardar. Si la boleta solo trae kilos, el importe se calcula con el precio por kilo del producto. Si el precio no está cargado se pide en ese momento y se puede guardar para las próximas.
- **Pagos** elegir el proveedor y las boletas que se pagan, en el orden en que se cancelan. Si el monto no alcanza, la última queda con pago parcial; si sobra, queda saldo a favor para las próximas.
- **Panel** deuda por proveedor, cheques a cobrar, listado de boletas con su foto y compras por mes.
- **Precios** precios por kilo de cada proveedor y producto, con la fecha desde la que valen.

## 6. Prueba en el local (segunda ronda de evaluación)

Cada boleta que se carga guarda lo que leyó el sistema y lo que confirmó el usuario, y cuánto tardó. Para ver los resultados

```
.venv\Scripts\activate
python evaluar_campo.py --desde 2026-11-08
```

## 7. Copias de seguridad

Todo queda en la carpeta `datos` (base `boletas.db` y fotos). Conviene copiarla cada tanto a un pendrive o a Drive. Esa carpeta no se sube a GitHub.
