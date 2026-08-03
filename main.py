import time
from src.services.search_manager import SearchManager
from src.services.ai_service import AIService
from src.services.data_pipeline import DataPipeline

def main():
    query = "bocina jbl"
    
    # Instancia de módulos independientes
    search_manager = SearchManager()
    ai_service = AIService(project_id="smartshooper")
    pipeline = DataPipeline(project_id="smartshooper")

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

    print("\n" + "="*70)
    print(f"RANKING DE PRECIOS CONSOLIDADO (Tiempo total: {total_time}s)")
    print("="*70 + "\n")

    for i, prod in enumerate(enriched_results, 1):
        print(f"{i}. [{prod['store']}] {prod['title']}")
        print(f"   Modelo Estandarizado: {prod.get('normalized_model', 'N/A')}")
        print(f"   Precio: ${prod['price']:,.2f} {prod['currency']}")
        print(f"   Link: {prod['link']}")
        print("-" * 70)

if __name__ == "__main__":
    main()