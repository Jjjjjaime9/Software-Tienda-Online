"""Esquemas Pydantic de usuario (peticiones y respuestas de la API)."""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from models.usuario import Usuario


class UsuarioCreate(BaseModel):
    """Datos que envía el cliente de la API para registrar un usuario."""

    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str = Field(min_length=2, max_length=80, examples=["Olaia Errazkin"])
    email: EmailStr = Field(examples=["olaia.errazkin@faromail.eus"])
    tipo: Literal["cliente", "administrador"] = Field(examples=["cliente"])
    direccion: Optional[str] = Field(
        default=None,
        max_length=150,
        description="Dirección postal. Obligatoria para clientes; los administradores no tienen.",
        examples=["Calle de los Tintoreros 21, Burgos"],
    )

    @model_validator(mode="after")
    def validar_direccion_segun_tipo(self) -> "UsuarioCreate":
        """Un cliente necesita dirección postal y un administrador no debe tenerla."""
        if self.tipo == "cliente" and not self.direccion:
            raise ValueError("Un cliente debe indicar una dirección postal.")
        if self.tipo == "administrador" and self.direccion is not None:
            raise ValueError("Un administrador no tiene dirección postal.")
        return self


class UsuarioRead(BaseModel):
    """Información de un usuario que la API devuelve al cliente."""

    id: str = Field(examples=["61aa060f-f6d8-48b7-8fda-698e76b00baa"])
    nombre: str = Field(examples=["Eladio Dapena"])
    email: str = Field(examples=["eladio.dapena@uie.edu"])
    es_admin: bool = Field(examples=[False])

    @classmethod
    def desde_modelo(cls, usuario: Usuario) -> "UsuarioRead":
        """Construye el esquema de salida a partir de un objeto de dominio Usuario."""
        return cls(
            id=usuario.id,
            nombre=usuario.nombre,
            email=usuario.email,
            es_admin=usuario.is_admin(),
        )
