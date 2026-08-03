import os
import json
import base64
import requests
from flask import Flask, request, jsonify
from google.cloud import pubsub_v1

# Importaciones de tu pipeline
from src.services.search_manager import SearchManager
from src.services.ai_service import AIService
from src.services.data_pipeline import DataPipeline

app = Flask(__name__)

# Configuración GCP & Telegram
PROJECT_ID = os.environ.get("GCP_PROJECT", "smartshooper")
TOPIC_ID = os.environ.get("PUBSUB_TOPIC", "search-requests-topic")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# Instancia de Pub/Sub Publisher
publicador_client = pubsub_v1.PublisherClient()
TOPIC_PATH = publicador_client.topic_path(PROJECT_ID, TOPIC_ID)

# Instancia de servicios una sola vez al arrancar el contenedor
search_manager = SearchManager()
ai_service = AIService(project_id=PROJECT_ID)
pipeline = DataPipeline(project_id=PROJECT_ID)

def enviar_mensaje_telegram(chat_id, texto):
    if not TELEGRAM_TOKEN:
        print("[Main] Warning: TELEGRAM_BOT_TOKEN no configurado.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"[Main ERROR] Fallo enviando mensaje a Telegram: {e}")

@app.route("/", methods=["GET"])
def health_check():
    return "SmartShopper OK", 200

# =====================================================================
# RUTA 1: EL RECEPTOR / WEBHOOK (RESPUESTA ULTRA RÁPIDA)
# =====================================================================
@app.route('/webhook', methods=['POST'])
def webhook():
    datos = request.get_json(silent=True)
    if not datos or "message" not in datos:
        return jsonify({"status": "ok"}), 200
    
    message = datos["message"]
    chat_id = message.get("chat", {}).get("id")
    texto_recibido = message.get("text", "").strip()

    if not texto_recibido or not chat_id:
        return jsonify({"status": "ok"}), 200

    if texto_recibido.startswith("/start"):
        enviar_mensaje_telegram(
            chat_id, 
            "🛒 *¡Hola! Soy SmartShopper Bot.*\n\nEscríbeme el producto que buscas (ej. `bocina jbl`) y escaneo las tiendas para traerte las mejores ofertas."
        )
        return jsonify({"status": "ok"}), 200

    # 1. Empaquetamos los datos de la búsqueda
    paquete_datos = {
        "chat_id": chat_id,
        "query": texto_recibido
    }
    
    # 2. Transformamos a bytes para Pub/Sub
    datos_en_bytes = json.dumps(paquete_datos).encode("utf-8")
    
    # 3. Publicamos en Pub/Sub en milisegundos
    print(f"--- Publicando búsqueda '{texto_recibido}' del chat {chat_id} en Pub/Sub... ---")
    futuro_envio = publicador_client.publish(TOPIC_PATH, datos_en_bytes)
    futuro_envio.result()
    
    # 4. Avisamos al usuario para calmar ansias (Markdown limpio)
    enviar_mensaje_telegram(
        chat_id, 
        f"🔍 *Buscando ofertas para:* `{texto_recibido}`...\nEn unos segundos te mando el análisis de Gemini."
    )
    
    # 5. HTTP 200 a Telegram de inmediato (evita retries y duplicados)
    return jsonify({"status": "queued"}), 200

# =====================================================================
# RUTA 2: EL TRABAJADOR ASÍNCRONO (INVOCADO POR PUB/SUB PUSH)
# =====================================================================
@app.route('/procesar-busqueda', methods=['POST'])
def procesar_busqueda():
    sobre_mensaje = request.get_json(silent=True)
    if not sobre_mensaje or "message" not in sobre_mensaje:
        return jsonify({"status": "bad request"}), 400
    
    try:
        # 1. Decodificamos el payload desde Base64
        datos_base64 = sobre_mensaje["message"]["data"]
        datos_decodificados = base64.b64decode(datos_base64).decode("utf-8")
        tarea_meta = json.loads(datos_decodificados)
        
        chat_id = tarea_meta["chat_id"]
        query = tarea_meta["query"]
        
        print(f"--- [Worker] Iniciando scraping pesado para '{query}' (Chat {chat_id}) ---")
        
        # 2. Scraping en paralelo
        raw_results = search_manager.search_all(query, limit_per_store=3)
        
        if raw_results:
            # 3. Guardar en GCS Raw Data Lake
            gcs_uri = pipeline.save_raw_to_gcs(query, raw_results)
            
            # 4. Normalizar modelos con Gemini
            enriched_results = ai_service.normalize_product_models(raw_results)
            
            # 5. Guardar datos procesados en BigQuery
            pipeline.insert_to_bigquery(query, enriched_results, gcs_uri)
            
            # 6. RESUMEN INTELIGENTE CON GEMINI 
            mensaje_res = ai_service.generate_telegram_summary(query, enriched_results)
        else:
            mensaje_res = f"No encontré nada disponible para '{query}' ahorita."
        
        # 7. Despachamos la recomendación de Gemini a Telegram
        enviar_mensaje_telegram(chat_id, mensaje_res)
        
    except Exception as e:
        print(f" Error en el procesamiento asíncrono: {str(e)}")
        if 'chat_id' in locals():
            enviar_mensaje_telegram(chat_id, "Hubo un fallo técnico al analizar las tiendas. Intenta de nuevo.")
        
    return jsonify({"status": "processed"}), 200

if __name__ == '__main__':
    puerto = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=puerto)