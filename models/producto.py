"""Modelos de producto de la tienda online."""
import uuid


class Producto:
    """Clase base que representa un producto genérico de la tienda."""

    def __init__(self, nombre: str, precio: float, stock: int) -> None:
        self.id: str = str(uuid.uuid4())
        self.nombre: str = nombre
        self.precio: float = precio
        self.stock: int = stock

    def hay_stock(self, cantidad: int) -> bool:
        """Comprueba si hay stock suficiente para la cantidad solicitada."""
        return self.stock >= cantidad

    def actualizar_stock(self, cantidad: int) -> None:
        """Actualiza el stock. Usar valores negativos en compras y positivos en reposiciones."""
        nuevo_stock = self.stock + cantidad
        if nuevo_stock < 0:
            raise ValueError("El stock no puede quedar por debajo de cero.")
        self.stock = nuevo_stock

    def __str__(self) -> str:
        return f"[{self.id}] {self.nombre} - {self.precio:.2f}€ (stock: {self.stock})"


class ProductoElectronico(Producto):
    """Producto electrónico, con meses de garantía como atributo adicional."""

    def __init__(self, nombre: str, precio: float, stock: int, meses_garantia: int) -> None:
        super().__init__(nombre, precio, stock)
        self.meses_garantia: int = meses_garantia

    def __str__(self) -> str:
        return f"{super().__str__()} | Garantía: {self.meses_garantia} meses"


class ProductoRopa(Producto):
    """Producto de ropa, con talla y color como atributos adicionales."""

    def __init__(self, nombre: str, precio: float, stock: int, talla: str, color: str) -> None:
        super().__init__(nombre, precio, stock)
        self.talla: str = talla
        self.color: str = color

    def __str__(self) -> str:
        return f"{super().__str__()} | Talla: {self.talla}, Color: {self.color}"
