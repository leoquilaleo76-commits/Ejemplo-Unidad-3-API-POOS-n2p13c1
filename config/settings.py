import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass


class Settings:
    """Configuración centralizada para la API externa y comportamiento del sistema."""

    API_BASE_URL: str = os.getenv("API_BASE_URL", "https://api.fda.gov/drug/label.json")
    API_KEY: str = os.getenv("API_KEY", "")
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "5"))
    ENABLE_OFFLINE_FALLBACK: bool = os.getenv("ENABLE_OFFLINE_FALLBACK", "True").strip().lower() in (
        "true",
        "1",
        "yes",
        "y",
    )
    ADMIN_INITIAL_USER: str = os.getenv("ADMIN_INITIAL_USER", "admin")
    ADMIN_INITIAL_CLAVE: str = os.getenv("ADMIN_INITIAL_CLAVE", "admin1234")
    MAX_LOGIN_ATTEMPTS: int = max(1, int(os.getenv("MAX_LOGIN_ATTEMPTS", "3")))
