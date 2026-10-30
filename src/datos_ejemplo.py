"""Datos de ejemplo con los que arranca la tienda para poder probar la API desde /docs."""
from services.tienda_service import TiendaService


def cargar_datos_ejemplo(servicio: TiendaService) -> None:
    """Registra usuarios, productos y pedidos de ejemplo en el servicio indicado."""
    cliente1 = servicio.registrar_usuario(
        "cliente",
        "Eladio Dapena",
        "eladio.dapena@uie.edu",
        direccion="Travesía del Pilar 14, Zaragoza",
    )
    cliente2 = servicio.registrar_usuario(
        "cliente",
        "Yayo Rodriguez",
        "yayo.rodriguez@gmail.com",
        direccion="Rambla de Poblenou 88, Barcelona",
    )
    cliente3 = servicio.registrar_usuario(
        "cliente",
        "Maria Ecker",
        "maria.ecker@gmail.com",
        direccion="Cuesta de la Vega 7, Toledo",
    )
    cliente4 = servicio.registrar_usuario(
        "cliente",
        "María del Pilar Rodríguez",
        "mariapilar.rodriguez@gmail.com",
        direccion="Calle Real 32, A Coruña",
    )
    servicio.registrar_usuario(
        "cliente",
        "Delfina Barrosa",
        "delfina.barrosa@gmail.com",
        direccion="Avenida de la Constitución 5, Sevilla",
    )
    cliente6 = servicio.registrar_usuario(
        "cliente",
        "Guillem Alberti",
        "guillem.alberti@gmail.com",
        direccion="Carrer de Sant Miquel 19, Girona",
    )
    servicio.registrar_usuario(
        "administrador", "Jaime Calviño", "jaime.calvino@tiendacentral.es"
    )

    macbook = servicio.agregar_producto(
        "electronico", "MacBook Neo", 699.95, 15, meses_garantia=18, imagen="MacBook_NEO.jpg"
    )
    msi = servicio.agregar_producto(
        "electronico", "Msi, Intel 9, 32 RAM", 1450.50, 12, meses_garantia=6,
        imagen="MSI_Intel9.webp",
    )
    sudadera = servicio.agregar_producto(
        "ropa", "Sudadera EMEstudios", 45.50, 25, talla="XL", color="Gris",
        imagen="EMEStudios_Sudadera.webp",
    )
    pantalon = servicio.agregar_producto(
        "ropa", "Chino Easy Wear", 30.00, 18, talla="42", color="Beige",
        imagen="Chino_Easy_Wear.avif",
    )
    mesa = servicio.agregar_producto(
        "generico", "Mesa de Trabajo", 50.50, 15, imagen="Mesa_Trabajo.jpg"
    )

    servicio.realizar_pedido(cliente1.id, [(macbook.id, 1), (sudadera.id, 2)])
    servicio.realizar_pedido(cliente2.id, [(msi.id, 1), (mesa.id, 3)])
    servicio.realizar_pedido(cliente3.id, [(pantalon.id, 1), (sudadera.id, 1), (mesa.id, 1)])
    servicio.realizar_pedido(cliente4.id, [(macbook.id, 1), (pantalon.id, 2)])
    servicio.realizar_pedido(cliente6.id, [(msi.id, 1), (sudadera.id, 1), (mesa.id, 1)])
