// Arranque: carga datos, enlaza vistas y enruta por el hash (#probador, #armario, #conjuntos).
import * as armario from './armario.js';
import * as conjuntos from './conjuntos.js';
import { alCambiar, cargarTodo } from './estado.js';
import { iniciarFicha } from './ficha.js';
import * as probador from './probador.js';
import { aviso } from './util.js';

const VISTAS = { probador, armario, conjuntos };

function enrutar() {
  document.querySelectorAll('dialog[open]').forEach((d) => d.close());
  const nombre = location.hash.slice(1) in VISTAS ? location.hash.slice(1) : 'probador';
  for (const s of document.querySelectorAll('.vista')) s.hidden = s.dataset.vista !== nombre;
  for (const a of document.querySelectorAll('.nav a')) {
    if (a.dataset.ir === nombre) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
  }
  VISTAS[nombre].render();
  window.scrollTo(0, 0);
}

function renderVisible() {
  const visible = document.querySelector('.vista:not([hidden])')?.dataset.vista ?? 'probador';
  VISTAS[visible].render();
}

async function iniciar() {
  probador.iniciarProbador();
  armario.iniciarArmario();
  iniciarFicha();
  alCambiar(renderVisible);
  window.addEventListener('hashchange', enrutar);
  try {
    await cargarTodo();
  } catch (e) {
    aviso(`No se pudo cargar el armario: ${e.message}`, 10000);
  }
  enrutar();
}

iniciar();
