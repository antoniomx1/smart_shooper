import random
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from seleniumbase import Driver


class BaseScraper(ABC):
    """Clase base abstracta que define el contrato obligatorio para todos los scrapers."""

    def __init__(self, store_name: str):
        self.store_name = store_name

    def get_driver(self, extra_evasion: bool = False):
        """Crea una instancia de Driver lista para Docker y multihilo.

        Args:
            extra_evasion: Si es True, añade flags adicionales anti-detección
                           (viewport random, flags anti-headless, etc.)
        """
        # Flags base para todos los scrapers
        base_args = [
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-gpu",
        ]

        # Flags extra para portales agresivos (Walmart, MeLi)
        if extra_evasion:
            vp_width = random.randint(1280, 1920)
            vp_height = random.randint(800, 1080)
            base_args.extend([
                f"--window-size={vp_width},{vp_height}",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-site-isolation-trials",
            ])

        return Driver(
            uc=True,
            headless=True,
            no_sandbox=True,
            disable_gpu=True,
            chromium_arg=",".join(base_args)
        )

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        pass