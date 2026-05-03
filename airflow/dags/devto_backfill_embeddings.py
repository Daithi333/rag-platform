"""Manual DAG for backfilling missing embeddings on indexed articles.

Finds chunks in OpenSearch that have no embedding vector and re-indexes
their parent articles (delete old chunks, re-chunk, embed, index).

No params needed -- automatically finds and processes all affected articles.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

from devto_ingestion.indexing import reindex_missing_embeddings, setup_opensearch_index

default_args = {
    "owner": "devto-ingestion",
    "depends_on_past": False,
    "start_date": datetime(2026, 3, 17),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "devto_backfill_embeddings",
    default_args=default_args,
    description="Manual backfill: re-index articles with missing embeddings",
    schedule=None,
    max_active_runs=1,
    tags=["devto", "opensearch", "embeddings", "backfill", "manual"],
)

setup_task = PythonOperator(
    task_id="setup_opensearch_index",
    python_callable=setup_opensearch_index,
    dag=dag,
)

backfill_task = PythonOperator(
    task_id="reindex_missing_embeddings",
    python_callable=reindex_missing_embeddings,
    dag=dag,
)

setup_task >> backfill_task
