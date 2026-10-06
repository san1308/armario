"""Identificación del usuario a partir de Cloudflare Access.

Orden de preferencia:
1. Si hay CF_ACCESS_TEAM_DOMAIN + CF_ACCESS_AUD: se valida la firma del JWT
   `Cf-Access-Jwt-Assertion` y se toma el email del token.
2. Si no, se confía en la cabecera `Cf-Access-Authenticated-User-Email`
   (válido mientras el puerto solo sea accesible a través del túnel).
3. En desarrollo, DEV_EMAIL.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import get_session
from app.models import Usuario

logger = logging.getLogger(__name__)

CABECERA_EMAIL = "Cf-Access-Authenticated-User-Email"
CABECERA_JWT = "Cf-Access-Jwt-Assertion"


@lru_cache(maxsize=1)
def _jwks_client():
    import jwt

    url = f"https://{settings.cf_access_team_domain}/cdn-cgi/access/certs"
    return jwt.PyJWKClient(url, cache_keys=True)


def _email_desde_jwt(token: str) -> str:
    import jwt

    try:
        clave = _jwks_client().get_signing_key_from_jwt(token).key
        datos = jwt.decode(token, clave, algorithms=["RS256"], audience=settings.cf_access_aud)
    except Exception as e:  # noqa: BLE001 — cualquier fallo de validación es 401
        logger.warning("JWT de Cloudflare Access no válido: %s", e)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión no válida.") from e
    email = datos.get("email")
    if not email:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "El token no incluye email.")
    return email


def email_de_peticion(request: Request) -> str:
    if settings.cf_access_team_domain and settings.cf_access_aud:
        token = request.headers.get(CABECERA_JWT)
        if not token:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Falta la sesión de Cloudflare Access.")
        email = _email_desde_jwt(token)
    else:
        email = request.headers.get(CABECERA_EMAIL) or settings.dev_email
    if not email:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No se ha podido identificar al usuario.")
    email = email.strip().lower()
    permitidos = settings.emails_permitidos_set
    if permitidos and email not in permitidos:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Este email no tiene acceso al armario.")
    return email


def obtener_o_crear_usuario(session: Session, email: str) -> Usuario:
    consulta = select(Usuario).where(Usuario.email == email)
    usuario = session.exec(consulta).first()
    if usuario is not None:
        return usuario
    try:
        usuario = Usuario(email=email, nombre=email.split("@")[0].capitalize())
        session.add(usuario)
        session.commit()
        session.refresh(usuario)
        logger.info("Usuario nuevo: %s", email)
        return usuario
    except IntegrityError:
        # En el primer acceso el front lanza varias peticiones en paralelo y
        # todas intentan crear el usuario: la que pierde la carrera lo relee.
        session.rollback()
        return session.exec(consulta).one()


def usuario_actual(request: Request, session: Session = Depends(get_session)) -> Usuario:
    return obtener_o_crear_usuario(session, email_de_peticion(request))
