from enum import IntEnum, StrEnum
from typing import Self


class Agency(StrEnum):
    MPK = "mpk"
    MOBILIS = "mobilis"


class VehicleStatus(IntEnum):
    INCOMING_AT = 0
    STOPPED_AT = 1
    IN_TRANSIT_TO = 2

    @classmethod
    def from_int(cls, value: int | None) -> Self | None:
        if value is None:
            return None
        try:
            return cls(value)
        except ValueError:
            return None


class DetectionMethod(IntEnum):
    """Specify how a stop event was detected"""

    STOPPED_AT = 1  # Direct STOPPED_AT status from VehiclePositions
    SEQ_JUMP = 2  # Detected via stop_sequence jump, time from TripUpdates
    TIMEOUT = 3  # Using cached TripUpdates time (vehicle disappeared)
