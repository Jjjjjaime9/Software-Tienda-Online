# Tienda-Online-A-S

**Autor:** Jjjjjaime9

## Descripción

API REST en Python (FastAPI) que modela una tienda online, con un cliente Python y un frontend web
que la consumen por HTTP.

El sistema permite:

- Gestionar **productos** de distintas categorías: electrónicos (con meses de garantía),
  ropa (con talla y color) y genéricos, cada uno con su foto.
- Registrar **usuarios**: clientes (con dirección postal) y administradores.
- Realizar **pedidos** comprobando que el cliente existe y que hay stock suficiente,
  descontando las unidades del inventario y calculando el importe total.
- Consultar el histórico de pedidos de un cliente ordenado por fecha.

Toda la lógica se centraliza en la capa de servicios `TiendaService`. Los endpoints de `main.py`
solo validan los datos (esquemas de Pydantic) y delegan en el servicio.

## Estructura del proyecto

```
Tienda-Online-A-S/
├── src/                         ← API REST (lo que va en la imagen Docker)
│   ├── main.py                  # Endpoints FastAPI
│   ├── datos_ejemplo.py         # Usuarios, productos y pedidos cargados al arrancar
│   ├── models/                  # Producto, Usuario, Cliente, Administrador, Pedido
│   ├── schemas/                 # Esquemas Pydantic de entrada y salida
│   ├── services/
│   │   ├── tienda_service.py    # TiendaService
│   │   └── excepciones.py       # Errores de negocio (stock, email duplicado, ...)
│   └── imagenes/                # Fotos de los productos, servidas en /imagenes/<fichero>
├── cliente/cliente.py           ← cliente Python (requests)
├── frontend/                    ← frontend web (HTML + JS)
├── requirements.txt             # Dependencias de la API con versiones fijadas
├── dockerfile
└── .dockerignore
```

Ni el cliente ni el frontend importan `TiendaService` ni los modelos: solo conocen los endpoints.

## Ejecución local

Requiere Python 3.12 o superior. Desde la raíz del repositorio:

```bash
pip install -r requirements.txt
uvicorn main:app --app-dir src --host 0.0.0.0 --port 8000 --reload
```

- Documentación interactiva: http://localhost:8000/docs
- Los datos se guardan en memoria. Al reiniciar se vuelven a cargar los datos de ejemplo y
  **los ids (UUID) cambian**.

### Endpoints

| Método | Ruta | Uso |
|---|---|---|
| `POST` | `/usuarios` | Crear un usuario (cliente o administrador) |
| `GET` | `/usuarios` | Listar usuarios; admite `nombre`, `skip` y `limit` |
| `GET` | `/usuarios/{id}` | Consultar un usuario |
| `POST` | `/productos` | Dar de alta un producto (genérico, electrónico o ropa) |
| `POST` | `/imagenes` | Subir la foto de un producto |
| `GET` | `/productos` | Listar productos; admite `nombre`, `skip` y `limit` |
| `GET` | `/productos/{id}` | Consultar un producto |
| `DELETE` | `/productos/{id}` | Eliminar un producto |
| `POST` | `/pedidos` | Realizar un pedido |
| `GET` | `/usuarios/{id}/pedidos` | Historial de pedidos de un cliente |
| `GET` | `/imagenes/{fichero}` | Foto de un producto |

`nombre` filtra por una parte del nombre (sin distinguir mayúsculas ni tildes), `skip` salta
resultados y `limit` limita cuántos se devuelven (de 1 a 100):

```text
GET /productos?nombre=mac
GET /productos?skip=2&limit=2
```

### Cliente Python

```bash
pip install -r cliente/requirements.txt
python cliente/cliente.py                            # contra http://localhost:8000
python cliente/cliente.py http://192.168.1.34:8000   # contra la API de otro equipo
```

Crea usuarios, productos y un pedido, consulta los listados y comprueba los errores controlados
(409, 404 y 422). Termina con `Flujo completado correctamente.`

### Frontend

```bash
python -m http.server 5500 --directory frontend
```

Abre http://localhost:5500. La página usa la API del mismo equipo en el puerto 8000 (se puede
cambiar desde el icono de conexión de la cabecera). Tiene tienda con carrito, historial de pedidos
y panel de administración.

## Docker

La imagen se basa en `python:3.12-slim`, instala `requirements.txt`, copia solo `src/` y
arranca la API con uvicorn en el puerto 8000, con un usuario sin privilegios (`appuser`).
El `.dockerignore` deja fuera `.git`, entornos virtuales, cachés de Python, tests, el cliente
y el frontend.

### Construir la imagen

Desde la raíz del repositorio:

```bash
docker build -t tienda-online:1.0.0 -f dockerfile .
```

### Ejecutar el contenedor

```bash
docker run --rm -p 8000:8000 tienda-online:1.0.0
```

`-p 8000:8000` publica el puerto 8000 del contenedor en el 8000 del equipo. Para usar otro puerto
del equipo, cambia el primero (la API queda en http://localhost:8080):

```bash
docker run --rm -p 8080:8000 tienda-online:1.0.0
```

En segundo plano:

```bash
docker run -d --name tienda -p 8000:8000 tienda-online:1.0.0
docker logs -f tienda
docker stop tienda && docker rm tienda
```

### Variables de entorno

La aplicación no necesita secretos ni configuración. La imagen fija estas variables:

| Variable | Valor | Para qué |
|---|---|---|
| `PYTHONUNBUFFERED` | `1` | Los logs de uvicorn aparecen al momento en `docker logs` |
| `PYTHONIOENCODING` | `utf-8` | Los acentos y el símbolo `€` se imprimen bien |
| `PYTHONDONTWRITEBYTECODE` | `1` | No genera ficheros `.pyc` dentro del contenedor |
| `PIP_NO_CACHE_DIR` | `1` | pip no guarda caché, la imagen ocupa menos |

### Salida esperada y pruebas

Al arrancar, el contenedor muestra:

```text
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

Con el contenedor en marcha:

1. http://localhost:8000/docs abre la documentación interactiva (Swagger).
2. `curl http://localhost:8000/productos` devuelve los 5 productos de ejemplo (MacBook Neo, Msi,
   Sudadera EMEstudios, Chino Easy Wear y Mesa de Trabajo).
3. `curl http://localhost:8000/usuarios` devuelve los clientes y el administrador de ejemplo.
4. http://localhost:8000/imagenes/MacBook_NEO.jpg muestra la foto del producto.
5. `python cliente/cliente.py` recorre todos los endpoints y termina con
   `Flujo completado correctamente.`
6. `python -m http.server 5500 --directory frontend` y http://localhost:5500 muestra la tienda
   con los productos del contenedor.

Comprobar que el contenedor no se ejecuta como root:

```bash
docker run --rm tienda-online:1.0.0 whoami
# appuser
```

### Publicar la imagen en Docker Hub

```bash
docker login
docker tag tienda-online:1.0.0 jjjjjaime9/tienda-online:1.0.0
docker tag tienda-online:1.0.0 jjjjjaime9/tienda-online:latest
docker push jjjjjaime9/tienda-online:1.0.0
docker push jjjjjaime9/tienda-online:latest
```

### Descargar y ejecutar la imagen publicada

```bash
docker pull jjjjjaime9/tienda-online:1.0.0
docker run --rm -p 8000:8000 jjjjjaime9/tienda-online:1.0.0
```

### Flujo completo

build → run → test → push:

```bash
docker build -t tienda-online:1.0.0 -f dockerfile .
docker run -d --name tienda -p 8000:8000 tienda-online:1.0.0
curl http://localhost:8000/productos
python cliente/cliente.py
docker stop tienda && docker rm tienda
docker tag tienda-online:1.0.0 jjjjjaime9/tienda-online:1.0.0
docker push jjjjjaime9/tienda-online:1.0.0
```
