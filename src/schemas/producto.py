"""Esquemas Pydantic de producto (peticiones y respuestas de la API)."""
from typing import Any, Dict, Literal, Optional, Tuple
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from models.producto import Producto, ProductoElectronico, ProductoRopa

TipoProducto = Literal["generico", "electronico", "ropa"]

# Atributos adicionales que admite (y exige) cada tipo de producto
ATRIBUTOS_POR_TIPO: Dict[str, Tuple[str, ...]] = {
    "generico": (),
    "electronico": ("meses_garantia",),
    "ropa": ("talla", "color"),
}
ATRIBUTOS_ESPECIFICOS: Tuple[str, ...] = ("meses_garantia", "talla", "color")


class ProductoCreate(BaseModel):
    """Datos que envía el cliente de la API para dar de alta un producto."""

    model_config = ConfigDict(str_strip_whitespace=True)

    tipo: TipoProducto = Field(examples=["electronico"])
    nombre: str = Field(min_length=2, max_length=100, examples=["Altavoz Borealis Mini"])
    precio: float = Field(gt=0, allow_inf_nan=False, description="Precio en euros.", examples=[74.95])
    stock: int = Field(ge=0, examples=[22])
    meses_garantia: Optional[int] = Field(
        default=None, ge=0, le=120, description="Solo para productos electrónicos.", examples=[30]
    )
    talla: Optional[str] = Field(
        default=None, min_length=1, max_length=10, description="Solo para ropa.", examples=["M"]
    )
    color: Optional[str] = Field(
        default=None, min_length=2, max_length=30, description="Solo para ropa.", examples=["Verde musgo"]
    )
    imagen: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=150,
        description="Nombre del fichero de la foto dentro de la carpeta imagenes/ de la API (opcional).",
        examples=["MacBook_NEO.jpg"],
    )

    @field_validator("imagen")
    @classmethod
    def validar_nombre_imagen(cls, imagen: Optional[str]) -> Optional[str]:
        """Solo se admite un nombre de fichero, no rutas (evita salir de la carpeta imagenes/)."""
        if imagen is not None and ("/" in imagen or "\\" in imagen or ".." in imagen):
            raise ValueError("La imagen debe ser solo el nombre del fichero, sin carpetas.")
        return imagen

    @model_validator(mode="after")
    def validar_atributos_segun_tipo(self) -> "ProductoCreate":
        """Exige los atributos propios del tipo y rechaza los que pertenecen a otro tipo."""
        requeridos = ATRIBUTOS_POR_TIPO[self.tipo]
        faltan = [a for a in requeridos if getattr(self, a) is None]
        sobran = [
            a for a in ATRIBUTOS_ESPECIFICOS if a not in requeridos and getattr(self, a) is not None
        ]
        if faltan:
            raise ValueError(f"Un producto de tipo '{self.tipo}' requiere: {', '.join(faltan)}.")
        if sobran:
            raise ValueError(
                f"Un producto de tipo '{self.tipo}' no admite: {', '.join(sobran)}."
            )
        return self

    def atributos_especificos(self) -> Dict[str, Any]:
        """Devuelve solo los atributos adicionales que corresponden al tipo de producto."""
        return {a: getattr(self, a) for a in ATRIBUTOS_POR_TIPO[self.tipo]}


class ImagenRead(BaseModel):
    """Foto subida a la API, lista para usarla al dar de alta un producto."""

    imagen: str = Field(
        description="Nombre con el que se ha guardado el fichero en la carpeta imagenes/. "
        "Es el valor que se envía en el campo `imagen` de POST /productos.",
        examples=["Lampara_3f9a1c2b.jpg"],
    )
    imagen_url: str = Field(
        description="Ruta de la foto en la API (relativa a su dirección).",
        examples=["/imagenes/Lampara_3f9a1c2b.jpg"],
    )


class ProductoRead(BaseModel):
    """Información de un producto que la API devuelve al cliente.

    Los atributos adicionales solo aparecen si corresponden al tipo de producto.
    """

    id: str = Field(examples=["fbc9b84d-63e3-4eb4-96c1-8ec982b351cd"])
    tipo: TipoProducto = Field(examples=["electronico"])
    nombre: str = Field(examples=["Altavoz Borealis Mini"])
    precio: float = Field(examples=[74.95])
    stock: int = Field(examples=[22])
    meses_garantia: Optional[int] = Field(default=None, examples=[30])
    talla: Optional[str] = Field(default=None, examples=["M"])
    color: Optional[str] = Field(default=None, examples=["Verde musgo"])
    imagen_url: Optional[str] = Field(
        default=None,
        description="Ruta de la foto en la API (relativa a su dirección). Solo aparece si el producto tiene imagen.",
        examples=["/imagenes/MacBook_NEO.jpg"],
    )

    @classmethod
    def desde_modelo(cls, producto: Producto) -> "ProductoRead":
        """Construye el esquema de salida a partir de un objeto de dominio Producto."""
        datos: Dict[str, Any] = {
            "id": producto.id,
            "nombre": producto.nombre,
            "precio": producto.precio,
            "stock": producto.stock,
        }
        if producto.imagen:
            datos["imagen_url"] = f"/imagenes/{quote(producto.imagen)}"
        if isinstance(producto, ProductoElectronico):
            datos.update(tipo="electronico", meses_garantia=producto.meses_garantia)
        elif isinstance(producto, ProductoRopa):
            datos.update(tipo="ropa", talla=producto.talla, color=producto.color)
        else:
            datos["tipo"] = "generico"
        return cls(**datos)
