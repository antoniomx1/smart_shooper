import re
from seleniumbase import Driver
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from src.scrapers.base_scraper import BaseScraper

class AmazonScraper(BaseScraper):
    """Scraper profesional para Amazon México usando SeleniumBase UC y selectores híbridos."""

    def __init__(self):
        super().__init__(store_name="Amazon")
        self.base_url = "https://www.amazon.com.mx/s?k="

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        formatted_query = query.strip().replace(" ", "+")
        url = f"{self.base_url}{formatted_query}"
        results = []

        try:
            driver = self.get_driver()
            driver.uc_open_with_reconnect(url, reconnect_time=3)
            
            html_content = driver.page_source
            driver.quit()

            soup = BeautifulSoup(html_content, "html.parser")
            
            # Selectores amplios de resultados en Amazon
            items = soup.select("div[data-component-type='s-search-result'], div.s-result-item[data-asin]")

            seen_titles = set()

            for item in items:
                if len(results) >= limit:
                    break

                # Título
                title_elem = item.select_one("h2 a span, h2 span, span.a-size-base-plus, span.a-size-medium")
                # Link
                link_elem = item.select_one("h2 a, a.a-link-normal.s-no-outline")

                # Estrategia 1 de precio: .a-price .a-offscreen
                price_offscreen = item.select_one(".a-price .a-offscreen")
                # Estrategia 2 de precio: .a-price-whole
                price_whole = item.select_one(".a-price-whole")

                price = 0.0

                if price_offscreen:
                    # Formato típico: "$1,299.00" -> 1299.00
                    raw_p = price_offscreen.text.replace("$", "").replace(",", "").strip()
                    try:
                        price = float(raw_p)
                    except ValueError:
                        price = 0.0
                elif price_whole:
                    whole_str = price_whole.text.strip().replace(",", "").replace(".", "")
                    price_fraction = item.select_one(".a-price-fraction")
                    fraction_str = price_fraction.text.strip() if price_fraction else "00"
                    try:
                        price = float(f"{whole_str}.{fraction_str}")
                    except ValueError:
                        price = 0.0

                if title_elem and link_elem and price > 0:
                    title = title_elem.text.strip()
                    raw_href = link_elem.get("href", "")
                    
                    if not raw_href:
                        continue

                    link = f"https://www.amazon.com.mx{raw_href}" if raw_href.startswith("/") else raw_href

                    if title not in seen_titles:
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
            print(f"❌ Error al consultar Amazon con SeleniumBase: {e}")
            return []