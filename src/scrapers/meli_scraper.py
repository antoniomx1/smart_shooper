import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from src.scrapers.base_scraper import BaseScraper

class MeliScraper(BaseScraper):
    """Scraper ultrarrápido y liviano para Mercado Libre usando requests + BS4."""

    def __init__(self):
        super().__init__(store_name="MeLi")
        self.base_url = "https://listado.mercadolibre.com.mx/"

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        formatted_query = query.strip().replace(" ", "-")
        url = f"{self.base_url}{formatted_query}"
        results = []

        # Headers simulan navegador Chrome real
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "es-MX,es-419;q=0.9,es;q=0.8",
            "Cache-Control": "max-age=0",
        }

        try:
            response = requests.get(url, headers=headers, timeout=8)
            
            if response.status_code != 200:
                print(f"⚠️ [MeLi Log] Status HTTP: {response.status_code}")
                return []

            soup = BeautifulSoup(response.text, "html.parser")
            
            # Búsqueda ampliada de selectores por si cambia la estructura
            items = soup.select(".poly-card, .ui-search-layout__item, .ui-search-result, .ui-search-layout__stack")

            # LOG DE DIAGNÓSTICO
            print(f"🔍 [MeLi Debug] Items detectados con BS4: {len(items)} | URL: {url}")

            seen_titles = set()

            for item in items:
                if len(results) >= limit:
                    break

                title_elem = item.select_one(".poly-component__title, .ui-search-item__title, h2, h3")
                link_elem = item.select_one("a[href*='mercadolibre.com.mx']") or item.select_one("a")
                price_elem = item.select_one(".andes-money-amount__fraction")

                if title_elem and price_elem and link_elem:
                    title = title_elem.text.strip()
                    raw_price = price_elem.text.strip().replace(",", "").replace(".", "")
                    price = float(raw_price) if raw_price.isdigit() else 0.0
                    link = link_elem.get("href", "")

                    if price > 0 and title not in seen_titles:
                        seen_titles.add(title)
                        results.append({
                            "title": title,
                            "price": price,
                            "currency": "MXN",
                            "link": link,
                            "thumbnail": "",
                            "store": self.store_name
                        })

            return results

        except Exception as e:
            print(f"❌ Error al consultar Mercado Libre con Requests: {e}")
            return []