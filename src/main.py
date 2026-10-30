"""Punto de entrada del programa: prueba manual del funcionamiento de la tienda."""
import sys

from services.tienda_service import TiendaService

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    """Registra usuarios y productos de ejemplo, y simula pedidos en la tienda."""
    servicio = TiendaService()

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
        "electronico", "MacBook Neo", 699.95, 15, meses_garantia=18
    )
    msi = servicio.agregar_producto(
        "electronico", "Msi, Intel 9, 32 RAM", 1450.50, 12, meses_garantia=6
    )
    sudadera = servicio.agregar_producto(
        "ropa", "Sudadera EMEstudios", 45.50, 25, talla="XL", color="Gris"
    )
    pantalon = servicio.agregar_producto(
        "ropa", "Chino Easy Wear", 30.00, 18, talla="42", color="Beige"
    )
    mesa = servicio.agregar_producto(
        "generico", "Mesa de Trabajo", 50.50, 15
    )

    print("=== Inventario inicial ===")
    for producto in servicio.listar_productos():
        print(producto)
    print()

    print("=== Pedido 1 (Eladio) ===")
    pedido1 = servicio.realizar_pedido(cliente1.id, [(macbook.id, 1), (sudadera.id, 2)])
    print(pedido1)
    print()

    print("=== Pedido 2 (Yayo) ===")
    pedido2 = servicio.realizar_pedido(cliente2.id, [(msi.id, 1), (mesa.id, 3)])
    print(pedido2)
    print()

    print("=== Pedido 3 (Maria) ===")
    pedido3 = servicio.realizar_pedido(
        cliente3.id, [(pantalon.id, 1), (sudadera.id, 1), (mesa.id, 1)]
    )
    print(pedido3)
    print()

    print("=== Pedido 4 (María del Pilar) ===")
    pedido4 = servicio.realizar_pedido(cliente4.id, [(macbook.id, 1), (pantalon.id, 2)])
    print(pedido4)
    print()

    print("=== Pedido 5 (Guillem) ===")
    pedido5 = servicio.realizar_pedido(
        cliente6.id, [(msi.id, 1), (sudadera.id, 1), (mesa.id, 1)]
    )
    print(pedido5)
    print()

    print("=== Stock actualizado tras los pedidos ===")
    for producto in servicio.listar_productos():
        print(producto)
    print()

    print(f"=== Histórico de pedidos de {cliente1.nombre} ===")
    for pedido in servicio.listar_pedidos_usuario(cliente1.id):
        print(pedido)


if __name__ == "__main__":
    main()
