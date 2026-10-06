// Composición del conjunto: coloca cada prenda recortada en un SVG.
//
// Trabajamos en "unidades de cuerpo": el ancho de referencia es 100. Cada zona
// tiene un ancho base (una camiseta con mangas ocupa más que un pantalón
// colgado). Las fotos están hechas a escalas distintas, así que el usuario puede
// corregir cada prenda con `escala` (multiplica el ancho) y `desplazamiento`
// (mueve en vertical, en fracción de su altura). El SVG usa viewBox, de modo
// que la misma composición sirve para el espejo y para las miniaturas.
import { urlImagen } from './api.js';
import { svgEl } from './util.js';

const ANCHO_BASE = { exterior: 86, arriba: 78, abajo: 56, entera: 74 };
// Cuánto se solapa la parte de arriba con la cintura del pantalón (fracción de su altura)
const SOLAPE_CINTURA = 0.16;
const MARGEN = 8;

function caja(p, zona, y) {
  const w = ANCHO_BASE[zona] * (p.escala ?? 1);
  const h = w * (p.alto / p.ancho);
  return { p, zona, x: 50 - w / 2, y: y + (p.desplazamiento ?? 0) * h, w, h };
}

/** Calcula las posiciones. `sel` = {exterior, arriba, abajo, entera} con objetos prenda o null. */
export function calcularCapas(sel) {
  const capas = [];
  if (sel.entera) {
    capas.push(caja(sel.entera, 'entera', 0));
  } else {
    let arriba = null;
    if (sel.arriba) arriba = caja(sel.arriba, 'arriba', 0);
    if (sel.abajo) {
      // El pantalón empieza donde termina la parte de arriba (sin su desplazamiento manual)
      const base = arriba ? (arriba.w * sel.arriba.alto / sel.arriba.ancho) * (1 - SOLAPE_CINTURA) : 0;
      capas.push(caja(sel.abajo, 'abajo', base));
    }
    if (arriba) capas.push(arriba);
  }
  if (sel.exterior) capas.push(caja(sel.exterior, 'exterior', 0));
  return capas;   // en orden de pintado: lo último queda encima
}

/** Devuelve un <svg> con la composición. `opciones.alPulsar(zona)` hace las capas pulsables. */
export function componer(sel, opciones = {}) {
  const capas = calcularCapas(sel);
  const svg = svgEl('svg', { class: 'lienzo', role: 'img', preserveAspectRatio: 'xMidYMid meet' });
  if (!capas.length) { svg.setAttribute('viewBox', '0 0 100 160'); return svg; }

  const minX = Math.min(...capas.map((c) => c.x), 0);
  const maxX = Math.max(...capas.map((c) => c.x + c.w), 100);
  const minY = Math.min(...capas.map((c) => c.y));
  const maxY = Math.max(...capas.map((c) => c.y + c.h));
  const ancho = maxX - minX + MARGEN * 2;
  const alto = maxY - minY + MARGEN * 2;
  // Proporción mínima tipo espejo de cuerpo entero, para que una sola prenda no se vea gigante
  const altoFinal = Math.max(alto, ancho * (opciones.proporcionMinima ?? 1.25));
  const extra = (altoFinal - alto) / 2;
  svg.setAttribute('viewBox', `${minX - MARGEN} ${minY - MARGEN - extra} ${ancho} ${altoFinal}`);

  for (const c of capas) {
    const img = svgEl('image', {
      href: urlImagen(c.p), x: c.x, y: c.y, width: c.w, height: c.h,
      preserveAspectRatio: 'xMidYMid meet', class: 'capa', 'data-zona': c.zona,
    });
    if (opciones.alPulsar) img.addEventListener('click', () => opciones.alPulsar(c.zona));
    svg.append(img);
  }
  return svg;
}
