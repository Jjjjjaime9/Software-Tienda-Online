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
        "Clara Montenegro",
        "clara.montenegro@correofresco.com",
        direccion="Travesía del Pilar 14, Zaragoza",
    )
    cliente2 = servicio.registrar_usuario(
        "cliente",
        "Bruno Salaverría",
        "bruno.salaverria@vientosur.net",
        direccion="Rambla de Poblenou 88, Barcelona",
    )
    cliente3 = servicio.registrar_usuario(
        "cliente",
        "Nadia Ferreiro",
        "nadia.ferreiro@ondamail.es",
        direccion="Cuesta de la Vega 7, Toledo",
    )
    servicio.registrar_usuario(
        "administrador", "Ignacio Bastos", "ignacio.bastos@tiendacentral.es"
    )

    tablet = servicio.agregar_producto(
        "electronico", "Tablet Nébula 10", 349.50, 12, meses_garantia=18
    )
    auriculares = servicio.agregar_producto(
        "electronico", "Auriculares Zenith Pro", 129.90, 40, meses_garantia=6
    )
    sudadera = servicio.agregar_producto(
        "ropa", "Sudadera Kodiak", 45.50, 25, talla="XL", color="Grafito"
    )
    falda = servicio.agregar_producto(
        "ropa", "Falda Marlow", 32.75, 18, talla="S", color="Terracota"
    )
    manual = servicio.agregar_producto(
        "generico", "Manual de Arquitectura de Software", 28.40, 15
    )

    print("=== Inventario inicial ===")
    for producto in servicio.listar_productos():
        print(producto)
    print()

    print("=== Pedido 1 (Clara) ===")
    pedido1 = servicio.realizar_pedido(cliente1.id, [(tablet.id, 1), (sudadera.id, 2)])
    print(pedido1)
    print()

    print("=== Pedido 2 (Bruno) ===")
    pedido2 = servicio.realizar_pedido(cliente2.id, [(auriculares.id, 1), (manual.id, 3)])
    print(pedido2)
    print()

    print("=== Pedido 3 (Nadia) ===")
    pedido3 = servicio.realizar_pedido(
        cliente3.id, [(falda.id, 1), (sudadera.id, 1), (manual.id, 1)]
    )
    print(pedido3)
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
