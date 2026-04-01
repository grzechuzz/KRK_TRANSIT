#!/bin/bash
set -e

API_PASS=$(cat /run/secrets/db_password_api)
WRITER_PASS=$(cat /run/secrets/db_password_writer)
IMPORTER_PASS=$(cat /run/secrets/db_password_importer)
RT_POLLER_PASS=$(cat /run/secrets/db_password_rt_poller)
WEATHER_COLLECTOR_PASS=$(cat /run/secrets/db_password_weather_collector)

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE api_reader WITH LOGIN PASSWORD '$API_PASS';
    CREATE ROLE writer WITH LOGIN PASSWORD '$WRITER_PASS';
    CREATE ROLE importer WITH LOGIN PASSWORD '$IMPORTER_PASS';
    CREATE ROLE rt_poller WITH LOGIN PASSWORD '$RT_POLLER_PASS';
    CREATE ROLE weather_collector WITH LOGIN PASSWORD '$WEATHER_COLLECTOR_PASS';

    GRANT CONNECT ON DATABASE $POSTGRES_DB TO api_reader, writer, importer, rt_poller, weather_collector;
EOSQL
# All schema/table grants are handled by Alembic migrations (reset_db_permissions).
