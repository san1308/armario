/** Crea un elemento: el('button.btn', {onclick}, 'Texto', hijo...) */
export function el(etiqueta, props = {}, ...hijos) {
  const [nombre, ...clases] = etiqueta.split('.');
  const nodo = document.createElement(nombre);
  if (clases.length) nodo.className = clases.join(' ');
  for (const [k, v] of Object.entries(props ?? {})) {
    if (v == null || v === false) continue;
    if (k.startsWith('on')) nodo.addEventListener(k.slice(2), v);
    else if (k === 'dataset') Object.assign(nodo.dataset, v);
    else if (k in nodo && k !== 'list') nodo[k] = v;
    else nodo.setAttribute(k, v === true ? '' : v);
  }
  for (const h of hijos.flat()) if (h != null && h !== false) nodo.append(h);
  return nodo;
}

const SVG_NS = 'http://www.w3.org/2000/svg';
export function svgEl(nombre, attrs = {}) {
  const n = document.createElementNS(SVG_NS, nombre);
  for (const [k, v] of Object.entries(attrs)) if (v != null) n.setAttribute(k, v);
  return n;
}

let temporizador;
export function aviso(texto, ms = 2600) {
  const t = document.getElementById('toast');
  t.textContent = texto;
  t.hidden = false;
  clearTimeout(temporizador);
  temporizador = setTimeout(() => { t.hidden = true; }, ms);
}

/** Botón de borrar en dos pasos: el primer toque pide confirmación. */
export function confirmarEnDosPasos(boton, textoConfirmar, accion) {
  let armado = false, t;
  const original = boton.innerHTML;
  boton.addEventListener('click', async (e) => {
    e.stopPropagation();
    if (!armado) {
      armado = true;
      boton.classList.add('confirmar');
      if (textoConfirmar) boton.textContent = textoConfirmar;
      t = setTimeout(() => { armado = false; boton.classList.remove('confirmar'); boton.innerHTML = original; }, 3500);
      return;
    }
    clearTimeout(t);
    await accion();
  });
}

export function debounce(fn, ms) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

export const ICONOS = {
  candado: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>',
  papelera: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/></svg>',
};
