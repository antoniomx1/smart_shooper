from curl_cffi import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from src.scrapers.base_scraper import BaseScraper

class MeliScraper(BaseScraper):
    """Scraper ultrarrápido para Mercado Libre con parsing resiliente sobre TLS Chrome."""

    def __init__(self):
        super().__init__(store_name="MeLi")
        self.base_url = "https://listado.mercadolibre.com.mx/"

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        formatted_query = query.strip().replace(" ", "-")
        url = f"{self.base_url}{formatted_query}"
        results = []

        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "es-MX,es-419;q=0.9,es;q=0.8",
        }

        try:
            response = requests.get(url, headers=headers, impersonate="chrome", timeout=8)
            
            if response.status_code != 200:
                print(f"⚠️ [MeLi Log] Status HTTP: {response.status_code}")
                return []

            # LOG DE ORO: Vamos a ver qué diantres nos regresa MeLi
            print(f"📄 [MeLi Preview HTML]: {response.text[:500].replace('\n', ' ')}")

            soup = BeautifulSoup(response.text, "html.parser")
            items = soup.select(".poly-card, .ui-search-result, .ui-search-layout__item, li.ui-search-layout__stack")

            if not items:
                items = []
                for price_elem in soup.select(".andes-money-amount"):
                    parent = price_elem.find_parent("li") or price_elem.find_parent("div")
                    if parent and parent not in items:
                        items.append(parent)

            seen_titles = set()

            for item in items:
                if not item or len(results) >= limit:
                    break

                title_elem = item.select_one(".poly-component__title, .ui-search-item__title, h2, h3, .ui-search-item__group__element")
                link_elem = item.select_one("a[href*='mercadolibre.com.mx']") or item.select_one("a")
                price_elem = item.select_one(".andes-money-amount__fraction")

                if title_elem and price_elem and link_elem:
                    title = title_elem.text.strip()
                    raw_price = price_elem.text.strip().replace(",", "").replace(".", "")
                    price = float(raw_price) if raw_price.isdigit() else 0.0
                    link = link_elem.get("href", "")

                    if price > 0 and title not in seen_titles and len(title) > 3:
                        seen_titles.add(title)
                        results.append({
                            "title": title,
                            "price": price,
                            "currency": "MXN",
                            "link": link,
                            "thumbnail": "",
                            "store": self.store_name
                        })

            print(f"🔍 [MeLi Debug TLS] Productos procesados: {len(results)}")
            return results

        except Exception as e:
            print(f"❌ Error al consultar Mercado Libre con curl_cffi: {e}")
            return []