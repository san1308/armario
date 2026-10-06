// Cliente de la API. Todas las llamadas van con las cookies de Cloudflare Access.
const BASE = 'api/v1';

async function pedir(ruta, opciones = {}) {
  const r = await fetch(`${BASE}${ruta}`, { credentials: 'same-origin', ...opciones });
  if (r.status === 204) return null;
  let datos = null;
  try { datos = await r.json(); } catch { /* respuesta sin cuerpo */ }
  if (!r.ok) {
    const detalle = datos?.detail;
    const msg = typeof detalle === 'string' ? detalle : `Error ${r.status}`;
    throw new Error(msg);
  }
  return datos;
}

const json = (metodo, cuerpo) => ({
  method: metodo,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(cuerpo),
});

export const api = {
  yo: () => pedir('/yo'),
  catalogo: () => pedir('/catalogo'),

  prendas: () => pedir('/prendas/'),
  prenda: (id) => pedir(`/prendas/${id}`),
  actualizarPrenda: (id, cambios) => pedir(`/prendas/${id}`, json('PATCH', cambios)),
  reprocesar: (id) => pedir(`/prendas/${id}/reprocesar`, { method: 'POST' }),
  borrarPrenda: (id) => pedir(`/prendas/${id}`, { method: 'DELETE' }),
  subirFotos(ficheros, categoria) {
    const fd = new FormData();
    for (const f of ficheros) fd.append('fotos', f, f.name);
    if (categoria) fd.append('categoria', categoria);
    return pedir('/prendas/', { method: 'POST', body: fd });
  },

  conjuntos: () => pedir('/conjuntos/'),
  crearConjunto: (datos) => pedir('/conjuntos/', json('POST', datos)),
  borrarConjunto: (id) => pedir(`/conjuntos/${id}`, { method: 'DELETE' }),
};

/** URL de una imagen de prenda; la versión invalida la caché cuando cambia el recorte. */
export const urlImagen = (p, tipo = 'recorte') => `${BASE}/prendas/${p.id}/imagen/${tipo}?v=${p.version}`;
