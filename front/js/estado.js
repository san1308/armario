// Estado compartido entre vistas y un bus de eventos mínimo.
import { api } from './api.js';

export const estado = {
  usuario: null,
  zonas: [],            // [{slug, nombre}]
  categorias: [],       // [{slug, nombre, zona}]
  prendas: [],          // todas las del usuario
  conjuntos: [],
};

const oyentes = new Set();
export const alCambiar = (fn) => oyentes.add(fn);
const avisar = () => oyentes.forEach((fn) => fn());

export const categoria = (slug) => estado.categorias.find((c) => c.slug === slug);
export const nombreCategoria = (slug) => categoria(slug)?.nombre ?? 'Sin clasificar';
export const prendaPorId = (id) => estado.prendas.find((p) => p.id === id);
export const listasDeZona = (zona) => estado.prendas.filter((p) => p.zona === zona && p.estado === 'lista');
export const hayPendientes = () => estado.prendas.some((p) => p.estado === 'pendiente' || p.estado === 'procesando');

export async function cargarTodo() {
  const [usuario, catalogo, prendas, conjuntos] = await Promise.all([
    api.yo(), api.catalogo(), api.prendas(), api.conjuntos(),
  ]);
  Object.assign(estado, { usuario, zonas: catalogo.zonas, categorias: catalogo.categorias, prendas, conjuntos });
  avisar();
}

export async function recargarPrendas() {
  estado.prendas = await api.prendas();
  avisar();
}

export async function recargarConjuntos() {
  estado.conjuntos = await api.conjuntos();
  avisar();
}

/** Sustituye una prenda en el estado tras un PATCH, sin recargar todo. */
export function reemplazarPrenda(p) {
  const i = estado.prendas.findIndex((x) => x.id === p.id);
  if (i >= 0) estado.prendas[i] = p; else estado.prendas.unshift(p);
  avisar();
}

export function quitarPrenda(id) {
  estado.prendas = estado.prendas.filter((p) => p.id !== id);
  for (const c of estado.conjuntos) for (const k of ['exterior_id', 'arriba_id', 'abajo_id', 'entera_id']) if (c[k] === id) c[k] = null;
  estado.conjuntos = estado.conjuntos.filter((c) => c.exterior_id || c.arriba_id || c.abajo_id || c.entera_id);
  avisar();
}
