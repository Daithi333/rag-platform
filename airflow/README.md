# Airflow

Apache Airflow 3.2 setup for data ingestion pipelines. Uses a custom Docker image with
separate containers for each Airflow component.

## Architecture

Airflow 3 requires four separate services (defined in `compose.yml` via `x-airflow-common` anchor):

- `airflow-init` -- runs `db migrate` on startup, then exits
- `airflow-webserver` -- serves the UI and REST API (`airflow api-server`)
- `airflow-scheduler` -- schedules and executes tasks via LocalExecutor
- `airflow-dag-processor` -- parses DAG files and serializes them to the metadata DB
- `airflow-postgres` -- dedicated metadata database (separate from the app DB)

## Critical Configuration (Airflow 3)

These env vars are required for inter-container communication. Without them, tasks will
fail with opaque errors like "Cannot assign requested address" or "Signature verification failed".

| Variable | Purpose |
|---|---|
| `AIRFLOW__CORE__EXECUTION_API_SERVER_URL` | Workers report task state to the API server via this URL |
| `AIRFLOW__CORE__INTERNAL_API_URL` | Scheduler communicates with the API server |
| `AIRFLOW__API_AUTH__JWT_SECRET` | Shared JWT signing key across all containers |
| `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN` | Airflow metadata DB connection (not the app DB) |

## Authentication

Airflow 3 uses the Simple Auth Manager by default. For local dev, `SIMPLE_AUTH_MANAGER_ALL_ADMINS=True`
disables login entirely. For other environments, users are configured via
`AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_USERS=username:role` and passwords are auto-generated
(check webserver logs).

## DAGs

DAG files live in `airflow/dags/` and are bind-mounted into the containers.
Application code in `src/` is also mounted at `/opt/airflow/src`, with `PYTHONPATH=/opt/airflow`
set in the Dockerfile so DAGs can import from `src/` directly.

DAG dependencies (separate from the app) are managed in `requirements-airflow.txt`.

## Commands

```bash
# Start all Airflow services
docker compose up -d airflow-postgres airflow-init airflow-webserver airflow-scheduler airflow-dag-processor

# View DAGs
docker compose exec airflow-scheduler airflow dags list

# Check for DAG import errors
docker compose exec airflow-scheduler airflow dags list-import-errors

# Test a task locally
docker compose exec airflow-scheduler airflow tasks test <dag_id> <task_id> <date>

# View auto-generated password (if not using all_admins)
docker compose logs airflow-webserver | grep -i password

# Reset Airflow (wipe metadata DB)
docker compose down
docker volume rm <project>_airflow_postgres_data
docker compose up -d
```

## Upgrading from Airflow 2.x

Key differences from Airflow 2:

- `airflow webserver` is replaced by `airflow api-server`
- DAG processor is a separate required component
- `airflow users create` is replaced by config-based user management
- `PythonOperator` import moved to `airflow.providers.standard.operators.python`
- Tasks communicate via the Execution API, not direct DB access
- `/health` endpoint moved to `/api/v2/monitor/health`
