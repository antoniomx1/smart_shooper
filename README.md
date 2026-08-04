# SmartShopper

Bot de comparacion de precios en tiempo real para e-commerce mexicano, usando web scraping, Vertex AI Gemini y Google Cloud Platform.

## Descripcion general

SmartShopper es un bot de Telegram que escanea cinco tiendas mexicanas, extrae listados de productos, los normaliza con Gemini y devuelve una recomendacion al usuario basada en precio y especificaciones. El sistema esta disenado como un pipeline serverless orientado a eventos sobre GCP.

Un usuario envia el nombre de un producto por Telegram. El webhook encola la solicitud en Pub/Sub y responde de inmediato. Un worker en Cloud Run procesa la busqueda: ejecuta los scrapers de forma secuencial, normaliza los resultados con Vertex AI Gemini y envia la comparacion al usuario. En paralelo, los datos sin procesar se archivan en Cloud Storage y se transmiten a BigQuery para su analisis posterior.

## Arquitectura

```
Telegram -> Cloud Run (/webhook) -> Pub/Sub -> Cloud Run (/procesar-busqueda)
                                                  |
                                                  +-> Scrapers (Amazon, Liverpool, Coppel, MeLi, Walmart)
                                                  +-> Vertex AI Gemini (normalizacion + recomendacion)
                                                  +-> Cloud Storage (JSON sin procesar)
                                                  +-> BigQuery (datos estructurados)
                                                  |
                                                  v
                                            Telegram (respuesta)
```

El endpoint del webhook responde a Telegram de inmediato (HTTP 200) para evitar reintentos, mientras el procesamiento pesado ocurre de forma asincrona en un servicio Cloud Run separado, activado mediante suscripcion push de Pub/Sub. Este desacoplamiento mantiene los tiempos de respuesta por debajo del limite de Telegram y aisla las fallas.

## Tiendas soportadas

| Tienda | Metodo de scraping | Estado |
|--------|--------------------|--------|
| Amazon Mexico | SeleniumBase UC (Chromium headless) | Activo |
| Liverpool | SeleniumBase UC | Activo |
| Coppel | SeleniumBase UC | Activo |
| Mercado Libre | SeleniumBase UC | Activo (local), bloqueado en Cloud Run |
| Walmart Mexico | SeleniumBase UC + evasion de huella | Activo (local), bloqueado en Cloud Run |

### Limitaciones anti-bot

Mercado Libre y Walmart emplean proteccion anti-bot a nivel CDN (CloudFront WAF y Akamai/PerimeterX, respectivamente). Estos servicios marcan las solicitudes originadas desde rangos IP de datacenter, incluyendo las IPs de salida de Cloud Run.

Los scrapers funcionan correctamente desde una IP residencial. En un despliegue de produccion, la solucion consistiria en enrutar el trafico a traves de un proxy residencial rotativo o usar una API de scraping gestionada. Esta limitacion se documenta como un caso real de ingenieria: la arquitectura lo maneja devolviendo resultados parciales en lugar de fallar por completo.

## Stack tecnologico

- **Runtime:** Python 3.11, Flask
- **Scraping:** SeleniumBase (modo undetected-chrome), BeautifulSoup 4
- **IA:** Vertex AI Gemini (gemini-2.5-flash) para normalizacion de productos y generacion de respuestas
- **Infraestructura:** Cloud Run (contenedores serverless), Cloud Pub/Sub (mensajeria asincrona), Cloud Storage (data lake), BigQuery (analitica)
- **Interfaz de bot:** API de Telegram (modo webhook)
- **Contenedor:** Docker, Chromium headless

## Estructura del proyecto

```
smart_shooper/
|-- main.py                      # Servidor Flask: endpoints webhook + worker
|-- Dockerfile                   # Imagen de contenedor con Chromium para Cloud Run
|-- requirements.txt
|-- config/
|   |-- settings.py              # Configuracion centralizada por variables de entorno
|-- src/
    |-- scrapers/
    |   |-- base_scraper.py      # Clase base abstracta con fabrica de drivers UC
    |   |-- amazon_scraper.py
    |   |-- liverpool_scraper.py
    |   |-- coppel_scraper.py
    |   |-- meli_scraper.py
    |   |-- walmart_scraper.py
    |-- ai/
    |   |-- gemini_parser.py     # Definicion de esquemas para parsing con Gemini
    |-- bot/
    |   |-- telegram_bot.py      # Despacho de mensajes de Telegram
    |-- services/
        |-- search_manager.py    # Orquestador secuencial de scrapers
        |-- ai_service.py        # Cliente de Vertex AI Gemini + normalizacion + resumenes
        |-- data_pipeline.py     # Persistencia en GCS y BigQuery
```

## Desarrollo local

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configurar variables de entorno requeridas
cp .env.example .env

python main.py
```

Probando un scraper individual:

```python
from src.scrapers.amazon_scraper import AmazonScraper
scraper = AmazonScraper()
results = scraper.search("audifonos bose", limit=3)
```

## Despliegue

El proyecto se despliega en Cloud Run mediante Cloud Build. El contenedor incluye las dependencias de Python junto con Chromium headless. Las variables de entorno se inyectan en tiempo de ejecucion a traves de la configuracion de Cloud Run.

## Lo que demuestra este proyecto

- Arquitectura serverless orientada a eventos en GCP (Cloud Run, Pub/Sub, BigQuery)
- Automatizacion de navegador y web scraping con tecnicas anti-deteccion
- Integracion con APIs de LLM (Vertex AI Gemini) para normalizacion de datos no estructurados
- Diseno de pipeline de datos: ingestion, procesamiento, almacenamiento y data warehousing
- Manejo de restricciones reales como proteccion anti-bot a nivel CDN y reputacion de IP
