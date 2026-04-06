from datetime import date

# API statistics filters
MIN_DELAY_SECONDS: int = -90
ESTIMATED_VALID_FROM: date = date(2026, 3, 19)
MAX_DATE_RANGE_DAYS: int = 365

# API cache TTL
DEFAULT_TTL: int = 90
LONG_TTL: int = 600
LONG_TTL_THRESHOLD_DAYS: int = 7
VEHICLES_CACHE_TTL: int = 3

# API rate limits (per IP, per minute)
RATE_LIMIT_DEFAULT: str = "80/minute"
RATE_LIMIT_STATS: str = "40/minute"

# API Redis keys
REDIS_KEY_VEHICLES_CACHE: str = "cache:vehicles:positions"
