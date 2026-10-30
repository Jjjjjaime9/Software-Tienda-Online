"""Punto de entrada de la aplicación y capa de exposición del servicio (API REST).

Define los endpoints con FastAPI y delega toda la lógica de negocio en TiendaService.

Ejecución (desde la carpeta Tienda_online):
    pip install -r requirements.txt
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Con --host 0.0.0.0 la API acepta conexiones de otros equipos de la red local,
no solo desde localhost.

Documentación interactiva: http://127.0.0.1:8000/docs
Fotos de los productos: se guardan en la carpeta imagenes/ y la API las sirve en /imagenes/<fichero>.
Para dar de alta un producto con una foto nueva, primero se sube con POST /imagenes y luego se
envía el nombre devuelto en el campo `imagen` de POST /productos.
Inicializar frontend desde el local: python -m http.server 5500 --directory frontend
http://localhost:5500

"""
import re
import unicodedata
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import Body, Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from datos_ejemplo import cargar_datos_ejemplo
from schemas import (
    ErrorRead,
    ImagenRead,
    PedidoCreate,
    PedidoRead,
    ProductoCreate,
    ProductoRead,
    UsuarioCreate,
    UsuarioRead,
)
from services.excepciones import (
    EmailDuplicadoError,
    ProductoNoEncontradoError,
    StockInsuficienteError,
    UsuarioNoEncontradoError,
    UsuarioNoEsClienteError,
)
from services.tienda_service import TiendaService

app = FastAPI(
    title="Tienda Online API",
    description="API REST de la tienda online: gestión de usuarios, productos y pedidos.",
    version="2.0.0",
)

# CORS: permite que el frontend (servido desde otro origen, p. ej. http://localhost:5500
# o abierto como fichero) haga peticiones a la API desde el navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fotos de los productos: los ficheros de la carpeta imagenes/ se sirven tal cual en
# /imagenes/<fichero>, y cada producto guarda solo el nombre de su fichero
CARPETA_IMAGENES = Path(__file__).parent / "imagenes"
CARPETA_IMAGENES.mkdir(exist_ok=True)
app.mount("/imagenes", StaticFiles(directory=CARPETA_IMAGENES), name="imagenes")

# Fotos que se pueden subir con POST /imagenes
EXTENSIONES_IMAGEN = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif"}
TAMANO_MAXIMO_IMAGEN = 5 * 1024 * 1024   # 5 MB

# Instancia única del servicio: los datos se mantienen en memoria mientras la API está en marcha
_servicio = TiendaService()
cargar_datos_ejemplo(_servicio)


def get_servicio() -> TiendaService:
    """Dependencia que proporciona el servicio de la tienda a los endpoints."""
    return _servicio


# Parámetros de consulta (query params) de los listados: GET /productos?nombre=mac&skip=0&limit=10
LIMITE_MAXIMO = 100


def parametro_nombre(descripcion: str) -> Optional[str]:
    return Query(
        default=None,
        min_length=1,
        max_length=100,
        description=descripcion,
        examples=["mac"],
    )


def parametro_skip() -> int:
    return Query(default=0, ge=0, description="Número de resultados que se saltan (paginación).")


def parametro_limit() -> Optional[int]:
    return Query(
        default=None,
        ge=1,
        le=LIMITE_MAXIMO,
        description=f"Número máximo de resultados que se devuelven (de 1 a {LIMITE_MAXIMO}). "
        "Si no se indica, se devuelven todos.",
    )


# Ejemplos que se muestran en Swagger (/docs) para cada tipo de alta
EJEMPLOS_USUARIO = {
    "cliente": {
        "summary": "Cliente",
        "value": {
            "nombre": "Olaia Errazkin",
            "email": "olaia.errazkin@faromail.eus",
            "tipo": "cliente",
            "direccion": "Calle de los Tintoreros 21, Burgos",
        },
    },
    "administrador": {
        "summary": "Administrador",
        "value": {
            "nombre": "Teodoro Villalustre",
            "email": "teodoro.villalustre@tiendacentral.es",
            "tipo": "administrador",
        },
    },
}

EJEMPLOS_PRODUCTO = {
    "electronico": {
        "summary": "Producto electrónico",
        "value": {
            "tipo": "electronico",
            "nombre": "Altavoz Borealis Mini",
            "precio": 74.95,
            "stock": 22,
            "meses_garantia": 30,
            "imagen": "MacBook_NEO.jpg",
        },
    },
    "ropa": {
        "summary": "Producto de ropa",
        "value": {
            "tipo": "ropa",
            "nombre": "Chaqueta Fiordo",
            "precio": 89.00,
            "stock": 14,
            "talla": "M",
            "color": "Verde musgo",
        },
    },
    "generico": {
        "summary": "Producto genérico",
        "value": {
            "tipo": "generico",
            "nombre": "Cuaderno Cartógrafo A5",
            "precio": 12.80,
            "stock": 60,
        },
    },
}


# ---------------------------------------------------------------------------
# Usuarios
# ---------------------------------------------------------------------------

@app.post(
    "/usuarios",
    response_model=UsuarioRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Usuarios"],
    summary="Crear un usuario",
    responses={409: {"model": ErrorRead, "description": "El email ya está registrado"}},
)
def crear_usuario(
    datos: UsuarioCreate = Body(openapi_examples=EJEMPLOS_USUARIO),
    servicio: TiendaService = Depends(get_servicio),
) -> UsuarioRead:
    try:
        usuario = servicio.registrar_usuario(
            datos.tipo, datos.nombre, datos.email, direccion=datos.direccion or ""
        )
    except EmailDuplicadoError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return UsuarioRead.desde_modelo(usuario)


@app.get(
    "/usuarios",
    response_model=List[UsuarioRead],
    tags=["Usuarios"],
    summary="Listar los usuarios registrados",
    description="Admite filtrar por nombre y paginar con parámetros de consulta, "
    "p. ej. `/usuarios?nombre=maria&skip=0&limit=10`.",
)
def listar_usuarios(
    nombre: Optional[str] = parametro_nombre(
        "Devuelve solo los usuarios cuyo nombre contiene este texto "
        "(sin distinguir mayúsculas ni tildes)."
    ),
    skip: int = parametro_skip(),
    limit: Optional[int] = parametro_limit(),
    servicio: TiendaService = Depends(get_servicio),
) -> List[UsuarioRead]:
    usuarios = servicio.listar_usuarios(nombre=nombre, skip=skip, limit=limit)
    return [UsuarioRead.desde_modelo(u) for u in usuarios]


@app.get(
    "/usuarios/{usuario_id}",
    response_model=UsuarioRead,
    tags=["Usuarios"],
    summary="Obtener un usuario concreto",
    responses={404: {"model": ErrorRead, "description": "El usuario no existe"}},
)
def obtener_usuario(
    usuario_id: str, servicio: TiendaService = Depends(get_servicio)
) -> UsuarioRead:
    try:
        usuario = servicio.obtener_usuario(usuario_id)
    except UsuarioNoEncontradoError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return UsuarioRead.desde_modelo(usuario)


# ---------------------------------------------------------------------------
# Productos
# ---------------------------------------------------------------------------

@app.post(
    "/productos",
    response_model=ProductoRead,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    tags=["Productos"],
    summary="Dar de alta un producto",
    description="La imagen es opcional: el nombre de un fichero que ya esté en la carpeta "
    "`imagenes/` de la API. Para usar una foto nueva, súbela antes con `POST /imagenes` "
    "y envía aquí el nombre que devuelve.",
    responses={400: {"model": ErrorRead, "description": "La imagen indicada no existe"}},
)
def crear_producto(
    datos: ProductoCreate = Body(openapi_examples=EJEMPLOS_PRODUCTO),
    servicio: TiendaService = Depends(get_servicio),
) -> ProductoRead:
    if datos.imagen and not (CARPETA_IMAGENES / datos.imagen).is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No existe la imagen '{datos.imagen}' en la carpeta imagenes/.",
        )
    producto = servicio.agregar_producto(
        datos.tipo,
        datos.nombre,
        datos.precio,
        datos.stock,
        imagen=datos.imagen,
        **datos.atributos_especificos(),
    )
    return ProductoRead.desde_modelo(producto)


@app.post(
    "/imagenes",
    response_model=ImagenRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Productos"],
    summary="Subir la foto de un producto",
    description="Guarda la foto en la carpeta `imagenes/` de la API con un nombre único y "
    "devuelve ese nombre, que se usa después en el campo `imagen` de `POST /productos`. "
    f"Formatos admitidos: {', '.join(sorted(EXTENSIONES_IMAGEN))}; "
    f"tamaño máximo: {TAMANO_MAXIMO_IMAGEN // (1024 * 1024)} MB.",
    responses={
        400: {"model": ErrorRead, "description": "El fichero no es una imagen admitida"},
        413: {"model": ErrorRead, "description": "La imagen es demasiado grande"},
    },
)
async def subir_imagen(
    archivo: UploadFile = File(description="Fichero de la foto."),
) -> ImagenRead:
    original = Path(archivo.filename or "")
    extension = original.suffix.lower()
    if extension not in EXTENSIONES_IMAGEN or not (archivo.content_type or "").startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El fichero debe ser una imagen ({', '.join(sorted(EXTENSIONES_IMAGEN))}).",
        )

    contenido = await archivo.read(TAMANO_MAXIMO_IMAGEN + 1)
    if len(contenido) > TAMANO_MAXIMO_IMAGEN:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"La imagen no puede superar los {TAMANO_MAXIMO_IMAGEN // (1024 * 1024)} MB.",
        )

    # Nombre seguro y único: solo letras, números, '_' y '-' del nombre original más un
    # sufijo aleatorio, así nunca se sobrescribe otra foto ni se sale de la carpeta
    sin_tildes = unicodedata.normalize("NFKD", original.stem).encode("ascii", "ignore").decode()
    base = re.sub(r"[^A-Za-z0-9_-]+", "_", sin_tildes).strip("_")[:50] or "imagen"
    nombre = f"{base}_{uuid.uuid4().hex[:8]}{extension}"
    (CARPETA_IMAGENES / nombre).write_bytes(contenido)
    return ImagenRead(imagen=nombre, imagen_url=f"/imagenes/{nombre}")


@app.get(
    "/productos",
    response_model=List[ProductoRead],
    response_model_exclude_none=True,
    tags=["Productos"],
    summary="Listar los productos",
    description="Admite filtrar por nombre y paginar con parámetros de consulta, "
    "p. ej. `/productos?nombre=mac&skip=0&limit=10`.",
)
def listar_productos(
    nombre: Optional[str] = parametro_nombre(
        "Devuelve solo los productos cuyo nombre contiene este texto "
        "(sin distinguir mayúsculas ni tildes)."
    ),
    skip: int = parametro_skip(),
    limit: Optional[int] = parametro_limit(),
    servicio: TiendaService = Depends(get_servicio),
) -> List[ProductoRead]:
    productos = servicio.listar_productos(nombre=nombre, skip=skip, limit=limit)
    return [ProductoRead.desde_modelo(p) for p in productos]


@app.get(
    "/productos/{producto_id}",
    response_model=ProductoRead,
    response_model_exclude_none=True,
    tags=["Productos"],
    summary="Obtener un producto concreto",
    responses={404: {"model": ErrorRead, "description": "El producto no existe"}},
)
def obtener_producto(
    producto_id: str, servicio: TiendaService = Depends(get_servicio)
) -> ProductoRead:
    try:
        producto = servicio.obtener_producto(producto_id)
    except ProductoNoEncontradoError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return ProductoRead.desde_modelo(producto)


@app.delete(
    "/productos/{producto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Productos"],
    summary="Eliminar un producto",
    responses={404: {"model": ErrorRead, "description": "El producto no existe"}},
)
def eliminar_producto(
    producto_id: str, servicio: TiendaService = Depends(get_servicio)
) -> None:
    if not servicio.eliminar_producto(producto_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ProductoNoEncontradoError(producto_id)),
        )


# ---------------------------------------------------------------------------
# Pedidos
# ---------------------------------------------------------------------------

@app.post(
    "/pedidos",
    response_model=PedidoRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Pedidos"],
    summary="Realizar un pedido",
    responses={
        400: {"model": ErrorRead, "description": "El usuario no es un cliente"},
        404: {"model": ErrorRead, "description": "El cliente o algún producto no existe"},
        409: {"model": ErrorRead, "description": "No hay stock suficiente"},
    },
)
def crear_pedido(
    datos: PedidoCreate, servicio: TiendaService = Depends(get_servicio)
) -> PedidoRead:
    cantidades = [(item.producto_id, item.cantidad) for item in datos.items]
    try:
        pedido = servicio.realizar_pedido(datos.cliente_id, cantidades)
    except (UsuarioNoEncontradoError, ProductoNoEncontradoError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except UsuarioNoEsClienteError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    except StockInsuficienteError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return PedidoRead.desde_modelo(pedido)


@app.get(
    "/usuarios/{cliente_id}/pedidos",
    response_model=List[PedidoRead],
    tags=["Pedidos"],
    summary="Historial de pedidos de un cliente",
    responses={
        400: {"model": ErrorRead, "description": "El usuario no es un cliente"},
        404: {"model": ErrorRead, "description": "El cliente no existe"},
    },
)
def listar_pedidos_cliente(
    cliente_id: str, servicio: TiendaService = Depends(get_servicio)
) -> List[PedidoRead]:
    try:
        pedidos = servicio.listar_pedidos_usuario(cliente_id)
    except UsuarioNoEncontradoError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except UsuarioNoEsClienteError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    return [PedidoRead.desde_modelo(p) for p in pedidos]


@app.get("/", include_in_schema=False)
def raiz() -> RedirectResponse:
    """Redirige la raíz a la documentación interactiva."""
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
