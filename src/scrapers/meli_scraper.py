from seleniumbase import Driver
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from src.scrapers.base_scraper import BaseScraper

class MeliScraper(BaseScraper):
    """Scraper profesional para Mercado Libre usando SeleniumBase UC."""

    def __init__(self):
        super().__init__(store_name="MeLi")
        self.base_url = "https://listado.mercadolibre.com.mx/"

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        formatted_query = query.strip().replace(" ", "-")
        url = f"{self.base_url}{formatted_query}"
        results = []

        try:
            # Levantamos UC Mode en modo Headless
            driver = self.get_driver()
            driver.uc_open_with_reconnect(url, reconnect_time=3)
            
            html_content = driver.page_source
            driver.quit()

            soup = BeautifulSoup(html_content, "html.parser")
            items = soup.select(".poly-card, .ui-search-layout__item, .ui-search-result")

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

                    # Evitamos duplicados por título o si el precio es cero
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
            print(f"❌ Error al consultar Mercado Libre con SeleniumBase: {e}")
            return []