#!/bin/bash
set -e

COMMAND=${1:-scheduler}

if [ "$COMMAND" = "init" ]; then
    echo "Running Airflow db migration..."
    airflow db migrate

    echo "Creating admin user..."
    airflow users create \
        --username admin \
        --firstname Admin \
        --lastname User \
        --role Admin \
        --email admin@example.com \
        --password admin || echo "Admin user already exists"

    echo "Init complete."
    exit 0
fi

exec airflow "$COMMAND"
