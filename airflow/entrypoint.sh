#!/bin/bash
set -e

COMMAND=${1:-scheduler}

if [ "$COMMAND" = "init" ]; then
    echo "Running Airflow db migration..."
    airflow db migrate

    echo "Init complete."
    exit 0
fi

exec airflow "$COMMAND"
