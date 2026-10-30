"""Esquemas Pydantic de pedido (peticiones y respuestas de la API)."""
from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from models.pedido import Pedido
from schemas.usuario import UsuarioRead


class PedidoItemCreate(BaseModel):
    """Línea de pedido enviada al crear un pedido: un producto y su cantidad."""

    producto_id: str = Field(examples=["575f07bf-c241-4e87-91a0-5fbcd517127c"])
    cantidad: int = Field(gt=0, le=1000, examples=[2])


class PedidoCreate(BaseModel):
    """Datos que envía el cliente de la API para realizar un pedido."""

    cliente_id: str = Field(examples=["61aa060f-f6d8-48b7-8fda-698e76b00baa"])
    items: List[PedidoItemCreate] = Field(min_length=1)


class PedidoItemRead(BaseModel):
    """Información de cada línea de un pedido que la API devuelve al cliente."""

    producto_id: str = Field(examples=["575f07bf-c241-4e87-91a0-5fbcd517127c"])
    nombre: str = Field(examples=["MacBook Neo"])
    precio_unitario: float = Field(examples=[699.95])
    cantidad: int = Field(examples=[1])
    subtotal: float = Field(examples=[699.95])


class PedidoRead(BaseModel):
    """Estructura completa de un pedido que la API devuelve al cliente."""

    id: str = Field(examples=["d0e99574-e790-4f2f-b581-b17dcf2c21cf"])
    fecha: datetime
    cliente: UsuarioRead
    total: float = Field(examples=[790.95])
    items: List[PedidoItemRead] = Field(
        examples=[
            [
                {
                    "producto_id": "575f07bf-c241-4e87-91a0-5fbcd517127c",
                    "nombre": "MacBook Neo",
                    "precio_unitario": 699.95,
                    "cantidad": 1,
                    "subtotal": 699.95,
                },
                {
                    "producto_id": "8c3e2a41-7b9d-4f6e-a1c5-2d0f9e8b7a63",
                    "nombre": "Sudadera EMEstudios",
                    "precio_unitario": 45.50,
                    "cantidad": 2,
                    "subtotal": 91.0,
                },
            ]
        ]
    )

    @classmethod
    def desde_modelo(cls, pedido: Pedido) -> "PedidoRead":
        """Construye el esquema de salida a partir de un objeto de dominio Pedido."""
        return cls(
            id=pedido.id,
            fecha=pedido.fecha,
            cliente=UsuarioRead.desde_modelo(pedido.cliente),
            total=round(pedido.calcular_total(), 2),
            items=[
                PedidoItemRead(
                    producto_id=linea.producto.id,
                    nombre=linea.producto.nombre,
                    precio_unitario=linea.precio_unitario,
                    cantidad=linea.cantidad,
                    subtotal=round(linea.calcular_subtotal(), 2),
                )
                for linea in pedido.lineas
            ],
        )
