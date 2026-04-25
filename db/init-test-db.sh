#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT 'CREATE DATABASE rag_platform_test_db'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'rag_platform_test_db')\gexec
    GRANT ALL PRIVILEGES ON DATABASE rag_platform_test_db TO $POSTGRES_USER;
EOSQL
