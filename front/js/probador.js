// Vista Probador: el espejo, las zonas, la tira de prendas y las acciones.
import { api, urlImagen } from './api.js';
import { componer } from './componer.js';
import {
  estado, listasDeZona, nombreCategoria, prendaPorId, reemplazarPrenda, recargarConjuntos, temporadaDeHoy, valeParaTemporada,
} from './estado.js';
import { aviso, debounce, el, ICONOS } from './util.js';

const CLAVE_LOCAL = 'armario.probador';
const ZONAS_SEPARADO = ['exterior', 'arriba', 'abajo'];
const ZONAS_ENTERA = ['exterior', 'entera'];

const p = {
  modo: 'separado',                   // 'separado' (arriba + abajo) o 'entera' (vestido/mono)
  sel: { exterior: null, arriba: null, abajo: null, entera: null },
  zonaActiva: 'arriba',
  fijadas: new Set(),
  ajusteAbierto: false,
  temporada: temporadaDeHoy(),        // '' = todo el año
};

const $ = (id) => document.getElementById(id);

// ── Persistencia ligera (solo comodidad: si falla, no pasa nada) ───────────────
function guardarLocal() {
  try {
    localStorage.setItem(CLAVE_LOCAL, JSON.stringify({ modo: p.modo, sel: p.sel, zonaActiva: p.zonaActiva, fijadas: [...p.fijadas], temporada: p.temporada }));
  } catch { /* modo privado o almacenamiento bloqueado */ }
}
function leerLocal() {
  try {
    const d = JSON.parse(localStorage.getItem(CLAVE_LOCAL) || 'null');
    if (d) Object.assign(p, { modo: d.modo, sel: { ...p.sel, ...d.sel }, zonaActiva: d.zonaActiva, fijadas: new Set(d.fijadas) });
    if (d && typeof d.temporada === 'string') p.temporada = d.temporada;
  } catch { /* ignorar */ }
}

// ── Lógica ─────────────────────────────────────────────────────────────────────
const zonasVisibles = () => (p.modo === 'entera' ? ZONAS_ENTERA : ZONAS_SEPARADO);
const opcional = (zona) => zona === 'exterior';
/** Prendas listas de una zona que valen para la temporada elegida. */
const disponibles = (zona) => listasDeZona(zona).filter((x) => valeParaTemporada(x, p.temporada));

/** Corrige la selección: ids que ya no existen, zonas vacías → primera prenda disponible. */
function sanear() {
  for (const zona of ['exterior', 'arriba', 'abajo', 'entera']) {
    const lista = disponibles(zona);
    const actual = prendaPorId(p.sel[zona]);
    if (!actual || actual.zona !== zona || actual.estado !== 'lista' || !valeParaTemporada(actual, p.temporada)) {
      p.sel[zona] = opcional(zona) ? null : (lista[0]?.id ?? null);
    }
  }
  if (p.modo === 'entera' && !disponibles('entera').length) p.modo = 'separado';
  if (!zonasVisibles().includes(p.zonaActiva)) p.zonaActiva = p.modo === 'entera' ? 'entera' : 'arriba';
}

function seleccionVisible() {
  const s = { exterior: prendaPorId(p.sel.exterior) ?? null, arriba: null, abajo: null, entera: null };
  if (p.modo === 'entera') s.entera = prendaPorId(p.sel.entera) ?? null;
  else { s.arriba = prendaPorId(p.sel.arriba) ?? null; s.abajo = prendaPorId(p.sel.abajo) ?? null; }
  return s;
}

function elegir(zona, id) {
  p.sel[zona] = id;
  if (zona === 'entera') p.modo = 'entera';
  if (zona === 'arriba' || zona === 'abajo') p.modo = 'separado';
  p.zonaActiva = zona;
  guardarLocal();
  render();
}

function moverEnZona(paso) {
  const zona = p.zonaActiva;
  const ids = disponibles(zona).map((x) => x.id);
  if (opcional(zona)) ids.unshift(null);
  if (!ids.length) return;
  const i = ids.indexOf(p.sel[zona]);
  elegir(zona, ids[(i + paso + ids.length) % ids.length]);
}

function sorprender() {
  const azar = (lista, actual) => {
    const otras = lista.length > 1 ? lista.filter((x) => x !== actual) : lista;
    return otras[Math.floor(Math.random() * otras.length)] ?? null;
  };
  for (const zona of zonasVisibles()) {
    if (p.fijadas.has(zona)) continue;
    if (zona === 'exterior' && p.sel.exterior == null) continue;  // si no lleva nada encima, se respeta
    p.sel[zona] = azar(disponibles(zona).map((x) => x.id), p.sel[zona]);
  }
  guardarLocal();
  render();
}

// ── Pintado ────────────────────────────────────────────────────────────────────
function renderEspejo() {
  const espejo = $('espejo');
  espejo.querySelector('svg.lienzo')?.remove();
  const vacio = $('espejo-vacio');
  const sel = seleccionVisible();
  const algo = Object.values(sel).some(Boolean);
  vacio.hidden = algo;
  document.querySelector('.espejo-flechas').hidden = !algo;
  document.querySelector('.tira-cabecera').style.visibility = algo ? '' : 'hidden';
  if (!algo) {
    vacio.replaceChildren(el('p', {},
      estado.prendas.length
        ? 'Aún no hay prendas clasificadas. En '
        : 'Todavía no hay prendas. Añade las fotos en ',
      el('a', { href: '#armario' }, 'Armario'),
      estado.prendas.length ? ' indica qué es cada una.' : '.'));
    return;
  }
  espejo.append(componer(sel, { alPulsar: (zona) => { p.zonaActiva = zona; guardarLocal(); render(); } }));
}

function renderZonas() {
  const cont = $('zonas');
  cont.replaceChildren();
  for (const z of estado.zonas) {
    const n = disponibles(z.slug).length;
    if (!n && z.slug !== 'arriba' && z.slug !== 'abajo') continue;  // no mostrar zonas sin prendas
    const visible = zonasVisibles().includes(z.slug) && (z.slug !== 'exterior' || p.sel.exterior);
    const chip = el('button.zona-chip', {
      role: 'tab', 'aria-selected': String(p.zonaActiva === z.slug),
      onclick: () => {
        if (z.slug === 'entera') p.modo = 'entera';
        else if (z.slug !== 'exterior') p.modo = 'separado';
        p.zonaActiva = z.slug; sanear(); guardarLocal(); render();
      },
    }, z.nombre);
    if (!visible) chip.classList.add('inactiva');
    if (p.fijadas.has(z.slug)) chip.insertAdjacentHTML('afterbegin', ICONOS.candado);
    cont.append(chip);
  }
}

function renderTemporadas() {
  const cont = $('temporadas-probador');
  cont.replaceChildren();
  for (const [slug, nombre] of [['', 'Todo el año'], ...estado.temporadas.map((t) => [t.slug, t.nombre])]) {
    cont.append(el('button.temporada', {
      role: 'radio', 'aria-checked': String(p.temporada === slug),
      onclick: () => { p.temporada = slug; guardarLocal(); render(); },
    }, nombre));
  }
}

function renderTira() {
  const zona = p.zonaActiva;
  const lista = disponibles(zona);
  const actual = prendaPorId(p.sel[zona]);
  $('tira-titulo').textContent = actual ? (actual.nombre || nombreCategoria(actual.categoria)) : (opcional(zona) ? 'Nada encima' : '');
  const fijar = $('btn-fijar');
  fijar.setAttribute('aria-pressed', String(p.fijadas.has(zona)));
  fijar.querySelector('span').textContent = p.fijadas.has(zona) ? 'Fijada' : 'Fijar';
  $('btn-ajustar').disabled = !actual;

  const tira = $('tira');
  tira.replaceChildren();
  if (opcional(zona)) {
    tira.append(el('button.miniatura.nada', { role: 'option', 'aria-selected': String(p.sel[zona] == null), onclick: () => elegir(zona, null) }, 'Nada encima'));
  }
  if (!lista.length) {
    const hayFueraDeTemporada = listasDeZona(zona).length > 0;
    tira.append(el('p.tira-vacia', {}, hayFueraDeTemporada
      ? 'No hay prendas de este tipo para esta temporada.'
      : 'No hay prendas de este tipo todavía.'));
    return;
  }
  for (const pr of lista) {
    const b = el('button.miniatura', {
      role: 'option', 'aria-selected': String(pr.id === p.sel[zona]),
      'aria-label': pr.nombre || nombreCategoria(pr.categoria), onclick: () => elegir(zona, pr.id),
    }, el('img', { src: urlImagen(pr, 'mini'), alt: '', loading: 'lazy' }));
    tira.append(b);
  }
  tira.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: 'nearest', inline: 'center' });
}

function renderAjuste() {
  const panel = $('ajuste');
  const actual = prendaPorId(p.sel[p.zonaActiva]);
  panel.hidden = !(p.ajusteAbierto && actual);
  $('btn-ajustar').setAttribute('aria-expanded', String(!panel.hidden));
  if (actual && document.activeElement?.type !== 'range') {
    $('ajuste-escala').value = actual.escala;
    $('ajuste-altura').value = actual.desplazamiento;
  }
}

export function render() {
  if (!estado.usuario) return;
  sanear();
  renderTemporadas();
  renderEspejo();
  renderZonas();
  renderTira();
  renderAjuste();
}

// ── API pública para otras vistas ─────────────────────────────────────────────
export function cargarConjunto(c) {
  p.modo = c.entera_id ? 'entera' : 'separado';
  Object.assign(p.sel, {
    exterior: c.exterior_id,
    entera: c.entera_id ?? p.sel.entera,
    arriba: c.arriba_id ?? p.sel.arriba,
    abajo: c.abajo_id ?? p.sel.abajo,
  });
  p.zonaActiva = p.modo === 'entera' ? 'entera' : 'arriba';
  const prendas = [c.exterior_id, c.arriba_id, c.abajo_id, c.entera_id].map(prendaPorId).filter(Boolean);
  if (prendas.some((x) => !valeParaTemporada(x, p.temporada))) p.temporada = '';
  guardarLocal();
  location.hash = '#probador';
}

export function probarPrenda(prenda) {
  if (!prenda.zona) return;
  if (!valeParaTemporada(prenda, p.temporada)) p.temporada = '';
  elegir(prenda.zona, prenda.id);
  location.hash = '#probador';
}

// ── Eventos ───────────────────────────────────────────────────────────────────
const guardarAjuste = debounce(async (id, cambios) => {
  try { reemplazarPrenda(await api.actualizarPrenda(id, cambios)); }
  catch (e) { aviso(`No se pudo guardar el ajuste: ${e.message}`); }
}, 450);

function alAjustar() {
  const actual = prendaPorId(p.sel[p.zonaActiva]);
  if (!actual) return;
  actual.escala = Number($('ajuste-escala').value);
  actual.desplazamiento = Number($('ajuste-altura').value);
  renderEspejo();
  guardarAjuste(actual.id, { escala: actual.escala, desplazamiento: actual.desplazamiento });
}

function activarDeslizar(nodo) {
  let x0 = null, y0 = null;
  nodo.addEventListener('pointerdown', (e) => { x0 = e.clientX; y0 = e.clientY; });
  nodo.addEventListener('pointerup', (e) => {
    if (x0 == null) return;
    const dx = e.clientX - x0, dy = e.clientY - y0;
    x0 = null;
    if (Math.abs(dx) > 45 && Math.abs(dx) > Math.abs(dy) * 1.3) moverEnZona(dx < 0 ? 1 : -1);
  });
  nodo.addEventListener('pointercancel', () => { x0 = null; });
}

export function iniciarProbador() {
  leerLocal();
  activarDeslizar($('espejo'));
  $('btn-anterior').addEventListener('click', () => moverEnZona(-1));
  $('btn-siguiente').addEventListener('click', () => moverEnZona(1));
  $('btn-sorpresa').addEventListener('click', sorprender);
  $('btn-fijar').addEventListener('click', () => {
    const z = p.zonaActiva;
    p.fijadas.has(z) ? p.fijadas.delete(z) : p.fijadas.add(z);
    guardarLocal(); render();
  });
  $('btn-ajustar').addEventListener('click', () => { p.ajusteAbierto = !p.ajusteAbierto; renderAjuste(); });
  $('ajuste-escala').addEventListener('input', alAjustar);
  $('ajuste-altura').addEventListener('input', alAjustar);
  $('ajuste-reset').addEventListener('click', () => {
    $('ajuste-escala').value = 1; $('ajuste-altura').value = 0; alAjustar();
  });
  document.addEventListener('keydown', (e) => {
    if (document.querySelector('dialog[open]') || !location.hash.startsWith('#probador') && location.hash) return;
    if (e.target.matches('input, textarea')) return;
    if (e.key === 'ArrowLeft') moverEnZona(-1);
    if (e.key === 'ArrowRight') moverEnZona(1);
  });

  const dlg = $('hoja-guardar');
  $('btn-guardar').addEventListener('click', () => {
    const s = seleccionVisible();
    if (!Object.values(s).some(Boolean)) { aviso('Elige alguna prenda antes de guardar.'); return; }
    $('guardar-nombre').value = '';
    dlg.showModal();
  });
  $('form-guardar').addEventListener('submit', async (e) => {
    e.preventDefault();
    const s = seleccionVisible();
    try {
      await api.crearConjunto({
        nombre: $('guardar-nombre').value.trim() || null,
        exterior_id: s.exterior?.id ?? null, arriba_id: s.arriba?.id ?? null,
        abajo_id: s.abajo?.id ?? null, entera_id: s.entera?.id ?? null,
      });
      dlg.close();
      await recargarConjuntos();
      aviso('Conjunto guardado');
    } catch (err) { aviso(`No se pudo guardar: ${err.message}`); }
  });
}
