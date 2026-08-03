import re
from seleniumbase import Driver
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from src.scrapers.base_scraper import BaseScraper

class CoppelScraper(BaseScraper):
    """Scraper profesional para Coppel con aislamiento por tarjeta cpl-card__root."""

    def __init__(self):
        super().__init__(store_name="Coppel")
        self.base_url = "https://www.coppel.com/SearchDisplay?searchTerm="

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        formatted_query = query.strip().replace(" ", "+")
        url = f"{self.base_url}{formatted_query}"
        results = []

        try:
            driver = self.get_driver()
            driver.uc_open_with_reconnect(url, reconnect_time=4)
            
            driver.execute_script("window.scrollTo(0, 800);")
            driver.sleep(2)
            
            html_content = driver.page_source
            driver.quit()

            soup = BeautifulSoup(html_content, "html.parser")
            
            # Buscamos directamente las tarjetas individuales de Coppel
            cards = soup.select(".cpl-card__root, [class*='cpl-card']")
            
            # Fallback si cambia la clase de las tarjetas
            if not cards:
                cards = []
                for a in soup.select("a[href*='/pdp/']"):
                    card_parent = a.find_parent("div", class_=re.compile(r"cpl-card")) or a.parent
                    if card_parent and card_parent not in cards:
                        cards.append(card_parent)

            seen_titles = set()

            for card in cards:
                if len(results) >= limit:
                    break

                # 1. Enlace al PDP
                link_elem = card.select_one("a[href*='/pdp/']") or card.select_one("a")
                if not link_elem:
                    continue

                href = link_elem.get("href", "")
                if not href or "SearchDisplay" in href:
                    continue

                # 2. Título
                title = ""
                img = card.select_one("img")
                if img and img.get("alt") and len(img.get("alt").strip()) > 3:
                    title = img.get("alt").strip()
                else:
                    raw_text = link_elem.text.strip()
                    # Limpiamos prefijos de badges como "Oferta"
                    title = re.sub(r'^(Oferta|Nuevo|Exclusivo en línea)\s*', '', raw_text, flags=re.IGNORECASE)

                if not title or len(title) < 5:
                    continue

                # 3. Precio aislado
                price = 0.0
                prices_found = re.findall(r'\$\s*([\d,]+(?:\.\d{2})?)', card.text)

                if prices_found:
                    try:
                        # El primer precio en cpl-card__root es el precio de contado/oferta
                        price = float(prices_found[0].replace(",", ""))
                    except ValueError:
                        price = 0.0

                full_link = f"https://www.coppel.com{href}" if href.startswith("/") else href

                if price > 0 and title not in seen_titles:
                    seen_titles.add(title)
                    results.append({
                        "title": title,
                        "price": price,
                        "currency": "MXN",
                        "link": full_link,
                        "thumbnail": "",
                        "store": self.store_name
                    })

            return results

        except Exception as e:
            print(f"❌ Error al consultar Coppel: {e}")
            return []