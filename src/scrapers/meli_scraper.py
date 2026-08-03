import re
import json
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from src.scrapers.base_scraper import BaseScraper

class MeliScraper(BaseScraper):
    """Scraper ultrarrápido y liviano para Mercado Libre usando parsing de HTML + JSON embebido."""

    def __init__(self):
        super().__init__(store_name="MeLi")
        self.base_url = "https://listado.mercadolibre.com.mx/"

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        formatted_query = query.strip().replace(" ", "-")
        url = f"{self.base_url}{formatted_query}"
        results = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-MX,es;q=0.9",
        }

        try:
            response = requests.get(url, headers=headers, timeout=8)
            
            if response.status_code != 200:
                print(f"⚠️ [MeLi Log] Status HTTP: {response.status_code}")
                return []

            html = response.text
            soup = BeautifulSoup(html, "html.parser")
            seen_titles = set()

            # Estrategia 1: Parseo por etiquetas <a> generales que contengan enlaces a articulos de MeLi
            links = soup.find_all("a", href=True)
            for a in links:
                if len(results) >= limit:
                    break

                href = a["href"]
                title = a.text.strip()

                # Filtramos links de productos reales de Mercado Libre
                if ("articulo.mercadolibre.com.mx" in href or "/p/MLM" in href) and len(title) > 10:
                    # Buscamos el contenedor padre para rascar el precio
                    parent = a.parent
                    for _ in range(4):
                        if parent and parent.parent:
                            parent = parent.parent

                    card_text = parent.text if parent else ""
                    
                    # Extraer precio en texto
                    price = 0.0
                    price_match = re.search(r'\$\s*([\d,]+(?:\.\d{2})?)', card_text)
                    if price_match:
                        try:
                            price = float(price_match.group(1).replace(",", ""))
                        except ValueError:
                            price = 0.0

                    if price > 0 and title not in seen_titles:
                        seen_titles.add(title)
                        results.append({
                            "title": title,
                            "price": price,
                            "currency": "MXN",
                            "link": href,
                            "thumbnail": "",
                            "store": self.store_name
                        })

            print(f"🔍 [MeLi Debug] Productos extraídos por fallback: {len(results)}")
            return results

        except Exception as e:
            print(f"❌ Error al consultar Mercado Libre con Requests: {e}")
            return []