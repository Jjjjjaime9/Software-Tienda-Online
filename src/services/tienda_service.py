"""Capa de servicios que centraliza las operaciones de la tienda online."""
import unicodedata
from typing import Dict, List, Optional, Sequence, Tuple, TypeVar

from models.pedido import Pedido
from models.producto import Producto, ProductoElectronico, ProductoRopa
from models.usuario import Administrador, Cliente, Usuario
from services.excepciones import (
    EmailDuplicadoError,
    ProductoNoEncontradoError,
    StockInsuficienteError,
    UsuarioNoEncontradoError,
    UsuarioNoEsClienteError,
)

T = TypeVar("T")


def _normalizar(texto: str) -> str:
    """Pasa el texto a minúsculas y le quita las tildes para comparar nombres."""
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn").casefold()


def _coincide_nombre(nombre: str, buscado: Optional[str]) -> bool:
    """Indica si el nombre contiene el texto buscado (sin distinguir mayúsculas ni tildes).

    Si no se busca nada (None), todos los nombres coinciden.
    """
    return buscado is None or _normalizar(buscado.strip()) in _normalizar(nombre)


def _paginar(elementos: Sequence[T], skip: int = 0, limit: Optional[int] = None) -> List[T]:
    """Devuelve como mucho `limit` elementos, saltándose los `skip` primeros."""
    fin = None if limit is None else skip + limit
    return list(elementos[skip:fin])


class TiendaService:
    """Actúa como intermediario entre los usuarios y los productos de la tienda."""

    def __init__(self) -> None:
        self.usuarios: Dict[str, Usuario] = {}
        self.productos: Dict[str, Producto] = {}
        self.pedidos: List[Pedido] = []

    # ------------------------------------------------------------------ usuarios

    def registrar_usuario(self, tipo: str, nombre: str, email: str, **kwargs: str) -> Usuario:
        """Registra un nuevo usuario en la tienda según su tipo ('cliente' o 'administrador').

        Raises:
            EmailDuplicadoError: si ya hay un usuario registrado con ese email.
            ValueError: si el tipo de usuario no es válido.
        """
        if any(u.email.lower() == email.lower() for u in self.usuarios.values()):
            raise EmailDuplicadoError(email)

        if tipo == "cliente":
            usuario: Usuario = Cliente(nombre, email, kwargs.get("direccion", ""))
        elif tipo == "administrador":
            usuario = Administrador(nombre, email)
        else:
            raise ValueError(f"Tipo de usuario desconocido: {tipo}")
        self.usuarios[usuario.id] = usuario
        return usuario

    def listar_usuarios(
        self, nombre: Optional[str] = None, skip: int = 0, limit: Optional[int] = None
    ) -> List[Usuario]:
        """Devuelve los usuarios registrados, opcionalmente filtrados por nombre y paginados.

        Args:
            nombre: texto que debe aparecer en el nombre (sin distinguir mayúsculas
                ni tildes). Si es None, no se filtra.
            skip: número de usuarios que se saltan desde el principio.
            limit: número máximo de usuarios devueltos. Si es None, se devuelven todos.
        """
        encontrados = [u for u in self.usuarios.values() if _coincide_nombre(u.nombre, nombre)]
        return _paginar(encontrados, skip, limit)

    def obtener_usuario(self, usuario_id: str) -> Usuario:
        """Devuelve el usuario con el identificador indicado.

        Raises:
            UsuarioNoEncontradoError: si el usuario no existe.
        """
        usuario = self.usuarios.get(usuario_id)
        if usuario is None:
            raise UsuarioNoEncontradoError(usuario_id)
        return usuario

    # ----------------------------------------------------------------- productos

    def agregar_producto(
        self,
        tipo: str,
        nombre: str,
        precio: float,
        stock: int,
        imagen: Optional[str] = None,
        **kwargs,
    ) -> Producto:
        """Crea un producto de la categoría indicada y lo añade al inventario.

        Args:
            imagen: nombre del fichero de la foto dentro de la carpeta imagenes/ (opcional).
        """
        if tipo == "electronico":
            producto: Producto = ProductoElectronico(
                nombre, precio, stock, kwargs.get("meses_garantia", 0), imagen=imagen
            )
        elif tipo == "ropa":
            producto = ProductoRopa(
                nombre, precio, stock, kwargs.get("talla", ""), kwargs.get("color", ""), imagen=imagen
            )
        elif tipo == "generico":
            producto = Producto(nombre, precio, stock, imagen=imagen)
        else:
            raise ValueError(f"Tipo de producto desconocido: {tipo}")
        self.productos[producto.id] = producto
        return producto

    def obtener_producto(self, producto_id: str) -> Producto:
        """Devuelve el producto con el identificador indicado.

        Raises:
            ProductoNoEncontradoError: si el producto no existe.
        """
        producto = self.productos.get(producto_id)
        if producto is None:
            raise ProductoNoEncontradoError(producto_id)
        return producto

    def eliminar_producto(self, producto_id: str) -> bool:
        """Elimina un producto del inventario a partir de su identificador."""
        return self.productos.pop(producto_id, None) is not None

    def listar_productos(
        self, nombre: Optional[str] = None, skip: int = 0, limit: Optional[int] = None
    ) -> List[Producto]:
        """Devuelve los productos de la tienda, opcionalmente filtrados por nombre y paginados.

        Args:
            nombre: texto que debe aparecer en el nombre (sin distinguir mayúsculas
                ni tildes). Si es None, no se filtra.
            skip: número de productos que se saltan desde el principio.
            limit: número máximo de productos devueltos. Si es None, se devuelven todos.
        """
        encontrados = [p for p in self.productos.values() if _coincide_nombre(p.nombre, nombre)]
        return _paginar(encontrados, skip, limit)

    # ------------------------------------------------------------------- pedidos

    def realizar_pedido(self, usuario_id: str, cantidades: List[Tuple[str, int]]) -> Pedido:
        """Genera un pedido si el cliente existe y hay stock suficiente de cada producto.

        El stock solo se descuenta cuando todas las líneas son válidas, de modo que
        un pedido rechazado nunca deja el inventario a medias.

        Args:
            usuario_id: identificador del cliente que realiza el pedido.
            cantidades: lista de tuplas (producto_id, cantidad).

        Raises:
            UsuarioNoEncontradoError: si el usuario no existe.
            UsuarioNoEsClienteError: si el usuario no es un cliente.
            ProductoNoEncontradoError: si algún producto no existe.
            StockInsuficienteError: si no hay stock suficiente de algún producto.
        """
        usuario = self.obtener_usuario(usuario_id)
        if not isinstance(usuario, Cliente):
            raise UsuarioNoEsClienteError(usuario_id)

        lineas: List[Tuple[Producto, int]] = []
        solicitado_por_producto: Dict[str, int] = {}
        for producto_id, cantidad in cantidades:
            producto = self.obtener_producto(producto_id)
            # Se acumula por producto por si aparece repetido en varias líneas
            total_solicitado = solicitado_por_producto.get(producto_id, 0) + cantidad
            if not producto.hay_stock(total_solicitado):
                raise StockInsuficienteError(producto.nombre, total_solicitado, producto.stock)
            solicitado_por_producto[producto_id] = total_solicitado
            lineas.append((producto, cantidad))

        for producto, cantidad in lineas:
            producto.actualizar_stock(-cantidad)

        pedido = Pedido(usuario, lineas)
        self.pedidos.append(pedido)
        return pedido

    def listar_pedidos_usuario(self, usuario_id: str) -> List[Pedido]:
        """Devuelve los pedidos de un cliente ordenados por fecha.

        Raises:
            UsuarioNoEncontradoError: si el usuario no existe.
            UsuarioNoEsClienteError: si el usuario no es un cliente.
        """
        usuario = self.obtener_usuario(usuario_id)
        if not isinstance(usuario, Cliente):
            raise UsuarioNoEsClienteError(usuario_id)

        pedidos_usuario = [p for p in self.pedidos if p.cliente.id == usuario_id]
        return sorted(pedidos_usuario, key=lambda p: p.fecha)
