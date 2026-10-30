# Tienda-Online-A-S

**Autor:** Jjjjjaime9

## Descripción

Aplicación en Python que modela una tienda online. Esta primera versión se ejecuta en consola y
está diseñada para evolucionar hacia una API REST con FastAPI en prácticas posteriores.

El sistema permite:

- Gestionar **productos** de distintas categorías: electrónicos (con meses de garantía),
  ropa (con talla y color) y genéricos.
- Registrar **usuarios**: clientes (con dirección postal) y administradores.
- Realizar **pedidos** comprobando que el cliente existe y que hay stock suficiente,
  descontando las unidades del inventario y calculando el importe total.
- Consultar el histórico de pedidos de un cliente ordenado por fecha.

Toda la lógica se centraliza en la capa de servicios `TiendaService`.

## Estructura del proyecto

```
Tienda-Online-A-S/
└── src/
    ├── main.py                  # Punto de entrada: carga datos de ejemplo y simula pedidos
    ├── models/
    │   ├── producto.py          # Producto, ProductoElectronico, ProductoRopa
    │   ├── usuario.py           # Usuario, Cliente, Administrador
    │   └── pedido.py            # Pedido
    └── services/
        └── tienda_service.py    # TiendaService
```

## Ejecución

Requiere Python 3.10 o superior (no tiene dependencias externas).

```bash
python src/main.py
```

## Docker

La imagen se basa en `python:3.12-slim`, instala `requirements.txt`, copia solo `src/` y
ejecuta la aplicación con un usuario sin privilegios (`appuser`). El `.dockerignore` deja fuera
`.git`, entornos virtuales, cachés de Python y tests.

### Construir la imagen

Desde la raíz del repositorio:

```bash
docker build -t tienda-online:1.0.0 -f dockerfile .
```

### Ejecutar el contenedor

```bash
docker run --rm tienda-online:1.0.0
```

El programa no pide datos por teclado: imprime la simulación y el contenedor termina.
`--rm` borra el contenedor al acabar.

### Variables de entorno

La aplicación no necesita secretos ni configuración. La imagen fija estas variables:

| Variable | Valor | Para qué |
|---|---|---|
| `PYTHONUNBUFFERED` | `1` | La salida aparece al momento en `docker run` / `docker logs` |
| `PYTHONIOENCODING` | `utf-8` | Los acentos y el símbolo `€` se imprimen bien |
| `PYTHONDONTWRITEBYTECODE` | `1` | No genera ficheros `.pyc` dentro del contenedor |
| `PIP_NO_CACHE_DIR` | `1` | pip no guarda caché, la imagen ocupa menos |

### Salida esperada y pruebas

`docker run --rm tienda-online:1.0.0` debe imprimir, en este orden:

1. `=== Inventario inicial ===` con los 5 productos (MacBook Neo, Msi, Sudadera EMEstudios,
   Chino Easy Wear y Mesa de Trabajo) y su stock inicial.
2. `=== Pedido 1 (Eladio) ===` … `=== Pedido 5 (Guillem) ===`, cada uno con sus productos y
   el total (por ejemplo, el pedido 1 suma `790.95€`).
3. `=== Stock actualizado tras los pedidos ===` con el stock ya descontado
   (MacBook Neo pasa de 15 a 13).
4. `=== Histórico de pedidos de Eladio Dapena ===` con su pedido.

Los ids (UUID) y las fechas cambian en cada ejecución.

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
docker run --rm jjjjjaime9/tienda-online:1.0.0
```

### Flujo completo

build → run → test → push:

```bash
docker build -t tienda-online:1.0.0 -f dockerfile .
docker run --rm tienda-online:1.0.0
docker run --rm tienda-online:1.0.0 whoami
docker tag tienda-online:1.0.0 jjjjjaime9/tienda-online:1.0.0
docker push jjjjjaime9/tienda-online:1.0.0
```
