import re
import json
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from src.scrapers.base_scraper import BaseScraper

class MeliScraper(BaseScraper):
    """Scraper ultrarrápido para Mercado Libre inspeccionando payloads JSON internos."""

    def __init__(self):
        super().__init__(store_name="MeLi")
        self.base_url = "https://listado.mercadolibre.com.mx/"

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        formatted_query = query.strip().replace(" ", "-")
        url = f"{self.base_url}{formatted_query}"
        results = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "es-MX,es;q=0.9",
        }

        try:
            response = requests.get(url, headers=headers, timeout=8)
            
            if response.status_code != 200:
                print(f"⚠️ [MeLi Log] Status HTTP: {response.status_code}")
                return []

            html = response.text
            seen_titles = set()

            # ESTRATEGIA 1: Buscar bloques JSON dentro de las etiquetas <script>
            # MeLi mete los ítems en variables JS tipo "results":[{...}] o "results": [...]
            json_matches = re.findall(r'\{\s*"id"\s*:\s*"MLM[^"]+"\s*,\s*"title"\s*:\s*"([^"]+)"\s*,\s*"price"\s*:\s*([\d\.]+)', html)

            if json_matches:
                for title, price_str in json_matches:
                    if len(results) >= limit:
                        break
                    try:
                        price = float(price_str)
                        if price > 0 and title not in seen_titles:
                            seen_titles.add(title)
                            results.append({
                                "title": title,
                                "price": price,
                                "currency": "MXN",
                                "link": url, # Fallback link general de búsqueda si viene anonimizado
                                "thumbnail": "",
                                "store": self.store_name
                            })
                    except ValueError:
                        continue

            # ESTRATEGIA 2: Fallback por Regex de enlaces + precios en el texto crudo del HTML
            if not results:
                # Búsqueda rápida de títulos dentro de h2/h3 usando Regex directo en el HTML crudo
                titles_raw = re.findall(r'<h[23][^>]*class="[^"]*poly-[^"]*"[^>]*>([^<]+)</h[23]>', html)
                prices_raw = re.findall(r'class="andes-money-amount__fraction"[^>]*>([\d\.,]+)<', html)

                for i in range(min(len(titles_raw), len(prices_raw))):
                    if len(results) >= limit:
                        break
                    
                    title = titles_raw[i].strip()
                    price_str = prices_raw[i].replace(",", "").replace(".", "")
                    price = float(price_str) if price_str.isdigit() else 0.0

                    if price > 0 and title not in seen_titles:
                        seen_titles.add(title)
                        results.append({
                            "title": title,
                            "price": price,
                            "currency": "MXN",
                            "link": url,
                            "thumbnail": "",
                            "store": self.store_name
                        })

            print(f"🔍 [MeLi Debug] Extraídos vía Regex/JSON: {len(results)}")
            return results

        except Exception as e:
            print(f"❌ Error al consultar Mercado Libre con Requests: {e}")
            return []