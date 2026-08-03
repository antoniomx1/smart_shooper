import re
from seleniumbase import Driver
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from src.scrapers.base_scraper import BaseScraper

class LiverpoolScraper(BaseScraper):
    """Scraper profesional para Liverpool por anclaje directo a etiquetas PDP."""

    def __init__(self):
        super().__init__(store_name="Liverpool")
        self.base_url = "https://www.liverpool.com.mx/tienda?s="

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
            pdp_links = soup.select("a[href*='/tienda/pdp/']")

            seen_titles = set()

            for a in pdp_links:
                if len(results) >= limit:
                    break

                href = a.get("href", "")
                if not href:
                    continue

                # 1. Extraemos el título usando el alt de la imagen o limpiando el texto
                img = a.select_one("img")
                title = ""
                
                if img and img.get("alt") and len(img.get("alt").strip()) > 3:
                    title = img.get("alt").strip()
                else:
                    # Fallback: Extraer desde el slug del enlace (ej: /bocina-portatil-jbl/ -> Bocina Portatil Jbl)
                    match = re.search(r'/pdp/([^/]+)/', href)
                    if match:
                        title = match.group(1).replace("-", " ").title()

                # Si el alt de la imagen es genérico (ej: 'JBL, ROJO'), usamos el fallback del slug
                if title.lower().startswith("jbl,") or len(title) < 5:
                    match = re.search(r'/pdp/([^/]+)/', href)
                    if match:
                        title = match.group(1).replace("-", " ").title()

                # 2. Extraemos el precio buscando números con formato de moneda dentro del enlace
                text_content = a.text.strip()
                prices_found = re.findall(r'\$\s*([\d,]+(?:\.\d{2})?)', text_content)
                
                price = 0.0
                if prices_found:
                    # Tomamos el primer precio (suele ser el precio de oferta/descuento)
                    raw_price = prices_found[0].replace(",", "")
                    try:
                        price = float(raw_price)
                    except ValueError:
                        price = 0.0

                full_link = f"https://www.liverpool.com.mx{href}" if href.startswith("/") else href

                if price > 0 and title and title not in seen_titles:
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
            print(f"❌ Error al consultar Liverpool: {e}")
            return []