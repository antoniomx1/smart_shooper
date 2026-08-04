import re
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from src.scrapers.base_scraper import BaseScraper


class WalmartScraper(BaseScraper):
    """Scraper para Walmart México con protección anti-bot reforzada."""

    def __init__(self):
        super().__init__(store_name="Walmart")
        self.base_url = "https://www.walmart.com.mx/search?q="

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        formatted_query = query.strip().replace(" ", "+")
        url = f"{self.base_url}{formatted_query}"
        results = []
        driver = None

        try:
            driver = self.get_driver(extra_evasion=True)
            driver.uc_open_with_reconnect(url, reconnect_time=5)

            # Scroll progresivo para cargar contendores lazy y superar detección JS
            driver.execute_script("window.scrollTo(0, 500);")
            driver.sleep(3)
            driver.execute_script("window.scrollTo(0, 1000);")
            driver.sleep(2)

            html_content = driver.page_source

            # HTML muy corto = bloqueo seguro
            if len(html_content) < 8000:
                print(f"[Walmart] HTML too short ({len(html_content)} bytes) - possible anti-bot block.")
                return []

            soup = BeautifulSoup(html_content, "html.parser")

            # Estrategia 1: Links a PDP con slug de producto
            ip_links = [a for a in soup.find_all("a") if a.get("href") and "/ip/" in a.get("href")]

            seen_titles = set()

            for a in ip_links:
                if len(results) >= limit:
                    break

                raw_href = a.get("href", "")
                title = a.text.strip()

                if not title or len(title) < 5:
                    continue

                # Subir hasta el contendor de la card para buscar precio
                card = a
                for _ in range(4):
                    if card.parent:
                        card = card.parent

                card_text = card.get_text() if card else ""

                # Extraer precio: múltiples patrones
                price = 0.0
                price_patterns = [
                    r'precio\s+actual\s*\$?\s*([\d,]+(?:\.\d{2})?)',
                    r'\$\s*([\d,]+(?:\.\d{2})?)',
                    r'([\d,]+(?:\.\d{2})?)\s*\$',
                ]

                for pattern in price_patterns:
                    price_match = re.search(pattern, card_text, re.IGNORECASE)
                    if price_match:
                        price_str = price_match.group(1).replace(",", "")
                        try:
                            price = float(price_str)
                            if price > 0:
                                break
                        except ValueError:
                            price = 0.0

                if price > 0 and title not in seen_titles and len(title) > 5:
                    seen_titles.add(title)
                    results.append({
                        "title": title,
                        "price": price,
                        "currency": "MXN",
                        "link": raw_href,
                        "thumbnail": "",
                        "store": self.store_name
                    })

            print(f"[Walmart] Products found: {len(results)}")
            return results

        except Exception as e:
            print(f"[Walmart] Search error: {e}")
            return []
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
