import re
from urllib.parse import unquote
from seleniumbase import Driver
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from src.scrapers.base_scraper import BaseScraper

class WalmartScraper(BaseScraper):
    """Scraper profesional para Walmart México usando análisis de nodos /ip/."""

    def __init__(self):
        super().__init__(store_name="Walmart")
        self.base_url = "https://www.walmart.com.mx/search?q="

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        formatted_query = query.strip().replace(" ", "+")
        url = f"{self.base_url}{formatted_query}"
        results = []

        try:
            driver = self.get_driver()
            driver.uc_open_with_reconnect(url, reconnect_time=4)
            
            driver.execute_script("window.scrollTo(0, 1000);")
            driver.sleep(2)
            
            html_content = driver.page_source
            driver.quit()

            soup = BeautifulSoup(html_content, "html.parser")
            ip_links = [a for a in soup.find_all("a") if a.get("href") and "/ip/" in a.get("href")]

            seen_titles = set()

            for a in ip_links:
                if len(results) >= limit:
                    break

                raw_href = a.get("href", "")
                title = a.text.strip()

                if not title or len(title) < 5:
                    continue

                # Subimos 3 niveles para encontrar la tarjeta y extraer el precio actual
                card = a
                for _ in range(3):
                    if card.parent:
                        card = card.parent

                card_text = card.text if card else ""
                
                # Buscamos patrones como "precio actual $1,399.00" o simplemente "$1,399.00"
                price = 0.0
                price_match = re.search(r'precio actual\s*\$\s*([\d,]+(?:\.\d{2})?)', card_text, re.IGNORECASE)
                
                if price_match:
                    price_str = price_match.group(1).replace(",", "")
                    try:
                        price = float(price_str)
                    except ValueError:
                        price = 0.0
                else:
                    # Fallback de búsqueda de precio general en la tarjeta
                    all_prices = re.findall(r'\$\s*([\d,]+(?:\.\d{2})?)', card_text)
                    if all_prices:
                        try:
                            price = float(all_prices[0].replace(",", ""))
                        except ValueError:
                            price = 0.0

                # Limpiamos la URL por si viene enmascarada con el tracker de Walmart
                clean_link = raw_href
                if "rd=" in raw_href:
                    # Extraemos el redirect real encodeado
                    match_rd = re.search(r'rd=(https%3A%2F%2F[^\&]+)', raw_href)
                    if match_rd:
                        clean_link = unquote(match_rd.group(1))

                if price > 0 and title not in seen_titles:
                    seen_titles.add(title)
                    results.append({
                        "title": title,
                        "price": price,
                        "currency": "MXN",
                        "link": clean_link,
                        "thumbnail": "",
                        "store": self.store_name
                    })

            return results

        except Exception as e:
            print(f"❌ Error al consultar Walmart: {e}")
            return []