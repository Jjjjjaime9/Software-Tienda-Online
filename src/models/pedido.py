"""Modelo de pedido de la tienda online."""
import uuid
from datetime import datetime
from typing import List, Tuple

from models.producto import Producto
from models.usuario import Cliente


class LineaPedido:
    """Línea de un pedido: un producto, la cantidad y el precio que tenía al comprarlo."""

    def __init__(self, producto: Producto, cantidad: int) -> None:
        self.producto: Producto = producto
        self.cantidad: int = cantidad
        # Se guarda el precio del momento de la compra para que el pedido no cambie
        # si más adelante se modifica el precio del producto
        self.precio_unitario: float = producto.precio

    def calcular_subtotal(self) -> float:
        """Calcula el importe de la línea (precio unitario por cantidad)."""
        return self.precio_unitario * self.cantidad


class Pedido:
    """Representa un pedido realizado por un cliente sobre una lista de productos."""

    def __init__(self, cliente: Cliente, lineas: List[Tuple[Producto, int]]) -> None:
        self.id: str = str(uuid.uuid4())
        self.cliente: Cliente = cliente
        self.lineas: List[LineaPedido] = [
            LineaPedido(producto, cantidad) for producto, cantidad in lineas
        ]
        self.fecha: datetime = datetime.now()

    def calcular_total(self) -> float:
        """Calcula el importe total del pedido sumando el subtotal de cada línea."""
        return sum(linea.calcular_subtotal() for linea in self.lineas)

    def __str__(self) -> str:
        detalle = ", ".join(
            f"{linea.cantidad}x {linea.producto.nombre}" for linea in self.lineas
        )
        return (
            f"Pedido [{self.id}] de {self.cliente.nombre} "
            f"({self.fecha.strftime('%Y-%m-%d %H:%M:%S')}) | "
            f"Productos: {detalle} | Total: {self.calcular_total():.2f}€"
        )
