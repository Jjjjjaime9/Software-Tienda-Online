"""Cliente de la API REST de la tienda online, hecho con la librería requests.

Es un programa independiente del servidor: no importa TiendaService, los modelos
ni ninguna función interna de la API. Toda la comunicación se hace mediante
peticiones HTTP a los endpoints, igual que haría cualquier otro cliente.

Ejecución (con la API ya arrancada):
    pip install -r requirements.txt
    python cliente.py                              # usa BASE_URL (localhost)
    python cliente.py http://192.168.1.34:8000     # API en otro equipo de la red
"""
import sys
import uuid
from typing import Any, Optional

import requests

# Dirección de la API. Para probar contra otro equipo se cambia aquí por su IP
# (p. ej. "http://192.168.1.34:8000") o se pasa como argumento al ejecutar.
BASE_URL = "http://localhost:8000"

TIMEOUT_SEGUNDOS = 5


class ErrorApi(Exception):
    """La API ha respondido con un código de estado distinto del esperado."""

    def __init__(self, status_code: int, detalle: Any) -> None:
        super().__init__(f"HTTP {status_code}: {detalle}")
        self.status_code = status_code
        self.detalle = detalle


def peticion(
    metodo: str,
    ruta: str,
    esperado: int,
    datos: Optional[dict] = None,
    parametros: Optional[dict] = None,
) -> Any:
    """Hace una petición HTTP a la API, comprueba el código de estado y devuelve el JSON.

    Args:
        metodo: método HTTP ("GET", "POST", "DELETE"...).
        ruta: ruta del endpoint, p. ej. "/usuarios".
        esperado: código de estado que indica éxito (200, 201, 204...).
        datos: cuerpo de la petición, que se envía como JSON.
        parametros: parámetros de consulta (query params) que se añaden a la URL,
            p. ej. {"nombre": "mac"} -> /productos?nombre=mac. Los None no se envían.

    Raises:
        ErrorApi: si el código de estado recibido no es el esperado.
    """
    url = f"{BASE_URL}{ruta}"
    if parametros:
        parametros = {clave: valor for clave, valor in parametros.items() if valor is not None}
    respuesta = requests.request(
        metodo, url, json=datos, params=parametros, timeout=TIMEOUT_SEGUNDOS
    )
    # respuesta.url incluye los parámetros de consulta que ha añadido requests
    ruta_completa = respuesta.url.removeprefix(BASE_URL)
    print(f"  {metodo} {ruta_completa} -> {respuesta.status_code}")

    if respuesta.status_code != esperado:
        # La API devuelve los errores como {"detail": ...}
        try:
            detalle = respuesta.json().get("detail", respuesta.text)
        except ValueError:
            detalle = respuesta.text
        # En los errores de validación (422) "detail" es una lista con un mensaje por fallo
        if isinstance(detalle, list):
            detalle = "; ".join(
                error.get("msg", str(error)).removeprefix("Value error, ") for error in detalle
            )
        raise ErrorApi(respuesta.status_code, detalle)

    # 204 No Content no lleva cuerpo
    if respuesta.status_code == 204:
        return None
    return respuesta.json()


def titulo(texto: str) -> None:
    print(f"\n=== {texto} ===")


# ---------------------------------------------------------------------------
# Operaciones sobre la API (una función por endpoint)
# ---------------------------------------------------------------------------

def crear_usuario(nombre: str, email: str, tipo: str, direccion: Optional[str] = None) -> dict:
    datos = {"nombre": nombre, "email": email, "tipo": tipo}
    if direccion is not None:
        datos["direccion"] = direccion
    return peticion("POST", "/usuarios", 201, datos)


# Los listados devuelven todos los elementos, o como mucho `limit` si se indica (100 como
# máximo). `skip` se salta los primeros y `nombre` filtra por una parte del nombre.
# Los parámetros que valen None no se envían.

def listar_usuarios(
    nombre: Optional[str] = None, skip: Optional[int] = None, limit: Optional[int] = None
) -> list:
    return peticion(
        "GET", "/usuarios", 200, parametros={"nombre": nombre, "skip": skip, "limit": limit}
    )


def crear_producto(datos: dict) -> dict:
    return peticion("POST", "/productos", 201, datos)


def listar_productos(
    nombre: Optional[str] = None, skip: Optional[int] = None, limit: Optional[int] = None
) -> list:
    return peticion(
        "GET", "/productos", 200, parametros={"nombre": nombre, "skip": skip, "limit": limit}
    )


def crear_pedido(cliente_id: str, items: list) -> dict:
    return peticion("POST", "/pedidos", 201, {"cliente_id": cliente_id, "items": items})


def listar_pedidos_usuario(cliente_id: str) -> list:
    return peticion("GET", f"/usuarios/{cliente_id}/pedidos", 200)


# ---------------------------------------------------------------------------
# Flujo de prueba
# ---------------------------------------------------------------------------

def mostrar_producto(p: dict) -> None:
    extra = ""
    if p["tipo"] == "electronico":
        extra = f" | garantía {p['meses_garantia']} meses"
    elif p["tipo"] == "ropa":
        extra = f" | talla {p['talla']}, color {p['color']}"
    print(f"    - [{p['tipo']}] {p['nombre']}: {p['precio']:.2f} € (stock {p['stock']}){extra}")


def mostrar_pedido(pedido: dict) -> None:
    print(f"    Pedido {pedido['id'][:8]}… del {pedido['fecha'][:19].replace('T', ' ')}")
    for item in pedido["items"]:
        print(
            f"      {item['cantidad']} x {item['nombre']} "
            f"({item['precio_unitario']:.2f} €) = {item['subtotal']:.2f} €"
        )
    print(f"      TOTAL: {pedido['total']:.2f} €")


def flujo_principal() -> None:
    # Sufijo aleatorio para que el email no se repita si el script se ejecuta varias veces
    sufijo = uuid.uuid4().hex[:6]

    titulo("1. Crear un usuario")
    cliente = crear_usuario(
        "Lucía Requena", f"lucia.requena.{sufijo}@correo.es", "cliente",
        direccion="Calle Mayor 5, Madrid",
    )
    print(f"    Creado: {cliente['nombre']} (id {cliente['id']})")

    titulo("2. Consultar la lista de usuarios")
    usuarios = listar_usuarios()
    for u in usuarios:
        rol = "admin" if u["es_admin"] else "cliente"
        print(f"    - {u['nombre']} <{u['email']}> [{rol}]")
    print(f"    Total: {len(usuarios)} usuarios")

    titulo("3. Crear varios productos")
    portatil = crear_producto({
        "tipo": "electronico", "nombre": "Portátil Orion 14",
        "precio": 899.99, "stock": 5, "meses_garantia": 24,
    })
    camiseta = crear_producto({
        "tipo": "ropa", "nombre": "Camiseta Atlas",
        "precio": 19.95, "stock": 30, "talla": "L", "color": "Azul marino",
    })
    taza = crear_producto({
        "tipo": "generico", "nombre": "Taza Requests", "precio": 8.50, "stock": 50,
    })
    for p in (portatil, camiseta, taza):
        mostrar_producto(p)

    titulo("4. Consultar la lista de productos")
    productos = listar_productos()
    for p in productos:
        mostrar_producto(p)
    print(f"    Total: {len(productos)} productos")

    titulo("5. Buscar por nombre y paginar (parámetros de consulta)")
    # Sin distinguir mayúsculas ni tildes, y basta con una parte del nombre
    encontrados = listar_productos(nombre="orión")
    print(f"    Productos con 'orión' en el nombre: {[p['nombre'] for p in encontrados]}")
    encontrados = listar_usuarios(nombre="requena")
    print(f"    Usuarios con 'requena' en el nombre: {[u['nombre'] for u in encontrados]}")
    pagina = listar_productos(skip=0, limit=2)
    print(f"    Primera página de productos (limit=2): {[p['nombre'] for p in pagina]}")
    pagina = listar_productos(skip=2, limit=2)
    print(f"    Segunda página de productos (skip=2, limit=2): {[p['nombre'] for p in pagina]}")

    titulo("6. Crear un pedido para el usuario")
    pedido = crear_pedido(cliente["id"], [
        {"producto_id": portatil["id"], "cantidad": 1},
        {"producto_id": camiseta["id"], "cantidad": 3},
    ])
    mostrar_pedido(pedido)

    titulo("7. Consultar los pedidos del usuario")
    pedidos = listar_pedidos_usuario(cliente["id"])
    for p in pedidos:
        mostrar_pedido(p)
    print(f"    Total: {len(pedidos)} pedido(s)")

    titulo("8. Comprobación de errores de la API")
    casos_error = [
        ("Pedido sin stock suficiente (409)",
         lambda: crear_pedido(cliente["id"], [{"producto_id": portatil["id"], "cantidad": 100}])),
        ("Email duplicado (409)",
         lambda: crear_usuario("Copia", cliente["email"], "cliente", direccion="Otra calle 1")),
        ("Pedidos de un usuario inexistente (404)",
         lambda: listar_pedidos_usuario("id-que-no-existe")),
        ("Producto de ropa sin talla ni color (422)",
         lambda: crear_producto({"tipo": "ropa", "nombre": "Gorra", "precio": 10, "stock": 1})),
        ("Listado con un limit mayor que el máximo (422)",
         lambda: listar_productos(limit=500)),
    ]
    for descripcion, operacion in casos_error:
        print(f"  {descripcion}:")
        try:
            operacion()
            print("    ¡La API no ha devuelto error!")
        except ErrorApi as error:
            print(f"    Error controlado -> {error}")


def main() -> None:
    global BASE_URL
    if len(sys.argv) > 1:
        BASE_URL = sys.argv[1].rstrip("/")

    print(f"Cliente de la Tienda Online -> {BASE_URL}")
    try:
        flujo_principal()
    except (requests.ConnectionError, requests.Timeout):
        print(f"\nNo se puede conectar con la API en {BASE_URL}. ¿Está arrancada? "
              "Si es otro equipo, revisa la IP, el --host 0.0.0.0 y el firewall.")
        sys.exit(1)
    except ErrorApi as error:
        print(f"\nLa API ha devuelto un error inesperado: {error}")
        sys.exit(1)
    print("\nFlujo completado correctamente.")


if __name__ == "__main__":
    main()
