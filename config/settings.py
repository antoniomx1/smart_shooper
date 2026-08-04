import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Cargar variables del archivo .env
load_dotenv()

class Settings(BaseModel):
    telegram_bot_token: str = Field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    gemini_api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    def validate_keys(self):
        """Valida que las credenciales esenciales existan antes de arrancar."""
        missing = []
        if not self.telegram_bot_token:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not self.gemini_api_key:
            missing.append("GEMINI_API_KEY")
        
        if missing:
            raise ValueError(f"Faltan las siguientes variables en tu archivo .env: {', '.join(missing)}")

# Instancia global de configuración
settings = Settings()


