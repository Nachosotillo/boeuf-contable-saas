"""
Configuración centralizada vía variables de entorno
Copiar .env.example → .env y rellenar valores
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Base de datos
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/boeuf_contable"

    # JWT
    SECRET_KEY: str = "cambia-esto-en-produccion-usa-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480   # 8 horas

    # App
    DEBUG: bool = False
    APP_NAME: str = "Boeuf Contable SaaS"
    VERSION: str = "1.0.0"

    # API BCV / Tasa de cambio
    BCV_API_URL: str = "https://ve.dolarapi.com/v1/dolares/oficial"  # API pública

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
