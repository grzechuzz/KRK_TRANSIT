# KRKTransit - live vehicle tracking and delay statistics for public transport in Kraków

Platform providing real-time public transport delay statistics (MPK, Mobilis) in Kraków. It is based on data provided by ZTP Kraków, published according to the GTFS specification (Static & Realtime).

Enables identification of route segments generating the highest delays, monitoring of long-term delay trends for each line and live vehicle tracking.

To avoid skewing results with unrealistic delays, statistics exclude the first and last stop of each trip.

**Website:** https://krktransit.pl/

**GTFS**: https://gtfs.org/documentation/overview/

**ZTP Data**: https://gtfs.ztp.krakow.pl/

<img width="1912" height="944" alt="image" src="https://github.com/user-attachments/assets/12410f06-6d1e-472e-b6c8-5492d4441027" />

<img width="1912" height="468" alt="image" src="https://github.com/user-attachments/assets/1bb9e101-0788-4f35-a6e4-70e3a4112ff0" />

<img width="1912" height="733" alt="image" src="https://github.com/user-attachments/assets/b422d0ba-30c9-4ed1-9ae9-a8e6d5e20e5e" />

## Architecture

The system consists of five services, each handling a specific stage of the data flow. The services are decoupled, they don't import each other directly and maintain a strict separation of concerns. The main flow of fetching, processing and storing data has the shape of an `event-driven data pipeline`.

The project deliberately relies on a shared database architecture, as a full microservices approach would introduce unnecessary overhead at this scale. To keep things organized, the database is divided into three separate schemas: `gtfs_static`, `events` and `weather`.

<p align="center">
<img width="569" height="927" alt="image" src="https://github.com/user-attachments/assets/bbd842d9-e373-4322-8252-03a249e0a245" />
</p>

| Service | Role |
|---|---|
| **Importer** | Downloads and loads GTFS Static data (routes, stops, schedules, route shapes) for both operators. Detects file changes via SHA-256 hashing. |
| **RT Poller** | Fetches `VehiclePositions.pb` and `TripUpdates.pb` feeds. Publishes parsed vehicle positions to Redis Pub/Sub and caches trip update predictions. |
| **Stop Writer** | Listens for vehicle positions from Redis Pub/Sub. Detects stop events using three methods (see below). Writes events to the database. |
| **API** | Serves delay statistics, punctuality data, daily trends, live vehicle positions and route geometry. Caches statistics responses in Redis. |
| **Weather Collector** | Fetches historical weather data from Open-Meteo and stores it in the database. |

## Stop Event Detection

| Method | Trigger | Time Source |
|---|---|---|
| `STOPPED_AT` | Vehicle reports `STOPPED_AT` status | GPS timestamp |
| `SEQ_JUMP` | Stop sequence jump (skipped stops) | TripUpdates prediction cache |
| `TIMEOUT` | Vehicle started a new trip (completing the previous one) | TripUpdates prediction cache for the previous trip |

## Tech Stack
- Python 3.13
- FastAPI + Uvicorn
- PostgreSQL 17 (primary database)
- Redis 7 (cache + Pub/Sub)
- msgspec (serialization), protobuf + gtfs-realtime-bindings (GTFS parsing)
- SQLAlchemy 2.0
- Alembic
- GitHub Actions (CI)
- Docker
