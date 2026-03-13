# KRKTransit - live vehicle tracking and delay statistics for public transport in Kraków

REST API providing real-time bus delay statistics (MPK, Mobilis) in Kraków. It is based on data provided by ZTP Kraków, published according to the GTFS specification (Static & Realtime).

The API enables identification of route segments generating the highest delays and monitoring of long-term delay trends for each line.

It also exposes endpoints with live vehicle positions and route geometry.

The code can be run locally, allowing you to independently build your own historical database of delays.

**Website (Frontend):** https://krktransit.pl/

**API:** https://api.krktransit.pl/docs

**GTFS**: https://gtfs.org/documentation/overview/

**ZTP Data**: https://gtfs.ztp.krakow.pl/


## API Endpoints

To avoid skewing results with unrealistic delays, statistics exclude the first and last stop of each trip.

| Endpoint | Description |
|---|---|
| `GET /v1/lines/{line}/stats/max-delay` | Top 10 delay increments between consecutive stops |
| `GET /v1/lines/{line}/stats/route-delay` | Top 10 delays generated across the entire route |
| `GET /v1/lines/{line}/stats/punctuality` | Punctuality statistics by delay thresholds |
| `GET /v1/lines/{line}/stats/trend` | Daily average delay trend |
| `GET /v1/vehicles/positions` | Live GPS positions of all active vehicles |
| `GET /v1/shapes/{shape_id}` | Route geometry (ordered GPS points) |
| `GET /v1/trips/{trip_id}/stops` | Stops on a given trip |
| `GET /health` | Health check |

Documentation: [api.krktransit.pl/docs](https://api.krktransit.pl/docs)

## Architecture

The system consists of four services.

| Service | Role |
|---|---|
| **Importer** | Downloads and loads GTFS Static data (routes, stops, schedules, route shapes) for both operators. Detects file changes via SHA-256 hashing. |
| **RT Poller** | Fetches `VehiclePositions.pb` and `TripUpdates.pb` feeds every 5 seconds. Publishes parsed vehicle positions to Redis Pub/Sub and caches trip update predictions. |
| **Stop Writer** | Listens for vehicle positions from Redis Pub/Sub. Detects stop events using three methods (see below). Writes events to the database. |
| **API** | Serves delay statistics, punctuality data, daily trends, live vehicle positions and route geometry. Caches statistics responses in Redis. |

## Stop Event Detection

The core logic (in `stop_writer/detector.py`) analyzes data from VehiclePositions.pb and TripUpdates.pb to determine when a vehicle has visited a stop.

| Method | Trigger | Time Source |
|---|---|---|
| `STOPPED_AT` | Vehicle reports `STOPPED_AT` status | GPS timestamp |
| `SEQ_JUMP` | Stop sequence jump (skipped stops) | TripUpdates prediction cache |
| `TIMEOUT` | Vehicle started a new trip (completing the previous one) | TripUpdates prediction cache for the previous trip |

Due to the fact that estimation methods for skipped stops (`SEQ_JUMP`, `TIMEOUT`) do not yet yield fully satisfactory results, the API currently only exposes events based on `STOPPED_AT` to guarantee data accuracy.

## Tech Stack
- Python 3.13
- FastAPI + Uvicorn
- PostgreSQL 17 (primary database)
- Redis 7 (cache)
- msgspec (serialization), protobuf + gtfs-realtime-bindings (GTFS parsing)
- SQLAlchemy 2.0
- Alembic
- Caddy (web server and reverse proxy with automatic HTTPS)
- GitHub Actions (CI)
- Docker

## Running Locally

1. Clone the repository:
```bash
git clone https://github.com/grzechuzz/KRK_TRANSIT.git
```

2. Create the required files:
   
   - `secrets/db_password` (DB admin)
   - `secrets/db_password_api` (API read-only)
   - `secrets/db_password_writer` (RT data writer)
   - `secrets/db_password_importer` (GTFS data writer)
   - `secrets/redis_password`
   - `redis/users.acl`
   
   Example `redis/users.acl`:
   ```text
   user mpk_redis on >CHANGE_THAT_PASSWORD ~* &* +@read +@write +@string +@hash +@set +@list +@pubsub +@keyspace +@connection -@dangerous
   user default off
   ```

   Create a `docker/.env` file and fill in the variables:
   ```env
   POSTGRES_DB=
   POSTGRES_USER=
   IMPORTER_USER=
   WRITER_USER=
   API_READER_USER=
   REDIS_USER=
   ```
   
3. Start the containers:
```bash
cd docker
docker compose up -d --build
```

4. Open the API documentation:
```text
http://localhost:8000/docs
```

## Tests & Linting

```bash
pip install -e ".[dev]"

pytest                  # unit tests
ruff check .            # linting
ruff format --check .   # formatting
mypy .                  # type checking
```

CI runs everything on every push to main.
