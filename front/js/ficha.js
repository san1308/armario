// Ficha de una prenda: clasificar, nombrar, ajustar el corte de la percha, borrar.
import { api, urlImagen } from './api.js';
import { estado, prendaPorId, quitarPrenda, reemplazarPrenda } from './estado.js';
import { probarPrenda } from './probador.js';
import { aviso, confirmarEnDosPasos, el, ICONOS } from './util.js';

const dlg = () => document.getElementById('hoja-prenda');
let recorrido = [];   // ids de la lista desde la que se abrió (para pasar a la siguiente)

export function abrirFicha(id, ids = []) {
  recorrido = ids;
  pintar(id);
  if (!dlg().open) dlg().showModal();
}

function siguienteSinClasificar(idActual) {
  const i = recorrido.indexOf(idActual);
  const resto = [...recorrido.slice(i + 1), ...recorrido.slice(0, Math.max(i, 0))];
  return resto.map(prendaPorId).find((p) => p && !p.categoria && p.id !== idActual);
}

async function guardar(p, cambios) {
  const nueva = await api.actualizarPrenda(p.id, cambios);
  reemplazarPrenda(nueva);
  return nueva;
}

function seccionCategorias(p) {
  const grupos = estado.zonas.map((z) => el('div.grupo', {},
    el('span.grupo-titulo', {}, z.nombre),
    el('div.grupo-botones', {}, estado.categorias.filter((c) => c.zona === z.slug).map((c) =>
      el('button.cat', {
        'aria-pressed': String(p.categoria === c.slug),
        onclick: async () => {
          const eraSinClasificar = !p.categoria;
          try {
            await guardar(p, { categoria: c.slug });
            const sig = eraSinClasificar ? siguienteSinClasificar(p.id) : null;
            if (sig) { aviso(`${c.nombre}. Siguiente prenda`); pintar(sig.id); }
            else { aviso(`Guardado como ${c.nombre.toLowerCase()}`); pintar(p.id); }
          } catch (e) { aviso(`No se pudo guardar: ${e.message}`); }
        },
      }, c.nombre)))));
  return el('div.seccion', {}, el('span.seccion-titulo', {}, '¿Qué es?'), el('div.categorias', {}, grupos));
}

function seccionNombre(p) {
  const input = el('input', { type: 'text', value: p.nombre ?? '', maxLength: 100, placeholder: 'Por ejemplo: blusa de flores', autocomplete: 'off' });
  input.addEventListener('change', async () => {
    try { await guardar(p, { nombre: input.value.trim() || null }); aviso('Nombre guardado'); }
    catch (e) { aviso(`No se pudo guardar: ${e.message}`); }
  });
  return el('label.campo', {}, 'Nombre (opcional)', input);
}

/** Editor del corte superior: la zona sombreada es lo que se elimina (la percha). */
function seccionCorte(p) {
  const valorInicial = p.corte_manual ?? p.corte_auto ?? 0;
  const img = el('img', { src: urlImagen(p, 'sinfondo'), alt: 'Foto sin fondo' });
  const sombra = el('div.corte-sombra');
  const caja = el('div.corte', {}, img, sombra);
  const rango = el('input', { type: 'range', min: 0, max: 0.6, step: 0.005, value: valorInicial, 'aria-label': 'Altura del corte' });

  const colocar = () => {
    if (!img.naturalWidth) return;
    // object-fit: contain → calcular dónde cae la imagen dentro de la caja
    const cw = caja.clientWidth, ch = caja.clientHeight;
    const k = Math.min(cw / img.naturalWidth, ch / img.naturalHeight);
    const alto = img.naturalHeight * k, arriba = (ch - alto) / 2;
    sombra.style.height = `${arriba + alto * Number(rango.value)}px`;
  };
  img.addEventListener('load', colocar);
  rango.addEventListener('input', colocar);

  const aplicar = el('button.btn.btn-primario', {
    onclick: async () => {
      try { await guardar(p, { corte_manual: Number(rango.value) }); aviso('Corte aplicado'); pintar(p.id); }
      catch (e) { aviso(`No se pudo aplicar: ${e.message}`); }
    },
  }, 'Aplicar corte');
  const auto = el('button.btn', {
    disabled: p.corte_manual == null,
    onclick: async () => {
      try { await guardar(p, { corte_manual: null }); aviso('Corte automático'); pintar(p.id); }
      catch (e) { aviso(`No se pudo guardar: ${e.message}`); }
    },
  }, 'Automático');

  return el('div.seccion', {},
    el('span.seccion-titulo', {}, 'Quitar la percha'),
    el('p.ayuda', {}, 'Mueve la línea hasta justo debajo de la percha. Lo sombreado se quita.'),
    caja, rango, el('div.fila-botones', {}, auto, aplicar));
}

function pintar(id) {
  const p = prendaPorId(id);
  const cont = document.getElementById('hoja-contenido');
  if (!p) { dlg().close(); return; }
  document.getElementById('hoja-titulo').textContent = p.categoria ? (p.nombre || 'Prenda') : 'Sin clasificar';

  const imagen = el('div.ficha-imagen', {},
    p.estado === 'lista'
      ? el('img', { src: urlImagen(p), alt: '' })
      : el('p.ayuda', {}, p.estado === 'error' ? `No se pudo quitar el fondo: ${p.error ?? ''}` : 'Quitando el fondo… puedes clasificarla mientras tanto.'));

  const probar = el('button.btn', { disabled: !(p.zona && p.estado === 'lista'), onclick: () => { dlg().close(); probarPrenda(p); } }, 'Probar en el espejo');
  const reprocesar = el('button.btn', {
    onclick: async () => {
      try { reemplazarPrenda(await api.reprocesar(p.id)); aviso('Quitando el fondo de nuevo…'); dlg().close(); }
      catch (e) { aviso(`No se pudo: ${e.message}`); }
    },
  }, 'Quitar el fondo otra vez');
  const borrar = el('button.btn.btn-peligro', {}, el('span', {}, 'Borrar prenda'));
  borrar.insertAdjacentHTML('afterbegin', ICONOS.papelera);
  confirmarEnDosPasos(borrar, 'Toca otra vez para borrar', async () => {
    try { await api.borrarPrenda(p.id); quitarPrenda(p.id); aviso('Prenda borrada'); dlg().close(); }
    catch (e) { aviso(`No se pudo borrar: ${e.message}`); }
  });

  cont.replaceChildren(
    el('div.hoja-cuerpo', { style: 'padding:0' },
      imagen,
      seccionCategorias(p),
      seccionNombre(p),
      p.estado === 'lista' ? seccionCorte(p) : null,
      el('div.fila-botones', {}, probar, p.estado !== 'pendiente' && p.estado !== 'procesando' ? reprocesar : null),
      borrar));
  cont.parentElement.scrollTop = 0;
}

export function iniciarFicha() {
  for (const d of document.querySelectorAll('dialog')) {
    d.addEventListener('click', (e) => { if (e.target === d) d.close(); });   // tocar fuera cierra
    d.querySelectorAll('[data-cerrar]').forEach((b) => b.addEventListener('click', () => d.close()));
  }
}
