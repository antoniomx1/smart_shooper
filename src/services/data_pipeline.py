import json
import uuid
from datetime import datetime, timezone
from google.cloud import storage, bigquery

class DataPipeline:
    """Módulo exclusivo de persistencia en Data Lake (GCS) y Data Warehouse (BigQuery)."""

    def __init__(self, project_id: str = "smartshooper"):
        self.project_id = project_id
        self.bucket_name = "smartshooper-raw-data"
        self.dataset_id = "smart_shopper_dw"
        self.table_id = "historical_prices"

        self.gcs_client = storage.Client(project=self.project_id)
        self.bq_client = bigquery.Client(project=self.project_id)

    def save_raw_to_gcs(self, query: str, search_results: list) -> str:
        try:
            bucket = self.gcs_client.bucket(self.bucket_name)
            now = datetime.now(timezone.utc)
            formatted_query = query.strip().lower().replace(" ", "_")
            timestamp_str = now.strftime("%Y%m%d_%H%M%S")
            
            blob_path = f"raw/{now.strftime('%Y/%m/%d')}/{formatted_query}_{timestamp_str}.json"
            blob = bucket.blob(blob_path)

            payload = {
                "search_query": query,
                "executed_at_utc": now.isoformat(),
                "total_results": len(search_results),
                "results": search_results
            }

            blob.upload_from_string(
                data=json.dumps(payload, ensure_ascii=False, indent=2),
                content_type="application/json"
            )

            gcs_uri = f"gs://{self.bucket_name}/{blob_path}"
            print(f"[GCS] Raw guardado en {gcs_uri}")
            return gcs_uri
        except Exception as e:
            print(f"[GCS ERROR] {e}")
            return ""

    def insert_to_bigquery(self, query: str, products: list, gcs_uri: str) -> bool:
        if not products:
            return False

        table_ref = f"{self.project_id}.{self.dataset_id}.{self.table_id}"
        search_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        today_date = now.strftime("%Y-%m-%d")

        rows_to_insert = []
        for prod in products:
            rows_to_insert.append({
                "search_id": search_id,
                "search_query": query,
                "product_title": prod.get("title", ""),
                "normalized_model": prod.get("normalized_model", "UNASSIGNED"),
                "store": prod.get("store", ""),
                "price": float(prod.get("price", 0.0)),
                "currency": prod.get("currency", "MXN"),
                "product_link": prod.get("link", ""),
                "raw_gcs_uri": gcs_uri,
                "search_date": today_date,
                "created_at": now.isoformat()
            })

        errors = self.bq_client.insert_rows_json(table_ref, rows_to_insert)
        if not errors:
            print(f"[BigQuery] {len(rows_to_insert)} registros insertados.")
            return True
        else:
            print(f"[BigQuery ERROR] {errors}")
            return False