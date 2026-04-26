from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator


from devto_ingestion.fetching import fetch_and_store_articles
from devto_ingestion.indexing import index_articles, setup_opensearch_index
from devto_ingestion.reporting import generate_daily_report
from devto_ingestion.setup import setup_environment

default_args = {
    "owner": "devto-ingestion",
    "depends_on_past": False,
    "start_date": datetime(2026, 3, 17),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=30),
}

dag = DAG(
    "devto_article_ingestion",
    default_args=default_args,
    description="Daily Dev.to article ingestion: fetch, chunk, and index to PostgreSQL and OpenSearch",
    schedule="0 7 * * 1-5",
    max_active_runs=1,
    tags=["devto", "articles", "ingestion"],
)

setup_task = PythonOperator(
    task_id="setup_environment",
    python_callable=setup_environment,
    dag=dag,
)

fetch_task = PythonOperator(
    task_id="fetch_and_store_articles",
    python_callable=fetch_and_store_articles,
    dag=dag,
)

setup_opensearch_task = PythonOperator(
    task_id="setup_opensearch_index",
    python_callable=setup_opensearch_index,
    dag=dag,
)

index_task = PythonOperator(
    task_id="index_articles",
    python_callable=index_articles,
    dag=dag,
)

report_task = PythonOperator(
    task_id="generate_daily_report",
    python_callable=generate_daily_report,
    dag=dag,
)

setup_task >> [fetch_task, setup_opensearch_task]
[fetch_task, setup_opensearch_task] >> index_task >> report_task
