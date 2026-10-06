// Vista Conjuntos: combinaciones guardadas.
import { api } from './api.js';
import { componer } from './componer.js';
import { estado, prendaPorId, recargarConjuntos } from './estado.js';
import { cargarConjunto } from './probador.js';
import { aviso, confirmarEnDosPasos, el, ICONOS } from './util.js';

const fecha = new Intl.DateTimeFormat('es-ES', { day: 'numeric', month: 'short' });

export function render() {
  if (!estado.usuario) return;
  const cont = document.getElementById('lista-conjuntos');
  cont.replaceChildren();
  if (!estado.conjuntos.length) {
    cont.append(el('div.vacio', {},
      el('p', {}, 'Cuando una combinación te guste, pulsa “Guardar conjunto” en el probador y aparecerá aquí.'),
      el('a.btn', { href: '#probador' }, 'Ir al probador')));
    return;
  }
  for (const c of estado.conjuntos) {
    const sel = {
      exterior: prendaPorId(c.exterior_id), arriba: prendaPorId(c.arriba_id),
      abajo: prendaPorId(c.abajo_id), entera: prendaPorId(c.entera_id),
    };
    const borrar = el('button.btn-icono', { 'aria-label': 'Borrar conjunto' });
    borrar.innerHTML = ICONOS.papelera;
    confirmarEnDosPasos(borrar, null, async () => {
      try { await api.borrarConjunto(c.id); await recargarConjuntos(); aviso('Conjunto borrado'); }
      catch (e) { aviso(`No se pudo borrar: ${e.message}`); }
    });
    cont.append(el('div.conjunto', {},
      el('button.tarjeta', { onclick: () => cargarConjunto(c), 'aria-label': `Abrir ${c.nombre || 'conjunto'} en el probador` },
        componer(sel, { proporcionMinima: 1.5 })),
      el('div.conjunto-pie', {},
        el('span.conjunto-nombre', {}, c.nombre || `Conjunto del ${fecha.format(new Date(c.creado))}`),
        borrar)));
  }
}
