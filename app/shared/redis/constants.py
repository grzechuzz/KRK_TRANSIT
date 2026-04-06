# Redis Pub/Sub channels
VEHICLE_POSITIONS_CHANNEL: str = "vehicle_positions"

# Redis TTLs for shared RT caches
REDIS_TRIP_UPDATES_TTL: int = 3 * 60 * 60
REDIS_LIVE_VEHICLE_TTL: int = 30
