"""Modelo de pedido de la tienda online."""
import uuid
from datetime import datetime
from typing import List, Tuple

from models.producto import Producto
from models.usuario import Cliente


class Pedido:
    """Representa un pedido realizado por un cliente sobre una lista de productos."""

    def __init__(self, cliente: Cliente, lineas: List[Tuple[Producto, int]]) -> None:
        self.id: str = str(uuid.uuid4())
        self.cliente: Cliente = cliente
        self.lineas: List[Tuple[Producto, int]] = lineas
        self.fecha: datetime = datetime.now()

    def calcular_total(self) -> float:
        """Calcula el importe total del pedido en función de precios y cantidades."""
        return sum(producto.precio * cantidad for producto, cantidad in self.lineas)

    def __str__(self) -> str:
        detalle = ", ".join(f"{cantidad}x {producto.nombre}" for producto, cantidad in self.lineas)
        return (
            f"Pedido [{self.id}] de {self.cliente.nombre} "
            f"({self.fecha.strftime('%Y-%m-%d %H:%M:%S')}) | "
            f"Productos: {detalle} | Total: {self.calcular_total():.2f}€"
        )
