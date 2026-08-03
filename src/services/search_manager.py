import time
from typing import List, Dict, Any
from src.scrapers.meli_scraper import MeliScraper
from src.scrapers.amazon_scraper import AmazonScraper
from src.scrapers.liverpool_scraper import LiverpoolScraper
from src.scrapers.walmart_scraper import WalmartScraper
from src.scrapers.coppel_scraper import CoppelScraper

class SearchManager:
    """Orquestador secuencial estable para entornos serverless en Cloud Run."""

    def __init__(self):
        # Mantenemos las clases de los scrapers
        self.scraper_classes = [
            MeliScraper,
            AmazonScraper,
            LiverpoolScraper,
            WalmartScraper,
            CoppelScraper
        ]

    def search_all(self, query: str, limit_per_store: int = 3) -> List[Dict[str, Any]]:
        all_results = []
        print(f"Lanzando búsqueda secuencial limpia en {len(self.scraper_classes)} tiendas para: '{query}'...\n")

        for scraper_cls in self.scraper_classes:
            store_name = scraper_cls.__name__.replace("Scraper", "")
            try:
                # Instanciamos y ejecutamos un scraper a la vez
                scraper = scraper_cls()
                data = scraper.search(query, limit=limit_per_store)
                
                if data:
                    all_results.extend(data)
                    print(f" {store_name}: {len(data)} productos encontrados.")
                else:
                    print(f" {store_name}: 0 productos encontrados.")
                    
            except Exception as exc:
                print(f" {store_name} generó una excepción: {exc}")
            
            # Pequeña pausa táctica entre scrapers para liberar memoria/sockets
            time.sleep(0.5)

        # Ordenamos de MENOR a MAYOR precio
        all_results.sort(key=lambda x: x["price"])
        return all_results