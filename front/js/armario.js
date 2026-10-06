// Vista Armario: subir fotos, filtrar y abrir la ficha de cada prenda.
import { api, urlImagen } from './api.js';
import { estado, hayPendientes, nombreCategoria, recargarPrendas } from './estado.js';
import { abrirFicha } from './ficha.js';
import { aviso, el } from './util.js';

const $ = (id) => document.getElementById(id);
const TANDA = 4;           // fotos por petición: evita peticiones enormes desde el móvil
let filtro = null;          // tipo: null = todas, 'sin' = sin clasificar, o slug de zona
let filtroTemp = null;      // temporada: null = todas, 'ninguna' = sin temporada, o slug
let sondeo = null;

const pasaTipo = (p, f = filtro) => f === null || (f === 'sin' ? !p.categoria : p.zona === f);
const pasaTemp = (p, f = filtroTemp) => f === null || (f === 'ninguna' ? !p.temporadas.length : p.temporadas.includes(f));
const filtradas = () => estado.prendas.filter((p) => pasaTipo(p) && pasaTemp(p));

function filaFiltros(contenedor, opciones, actual, contar, alElegir, destacado) {
  const cont = $(contenedor);
  cont.replaceChildren();
  for (const [valor, texto] of opciones) {
    const n = contar(valor);
    if (valor !== null && !n && valor !== actual) continue;
    const b = el('button.filtro', { 'aria-pressed': String(actual === valor), onclick: () => { alElegir(valor); render(); } },
      texto, el('span.n', {}, String(n)));
    if (valor === destacado) b.classList.add('destacado');
    cont.append(b);
  }
}

function renderFiltros() {
  // Cada fila cuenta teniendo en cuenta el filtro de la otra
  filaFiltros('filtros',
    [[null, 'Todas'], ['sin', 'Sin clasificar'], ...estado.zonas.map((z) => [z.slug, z.nombre])],
    filtro, (v) => estado.prendas.filter((p) => pasaTipo(p, v) && pasaTemp(p)).length,
    (v) => { filtro = v; }, 'sin');
  filaFiltros('filtros-temporada',
    [[null, 'Todas las temporadas'], ...estado.temporadas.map((t) => [t.slug, t.nombre]), ['ninguna', 'Sin temporada']],
    filtroTemp, (v) => estado.prendas.filter((p) => pasaTipo(p) && pasaTemp(p, v)).length,
    (v) => { filtroTemp = v; }, 'ninguna');
}

function tarjeta(p, lista) {
  const t = el('button.tarjeta', { onclick: () => abrirFicha(p.id, lista.map((x) => x.id)) });
  if (p.estado === 'lista') {
    t.append(el('img', { src: urlImagen(p, 'mini'), alt: p.nombre || nombreCategoria(p.categoria), loading: 'lazy' }));
  } else if (p.estado === 'error') {
    t.classList.add('error');
    t.append(el('div.estado', {}, 'No se pudo quitar el fondo. Toca para reintentar.'));
  } else {
    t.append(el('div.estado', {}, el('div.girando'), 'Quitando el fondo…'));
  }
  if (!p.categoria) t.classList.add('sin-clasificar');
  t.append(el('span.etiqueta', {}, p.nombre || nombreCategoria(p.categoria)));
  return t;
}

export function render() {
  if (!estado.usuario) return;
  renderFiltros();
  const lista = filtradas();
  const rejilla = $('rejilla');
  rejilla.replaceChildren();
  if (!estado.prendas.length) {
    rejilla.append(el('div.vacio', {},
      el('p', {}, 'Haz una foto a cada prenda colgada en su percha, con la pared detrás, y súbelas aquí. El fondo se quita solo.'),
      el('button.btn.btn-primario', { onclick: () => $('input-fotos').click() }, 'Añadir fotos')));
  } else {
    for (const p of lista) rejilla.append(tarjeta(p, lista));
  }

  const pendientes = estado.prendas.filter((p) => p.estado === 'pendiente' || p.estado === 'procesando').length;
  const aviso_ = $('aviso-procesando');
  aviso_.hidden = !pendientes;
  aviso_.textContent = `Quitando el fondo de ${pendientes} ${pendientes === 1 ? 'foto' : 'fotos'}. Puedes seguir usando la app.`;
  vigilar();
}

/** Mientras haya fotos en proceso, refresca cada pocos segundos. */
function vigilar() {
  if (hayPendientes() && !sondeo) {
    sondeo = setInterval(async () => {
      try { await recargarPrendas(); } catch { /* reintentará */ }
      if (!hayPendientes()) { clearInterval(sondeo); sondeo = null; }
    }, 4000);
  }
}

async function subir(ficheros) {
  const lista = [...ficheros];
  if (!lista.length) return;
  let hechas = 0;
  try {
    for (let i = 0; i < lista.length; i += TANDA) {
      aviso(`Subiendo fotos… ${hechas} de ${lista.length}`, 60000);
      await api.subirFotos(lista.slice(i, i + TANDA));  // se clasifican después
      hechas = Math.min(i + TANDA, lista.length);
      await recargarPrendas();
    }
    aviso(`${lista.length} ${lista.length === 1 ? 'foto subida' : 'fotos subidas'}. Ahora se quita el fondo.`);
  } catch (e) {
    aviso(`Se subieron ${hechas} de ${lista.length}. Error: ${e.message}`, 6000);
    await recargarPrendas();
  }
}

export function iniciarArmario() {
  $('input-fotos').addEventListener('change', async (e) => {
    await subir(e.target.files);
    e.target.value = '';
  });
}
