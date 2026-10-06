from PIL import Image

from tests.conftest import MAMA, OTRA, foto_prenda


def subir(client, headers=MAMA, categoria=None, n=1):
    files = [("fotos", (f"IMG_{i}.jpg", foto_prenda(), "image/jpeg")) for i in range(n)]
    data = {"categoria": categoria} if categoria else {}
    r = client.post("/api/v1/prendas/", files=files, data=data, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_health(client):
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_sin_identificar_es_401(client):
    assert client.get("/api/v1/yo").status_code == 401


def test_yo_crea_usuario(client):
    r = client.get("/api/v1/yo", headers=MAMA)
    assert r.status_code == 200
    assert r.json()["email"] == "mama@example.com"
    assert r.json()["nombre"] == "Mama"


def test_catalogo(client):
    c = client.get("/api/v1/catalogo").json()
    assert {z["slug"] for z in c["zonas"]} == {"exterior", "arriba", "abajo", "entera"}
    assert any(cat["slug"] == "pantalon" and cat["zona"] == "abajo" for cat in c["categorias"])


def test_subir_procesa_y_quita_gancho(client):
    [p] = subir(client, categoria="camiseta")
    assert p["estado"] == "lista"
    assert p["zona"] == "arriba"
    assert p["version"] == 1
    # El gancho (10 px de ancho sobre una prenda de 300) se elimina:
    # el recorte empieza en la prenda, no en el gancho
    assert abs(p["corte_auto"] - 200 / 800) < 0.01
    assert (p["ancho"], p["alto"]) == (301, 501)

    r = client.get(f"/api/v1/prendas/{p['id']}/imagen/recorte?v=1", headers=MAMA)
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/webp"
    assert "immutable" in r.headers["cache-control"]


def test_subir_varias_sin_clasificar(client):
    subir(client, n=3)
    subir(client, categoria="falda")
    assert len(client.get("/api/v1/prendas/?sin_clasificar=true", headers=MAMA).json()) == 3
    assert len(client.get("/api/v1/prendas/?zona=abajo", headers=MAMA).json()) == 1


def test_subir_algo_que_no_es_imagen(client):
    files = [("fotos", ("nota.txt", b"hola", "text/plain"))]
    r = client.post("/api/v1/prendas/", files=files, headers=MAMA)
    assert r.status_code == 422


def test_categoria_desconocida(client):
    [p] = subir(client)
    r = client.patch(f"/api/v1/prendas/{p['id']}", json={"categoria": "capa"}, headers=MAMA)
    assert r.status_code == 422


def test_corte_manual_regenera_recorte(client):
    [p] = subir(client)
    r = client.patch(f"/api/v1/prendas/{p['id']}", json={"corte_manual": 0.5}, headers=MAMA)
    q = r.json()
    assert q["corte_manual"] == 0.5
    assert q["version"] == 2
    assert q["alto"] == 700 - 400 + 1  # la prenda acaba en la fila 700; corte en 400
    # Volver al automático
    q = client.patch(f"/api/v1/prendas/{p['id']}", json={"corte_manual": None}, headers=MAMA).json()
    assert q["corte_manual"] is None
    assert q["alto"] == 501


def test_ajuste_encaje(client):
    [p] = subir(client)
    q = client.patch(f"/api/v1/prendas/{p['id']}", json={"escala": 1.2, "desplazamiento": -0.05},
                     headers=MAMA).json()
    assert (q["escala"], q["desplazamiento"], q["version"]) == (1.2, -0.05, 1)
    r = client.patch(f"/api/v1/prendas/{p['id']}", json={"escala": 9}, headers=MAMA)
    assert r.status_code == 422


def test_aislamiento_entre_usuarios(client):
    [p] = subir(client)
    assert client.get(f"/api/v1/prendas/{p['id']}", headers=OTRA).status_code == 404
    assert client.get(f"/api/v1/prendas/{p['id']}/imagen/original", headers=OTRA).status_code == 404
    assert client.get("/api/v1/prendas/", headers=OTRA).json() == []
    r = client.post("/api/v1/conjuntos/", json={"arriba_id": p["id"]}, headers=OTRA)
    assert r.status_code == 422


def test_conjuntos_y_borrado_en_cascada(client):
    [arriba] = subir(client, categoria="blusa")
    [abajo] = subir(client, categoria="pantalon")
    c = client.post("/api/v1/conjuntos/", json={"nombre": "Lunes", "arriba_id": arriba["id"],
                                                "abajo_id": abajo["id"]}, headers=MAMA)
    assert c.status_code == 201
    assert len(client.get("/api/v1/conjuntos/", headers=MAMA).json()) == 1

    # Al borrar una prenda, el conjunto la pierde pero sigue existiendo
    assert client.delete(f"/api/v1/prendas/{arriba['id']}", headers=MAMA).status_code == 204
    [cj] = client.get("/api/v1/conjuntos/", headers=MAMA).json()
    assert cj["arriba_id"] is None and cj["abajo_id"] == abajo["id"]

    # Si se queda vacío, desaparece
    client.delete(f"/api/v1/prendas/{abajo['id']}", headers=MAMA)
    assert client.get("/api/v1/conjuntos/", headers=MAMA).json() == []


def test_conjunto_vacio_rechazado(client):
    assert client.post("/api/v1/conjuntos/", json={}, headers=MAMA).status_code == 422


def test_reprocesar(client):
    [p] = subir(client)
    q = client.post(f"/api/v1/prendas/{p['id']}/reprocesar", headers=MAMA).json()
    assert q["estado"] == "lista" and q["version"] == 2


def test_front_servido(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_heic_y_rotacion_exif():
    """La foto vertical del iPhone llega apaisada con EXIF de rotación: se corrige."""
    import io

    from app.services.recorte_service import abrir_normalizada

    im = Image.new("RGB", (400, 300), "white")
    exif = Image.Exif()
    exif[0x0112] = 6  # Orientation: rotar 90º
    buf = io.BytesIO()
    im.save(buf, "JPEG", exif=exif)
    assert abrir_normalizada(buf.getvalue()).size == (300, 400)


def test_jwt_cloudflare_access(client, monkeypatch):
    """Con TEAM_DOMAIN + AUD configurados, solo vale un JWT firmado; la cabecera de email no basta."""
    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa

    from app.core import auth
    from app.core.config import settings

    clave = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class FalsoJWKS:
        def get_signing_key_from_jwt(self, token):
            return type("K", (), {"key": clave.public_key()})()

    monkeypatch.setattr(settings, "cf_access_team_domain", "equipo.cloudflareaccess.com")
    monkeypatch.setattr(settings, "cf_access_aud", "aud-armario")
    monkeypatch.setattr(auth, "_jwks_client", lambda: FalsoJWKS())

    # Cabecera de email sin JWT → rechazada
    assert client.get("/api/v1/yo", headers=MAMA).status_code == 401

    bueno = jwt.encode({"email": "Mama@Example.com", "aud": "aud-armario"}, clave, algorithm="RS256")
    r = client.get("/api/v1/yo", headers={"Cf-Access-Jwt-Assertion": bueno})
    assert r.status_code == 200 and r.json()["email"] == "mama@example.com"

    otra_aud = jwt.encode({"email": "mama@example.com", "aud": "otra-app"}, clave, algorithm="RS256")
    assert client.get("/api/v1/yo", headers={"Cf-Access-Jwt-Assertion": otra_aud}).status_code == 401


def test_emails_permitidos(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "emails_permitidos", "mama@example.com")
    assert client.get("/api/v1/yo", headers=MAMA).status_code == 200
    assert client.get("/api/v1/yo", headers=OTRA).status_code == 403


def test_primer_acceso_concurrente(client):
    """El front pide /yo, /catalogo, /prendas y /conjuntos a la vez en el primer acceso."""
    from concurrent.futures import ThreadPoolExecutor

    rutas = ["/api/v1/yo", "/api/v1/prendas/", "/api/v1/conjuntos/", "/api/v1/yo"] * 3
    nuevo = {"Cf-Access-Authenticated-User-Email": "nueva@example.com"}
    with ThreadPoolExecutor(8) as ex:
        codigos = list(ex.map(lambda r: client.get(r, headers=nuevo).status_code, rutas))
    assert codigos == [200] * len(rutas)


def test_temporadas(client):
    [a] = subir(client, categoria="top")
    [b] = subir(client, categoria="jersey")
    [c] = subir(client, categoria="blusa")
    assert a["temporadas"] == []

    # Se guarda en orden fijo y sin duplicados
    r = client.patch(f"/api/v1/prendas/{a['id']}", json={"temporadas": ["entretiempo", "verano", "verano"]}, headers=MAMA)
    assert r.json()["temporadas"] == ["verano", "entretiempo"]
    client.patch(f"/api/v1/prendas/{b['id']}", json={"temporadas": ["invierno"]}, headers=MAMA)

    ids = lambda q: {p["id"] for p in client.get(f"/api/v1/prendas/?{q}", headers=MAMA).json()}
    assert ids("temporada=verano") == {a["id"]}
    assert ids("temporada=entretiempo") == {a["id"]}
    assert ids("temporada=invierno") == {b["id"]}
    assert ids("temporada=ninguna") == {c["id"]}

    assert client.patch(f"/api/v1/prendas/{a['id']}", json={"temporadas": ["otoño"]}, headers=MAMA).status_code == 422
    assert client.get("/api/v1/prendas/?temporada=primavera", headers=MAMA).status_code == 422

    # Lista vacía = todo el año
    assert client.patch(f"/api/v1/prendas/{a['id']}", json={"temporadas": []}, headers=MAMA).json()["temporadas"] == []
    assert [t["slug"] for t in client.get("/api/v1/catalogo").json()["temporadas"]] == ["verano", "entretiempo", "invierno"]


def test_migracion_desde_0001():
    """Una BD creada con la fase 1 (sin temporadas) se actualiza sin perder prendas."""
    import sqlite3
    import tempfile

    from alembic import command
    from alembic.config import Config

    from app.core.config import settings

    ruta = tempfile.mktemp(suffix=".db")
    cfg = Config("alembic.ini")
    original = settings.database_url
    settings.database_url = f"sqlite:///{ruta}"
    try:
        command.upgrade(cfg, "0001")
        con = sqlite3.connect(ruta)
        con.execute("INSERT INTO usuario (email, nombre, creado) VALUES ('a@b.c', 'A', '2026-10-06')")
        con.execute("INSERT INTO prenda (usuario_id, estado, escala, desplazamiento, version, creada) "
                    "VALUES (1, 'lista', 1.0, 0.0, 1, '2026-10-06')")
        con.commit(); con.close()
        command.upgrade(cfg, "head")
        con = sqlite3.connect(ruta)
        assert con.execute("SELECT temporadas FROM prenda").fetchall() == [("",)]
    finally:
        settings.database_url = original
