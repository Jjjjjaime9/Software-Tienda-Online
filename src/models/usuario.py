"""Modelos de usuario de la tienda online."""
import uuid


class Usuario:
    """Clase base que representa a cualquier persona que interactúa con la tienda."""

    def __init__(self, nombre: str, email: str) -> None:
        self.id: str = str(uuid.uuid4())
        self.nombre: str = nombre
        self.email: str = email

    def is_admin(self) -> bool:
        """Indica si el usuario tiene privilegios de administrador."""
        return False

    def __str__(self) -> str:
        return f"[{self.id}] {self.nombre} ({self.email})"


class Cliente(Usuario):
    """Usuario de tipo cliente, con dirección postal como atributo adicional."""

    def __init__(self, nombre: str, email: str, direccion: str) -> None:
        super().__init__(nombre, email)
        self.direccion: str = direccion

    def __str__(self) -> str:
        return f"{super().__str__()} | Dirección: {self.direccion}"


class Administrador(Usuario):
    """Usuario de tipo administrador, gestor de la tienda."""

    def is_admin(self) -> bool:
        return True
