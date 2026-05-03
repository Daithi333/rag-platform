"""Manual DAG for backfilling article bodies from the Dev.to API.

Trigger from the Airflow UI with a config like:
  {"start_date": "2026-01-01", "end_date": "2026-04-26", "only_missing": true}

- only_missing=true (default): only fetches for articles with body_markdown = NULL
- only_missing=false: re-fetches bodies for all articles in the range
- Omit date params to process all articles

Safe to re-run: only_missing=true skips articles that already have bodies.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

from devto_ingestion.body_fetching import fetch_bodies_by_date
from devto_ingestion.setup import setup_environment

default_args = {
    "owner": "devto-ingestion",
    "depends_on_past": False,
    "start_date": datetime(2026, 3, 17),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "devto_backfill_bodies",
    default_args=default_args,
    description="Manual backfill: fetch full article bodies from Dev.to API",
    schedule=None,
    max_active_runs=1,
    tags=["devto", "backfill", "manual"],
    params={
        "start_date": "",
        "end_date": "",
        "only_missing": True,
    },
)


def _run_backfill(**context):
    params = context.get("params", {})
    return fetch_bodies_by_date(
        start_date=params.get("start_date") or None,
        end_date=params.get("end_date") or None,
        only_missing=params.get("only_missing", True),
    )


setup_task = PythonOperator(
    task_id="setup_environment",
    python_callable=setup_environment,
    dag=dag,
)

backfill_task = PythonOperator(
    task_id="backfill_article_bodies",
    python_callable=_run_backfill,
    dag=dag,
)

setup_task >> backfill_task
