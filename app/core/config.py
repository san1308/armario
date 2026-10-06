from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Base de datos y ficheros
    database_url: str = "sqlite:///./data/armario.db"
    data_dir: Path = Path("data")

    # ── Usuarios ──────────────────────────────────────────────────────────────
    # La app va detrás de Cloudflare Access: el usuario es el email que
    # Cloudflare ha autenticado. Si se rellenan team_domain + aud, además se
    # valida la firma del JWT (recomendado: evita que alguien que llegue al
    # puerto por la LAN falsifique la cabecera).
    cf_access_team_domain: str = ""   # p. ej. "domoticia.cloudflareaccess.com"
    cf_access_aud: str = ""           # "Application Audience (AUD) Tag"
    # Lista opcional de emails permitidos, separados por comas (vacía = todos
    # los que deje pasar Cloudflare Access).
    emails_permitidos: str = ""
    # Solo para desarrollo local: usuario a usar cuando no hay cabecera.
    dev_email: str = ""

    # ── Procesado de imágenes ─────────────────────────────────────────────────
    modelo_recorte: str = "isnet-general-use"
    # Desactivable en tests: si es False, las prendas se procesan en línea.
    procesar_en_segundo_plano: bool = True

    # App
    app_port: int = 8006
    debug: bool = False

    @property
    def emails_permitidos_set(self) -> set[str]:
        return {e.strip().lower() for e in self.emails_permitidos.split(",") if e.strip()}

    @property
    def prendas_dir(self) -> Path:
        return self.data_dir / "prendas"


settings = Settings()
