from dataclasses import dataclass

from app.shared.models.enums import Agency


@dataclass(frozen=True)
class FeedConfig:
    """Configuration for a single GTFS feed (static + realtime)"""

    agency: Agency
    static_url: str
    static_filename: str
    vehicle_positions_url: str
    trip_updates_url: str
    id_prefix: str = ""

    def prefix_id(self, raw_id: str) -> str:
        """Prefix an ID if this feed requires it. Used to avoid PK collisions between feeds."""
        return f"{self.id_prefix}:{raw_id}" if self.id_prefix else raw_id


FEED_CONFIGS: dict[Agency, FeedConfig] = {
    Agency.MPK: FeedConfig(
        agency=Agency.MPK,
        static_url="https://gtfs.ztp.krakow.pl/GTFS_KRK_A.zip",
        static_filename="GTFS_KRK_A.zip",
        vehicle_positions_url="https://gtfs.ztp.krakow.pl/VehiclePositions_A.pb",
        trip_updates_url="https://gtfs.ztp.krakow.pl/TripUpdates_A.pb",
    ),
    Agency.MOBILIS: FeedConfig(
        agency=Agency.MOBILIS,
        static_url="https://gtfs.ztp.krakow.pl/GTFS_KRK_M.zip",
        static_filename="GTFS_KRK_M.zip",
        vehicle_positions_url="https://gtfs.ztp.krakow.pl/VehiclePositions_M.pb",
        trip_updates_url="https://gtfs.ztp.krakow.pl/TripUpdates_M.pb",
    ),
    Agency.MPK_TRAM: FeedConfig(
        agency=Agency.MPK_TRAM,
        static_url="https://gtfs.ztp.krakow.pl/GTFS_KRK_T.zip",
        static_filename="GTFS_KRK_T.zip",
        vehicle_positions_url="https://gtfs.ztp.krakow.pl/VehiclePositions_T.pb",
        trip_updates_url="https://gtfs.ztp.krakow.pl/TripUpdates_T.pb",
        id_prefix="tram",
    ),
}


def get_feed_config(agency: Agency) -> FeedConfig:
    return FEED_CONFIGS[agency]


def get_all_feed_configs() -> list[FeedConfig]:
    return list(FEED_CONFIGS.values())
