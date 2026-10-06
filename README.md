# Armario

Probador virtual para el móvil: fotos de prendas colgadas en su percha → se
quita el fondo automáticamente → se combinan en un "espejo" para ver cómo
queda cada parte de arriba con cada parte de abajo.

Self-hosted en la **Raspberry Pi 5**, junto a DomoticIA y la Despensa, con el
mismo patrón (FastAPI + SQLModel + SQLite/Alembic + SPA vanilla JS + Docker
Compose + Cloudflare Tunnel/Access).

---

## Índice

1. [Qué hace (fase 1)](#qué-hace-fase-1)
2. [Arquitectura](#arquitectura)
3. [Decisiones de diseño](#decisiones-de-diseño)
4. [Estructura del proyecto](#estructura-del-proyecto)
5. [Desarrollo local](#desarrollo-local)
6. [Despliegue en la Raspberry Pi](#despliegue-en-la-raspberry-pi)
7. [Importación inicial de las fotos](#importación-inicial-de-las-fotos)
8. [Usuarios y Cloudflare Access](#usuarios-y-cloudflare-access)
9. [API](#api)
10. [Hoja de ruta](#hoja-de-ruta)

---

## Qué hace (fase 1)

- **Probador**: espejo con la combinación actual. Zonas *Encima* (opcional),
  *Arriba*, *Abajo* y *Vestidos* (que sustituye a arriba + abajo).
  - Deslizar sobre el espejo o usar las flechas cambia la prenda de la zona
    seleccionada; tocar una prenda del espejo selecciona su zona.
  - **Temporada** (todo el año / verano / entretiempo / invierno): por defecto la
    del mes actual; filtra las prendas y lo que sale en "Sorpréndeme". Una prenda
    sin temporada marcada sale en todas.
  - **Fijar** una zona y **Sorpréndeme** para combinaciones aleatorias del resto.
  - **Ajustar** tamaño y altura de cada prenda (se guarda en la prenda: se
    ajusta una vez y encaja siempre).
  - **Guardar conjunto**.
- **Armario**: subir fotos (varias a la vez, JPEG/PNG/HEIC), ver el progreso
  del recorte, filtrar por zona / "Sin clasificar" y por temporada / "Sin temporada".
  - Ficha de prenda: categoría, **temporadas** (varias a la vez), nombre,
    **corte de la percha** con vista previa, volver a quitar el fondo, borrar.
    Botones Anterior/Siguiente para recorrer la lista filtrada en serie.
- **Conjuntos**: combinaciones guardadas en miniatura; tocar una la abre en el probador.
- **Varios usuarios**: cada email de Cloudflare Access tiene su propio armario.
- Responsive: pensado para móvil; en ordenador el espejo queda a la izquierda
  y los mandos a la derecha. Instalable en la pantalla de inicio (manifest).

## Arquitectura

```
                          Cloudflare Tunnel + Access (login por email)
                                         │
┌────────────────────────────────────────▼─────────────────────────────────┐
│ Raspberry Pi 5 · contenedor "armario" :8006                              │
│                                                                          │
│  front/ (SPA vanilla JS)  ◀── servido en "/" por FastAPI (no-cache)      │
│                                                                          │
│  FastAPI  /api/v1/*                                                       │
│    ├─ core/auth ── email de Access (JWT validado) → Usuario              │
│    ├─ prendas ─── subir → guarda original.jpg → encola                   │
│    │                       │                                             │
│    │              ThreadPoolExecutor(1 hilo)                             │
│    │                       ▼                                             │
│    │      rembg (isnet-general-use, ONNX CPU)  → sinfondo.png            │
│    │      limpieza + corte del gancho + recorte → recorte.webp, mini.webp│
│    └─ conjuntos                                                          │
│                                                                          │
│  volumen armario_data: armario.db (SQLite WAL) + prendas/<usuario>/<id>/ │
└──────────────────────────────────────────────────────────────────────────┘
```

## Decisiones de diseño

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| `isnet-general-use` (rembg) | `u2net`, `birefnet-general-lite` | Probado con las fotos reales: u2net pierde prendas blancas sobre pared blanca; birefnet es mejor pero se queda sin memoria (OOM con 7 GB) |
| Guardar `sinfondo.png` a tamaño completo | Guardar solo el recorte final | Recortar la percha a mano es instantáneo (no vuelve a pasar por el modelo) |
| Corte automático del gancho por "ancho de fila" | Detección por color / morfología | El gancho y las pinzas son estrechos; la madera de la percha se confunde con prendas marrones. Lo que no se quita solo se corrige con la línea de corte |
| Cola con **un** hilo | Procesado en paralelo | En la Pi el modelo ya usa todos los núcleos y ~1 GB de RAM |
| Imágenes en disco, servidas con `?v=<versión>` + `immutable` | BLOBs en SQLite | Caché perfecta en el móvil e invalidación al recortar |
| Composición en SVG con `viewBox` | `<canvas>` | La misma función pinta el espejo y las miniaturas de conjuntos, y escala sola |
| Usuario = email de Cloudflare Access | Login propio con contraseñas | Cero gestión de contraseñas; añadir a alguien es añadir su email en Access |
| Categoría como texto + catálogo en código | Tabla de categorías | Añadir una categoría es una línea en `app/core/categorias.py`, sin migración |
| Un campo por zona en `Conjunto` | Tabla intermedia | Siempre hay como mucho una prenda por zona; consultas triviales |

**Encaje de prendas**: cada zona tiene un ancho base (arriba 78, abajo 56,
encima 86, vestido 74 sobre 100). La parte de abajo empieza donde acaba la de
arriba menos un 16 % de solape (la cintura). Como cada foto se hizo a una
distancia distinta, `escala` y `desplazamiento` por prenda corrigen el resto.

## Estructura del proyecto

```
app/
  core/        config, database, lifespan, auth (Cloudflare Access), categorias
  models/      Usuario, Prenda, Conjunto (SQLModel)
  schemas/     Pydantic de entrada/salida
  services/    recorte_service (rembg + percha), procesado_service (cola),
               prenda_service, conjunto_service, almacen (rutas de ficheros)
  api/v1/      yo, catalogo, prendas, conjuntos
front/         index.html, css/app.css, js/ (módulos ES: main, estado, api,
               componer, probador, armario, ficha, conjuntos, util)
alembic/       migraciones
scripts/       importar.py + clasificacion_inicial.csv
tests/         pytest (rembg sustituido por un recortador falso)
```

## Desarrollo local

```bash
make setup
make run            # http://localhost:8006 con DEV_EMAIL=yo@local
make test
```

La primera foto descarga el modelo (~170 MB) en `~/.u2net`.

## Despliegue en la Raspberry Pi

```bash
git clone <repo> ~/armario && cd ~/armario
cp .env.example .env        # rellenar CF_ACCESS_TEAM_DOMAIN y CF_ACCESS_AUD
make build                  # descarga el modelo dentro de la imagen
make up
curl localhost:8006/api/v1/health
```

En Cloudflare:
1. **Tunnel `ha-rpi5`** → Published application routes → Add:
   `armario.domoticia.fun` → `http://192.168.1.119:8006` (igual que despensa y futsal;
   `cloudflared` corre en Docker y llega a la Pi por su IP de la LAN).
2. **Access** → Applications → Self-hosted: `armario.domoticia.fun`, política
   *Allow* con los emails de quien vaya a usarla.
3. Copiar el **AUD** de la aplicación al `.env` y `make up` de nuevo.

## Importación inicial de las fotos

Las fotos del iPhone vienen como Live Photos (`.JPEG` + `.MOV`); el script
ignora los vídeos.

```bash
# Desde el PC: copiar la carpeta de iCloud a la Pi
scp "Fotos en iCloud"/*.JPEG pi@raspberry:~/armario/importar/

# En la Pi (~5-10 s por foto; 106 fotos ≈ 10-15 min)
make importar EMAIL=email.de.mama@ejemplo.com
```

`scripts/clasificacion_inicial.csv` trae una **propuesta de categoría y
temporadas** para cada una de las 106 fotos actuales (hecha mirando las fotos). Se corrige
desde la app en la ficha de cada prenda. El script es idempotente: se puede
relanzar sin duplicar.

Si el armario se importó antes de que existieran las temporadas:

```bash
make temporadas EMAIL=email.de.mama@ejemplo.com   # solo rellena las que no tienen
```

También se pueden subir desde el móvil con "Añadir fotos" (se suben de 4 en 4).

## Usuarios y Cloudflare Access

- Con `CF_ACCESS_TEAM_DOMAIN` + `CF_ACCESS_AUD`, se valida la firma del JWT
  `Cf-Access-Jwt-Assertion`. **Recomendado**: si no, cualquiera que llegue al
  puerto 8006 por la LAN o Tailscale podría falsificar la cabecera de email.
- Sin eso, se confía en `Cf-Access-Authenticated-User-Email`.
- `EMAILS_PERMITIDOS` limita aún más; `DEV_EMAIL` es solo para desarrollo.
- El primer acceso de un email crea su usuario (armario vacío).

## API

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/health` | Estado |
| GET | `/api/v1/yo` | Usuario actual |
| GET | `/api/v1/catalogo` | Zonas y categorías |
| GET | `/api/v1/prendas/?zona=&categoria=&sin_clasificar=&temporada=` | Listar (`temporada`: slug o `ninguna`) |
| POST | `/api/v1/prendas/` | Subir (`multipart`: `fotos[]`, `categoria?`) |
| GET/PATCH/DELETE | `/api/v1/prendas/{id}` | Ver / editar (`categoria`, `nombre`, `temporadas`, `escala`, `desplazamiento`, `corte_manual`) / borrar |
| POST | `/api/v1/prendas/{id}/reprocesar` | Volver a quitar el fondo |
| GET | `/api/v1/prendas/{id}/imagen/{original\|sinfondo\|recorte\|mini}` | Imágenes |
| GET/POST | `/api/v1/conjuntos/` | Listar / guardar |
| DELETE | `/api/v1/conjuntos/{id}` | Borrar |

Documentación interactiva en `/docs`.

## Hoja de ruta

- **Fase 1** ✅ Probador arriba/abajo/encima/vestido, armario, recorte
  automático, corte de percha, conjuntos, multiusuario.
- **Fase 1.1** ✅ Temporadas (verano, entretiempo, invierno) con filtro en probador y armario.
- **Fase 2** Etiquetas (color, ocasión) y filtros en el probador;
  goma de borrar para retocar el recorte (perchas de madera); "por dentro / por fuera".
- **Fase 3** Calzado y complementos; historial ("qué me puse"); compartir un conjunto.
