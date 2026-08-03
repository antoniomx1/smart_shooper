import concurrent.futures
import time
from typing import List, Dict, Any
from src.scrapers.meli_scraper import MeliScraper
from src.scrapers.amazon_scraper import AmazonScraper
from src.scrapers.liverpool_scraper import LiverpoolScraper
from src.scrapers.walmart_scraper import WalmartScraper
from src.scrapers.coppel_scraper import CoppelScraper

def run_single_scraper(item: tuple) -> List[Dict[str, Any]]:
    """Ejecuta cada scraper aisladamente con un pequeño stagger inicial."""
    scraper_class, query, limit_per_store, delay = item
    
    if delay > 0:
        time.sleep(delay)

    store_name = scraper_class.__name__.replace("Scraper", "")
    try:
        scraper = scraper_class()
        results = scraper.search(query, limit=limit_per_store)
        return results
    except Exception as e:
        print(f" Error ejecutando {store_name}: {e}")
        return []

class SearchManager:
    """Orquestador multi-hilo para evitar desbordamiento de memoria compartida en Cloud Run."""

    def __init__(self):
        self.scraper_classes = [
            MeliScraper,
            AmazonScraper,
            LiverpoolScraper,
            WalmartScraper,
            CoppelScraper
        ]

    def search_all(self, query: str, limit_per_store: int = 3) -> List[Dict[str, Any]]:
        all_results = []
        print(f"Lanzando búsqueda multihilo (con stagger) en {len(self.scraper_classes)} tiendas para: '{query}'...\n")

        tasks = [
            (cls, query, limit_per_store, i * 0.8)
            for i, cls in enumerate(self.scraper_classes)
        ]

        # CAMBIO CLAVE: Usamos ThreadPoolExecutor para no saturar los IPC Pipes ni la SHM
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_class = {
                executor.submit(run_single_scraper, task): task[0]
                for task in tasks
            }

            for future in concurrent.futures.as_completed(future_to_class):
                cls = future_to_class[future]
                store_name = cls.__name__.replace("Scraper", "")
                try:
                    data = future.result()
                    all_results.extend(data)
                    print(f"✅ {store_name}: {len(data)} productos encontrados.")
                except Exception as exc:
                    print(f"❌ {store_name} generó una excepción: {exc}")

        all_results.sort(key=lambda x: x["price"])
        return all_results