from datetime import timedelta

# Stop Writer (batch persistence)
WRITER_BATCH_SIZE: int = 100
WRITER_FLUSH_INTERVAL: timedelta = timedelta(seconds=10)
SUBSCRIBER_TIMEOUT: float = 1.0
STOP_WRITER_FLUSH_RETRY_BACKOFF_SECONDS: list[int] = [1, 5, 15, 30]

# Detector rules
DELAY_DROP_THRESHOLD: int = 180
MIN_EARLY_DELAY_SECONDS: int = -180

# In-memory cache limits
CACHE_MAX_TRIPS: int = 5000
CACHE_MAX_STOPS: int = 5000
CACHE_MAX_STOP_TIMES: int = 2000
CACHE_MAX_SEQUENCES: int = 5000

# Redis TTLs (stop_writer local state)
REDIS_SAVED_SEQS_TTL: int = 24 * 60 * 60
REDIS_VEHICLE_STATE_TTL: int = 3 * 60 * 60
