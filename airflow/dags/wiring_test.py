from datetime import datetime, timedelta

import httpx
import psycopg2
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator


def hello_world():
    print("Hello from Airflow!")
    return "success"


def check_services():
    """Check if other services are accessible."""
    try:
        # Check API health
        response = httpx.get("http://rag-platform-api:8000/api/v1/health", timeout=5)
        print(f"API Health: {response.status_code}")

        # Check database connection
        conn = psycopg2.connect(
            host="postgres",
            port=5432,
            database="rag_platform_db",
            user="rag_platform_user",
            password="rag_platform_password",
        )
        print("Database: Connected successfully")
        conn.close()

        return "Services are accessible"
    except Exception as e:
        print(f"Service check failed: {e}")
        raise


default_args = {
    "owner": "rag",
    "depends_on_past": False,
    "start_date": datetime(2026, 3, 15),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "wiring_test",
    default_args=default_args,
    description="Check the wiring of API and DB from Airflow",
    schedule=None,
    tags=["wiring_test"],
)

hello_task = PythonOperator(
    task_id="hello_world",
    python_callable=hello_world,
    dag=dag,
)

service_check_task = PythonOperator(
    task_id="check_services",
    python_callable=check_services,
    dag=dag,
)

# Set task dependencies
hello_task >> service_check_task
