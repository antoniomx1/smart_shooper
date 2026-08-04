from seleniumbase import Driver
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from src.scrapers.base_scraper import BaseScraper


class MeliScraper(BaseScraper):
    """Scraper para Mercado Libre usando SeleniumBase UC con evasión de detección."""

    def __init__(self):
        super().__init__(store_name="MeLi")
        self.base_url = "https://listado.mercadolibre.com.mx/"

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        formatted_query = query.strip().replace(" ", "-")
        url = f"{self.base_url}{formatted_query}"
        results = []
        driver = None

        try:
            driver = self.get_driver()
            driver.uc_open_with_reconnect(url, reconnect_time=4)

            # Scroll progresivo para que React renderice los productos lazy-load
            driver.execute_script("window.scrollTo(0, 600);")
            driver.sleep(2)
            driver.execute_script("window.scrollTo(0, 1200);")
            driver.sleep(1)

            html_content = driver.page_source

            # Verificar si el HTML tiene contenido real de productos
            if len(html_content) < 5000:
                print(f"[MeLi] HTML too short ({len(html_content)} bytes) - possible anti-bot block.")
                return []

            soup = BeautifulSoup(html_content, "html.parser")

            # Selectores multi-estrategia para tarjetas de producto
            items = soup.select(
                ".poly-card, "
                ".ui-search-result, "
                ".ui-search-layout__item, "
                "li.ui-search-layout__stack, "
                "div[class*='poly-card']"
            )

            # Fallback: si no hay tarjetas, buscar precio como ancla
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

                title_elem = item.select_one(
                    ".poly-component__title, "
                    ".ui-search-item__title, "
                    "h2, h3, "
                    ".ui-search-item__group__element"
                )

                link_elem = (
                    item.select_one("a[href*='mercadolibre.com.mx']")
                    or item.select_one("a[href*='articulo.mercadolibre']")
                    or item.select_one("a")
                )

                price_elem = item.select_one(".andes-money-amount__fraction")

                if title_elem and price_elem and link_elem:
                    title = title_elem.text.strip()
                    raw_price = price_elem.text.strip().replace(",", "").replace(".", "")
                    price = float(raw_price) if raw_price.isdigit() else 0.0
                    link = link_elem.get("href", "")

                    # Desduplicar por título + precio
                    key = f"{title[:50]}_{price}"
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

            print(f"[MeLi] Products found: {len(results)}")
            return results

        except Exception as e:
            print(f"[MeLi] Search error: {e}")
            return []
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
