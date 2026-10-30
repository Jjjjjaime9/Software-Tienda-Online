"""Capa de servicios que centraliza las operaciones de la tienda online."""
from typing import Dict, List, Optional, Tuple

from models.pedido import Pedido
from models.producto import Producto, ProductoElectronico, ProductoRopa
from models.usuario import Administrador, Cliente, Usuario


class TiendaService:
    """Actúa como intermediario entre los usuarios y los productos de la tienda."""

    def __init__(self) -> None:
        self.usuarios: Dict[str, Usuario] = {}
        self.productos: Dict[str, Producto] = {}
        self.pedidos: List[Pedido] = []

    def registrar_usuario(self, tipo: str, nombre: str, email: str, **kwargs: str) -> Usuario:
        """Registra un nuevo usuario en la tienda según su tipo ('cliente' o 'administrador')."""
        if tipo == "cliente":
            usuario: Usuario = Cliente(nombre, email, kwargs.get("direccion", ""))
        elif tipo == "administrador":
            usuario = Administrador(nombre, email)
        else:
            raise ValueError(f"Tipo de usuario desconocido: {tipo}")
        self.usuarios[usuario.id] = usuario
        return usuario

    def agregar_producto(self, tipo: str, nombre: str, precio: float, stock: int, **kwargs) -> Producto:
        """Crea un producto de la categoría indicada y lo añade al inventario."""
        if tipo == "electronico":
            producto: Producto = ProductoElectronico(
                nombre, precio, stock, kwargs.get("meses_garantia", 0)
            )
        elif tipo == "ropa":
            producto = ProductoRopa(
                nombre, precio, stock, kwargs.get("talla", ""), kwargs.get("color", "")
            )
        elif tipo == "generico":
            producto = Producto(nombre, precio, stock)
        else:
            raise ValueError(f"Tipo de producto desconocido: {tipo}")
        self.productos[producto.id] = producto
        return producto

    def eliminar_producto(self, producto_id: str) -> bool:
        """Elimina un producto del inventario a partir de su identificador."""
        return self.productos.pop(producto_id, None) is not None

    def listar_productos(self) -> List[Producto]:
        """Devuelve la lista de todos los productos disponibles en la tienda."""
        return list(self.productos.values())

    def realizar_pedido(
        self, usuario_id: str, cantidades: List[Tuple[str, int]]
    ) -> Optional[Pedido]:
        """Genera un pedido si el cliente existe y hay stock suficiente de cada producto.

        Args:
            usuario_id: identificador del cliente que realiza el pedido.
            cantidades: lista de tuplas (producto_id, cantidad).

        Returns:
            El pedido creado, o None si el usuario no existe, no es cliente,
            algún producto no existe o no hay stock suficiente.
        """
        usuario = self.usuarios.get(usuario_id)
        if usuario is None or not isinstance(usuario, Cliente):
            return None

        lineas: List[Tuple[Producto, int]] = []
        for producto_id, cantidad in cantidades:
            producto = self.productos.get(producto_id)
            if producto is None or not producto.hay_stock(cantidad):
                return None
            lineas.append((producto, cantidad))

        for producto, cantidad in lineas:
            producto.actualizar_stock(-cantidad)

        pedido = Pedido(usuario, lineas)
        self.pedidos.append(pedido)
        return pedido

    def listar_pedidos_usuario(self, usuario_id: str) -> List[Pedido]:
        """Devuelve los pedidos de un usuario ordenados por fecha."""
        pedidos_usuario = [p for p in self.pedidos if p.cliente.id == usuario_id]
        return sorted(pedidos_usuario, key=lambda p: p.fecha)
