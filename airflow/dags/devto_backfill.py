"""Manual DAG for backfilling article bodies and OpenSearch indexing.

Trigger from the Airflow UI with a config like:
  {"start_date": "2026-01-01", "end_date": "2026-04-26", "only_missing": true}

Steps:
  1. Setup environment and OpenSearch index
  2. Fetch article bodies from Dev.to API
  3. Index all articles with bodies into OpenSearch (chunk + embed)

Params:
  - start_date / end_date: optional date range filter on article created_at
  - only_missing: if true, only fetch bodies for articles where body_markdown is NULL.
    If false, re-fetch all bodies in range. Indexing always processes all articles
    with bodies (delete-before-reindex makes it idempotent).
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

from devto_ingestion.body_fetching import fetch_bodies_by_date
from devto_ingestion.indexing import index_articles_by_date, setup_opensearch_index
from devto_ingestion.setup import setup_environment

default_args = {
    "owner": "devto-ingestion",
    "depends_on_past": False,
    "start_date": datetime(2026, 3, 17),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "devto_backfill",
    default_args=default_args,
    description="Manual backfill: fetch bodies then index into OpenSearch",
    schedule=None,
    max_active_runs=1,
    tags=["devto", "opensearch", "backfill", "manual"],
    params={
        "start_date": "",
        "end_date": "",
        "only_missing": True,
    },
)


def _run_body_backfill(**context):
    params = context.get("params", {})
    return fetch_bodies_by_date(
        start_date=params.get("start_date") or None,
        end_date=params.get("end_date") or None,
        only_missing=params.get("only_missing", True),
    )


def _run_index_backfill(**context):
    params = context.get("params", {})
    return index_articles_by_date(
        start_date=params.get("start_date") or None,
        end_date=params.get("end_date") or None,
    )


setup_task = PythonOperator(
    task_id="setup_environment",
    python_callable=setup_environment,
    dag=dag,
)

setup_opensearch_task = PythonOperator(
    task_id="setup_opensearch_index",
    python_callable=setup_opensearch_index,
    dag=dag,
)

backfill_bodies_task = PythonOperator(
    task_id="backfill_article_bodies",
    python_callable=_run_body_backfill,
    dag=dag,
)

backfill_index_task = PythonOperator(
    task_id="backfill_index_articles",
    python_callable=_run_index_backfill,
    dag=dag,
)

setup_task >> [backfill_bodies_task, setup_opensearch_task]
[backfill_bodies_task, setup_opensearch_task] >> backfill_index_task
