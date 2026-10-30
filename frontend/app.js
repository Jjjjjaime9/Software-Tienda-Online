// Frontend de la Tienda Online.
// Se comunica con la API REST de FastAPI solo mediante peticiones HTTP (fetch).
// No accede a TiendaService ni a los modelos: únicamente conoce los endpoints.

// Dirección de la API por defecto: el mismo equipo que sirve la página, en el puerto 8000
// (si se abre como fichero, localhost). Así, si un compañero abre http://192.168.1.34:5500,
// la página usa la API de http://192.168.1.34:8000. Se puede cambiar desde la cabecera
// de la página (icono de conexión).
const API_URL_POR_DEFECTO = location.protocol.startsWith("http")
  ? `http://${location.hostname}:8000`
  : "http://localhost:8000";
let API_URL = leerGuardado("api_url") || API_URL_POR_DEFECTO;

// Estado de la página. Productos, usuarios y pedidos son copias de lo que devuelve
// la API; el carrito y el cliente activo solo existen en el navegador.
const estado = {
  productos: [],
  usuarios: [],
  pedidosCliente: [],                       // pedidos del cliente activo
  pedidosTodos: [],                         // pedidos de todos los clientes (administración)
  carrito: leerJson("carrito", {}),         // { productoId: cantidad }
  clienteId: leerGuardado("cliente_id") || "",
  filtro: { texto: "", tipo: "todos", orden: "relevancia", soloStock: false },
  textoUsuarios: "",
  // Resultado de la última búsqueda por nombre hecha en la API:
  // { ruta, ids } o null si no se está buscando nada
  busquedaProductos: null,
  busquedaUsuarios: null,
  cargandoProductos: true,
};

const STOCK_BAJO = 5;

// ===========================================================================
// 1. COMUNICACIÓN CON LA API
//    Todas las peticiones pasan por llamarApi(). Debajo hay una función por
//    endpoint, para ver de un vistazo qué endpoint usa cada operación.
// ===========================================================================

async function llamarApi(metodo, ruta, cuerpo) {
  const opciones = { method: metodo, headers: {} };
  if (cuerpo instanceof FormData) {
    // Ficheros (multipart/form-data): el navegador pone el Content-Type con su separador
    opciones.body = cuerpo;
  } else if (cuerpo !== undefined) {
    opciones.headers["Content-Type"] = "application/json";
    opciones.body = JSON.stringify(cuerpo);   // el cuerpo se envía como JSON
  }

  const respuesta = await fetch(API_URL + ruta, opciones);

  // 204 No Content (p. ej. al borrar) no trae cuerpo
  if (respuesta.status === 204) return null;

  // Si el cuerpo no es JSON (p. ej. un 500 en texto plano), datos queda a null
  const datos = await respuesta.json().catch(() => null);
  // respuesta.ok es true para los códigos 2xx (200, 201...)
  if (!respuesta.ok) {
    throw new Error(`HTTP ${respuesta.status}: ${textoDeError(datos?.detail) || respuesta.statusText}`);
  }
  return datos;
}

// Los errores de FastAPI vienen como {"detail": "..."}; en los de validación
// (422) "detail" es una lista con un mensaje por cada campo incorrecto.
function textoDeError(detalle) {
  if (Array.isArray(detalle)) {
    return detalle.map((e) => e.msg.replace(/^Value error, /, "")).join("; ");
  }
  return detalle;
}

// Los listados admiten filtros y paginación con parámetros de consulta (query params),
// p. ej. GET /productos?nombre=mac&skip=0&limit=10. La API devuelve como mucho
// `limit` resultados (100 como máximo), así que para tener una lista completa se
// piden páginas hasta que llega una incompleta.
const TAMANO_PAGINA = 100;

function rutaConConsulta(ruta, parametros = {}) {
  const consulta = new URLSearchParams();
  for (const [clave, valor] of Object.entries(parametros)) {
    if (valor !== undefined && valor !== null && valor !== "") consulta.set(clave, valor);
  }
  const texto = consulta.toString();
  return texto ? `${ruta}?${texto}` : ruta;
}

async function listarTodos(ruta, filtros = {}) {
  const todos = [];
  for (let skip = 0; ; skip += TAMANO_PAGINA) {
    const pagina = await llamarApi("GET", rutaConConsulta(ruta, { ...filtros, skip, limit: TAMANO_PAGINA }));
    todos.push(...pagina);
    if (pagina.length < TAMANO_PAGINA) return todos;
  }
}

const api = {
  listarProductos:  (filtros)     => listarTodos("/productos", filtros),   // filtros: { nombre }
  crearProducto:    (datos)       => llamarApi("POST", "/productos", datos),
  subirImagen:      (fichero)     => {
    const formulario = new FormData();
    formulario.append("archivo", fichero);
    return llamarApi("POST", "/imagenes", formulario);
  },
  eliminarProducto: (id)          => llamarApi("DELETE", `/productos/${encodeURIComponent(id)}`),
  listarUsuarios:   (filtros)     => listarTodos("/usuarios", filtros),    // filtros: { nombre }
  crearUsuario:     (datos)       => llamarApi("POST", "/usuarios", datos),
  crearPedido:      (datos)       => llamarApi("POST", "/pedidos", datos),
  pedidosDeUsuario: (clienteId)   => llamarApi("GET", `/usuarios/${encodeURIComponent(clienteId)}/pedidos`),
};

// ===========================================================================
// 2. CARGA DE DATOS
// ===========================================================================

async function cargarProductos() {
  try {
    estado.productos = await api.listarProductos();   // GET /productos?skip=0&limit=100
    sanearCarrito();
    if (estado.filtro.texto.trim()) buscarEnTienda();   // por si hay productos nuevos que coinciden
  } catch (error) {
    mostrarError(error);
  } finally {
    estado.cargandoProductos = false;
    pintarTienda();
    pintarCarrito();
    pintarInventario();
  }
}

async function cargarUsuarios() {
  try {
    estado.usuarios = await api.listarUsuarios();     // GET /usuarios?skip=0&limit=100
    pintarSelectorCliente();
    pintarUsuarios();
    if (estado.textoUsuarios.trim()) buscarUsuarios();
  } catch (error) {
    mostrarError(error);
  }
}

async function cargarPedidosCliente() {
  if (!estado.clienteId) {
    estado.pedidosCliente = [];
    pintarMisPedidos();
    return;
  }
  try {
    // GET /usuarios/{id}/pedidos
    estado.pedidosCliente = ordenarPorFecha(await api.pedidosDeUsuario(estado.clienteId));
  } catch (error) {
    estado.pedidosCliente = [];
    mostrarError(error);
  }
  pintarMisPedidos();
}

// La API no tiene un endpoint con todos los pedidos, así que el panel de
// administración pide el historial de cada cliente y los junta.
async function cargarTodosLosPedidos() {
  const clientes = estado.usuarios.filter((u) => !u.es_admin);
  try {
    const listas = await Promise.all(clientes.map((c) => api.pedidosDeUsuario(c.id)));
    estado.pedidosTodos = ordenarPorFecha(listas.flat());
  } catch (error) {
    mostrarError(error);
  }
  pintarAdmin();
  pintarInventario();
  pintarUsuarios();
}

// Busca por nombre en la API (GET /productos?nombre=... o GET /usuarios?nombre=...).
// Devuelve null si no hay nada que buscar, o undefined si mientras tanto se ha
// lanzado otra búsqueda del mismo recurso (así una respuesta lenta no pisa a una
// más reciente).
const ultimaBusqueda = {};
async function buscarPorNombre(recurso, texto) {
  const numero = (ultimaBusqueda[recurso] = (ultimaBusqueda[recurso] || 0) + 1);
  const nombre = texto.trim();
  if (!nombre) return null;
  const encontrados = await listarTodos(`/${recurso}`, { nombre });
  if (numero !== ultimaBusqueda[recurso]) return undefined;
  return { ruta: rutaConConsulta(`/${recurso}`, { nombre }), ids: new Set(encontrados.map((e) => e.id)) };
}

async function buscarEnTienda() {
  try {
    const resultado = await buscarPorNombre("productos", estado.filtro.texto);
    if (resultado === undefined) return;
    estado.busquedaProductos = resultado;
  } catch (error) {
    mostrarError(error);
  }
  pintarTienda();
}

async function buscarUsuarios() {
  try {
    const resultado = await buscarPorNombre("usuarios", estado.textoUsuarios);
    if (resultado === undefined) return;
    estado.busquedaUsuarios = resultado;
  } catch (error) {
    mostrarError(error);
  }
  pintarUsuarios();
}

function ordenarPorFecha(pedidos) {
  return [...pedidos].sort((a, b) => new Date(b.fecha) - new Date(a.fecha));
}

// ===========================================================================
// 3. TIENDA (catálogo)
// ===========================================================================

const NOMBRE_TIPO = { generico: "Genérico", electronico: "Electrónica", ropa: "Ropa" };

// Si el producto tiene foto, la API la sirve en imagen_url (p. ej. /imagenes/mesa.jpg).
// Si no, se dibuja un icono sobre un degradado cuyo tono depende del tipo y varía
// un poco con el nombre.
const TONO_TIPO = { electronico: 218, ropa: 340, generico: 32 };
const ICONOS = {
  electronico: `<svg viewBox="0 0 24 24"><rect x="4" y="5" width="16" height="11" rx="1.5"/><path d="M2 19h20"/></svg>`,
  ropa: `<svg viewBox="0 0 24 24"><path d="M9 4 4 6.5 2.5 11l3 1.2V20h13v-7.8l3-1.2L20 6.5 15 4a3 3 0 0 1-6 0Z"/></svg>`,
  generico: `<svg viewBox="0 0 24 24"><path d="M3 7.5 12 3l9 4.5v9L12 21l-9-4.5v-9Z"/><path d="M3 7.5 12 12l9-4.5M12 12v9"/></svg>`,
};

function estiloArte(p) {
  let hash = 0;
  for (const c of p.nombre) hash = (hash * 31 + c.charCodeAt(0)) % 997;
  const tono = (TONO_TIPO[p.tipo] ?? 200) + (hash % 40) - 20;
  return `--tono:${tono}`;
}

function arteProducto(p, clase = "") {
  if (p.imagen_url) {
    return `<div class="arte foto ${clase}"><img src="${esc(API_URL + p.imagen_url)}" alt="${esc(p.nombre)}" loading="lazy"></div>`;
  }
  return `<div class="arte ${clase}" style="${estiloArte(p)}">${ICONOS[p.tipo] || ICONOS.generico}</div>`;
}

function detallesProducto(p) {
  if (p.tipo === "electronico") return `Garantía de ${p.meses_garantia} meses`;
  if (p.tipo === "ropa") return `Talla ${esc(p.talla)} · ${esc(p.color)}`;
  return "Artículo de uso diario";
}

function insigniaStock(p) {
  if (p.stock === 0) return `<span class="insignia critico">✕ Agotado</span>`;
  if (p.stock <= STOCK_BAJO) return `<span class="insignia aviso">! Últimas ${p.stock} uds.</span>`;
  return "";
}

// El nombre lo filtra la API (estado.busquedaProductos); la categoría, la
// disponibilidad y el orden se aplican aquí, en el navegador.
function productosFiltrados() {
  const { tipo, orden, soloStock } = estado.filtro;
  const busqueda = estado.busquedaProductos;
  const lista = estado.productos.filter((p) =>
    (!busqueda || busqueda.ids.has(p.id)) &&
    (tipo === "todos" || p.tipo === tipo) &&
    (!soloStock || p.stock > 0)
  );
  const comparadores = {
    "precio-asc":  (a, b) => a.precio - b.precio,
    "precio-desc": (a, b) => b.precio - a.precio,
    "nombre":      (a, b) => a.nombre.localeCompare(b.nombre, "es"),
    "stock":       (a, b) => b.stock - a.stock,
  };
  return comparadores[orden] ? lista.sort(comparadores[orden]) : lista;
}

function pintarTienda() {
  const productos = estado.productos;
  document.getElementById("hero-productos").textContent = productos.length;
  document.getElementById("hero-stock").textContent =
    productos.reduce((suma, p) => suma + p.stock, 0).toLocaleString("es-ES");
  document.getElementById("hero-desde").textContent =
    productos.length ? euros(Math.min(...productos.map((p) => p.precio))) : "—";

  const rejilla = document.getElementById("rejilla-productos");
  const resultado = document.getElementById("resultado-filtros");

  if (estado.cargandoProductos) {
    resultado.textContent = "Cargando catálogo…";
    rejilla.innerHTML = `<div class="tarjeta esqueleto"></div>`.repeat(6);
    return;
  }

  const lista = productosFiltrados();
  resultado.innerHTML = `${lista.length} de ${productos.length} productos` +
    (estado.busquedaProductos ? ` · búsqueda en la API: ${codigoConsulta(estado.busquedaProductos.ruta)}` : "");

  if (lista.length === 0) {
    rejilla.innerHTML = estadoVacio(
      productos.length ? "Ningún producto coincide con los filtros." : "Todavía no hay productos en la tienda.",
      productos.length ? "Prueba con otra búsqueda o categoría." : "Créalos desde Administración → Inventario."
    );
    return;
  }

  rejilla.innerHTML = lista.map((p) => {
    const enCarrito = estado.carrito[p.id] || 0;
    const agotado = p.stock === 0;
    const sinMas = !agotado && enCarrito >= p.stock;
    return `
      <article class="tarjeta">
        <button class="tarjeta-imagen" data-ver="${esc(p.id)}" aria-label="Ver ${esc(p.nombre)}">
          ${arteProducto(p)}
          ${insigniaStock(p)}
          ${enCarrito ? `<span class="insignia en-carrito">${enCarrito} en el carrito</span>` : ""}
        </button>
        <div class="tarjeta-cuerpo">
          <span class="categoria">${NOMBRE_TIPO[p.tipo] || esc(p.tipo)}</span>
          <h3><button class="enlace" data-ver="${esc(p.id)}">${esc(p.nombre)}</button></h3>
          <p class="detalles">${detallesProducto(p)}</p>
          <div class="tarjeta-pie">
            <span class="precio">${euros(p.precio)}</span>
            <button class="boton-anadir" data-anadir="${esc(p.id)}" ${agotado || sinMas ? "disabled" : ""}>
              ${agotado ? "Agotado" : sinMas ? "Sin más stock" : "Añadir"}
            </button>
          </div>
        </div>
      </article>`;
  }).join("");
}

function verProducto(id) {
  const p = buscarProducto(id);
  if (!p) return;
  const disponible = p.stock - (estado.carrito[p.id] || 0);
  const dialogo = document.getElementById("dialogo-producto");
  dialogo.innerHTML = `
    <div class="ficha">
      ${arteProducto(p, "grande")}
      <div class="ficha-info">
        <button class="icono cerrar-dialogo" aria-label="Cerrar">
          <svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"/></svg>
        </button>
        <span class="categoria">${NOMBRE_TIPO[p.tipo] || esc(p.tipo)}</span>
        <h2>${esc(p.nombre)}</h2>
        <p class="precio grande">${euros(p.precio)}</p>
        <dl class="ficha-datos">
          ${p.tipo === "electronico" ? `<div><dt>Garantía</dt><dd>${p.meses_garantia} meses</dd></div>` : ""}
          ${p.tipo === "ropa" ? `<div><dt>Talla</dt><dd>${esc(p.talla)}</dd></div><div><dt>Color</dt><dd>${esc(p.color)}</dd></div>` : ""}
          <div><dt>Stock</dt><dd>${p.stock} uds. ${insigniaStock(p)}</dd></div>
          <div><dt>Referencia</dt><dd class="id">${esc(p.id.slice(0, 8))}</dd></div>
        </dl>
        ${disponible > 0 ? `
          <form class="ficha-comprar" id="form-ficha">
            <div class="selector-cantidad">
              <button type="button" class="icono" data-paso="-1" aria-label="Menos">−</button>
              <input type="number" name="cantidad" value="1" min="1" max="${disponible}" aria-label="Cantidad">
              <button type="button" class="icono" data-paso="1" aria-label="Más">+</button>
            </div>
            <button type="submit">Añadir al carrito</button>
          </form>` : `<p class="nota">${p.stock === 0 ? "Este producto está agotado." : "Ya tienes en el carrito todo el stock disponible."}</p>`}
      </div>
    </div>`;

  dialogo.querySelector(".cerrar-dialogo").addEventListener("click", () => dialogo.close());
  const form = dialogo.querySelector("#form-ficha");
  if (form) {
    const input = form.querySelector("input");
    form.addEventListener("click", (e) => {
      const paso = Number(e.target.dataset.paso || 0);
      if (paso) input.value = Math.min(disponible, Math.max(1, Number(input.value) + paso));
    });
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      anadirAlCarrito(p.id, Number(input.value));
      dialogo.close();
    });
  }
  dialogo.showModal();
}

// ===========================================================================
// 4. CARRITO (vive solo en el navegador hasta que se hace el pedido)
// ===========================================================================

function buscarProducto(id) {
  return estado.productos.find((p) => p.id === id);
}

function unidadesEnCarrito() {
  return Object.values(estado.carrito).reduce((suma, n) => suma + n, 0);
}

function totalCarrito() {
  return Object.entries(estado.carrito)
    .reduce((suma, [id, n]) => suma + (buscarProducto(id)?.precio || 0) * n, 0);
}

function anadirAlCarrito(id, cantidad = 1) {
  const p = buscarProducto(id);
  if (!p) return;
  const actual = estado.carrito[id] || 0;
  const nueva = Math.min(actual + cantidad, p.stock);
  if (nueva <= actual) {
    avisar(`No queda más stock de "${p.nombre}".`, "aviso");
    return;
  }
  estado.carrito[id] = nueva;
  guardarCarrito();
  avisar(`"${p.nombre}" añadido al carrito.`, "ok");
  const contador = document.getElementById("contador-carrito");
  contador.classList.remove("rebote");
  void contador.offsetWidth;                // reinicia la animación
  contador.classList.add("rebote");
}

function cambiarCantidad(id, cantidad) {
  const p = buscarProducto(id);
  if (!p || cantidad <= 0) delete estado.carrito[id];
  else estado.carrito[id] = Math.min(cantidad, p.stock);
  guardarCarrito();
}

// Tras recargar productos: quita los que ya no existen (p. ej. al reiniciar la
// API cambian los ids) y ajusta las cantidades al stock actual.
function sanearCarrito() {
  for (const [id, n] of Object.entries(estado.carrito)) {
    const p = buscarProducto(id);
    if (!p || p.stock === 0) delete estado.carrito[id];
    else if (n > p.stock) estado.carrito[id] = p.stock;
  }
  guardarJson("carrito", estado.carrito);
}

function guardarCarrito() {
  guardarJson("carrito", estado.carrito);
  pintarCarrito();
  pintarTienda();
}

function pintarCarrito() {
  const unidades = unidadesEnCarrito();
  const contador = document.getElementById("contador-carrito");
  contador.textContent = unidades;
  contador.hidden = unidades === 0;

  const contenedor = document.getElementById("carrito-lineas");
  const pie = document.getElementById("carrito-pie");
  const lineas = Object.entries(estado.carrito).filter(([id]) => buscarProducto(id));

  if (lineas.length === 0) {
    contenedor.innerHTML = estadoVacio("Tu carrito está vacío.", "Añade productos desde la tienda.");
    pie.hidden = true;
    return;
  }
  pie.hidden = false;

  contenedor.innerHTML = lineas.map(([id, n]) => {
    const p = buscarProducto(id);
    return `
      <div class="linea-carrito">
        ${arteProducto(p, "mini")}
        <div class="linea-info">
          <strong>${esc(p.nombre)}</strong>
          <span>${euros(p.precio)} / ud.</span>
          <div class="selector-cantidad pequeno">
            <button class="icono" data-cantidad="${esc(id)}" data-valor="${n - 1}" aria-label="Quitar una unidad">−</button>
            <span>${n}</span>
            <button class="icono" data-cantidad="${esc(id)}" data-valor="${n + 1}" ${n >= p.stock ? "disabled" : ""} aria-label="Añadir una unidad">+</button>
          </div>
        </div>
        <div class="linea-derecha">
          <strong>${euros(p.precio * n)}</strong>
          <button class="texto peligro-texto" data-cantidad="${esc(id)}" data-valor="0">Quitar</button>
        </div>
      </div>`;
  }).join("");

  document.getElementById("carrito-total").textContent = euros(totalCarrito());
  const cliente = clienteActivo();
  document.getElementById("carrito-cliente").innerHTML = cliente
    ? `Pedido a nombre de <strong>${esc(cliente.nombre)}</strong>`
    : `<span class="aviso-texto">Elige un cliente en la cabecera para poder comprar.</span>`;
  document.getElementById("realizar-pedido").disabled = !cliente;
}

function abrirCarrito() {
  document.getElementById("carrito").classList.add("abierto");
  document.getElementById("carrito").setAttribute("aria-hidden", "false");
  document.getElementById("velo-carrito").hidden = false;
}

function cerrarCarrito() {
  document.getElementById("carrito").classList.remove("abierto");
  document.getElementById("carrito").setAttribute("aria-hidden", "true");
  document.getElementById("velo-carrito").hidden = true;
}

async function realizarPedido() {
  const cliente = clienteActivo();
  if (!cliente) {
    avisar("Elige un cliente antes de realizar el pedido.", "error");
    return;
  }

  // Cada línea del carrito se convierte en un PedidoItemCreate
  const items = Object.entries(estado.carrito)
    .map(([producto_id, cantidad]) => ({ producto_id, cantidad }));

  const boton = document.getElementById("realizar-pedido");
  boton.disabled = true;
  boton.textContent = "Procesando…";
  try {
    const pedido = await api.crearPedido({ cliente_id: cliente.id, items });   // POST /pedidos -> 201
    estado.carrito = {};
    guardarCarrito();
    cerrarCarrito();
    mostrarConfirmacion(pedido);
    cargarPedidosCliente();
    cargarTodosLosPedidos();
  } catch (error) {
    mostrarError(error);
  } finally {
    boton.textContent = "Realizar pedido";
    cargarProductos();                     // el stock puede haber cambiado
  }
}

function mostrarConfirmacion(pedido) {
  const dialogo = document.getElementById("dialogo-pedido");
  dialogo.innerHTML = `
    <div class="confirmacion">
      <div class="confirmacion-icono" aria-hidden="true">
        <svg viewBox="0 0 24 24"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>
      </div>
      <h2>¡Pedido realizado!</h2>
      <p>Gracias, ${esc(pedido.cliente.nombre)}. Tu pedido <span class="id">#${esc(pedido.id.slice(0, 8))}</span> se ha registrado.</p>
      ${tablaLineas(pedido)}
      <div class="dialogo-acciones">
        <button class="secundario" value="pedidos">Ver mis pedidos</button>
        <button value="seguir">Seguir comprando</button>
      </div>
    </div>`;
  dialogo.querySelector(".dialogo-acciones").addEventListener("click", (e) => {
    if (!e.target.value) return;
    dialogo.close();
    if (e.target.value === "pedidos") cambiarSeccion("pedidos");
  });
  dialogo.showModal();
}

// ===========================================================================
// 5. CLIENTE ACTIVO Y MIS PEDIDOS
// ===========================================================================

function clienteActivo() {
  return estado.usuarios.find((u) => u.id === estado.clienteId && !u.es_admin);
}

// Solo los clientes pueden hacer pedidos, así que los administradores no se listan
function pintarSelectorCliente() {
  const clientes = estado.usuarios.filter((u) => !u.es_admin);
  if (!clientes.some((u) => u.id === estado.clienteId)) {
    estado.clienteId = clientes[0]?.id || "";
    guardarValor("cliente_id", estado.clienteId);
  }
  const select = document.getElementById("cliente-activo");
  select.innerHTML = clientes.length
    ? clientes.map((u) => `<option value="${esc(u.id)}">${esc(u.nombre)}</option>`).join("")
    : `<option value="">(no hay clientes)</option>`;
  select.value = estado.clienteId;
  pintarAvatarCliente();
  pintarCarrito();
  cargarPedidosCliente();
}

function pintarAvatarCliente() {
  const cliente = clienteActivo();
  const avatar = document.getElementById("avatar-cliente");
  avatar.textContent = cliente ? iniciales(cliente.nombre) : "?";
  avatar.style.setProperty("--tono", cliente ? tonoDeTexto(cliente.nombre) : 220);
}

function cambiarCliente(id) {
  estado.clienteId = id;
  guardarValor("cliente_id", id);
  pintarAvatarCliente();
  pintarCarrito();
  cargarPedidosCliente();
}

function pintarMisPedidos() {
  const cliente = clienteActivo();
  const pedidos = estado.pedidosCliente;
  const kpis = document.getElementById("kpis-cliente");
  const lista = document.getElementById("lista-pedidos");

  document.getElementById("pedidos-subtitulo").textContent = cliente
    ? `Historial de ${cliente.nombre} (${cliente.email}).`
    : "Elige un cliente en la cabecera para ver su historial.";

  if (!cliente) {
    kpis.innerHTML = "";
    lista.innerHTML = estadoVacio("No hay ningún cliente seleccionado.", "");
    return;
  }

  const gastado = pedidos.reduce((s, p) => s + p.total, 0);
  const unidades = pedidos.reduce((s, p) => s + p.items.reduce((t, i) => t + i.cantidad, 0), 0);
  kpis.innerHTML = [
    tarjetaKpi("Pedidos", pedidos.length),
    tarjetaKpi("Total gastado", euros(gastado)),
    tarjetaKpi("Artículos comprados", unidades),
    tarjetaKpi("Ticket medio", pedidos.length ? euros(gastado / pedidos.length) : "—"),
  ].join("");

  if (pedidos.length === 0) {
    lista.innerHTML = estadoVacio("Este cliente todavía no tiene pedidos.", "Los pedidos que hagas desde el carrito aparecerán aquí.");
    return;
  }

  lista.innerHTML = pedidos.map((p, indice) => `
    <details class="pedido" ${indice === 0 ? "open" : ""}>
      <summary>
        <div class="pedido-arte">${p.items.slice(0, 3).map((i) => {
          const producto = buscarProducto(i.producto_id);
          return producto ? arteProducto(producto, "mini") : `<div class="arte mini" style="--tono:220">${ICONOS.generico}</div>`;
        }).join("")}</div>
        <div class="pedido-resumen">
          <strong>Pedido #${esc(p.id.slice(0, 8))}</strong>
          <span>${fechaLarga(p.fecha)} · ${p.items.reduce((t, i) => t + i.cantidad, 0)} artículos</span>
        </div>
        <strong class="pedido-total">${euros(p.total)}</strong>
        <svg class="flecha" viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>
      </summary>
      <div class="pedido-detalle">
        ${tablaLineas(p)}
        <button class="secundario pequeno" data-repetir="${esc(p.id)}">Repetir pedido</button>
      </div>
    </details>`).join("");
}

function tablaLineas(pedido) {
  return `
    <div class="tabla-scroll">
      <table class="tabla-lineas">
        <thead><tr><th>Producto</th><th class="num">Precio</th><th class="num">Cant.</th><th class="num">Subtotal</th></tr></thead>
        <tbody>
          ${pedido.items.map((i) => `
            <tr>
              <td>${esc(i.nombre)}</td>
              <td class="num">${euros(i.precio_unitario)}</td>
              <td class="num">${i.cantidad}</td>
              <td class="num">${euros(i.subtotal)}</td>
            </tr>`).join("")}
        </tbody>
        <tfoot><tr><td colspan="3">Total</td><td class="num">${euros(pedido.total)}</td></tr></tfoot>
      </table>
    </div>`;
}

// Vuelve a meter en el carrito los productos de un pedido anterior (los que sigan existiendo)
function repetirPedido(id) {
  const pedido = estado.pedidosCliente.find((p) => p.id === id);
  if (!pedido) return;
  let anadidos = 0;
  for (const item of pedido.items) {
    const p = buscarProducto(item.producto_id);
    if (!p || p.stock === 0) continue;
    estado.carrito[p.id] = Math.min((estado.carrito[p.id] || 0) + item.cantidad, p.stock);
    anadidos++;
  }
  guardarCarrito();
  if (anadidos) {
    avisar(`${anadidos} producto(s) añadidos al carrito.`, "ok");
    abrirCarrito();
  } else {
    avisar("Ninguno de esos productos está disponible ahora.", "aviso");
  }
}

// ===========================================================================
// 6. ADMINISTRACIÓN
// ===========================================================================

function pintarAdmin() {
  const pedidos = estado.pedidosTodos;
  const clientes = estado.usuarios.filter((u) => !u.es_admin);
  const ventas = pedidos.reduce((s, p) => s + p.total, 0);
  const inventario = estado.productos.reduce((s, p) => s + p.precio * p.stock, 0);
  const stockBajo = estado.productos.filter((p) => p.stock <= STOCK_BAJO).length;

  document.getElementById("kpis-admin").innerHTML = [
    tarjetaKpi("Ventas totales", euros(ventas), "destacado"),
    tarjetaKpi("Pedidos", pedidos.length),
    tarjetaKpi("Ticket medio", pedidos.length ? euros(ventas / pedidos.length) : "—"),
    tarjetaKpi("Valor del inventario", euros(inventario)),
    tarjetaKpi("Productos con stock bajo", stockBajo, stockBajo ? "alerta" : ""),
  ].join("");

  // Unidades vendidas por producto (se agrupa por id; el nombre viene en cada línea)
  const vendidos = new Map();
  for (const p of pedidos) {
    for (const i of p.items) {
      const previo = vendidos.get(i.producto_id) || { nombre: i.nombre, valor: 0 };
      previo.valor += i.cantidad;
      vendidos.set(i.producto_id, previo);
    }
  }
  pintarBarras("grafico-vendidos", [...vendidos.values()], (v) => `${v} uds.`);

  const porCliente = clientes.map((c) => ({
    nombre: c.nombre,
    valor: pedidos.filter((p) => p.cliente.id === c.id).reduce((s, p) => s + p.total, 0),
  })).filter((c) => c.valor > 0);
  pintarBarras("grafico-clientes", porCliente, euros);

  const tbody = document.getElementById("tabla-ultimos-pedidos");
  tbody.innerHTML = pedidos.length
    ? pedidos.slice(0, 10).map((p) => `
        <tr>
          <td class="id">#${esc(p.id.slice(0, 8))}</td>
          <td>${fechaLarga(p.fecha)}</td>
          <td>${celdaUsuario(p.cliente)}</td>
          <td class="num">${p.items.reduce((t, i) => t + i.cantidad, 0)}</td>
          <td class="num"><strong>${euros(p.total)}</strong></td>
        </tr>`).join("")
    : `<tr><td colspan="5" class="vacio">Todavía no hay pedidos.</td></tr>`;
}

// Gráfico de barras horizontales (una sola serie) con el valor al final de cada
// barra y un tooltip al pasar el ratón.
function pintarBarras(idContenedor, datos, formato) {
  const contenedor = document.getElementById(idContenedor);
  if (datos.length === 0) {
    contenedor.innerHTML = `<p class="vacio">Sin datos todavía.</p>`;
    return;
  }
  const ordenados = [...datos].sort((a, b) => b.valor - a.valor).slice(0, 8);
  const maximo = ordenados[0].valor || 1;
  contenedor.innerHTML = ordenados.map((d) => `
    <div class="barra-fila" data-tip="${esc(d.nombre)}: ${esc(formato(d.valor))}">
      <span class="barra-etiqueta">${esc(d.nombre)}</span>
      <div class="barra-pista">
        <div class="barra" style="width:calc((100% - 84px) * ${d.valor / maximo})"></div>
        <span class="barra-valor">${esc(formato(d.valor))}</span>
      </div>
    </div>`).join("");
}

function tarjetaKpi(etiqueta, valor, clase = "") {
  return `<div class="kpi ${clase}"><span class="kpi-etiqueta">${esc(etiqueta)}</span><span class="kpi-valor">${esc(valor)}</span></div>`;
}

// ---------- Inventario ----------

function pintarInventario() {
  const tbody = document.getElementById("tabla-productos");
  if (estado.productos.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="vacio">No hay productos.</td></tr>`;
    return;
  }
  const vendidas = {};
  for (const p of estado.pedidosTodos) {
    for (const i of p.items) vendidas[i.producto_id] = (vendidas[i.producto_id] || 0) + i.cantidad;
  }
  tbody.innerHTML = estado.productos.map((p) => `
    <tr>
      <td>
        <div class="celda-producto">
          ${arteProducto(p, "mini")}
          <div><strong>${esc(p.nombre)}</strong><span>${detallesProducto(p)}</span></div>
        </div>
      </td>
      <td><span class="etiqueta">${NOMBRE_TIPO[p.tipo] || esc(p.tipo)}</span></td>
      <td class="num">${euros(p.precio)}</td>
      <td class="num">${p.stock} ${insigniaStock(p)}</td>
      <td class="num">${vendidas[p.id] || 0}</td>
      <td><button class="icono peligro-texto" data-borrar="${esc(p.id)}" aria-label="Eliminar ${esc(p.nombre)}">
        <svg viewBox="0 0 24 24"><path d="M4 7h16M10 11v6M14 11v6M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12M9 7V4h6v3"/></svg>
      </button></td>
    </tr>`).join("");
}

async function crearProducto(evento) {
  evento.preventDefault();
  const form = evento.target;
  const f = new FormData(form);
  const tipo = f.get("tipo");

  // Se construye el JSON que espera el esquema ProductoCreate
  const datos = {
    tipo,
    nombre: f.get("nombre"),
    precio: Number(f.get("precio")),
    stock: Number(f.get("stock")),
  };
  if (tipo === "electronico") datos.meses_garantia = Number(f.get("meses_garantia"));
  if (tipo === "ropa") {
    datos.talla = f.get("talla");
    datos.color = f.get("color");
  }
  const foto = f.get("foto");

  const boton = document.getElementById("crear-producto");
  boton.disabled = true;
  boton.textContent = foto?.size ? "Subiendo foto…" : "Creando…";
  try {
    // Si hay foto, primero se sube (POST /imagenes) y el producto guarda el nombre que devuelve
    if (foto?.size) {
      const subida = await api.subirImagen(foto);     // POST /imagenes -> 201
      datos.imagen = subida.imagen;
      boton.textContent = "Creando…";
    }
    const creado = await api.crearProducto(datos);    // POST /productos -> 201
    avisar(`Producto "${creado.nombre}" creado.`, "ok");
    form.reset();
    actualizarCamposProducto();
    mostrarPreviaFoto();
    await cargarProductos();
    pintarAdmin();
  } catch (error) {
    mostrarError(error);
  } finally {
    boton.disabled = false;
    boton.textContent = "Crear producto";
  }
}

// Miniatura de la foto elegida en el formulario de nuevo producto (sin fichero, se oculta)
const TAMANO_MAXIMO_FOTO = 5 * 1024 * 1024;   // el mismo límite que la API
let urlPreviaFoto = null;

function mostrarPreviaFoto() {
  const input = document.getElementById("producto-foto");
  const previa = document.getElementById("producto-foto-previa");
  const fichero = input.files[0];
  if (fichero && fichero.size > TAMANO_MAXIMO_FOTO) {
    avisar("La foto no puede superar los 5 MB.", "error");
    input.value = "";
  }
  if (urlPreviaFoto) URL.revokeObjectURL(urlPreviaFoto);
  urlPreviaFoto = input.files[0] ? URL.createObjectURL(input.files[0]) : null;
  previa.hidden = !urlPreviaFoto;
  if (urlPreviaFoto) previa.src = urlPreviaFoto;
  else previa.removeAttribute("src");
}

async function eliminarProducto(id) {
  const producto = buscarProducto(id);
  const confirmado = await confirmar(
    "Eliminar producto",
    `Se eliminará "${producto ? producto.nombre : id}" del catálogo. Esta acción no se puede deshacer.`
  );
  if (!confirmado) return;
  try {
    await api.eliminarProducto(id);                   // DELETE /productos/{id} -> 204
    avisar("Producto eliminado.", "ok");
    await cargarProductos();
    pintarAdmin();
  } catch (error) {
    mostrarError(error);
  }
}

// Muestra solo los campos que corresponden al tipo de producto elegido
function actualizarCamposProducto() {
  const tipo = document.getElementById("producto-tipo").value;
  for (const campo of document.querySelectorAll(".solo-electronico")) {
    campo.hidden = tipo !== "electronico";
    campo.querySelector("input").required = tipo === "electronico";
  }
  for (const campo of document.querySelectorAll(".solo-ropa")) {
    campo.hidden = tipo !== "ropa";
    campo.querySelector("input").required = tipo === "ropa";
  }
}

// ---------- Usuarios ----------

function pintarUsuarios() {
  const tbody = document.getElementById("tabla-usuarios");
  const busqueda = estado.busquedaUsuarios;
  const usuarios = busqueda ? estado.usuarios.filter((u) => busqueda.ids.has(u.id)) : estado.usuarios;

  const resultado = document.getElementById("resultado-usuarios");
  resultado.hidden = !busqueda;
  if (busqueda) {
    resultado.innerHTML = `${usuarios.length} de ${estado.usuarios.length} usuarios · búsqueda en la API: ${codigoConsulta(busqueda.ruta)}`;
  }

  if (usuarios.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="vacio">${busqueda ? "Ningún usuario coincide con la búsqueda." : "No hay usuarios."}</td></tr>`;
    return;
  }
  tbody.innerHTML = usuarios.map((u) => {
    const pedidos = estado.pedidosTodos.filter((p) => p.cliente.id === u.id);
    return `
      <tr>
        <td>${celdaUsuario(u, true)}</td>
        <td><span class="etiqueta ${u.es_admin ? "admin" : ""}">${u.es_admin ? "Administrador" : "Cliente"}</span></td>
        <td class="num">${u.es_admin ? "—" : pedidos.length}</td>
        <td class="num">${u.es_admin ? "—" : euros(pedidos.reduce((s, p) => s + p.total, 0))}</td>
        <td class="id" title="${esc(u.id)}">${esc(u.id.slice(0, 8))}…</td>
      </tr>`;
  }).join("");
}

function celdaUsuario(u, conEmail = false) {
  return `
    <div class="celda-usuario">
      <span class="avatar" style="--tono:${tonoDeTexto(u.nombre)}">${esc(iniciales(u.nombre))}</span>
      <div><strong>${esc(u.nombre)}</strong>${conEmail ? `<span>${esc(u.email)}</span>` : ""}</div>
    </div>`;
}

async function crearUsuario(evento) {
  evento.preventDefault();
  const form = evento.target;
  const f = new FormData(form);

  // JSON que espera el esquema UsuarioCreate (los administradores no llevan dirección)
  const datos = { nombre: f.get("nombre"), email: f.get("email"), tipo: f.get("tipo") };
  if (datos.tipo === "cliente") datos.direccion = f.get("direccion");

  try {
    const creado = await api.crearUsuario(datos);     // POST /usuarios -> 201
    avisar(`Usuario "${creado.nombre}" creado.`, "ok");
    form.reset();
    actualizarCampoDireccion();
    await cargarUsuarios();
    pintarAdmin();
  } catch (error) {
    mostrarError(error);
  }
}

function actualizarCampoDireccion() {
  const esCliente = document.getElementById("usuario-tipo").value === "cliente";
  const campo = document.getElementById("campo-direccion");
  campo.hidden = !esCliente;
  campo.querySelector("input").required = esCliente;
}

// ===========================================================================
// 7. UTILIDADES DE INTERFAZ
// ===========================================================================

// Escapa el texto antes de meterlo en el HTML (evita inyectar código con un nombre)
function esc(texto) {
  return String(texto ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

function euros(valor) {
  return Number(valor).toLocaleString("es-ES", { style: "currency", currency: "EUR" });
}

function fechaLarga(fecha) {
  return new Date(fecha).toLocaleString("es-ES", { dateStyle: "medium", timeStyle: "short" });
}

function iniciales(nombre) {
  return nombre.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join("");
}

function tonoDeTexto(texto) {
  let hash = 0;
  for (const c of texto) hash = (hash * 31 + c.charCodeAt(0)) % 360;
  return hash;
}

// Muestra la petición que se ha hecho a la API, p. ej. GET /productos?nombre=mac.
// En la URL real los caracteres especiales van codificados (maría -> mar%C3%ADa);
// aquí se decodifican para que se lea mejor.
function codigoConsulta(ruta) {
  const legible = decodeURIComponent(ruta.replace(/\+/g, " "));
  return `<code class="consulta" title="${esc(ruta)}">GET ${esc(legible)}</code>`;
}

// Espera a que se deje de escribir antes de llamar a la función (evita una petición por tecla)
function conRetardo(funcion, milisegundos = 300) {
  let temporizador;
  return (...argumentos) => {
    clearTimeout(temporizador);
    temporizador = setTimeout(() => funcion(...argumentos), milisegundos);
  };
}

function estadoVacio(titulo, texto) {
  return `<div class="vacio-grande"><strong>${esc(titulo)}</strong>${texto ? `<span>${esc(texto)}</span>` : ""}</div>`;
}

// Avisos flotantes que desaparecen solos
function avisar(texto, tipo = "ok") {
  const aviso = document.createElement("div");
  aviso.className = `aviso-flotante ${tipo}`;
  aviso.innerHTML = `<span class="aviso-icono" aria-hidden="true">${{ ok: "✓", error: "✕", aviso: "!" }[tipo]}</span><span>${esc(texto)}</span>`;
  document.getElementById("avisos").appendChild(aviso);
  setTimeout(() => {
    aviso.classList.add("saliendo");
    setTimeout(() => aviso.remove(), 300);
  }, tipo === "error" ? 7000 : 3500);
}

function mostrarError(error) {
  // fetch lanza TypeError cuando no puede conectar (API apagada, IP mal, CORS...)
  const texto = error instanceof TypeError
    ? `No se puede conectar con la API en ${API_URL}. ¿Está arrancada?`
    : error.message;
  avisar(texto, "error");
}

// Diálogo de confirmación que sustituye a confirm(); devuelve una promesa con true/false
function confirmar(titulo, texto) {
  const dialogo = document.getElementById("dialogo-confirmar");
  document.getElementById("confirmar-titulo").textContent = titulo;
  document.getElementById("confirmar-texto").textContent = texto;
  dialogo.returnValue = "";
  dialogo.showModal();
  return new Promise((resolver) => {
    dialogo.addEventListener("close", () => resolver(dialogo.returnValue === "si"), { once: true });
  });
}

function cambiarSeccion(seccion) {
  for (const boton of document.querySelectorAll(".pestana")) {
    boton.classList.toggle("activa", boton.dataset.seccion === seccion);
  }
  for (const s of document.querySelectorAll(".seccion")) {
    s.hidden = s.id !== seccion;
  }
  if (seccion === "pedidos") cargarPedidosCliente();
  if (seccion === "admin") cargarTodosLosPedidos();
  history.replaceState(null, "", `#/${seccion}`);  // la URL permite volver a la misma sección
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// Abre la sección indicada en la URL, p. ej. #/pedidos o #/admin/inventario.
// Se usa "#/" para que el navegador no salte al elemento con ese id.
function abrirSeccionDeUrl() {
  const [seccion, apartado] = location.hash.replace(/^#\/?/, "").split("/");
  if (document.getElementById(seccion)?.classList.contains("seccion")) cambiarSeccion(seccion);
  if (document.getElementById(`apartado-${apartado}`)) cambiarApartado(apartado);
}

function cambiarApartado(apartado) {
  if (location.hash.startsWith("#/admin")) history.replaceState(null, "", `#/admin/${apartado}`);
  for (const boton of document.querySelectorAll(".subpestana")) {
    boton.classList.toggle("activa", boton.dataset.apartado === apartado);
  }
  for (const a of document.querySelectorAll(".apartado")) {
    a.hidden = a.id !== `apartado-${apartado}`;
  }
}

// Tema claro/oscuro: sin elección guardada se sigue el del sistema
function aplicarTemaGuardado() {
  const tema = leerGuardado("tema");
  if (tema) document.documentElement.dataset.theme = tema;
}

function alternarTema() {
  const actual = document.documentElement.dataset.theme
    || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  const nuevo = actual === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = nuevo;
  guardarValor("tema", nuevo);
}

// Tooltip compartido por todos los elementos con data-tip
function activarTooltips() {
  const tooltip = document.getElementById("tooltip");
  document.addEventListener("pointermove", (e) => {
    const objetivo = e.target.closest?.("[data-tip]");
    if (!objetivo) { tooltip.hidden = true; return; }
    tooltip.textContent = objetivo.dataset.tip;
    tooltip.hidden = false;
    const x = Math.min(e.clientX + 14, window.innerWidth - tooltip.offsetWidth - 8);
    tooltip.style.transform = `translate(${x}px, ${e.clientY + 16}px)`;
  });
}

// Recuerda datos en este navegador (si el navegador lo permite)
function leerGuardado(clave) {
  try { return localStorage.getItem(clave); } catch { return null; }
}
function guardarValor(clave, valor) {
  try { localStorage.setItem(clave, valor); } catch { /* sin almacenamiento */ }
}
function leerJson(clave, porDefecto) {
  try { return JSON.parse(leerGuardado(clave)) || porDefecto; } catch { return porDefecto; }
}
function guardarJson(clave, valor) {
  guardarValor(clave, JSON.stringify(valor));
}

async function conectar() {
  const estadoApi = document.getElementById("estado-api");
  const punto = document.getElementById("punto-api");
  estadoApi.textContent = "conectando…";
  punto.className = "punto";
  document.getElementById("enlace-docs").href = API_URL + "/docs";

  estado.cargandoProductos = true;
  pintarTienda();
  await Promise.all([cargarProductos(), cargarUsuarios()]);
  try {
    await fetch(API_URL + "/openapi.json");
    estadoApi.textContent = `conectado a ${API_URL}`;
    punto.className = "punto ok";
  } catch {
    estadoApi.textContent = "sin conexión";
    punto.className = "punto error";
  }
  cargarTodosLosPedidos();
}

// ===========================================================================
// 8. ARRANQUE
// ===========================================================================

aplicarTemaGuardado();

document.addEventListener("DOMContentLoaded", () => {
  // --- Conexión con la API ---
  const inputApi = document.getElementById("api-url");
  const formApi = document.getElementById("form-api");
  const botonApi = document.getElementById("boton-api");
  inputApi.value = API_URL;
  botonApi.addEventListener("click", () => {
    formApi.hidden = !formApi.hidden;
    botonApi.setAttribute("aria-expanded", String(!formApi.hidden));
  });
  document.addEventListener("click", (e) => {
    if (!formApi.hidden && !e.target.closest(".api-ajustes")) {
      formApi.hidden = true;
      botonApi.setAttribute("aria-expanded", "false");
    }
  });
  formApi.addEventListener("submit", (e) => {
    e.preventDefault();
    API_URL = inputApi.value.trim().replace(/\/+$/, "");
    guardarValor("api_url", API_URL);
    formApi.hidden = true;
    conectar();
  });

  // --- Navegación ---
  for (const boton of document.querySelectorAll(".pestana")) {
    boton.addEventListener("click", () => cambiarSeccion(boton.dataset.seccion));
  }
  document.querySelector(".marca").addEventListener("click", (e) => {
    e.preventDefault();
    cambiarSeccion("tienda");
  });
  for (const boton of document.querySelectorAll(".subpestana")) {
    boton.addEventListener("click", () => cambiarApartado(boton.dataset.apartado));
  }
  document.getElementById("boton-tema").addEventListener("click", alternarTema);
  document.getElementById("cliente-activo").addEventListener("change", (e) => cambiarCliente(e.target.value));

  // --- Tienda: filtros y tarjetas ---
  const buscarEnTiendaConRetardo = conRetardo(buscarEnTienda);
  document.getElementById("filtro-texto").addEventListener("input", (e) => {
    estado.filtro.texto = e.target.value;
    buscarEnTiendaConRetardo();               // GET /productos?nombre=...
  });
  document.getElementById("filtro-tipo").addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    estado.filtro.tipo = chip.dataset.tipo;
    for (const c of document.querySelectorAll("#filtro-tipo .chip")) c.classList.toggle("activo", c === chip);
    pintarTienda();
  });
  document.getElementById("filtro-orden").addEventListener("change", (e) => {
    estado.filtro.orden = e.target.value;
    pintarTienda();
  });
  document.getElementById("filtro-stock").addEventListener("change", (e) => {
    estado.filtro.soloStock = e.target.checked;
    pintarTienda();
  });
  document.getElementById("rejilla-productos").addEventListener("click", (e) => {
    const anadir = e.target.closest("[data-anadir]");
    const ver = e.target.closest("[data-ver]");
    if (anadir) anadirAlCarrito(anadir.dataset.anadir);
    else if (ver) verProducto(ver.dataset.ver);
  });

  // --- Carrito ---
  document.getElementById("abrir-carrito").addEventListener("click", abrirCarrito);
  document.getElementById("cerrar-carrito").addEventListener("click", cerrarCarrito);
  document.getElementById("velo-carrito").addEventListener("click", cerrarCarrito);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") cerrarCarrito(); });
  document.getElementById("carrito-lineas").addEventListener("click", (e) => {
    const boton = e.target.closest("[data-cantidad]");
    if (boton) cambiarCantidad(boton.dataset.cantidad, Number(boton.dataset.valor));
  });
  document.getElementById("realizar-pedido").addEventListener("click", realizarPedido);
  document.getElementById("vaciar-carrito").addEventListener("click", () => {
    estado.carrito = {};
    guardarCarrito();
  });

  // --- Mis pedidos ---
  document.getElementById("recargar-pedidos").addEventListener("click", cargarPedidosCliente);
  document.getElementById("lista-pedidos").addEventListener("click", (e) => {
    const boton = e.target.closest("[data-repetir]");
    if (boton) repetirPedido(boton.dataset.repetir);
  });

  // --- Administración ---
  document.getElementById("recargar-admin").addEventListener("click", cargarTodosLosPedidos);
  document.getElementById("producto-tipo").addEventListener("change", actualizarCamposProducto);
  document.getElementById("form-producto").addEventListener("submit", crearProducto);
  document.getElementById("producto-foto").addEventListener("change", mostrarPreviaFoto);
  document.getElementById("recargar-productos").addEventListener("click", cargarProductos);
  document.getElementById("tabla-productos").addEventListener("click", (e) => {
    const boton = e.target.closest("[data-borrar]");
    if (boton) eliminarProducto(boton.dataset.borrar);
  });
  document.getElementById("usuario-tipo").addEventListener("change", actualizarCampoDireccion);
  document.getElementById("form-usuario").addEventListener("submit", crearUsuario);
  const buscarUsuariosConRetardo = conRetardo(buscarUsuarios);
  document.getElementById("buscar-usuarios").addEventListener("input", (e) => {
    estado.textoUsuarios = e.target.value;
    buscarUsuariosConRetardo();               // GET /usuarios?nombre=...
  });
  document.getElementById("recargar-usuarios").addEventListener("click", async () => {
    await cargarUsuarios();
    cargarTodosLosPedidos();
  });

  // Cerrar los diálogos al pulsar fuera de ellos
  for (const dialogo of document.querySelectorAll("dialog")) {
    dialogo.addEventListener("click", (e) => { if (e.target === dialogo) dialogo.close(); });
  }

  activarTooltips();
  actualizarCamposProducto();
  actualizarCampoDireccion();
  pintarCarrito();
  abrirSeccionDeUrl();
  conectar();
});
