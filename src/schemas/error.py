"""Esquema de las respuestas de error de la API."""
from pydantic import BaseModel, Field


class ErrorRead(BaseModel):
    """Formato común de los errores que devuelve la API (igual que HTTPException)."""

    detail: str = Field(examples=["No existe ningún producto con id '8664f167-f350-4fe4-be0b-db1616d2bb94'."])
