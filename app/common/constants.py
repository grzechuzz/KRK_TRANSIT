from datetime import date, timedelta

# Redis TTLs
REDIS_SAVED_SEQS_TTL: int = 24 * 60 * 60  # 24h - how long we remember which stop_sequences were already saved
REDIS_TRIP_UPDATES_TTL: int = 3 * 60 * 60  # 3h - cached TripUpdate predictions
REDIS_VEHICLE_STATE_TTL: int = 3 * 60 * 60  # 3h - last known vehicle state

# Redis keys
REDIS_KEY_GTFS_READY: str = "gtfs:ready"
REDIS_KEY_VEHICLES_CACHE: str = "cache:vehicles:positions"

# Redis Pub/Sub channels
VEHICLE_POSITIONS_CHANNEL: str = "vehicle_positions"

# In-memory cache limits (detector + publisher)
CACHE_MAX_TRIPS: int = 5000
CACHE_MAX_STOPS: int = 5000
CACHE_MAX_STOP_TIMES: int = 2000
CACHE_MAX_SEQUENCES: int = 5000
CACHE_MAX_STOP_ID_TO_SEQ: int = 5000

# GTFS readiness
GTFS_READINESS_TIMEOUT: int = 180  # seconds to wait for GTFS static data before giving up
GTFS_READINESS_POLL_INTERVAL: int = 5  # seconds between readiness checks

# Database connection pool
DB_POOL_SIZE: int = 5
DB_MAX_OVERFLOW: int = 10

# RT Poller
POLL_INTERVAL_SECONDS: int = 5
CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
CIRCUIT_BREAKER_COOLDOWN_SECONDS: int = 60

# Stop Writer (batch persistence)
WRITER_BATCH_SIZE: int = 100
WRITER_FLUSH_INTERVAL: timedelta = timedelta(seconds=10)
SUBSCRIBER_TIMEOUT: float = 1.0

# Importer
IMPORT_CYCLE_SLEEP: int = 3600  # 1 hour between GTFS static imports

# Protobuf parsing
PB_MIN_PAYLOAD_BYTES: int = 10  # minimum bytes to consider a .pb feed valid

# Detector
DELAY_DROP_THRESHOLD: int = 180  # if estimated delay is this much higher than the next STOPPED_AT delay then discard it
MIN_EARLY_DELAY_SECONDS: int = -180  # cross-batch: reject events earlier than this (except first stop)

# Timezone
TIMEZONE: str = "Europe/Warsaw"

# API statistics filters
MIN_DELAY_SECONDS: int = -90  # stops with delay below this are treated as garbage data
ESTIMATED_VALID_FROM: date = date(2026, 3, 19)  # estimated events before this date lack cross-batch validation

# API cache TTL
DEFAULT_TTL: int = 90
LONG_TTL: int = 600
LONG_TTL_THRESHOLD_DAYS: int = 7
VEHICLES_CACHE_TTL: int = 3  # seconds - live vehicle positions cache

# API rate limits (per IP, per minute)
RATE_LIMIT_DEFAULT: str = "80/minute"
RATE_LIMIT_STATS: str = "40/minute"

# API dates filter
MAX_DATE_RANGE_DAYS: int = 365

# User agent
USER_AGENT: str = "KRKTransit/1.0"

# Weather Collector
WEATHER_COLLECT_INTERVAL: int = 3600  # 1 hour between fetches
WEATHER_BACKFILL_DAYS: int = 21  # max days to backfill on first run (Open-Meteo limit)
WEATHER_FETCH_TIMEOUT_SECONDS: int = 30
WEATHER_FETCH_MAX_RETRIES: int = 3
WEATHER_FETCH_RETRY_BACKOFF_SECONDS: list[int] = [5, 30, 120]
