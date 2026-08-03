from abc import ABC, abstractmethod
from typing import List, Dict, Any
from seleniumbase import Driver

class BaseScraper(ABC):
    """Clase base abstracta que define el contrato obligatorio para todos los scrapers."""

    def __init__(self, store_name: str):
        self.store_name = store_name

    def get_driver(self):
        """Crea una instancia de Driver lista para Docker y multihilo sin colapsar memoria."""
        return Driver(
            uc=True,
            headless=True,
            no_sandbox=True,
            disable_gpu=True,
            chromium_arg="--disable-dev-shm-usage,--no-sandbox,--disable-gpu"
        )

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        pass