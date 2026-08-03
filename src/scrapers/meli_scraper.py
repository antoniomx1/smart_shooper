import requests
from typing import List, Dict, Any
from src.scrapers.base_scraper import BaseScraper

class MeliScraper(BaseScraper):
    """Scraper ultrarrápido para Mercado Libre usando la API REST pública."""

    def __init__(self):
        super().__init__(store_name="MeLi")
        self.api_url = "https://api.mercadolibre.com/sites/MLM/search"

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        results = []
        params = {
            "q": query.strip(),
            "limit": limit
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            response = requests.get(self.api_url, params=params, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("results", [])

                for item in items:
                    title = item.get("title", "")
                    price = float(item.get("price", 0.0))
                    link = item.get("permalink", "")
                    thumbnail = item.get("thumbnail", "")

                    if price > 0 and title:
                        results.append({
                            "title": title,
                            "price": price,
                            "currency": "MXN",
                            "link": link,
                            "thumbnail": thumbnail,
                            "store": self.store_name
                        })
                return results
            else:
                print(f"⚠️ [MeLi API] Status code inesperado: {response.status_code}")
                return []

        except Exception as e:
            print(f"❌ Error al consultar la API de Mercado Libre: {e}")
            return []