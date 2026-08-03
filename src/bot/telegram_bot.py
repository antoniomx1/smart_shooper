import os
import json
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from src.services.search_manager import SearchManager
from src.services.ai_service import AIService
from src.services.data_pipeline import DataPipeline

# Token de Telegram desde variable de entorno
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    chat_id = update.effective_chat.id

    ai_service = AIService(project_id="smartshooper")

    # 1. EVALUAR INTENCIÓN Y BLINDAJE CON IA
    classification = ai_service.classify_user_input(user_text)
    intent = classification.get("intent")

    # Caso A: Intento de Injection o entrada inválida
    if intent == "INJECTION_OR_INVALID":
        await context.bot.send_message(
            chat_id=chat_id, 
            text="⚠️ **Acción no permitida.** Solo puedo ayudarte a comparar precios de productos en tiendas de México."
        )
        return

    # Caso B: Saludo o plática casual
    if intent == "CHAT":
        reply = classification.get("reply_message") or "¡Qué onda! Escríbeme el nombre de un producto (ej: *Bocina JBL*) y te busco los mejores precios."
        await context.bot.send_message(chat_id=chat_id, text=reply, parse_mode="HTML")
        return

    # Caso C: Búsqueda legítima de producto
    clean_query = classification.get("clean_query", user_text)

    # Feedback inmediato
    await context.bot.send_message(
        chat_id=chat_id, 
        text=f"🔎 Buscando <b>'{clean_query}'</b> en las 5 tiendas en tiempo real... Espera unos segundos.",
        parse_mode="HTML"
    )

    # 2. INSTANCIAR Y EJECUTAR PIPELINE
    search_manager = SearchManager()
    pipeline = DataPipeline(project_id="smartshooper")

    raw_results = search_manager.search_all(clean_query, limit_per_store=3)

    if raw_results:
        gcs_uri = pipeline.save_raw_to_gcs(clean_query, raw_results)
        enriched_results = ai_service.normalize_product_models(raw_results)
        pipeline.insert_to_bigquery(clean_query, enriched_results, gcs_uri)

        final_response = ai_service.generate_telegram_summary(clean_query, enriched_results)
    else:
        final_response = f"❌ Chale, no encontré productos para '{clean_query}' en las tiendas ahorita."

    # 3. ENVIAR RESPUESTA FINAL
    try:
        await context.bot.send_message(chat_id=chat_id, text=final_response, parse_mode="Markdown")
    except Exception as e:
        print(f"⚠️ Error enviando HTML: {e}")
        await context.bot.send_message(chat_id=chat_id, text=final_response)

def start_bot():
    if not TELEGRAM_TOKEN:
        raise ValueError(" Falta la variable de entorno TELEGRAM_BOT_TOKEN")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print(" Bot de Telegram corriendo y escuchando mensajes...")
    app.run_polling()

if __name__ == "__main__":
    start_bot()