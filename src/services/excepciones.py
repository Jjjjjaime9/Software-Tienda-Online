"""Excepciones de la lógica de negocio de la tienda online.

Permiten que la capa de exposición (la API) distinga el motivo exacto de un fallo
y lo traduzca al código HTTP adecuado.
"""


class TiendaError(Exception):
    """Excepción base de todos los errores de la tienda."""


class UsuarioNoEncontradoError(TiendaError):
    """El usuario indicado no existe."""

    def __init__(self, usuario_id: str) -> None:
        super().__init__(f"No existe ningún usuario con id '{usuario_id}'.")


class UsuarioNoEsClienteError(TiendaError):
    """La operación requiere un cliente y el usuario indicado no lo es."""

    def __init__(self, usuario_id: str) -> None:
        super().__init__(f"El usuario '{usuario_id}' no es un cliente.")


class EmailDuplicadoError(TiendaError):
    """Ya existe un usuario registrado con ese email."""

    def __init__(self, email: str) -> None:
        super().__init__(f"Ya existe un usuario registrado con el email '{email}'.")


class ProductoNoEncontradoError(TiendaError):
    """El producto indicado no existe."""

    def __init__(self, producto_id: str) -> None:
        super().__init__(f"No existe ningún producto con id '{producto_id}'.")


class StockInsuficienteError(TiendaError):
    """No hay stock suficiente de un producto para la cantidad solicitada."""

    def __init__(self, nombre: str, solicitado: int, disponible: int) -> None:
        super().__init__(
            f"Stock insuficiente de '{nombre}': solicitadas {solicitado} unidades, "
            f"disponibles {disponible}."
        )
