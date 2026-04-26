"""Manual DAG for backfill-indexing articles into OpenSearch.

Trigger from the Airflow UI with a config like:
  {"start_date": "2026-01-01", "end_date": "2026-04-26"}

If no end_date is provided, indexes everything from start_date onwards.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

from devto_ingestion.indexing import index_articles_by_date, setup_opensearch_index

default_args = {
    "owner": "devto-ingestion",
    "depends_on_past": False,
    "start_date": datetime(2026, 3, 17),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "devto_backfill_indexing",
    default_args=default_args,
    description="Manual backfill: index existing articles into OpenSearch by date range",
    schedule=None,
    max_active_runs=1,
    tags=["devto", "opensearch", "backfill", "manual"],
    params={
        "start_date": "2026-01-01",
        "end_date": "",
    },
)


def _run_backfill(**context):
    params = context.get("params", {})
    start_date = params.get("start_date", "2026-01-01")
    end_date = params.get("end_date") or None
    return index_articles_by_date(start_date, end_date)


setup_task = PythonOperator(
    task_id="setup_opensearch_index",
    python_callable=setup_opensearch_index,
    dag=dag,
)

backfill_task = PythonOperator(
    task_id="backfill_index_articles",
    python_callable=_run_backfill,
    dag=dag,
)

setup_task >> backfill_task
