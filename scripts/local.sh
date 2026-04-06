#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_CMD=(docker compose --env-file "$ROOT_DIR/docker/.env" -f "$ROOT_DIR/docker/docker-compose.yml")

usage() {
  cat <<'EOF'
Usage:
  ./scripts/local.sh bootstrap   Create missing local config, secrets, ACL, and data dir
  ./scripts/local.sh up          Start local stack
  ./scripts/local.sh down        Stop local stack
  ./scripts/local.sh restart     Rebuild and restart local stack
  ./scripts/local.sh logs        Follow compose logs
  ./scripts/local.sh ps          Show compose status
EOF
}

create_file_if_missing() {
  local path="$1"
  local content="$2"

  if [[ -f "$path" ]]; then
    return
  fi

  mkdir -p "$(dirname "$path")"
  printf '%s\n' "$content" >"$path"

  case "$path" in
    "$ROOT_DIR"/secrets/*|"$ROOT_DIR"/redis/users.acl)
      chmod 600 "$path"
      ;;
  esac

  printf 'Created %s\n' "${path#$ROOT_DIR/}"
}

bootstrap() {
  local redis_password

  mkdir -p "$ROOT_DIR/secrets" "$ROOT_DIR/redis" "$ROOT_DIR/data" "$ROOT_DIR/scripts"

  create_file_if_missing "$ROOT_DIR/docker/.env" "POSTGRES_DB=mpk_db
POSTGRES_USER=mpk
IMPORTER_USER=mpk_importer
RT_POLLER_USER=mpk_rt_poller
WRITER_USER=mpk_writer
API_READER_USER=mpk_api
WEATHER_COLLECTOR_USER=mpk_weather
REDIS_USER=mpk_redis
SENTRY_DSN=
SENTRY_ENVIRONMENT=local"

  create_file_if_missing "$ROOT_DIR/secrets/db_password" "change-me-db-admin-password"
  create_file_if_missing "$ROOT_DIR/secrets/db_password_api" "change-me-db-api-password"
  create_file_if_missing "$ROOT_DIR/secrets/db_password_writer" "change-me-db-writer-password"
  create_file_if_missing "$ROOT_DIR/secrets/db_password_importer" "change-me-db-importer-password"
  create_file_if_missing "$ROOT_DIR/secrets/db_password_rt_poller" "change-me-db-rt-poller-password"
  create_file_if_missing "$ROOT_DIR/secrets/db_password_weather_collector" "change-me-db-weather-password"
  create_file_if_missing "$ROOT_DIR/secrets/redis_password" "change-me-redis-password"

  if [[ ! -f "$ROOT_DIR/redis/users.acl" ]]; then
    redis_password="$(tr -d '\r\n' < "$ROOT_DIR/secrets/redis_password")"
    cat >"$ROOT_DIR/redis/users.acl" <<EOF
user mpk_redis on >${redis_password} ~* &* +@read +@write +@string +@hash +@set +@list +@pubsub +@keyspace +@connection -@dangerous
user default off
EOF
    chmod 600 "$ROOT_DIR/redis/users.acl"
    printf 'Created redis/users.acl\n'
  fi

  cat <<'EOF'

Bootstrap complete.

Created only missing local files. Existing config was left untouched.
Next steps:
  ./scripts/local.sh up
EOF
}

require_env() {
  if [[ ! -f "$ROOT_DIR/docker/.env" ]]; then
    printf 'Missing docker/.env. Run ./scripts/local.sh bootstrap first.\n' >&2
    exit 1
  fi
}

cmd="${1:-help}"

case "$cmd" in
  bootstrap)
    bootstrap
    ;;
  up)
    require_env
    "${COMPOSE_CMD[@]}" up -d --build
    ;;
  down)
    require_env
    "${COMPOSE_CMD[@]}" down
    ;;
  restart)
    require_env
    "${COMPOSE_CMD[@]}" down
    "${COMPOSE_CMD[@]}" up -d --build
    ;;
  logs)
    require_env
    "${COMPOSE_CMD[@]}" logs -f --tail=100
    ;;
  ps)
    require_env
    "${COMPOSE_CMD[@]}" ps
    ;;
  help|--help|-h)
    usage
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac
