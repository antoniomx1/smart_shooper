import os
import base64
import json
import time
from flask import Flask, request, jsonify
from src.services.search_manager import SearchManager
from src.services.ai_service import AIService
from src.services.data_pipeline import DataPipeline

app = Flask(__name__)

# Instancia de servicios una sola vez al arrancar
search_manager = SearchManager()
ai_service = AIService(project_id="smartshooper")
pipeline = DataPipeline(project_id="smartshooper")

@app.route("/", methods=["GET"])
def health_check():
    # Para que Cloud Run sepa que la app está viva en el puerto 8080
    return "SmartShopper Worker OK", 200

@app.route("/pubsub", methods=["POST"])
def process_pubsub_message():
    """Endpoint para recibir la tarea desde Pub/Sub Push Subscription"""
    envelope = request.get_json()
    if not envelope:
        return "Bad Request: No Pub/Sub envelope found", 400

    if not isinstance(envelope, dict) or "message" not in envelope:
        return "Bad Request: Invalid Pub/Sub message format", 400

    pubsub_message = envelope["message"]
    
    # Decodificar el mensaje enviado por Pub/Sub
    if "data" in pubsub_message:
        data_str = base64.b64decode(pubsub_message["data"]).decode("utf-8").strip()
        payload = json.loads(data_str)
    else:
        return "OK", 200

    query = payload.get("query", "bocina jbl")
    chat_id = payload.get("chat_id")

    print(f"[Worker] Procesando búsqueda recibida desde Pub/Sub para: '{query}'")

    start_time = time.time()
    
    # 1. Scraping en paralelo
    raw_results = search_manager.search_all(query, limit_per_store=3)
    
    if raw_results:
        # 2. Persistencia en Raw Data Lake (GCS)
        gcs_uri = pipeline.save_raw_to_gcs(query, raw_results)
        
        # 3. Normalización con servicio de IA
        enriched_results = ai_service.normalize_product_models(raw_results)
        
        # 4. Inserción a Data Warehouse (BigQuery)
        pipeline.insert_to_bigquery(query, enriched_results, gcs_uri)
    else:
        enriched_results = []

    end_time = time.time()
    total_time = round(end_time - start_time, 2)
    print(f"[Worker] Búsqueda completada en {total_time}s para '{query}'")

    # TODO: Enviar mensaje de respuesta a Telegram usando chat_id

    return jsonify({"status": "success", "query": query, "time": total_time}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)