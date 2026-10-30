# Tienda-Online-A-S

**Autor:** Jjjjjaime9

## Descripción

Aplicación en Python que modela una tienda online. Esta primera versión se ejecuta en consola y
está diseñada para evolucionar hacia una API REST con FastAPI en prácticas posteriores.

El sistema permite:

- Gestionar **productos** de distintas categorías: electrónicos (con meses de garantía),
  ropa (con talla y color) y genéricos.
- Registrar **usuarios**: clientes (con dirección postal) y administradores.
- Realizar **pedidos** comprobando que el cliente existe y que hay stock suficiente,
  descontando las unidades del inventario y calculando el importe total.
- Consultar el histórico de pedidos de un cliente ordenado por fecha.

Toda la lógica se centraliza en la capa de servicios `TiendaService`.

## Estructura del proyecto

```
Tienda-Online-A-S/
├── main.py                  # Punto de entrada: carga datos de ejemplo y simula pedidos
├── models/
│   ├── producto.py          # Producto, ProductoElectronico, ProductoRopa
│   ├── usuario.py           # Usuario, Cliente, Administrador
│   └── pedido.py            # Pedido
└── services/
    └── tienda_service.py    # TiendaService
```

## Ejecución

Requiere Python 3.10 o superior (no tiene dependencias externas).

```bash
python main.py
```
