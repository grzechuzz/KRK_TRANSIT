from pydantic import BaseModel, ConfigDict


class MaxDelayBetweenStops(BaseModel):
    trip_id: str
    line_number: str
    vehicle_number: str
    from_stop: str
    to_stop: str
    from_sequence: int
    to_sequence: int
    from_planned_time: str
    from_event_time: str
    to_planned_time: str
    to_event_time: str
    delay_generated_seconds: int
    headsign: str
    service_date: str
    is_estimated: bool


class RouteDelay(BaseModel):
    trip_id: str
    line_number: str
    vehicle_number: str
    first_stop: str
    last_stop: str
    first_planned_time: str
    first_event_time: str
    last_planned_time: str
    last_event_time: str
    start_delay_seconds: int
    end_delay_seconds: int
    delay_generated_seconds: int
    headsign: str
    service_date: str
    is_estimated: bool


class TrendDay(BaseModel):
    date: str
    avg_delay_seconds: float
    trips_count: int


class LiveVehicle(BaseModel):
    trip_id: str
    license_plate: str
    line_number: str
    headsign: str
    shape_id: str | None
    latitude: float
    longitude: float
    bearing: float | None
    timestamp: str


class MaxDelayBetweenStopsResponse(BaseModel):
    line_number: str
    start_date: str
    end_date: str
    max_delay: list[MaxDelayBetweenStops]
    trips_analyzed: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "line_number": "194",
                "start_date": "2026-02-03",
                "end_date": "2026-02-16",
                "max_delay": [
                    {
                        "trip_id": "block_675_trip_13_service_2",
                        "line_number": "194",
                        "vehicle_number": "DR521",
                        "from_stop": "Czarnowiejska",
                        "to_stop": "AGH / UR",
                        "from_sequence": 10,
                        "to_sequence": 11,
                        "from_planned_time": "2026-02-14 16:49:00",
                        "from_event_time": "2026-02-14 16:50:50",
                        "to_planned_time": "2026-02-14 16:51:00",
                        "to_event_time": "2026-02-14 16:56:43",
                        "delay_generated_seconds": 233,
                        "headsign": "Os. Pod Fortem",
                        "service_date": "2026-02-14",
                        "is_estimated": False,
                    },
                    {
                        "trip_id": "block_675_trip_13_service_2",
                        "line_number": "194",
                        "vehicle_number": "DR521",
                        "from_stop": "AGH / UR",
                        "to_stop": "Muzeum Narodowe",
                        "from_sequence": 11,
                        "to_sequence": 12,
                        "from_planned_time": "2026-02-14 16:51:00",
                        "from_event_time": "2026-02-14 16:56:43",
                        "to_planned_time": "2026-02-14 16:53:00",
                        "to_event_time": "2026-02-14 17:01:16",
                        "delay_generated_seconds": 153,
                        "headsign": "Os. Pod Fortem",
                        "service_date": "2026-02-14",
                        "is_estimated": False,
                    },
                ],
                "trips_analyzed": 88,
            }
        }
    )


class RouteDelayResponse(BaseModel):
    line_number: str
    start_date: str
    end_date: str
    max_route_delay: list[RouteDelay]
    trips_analyzed: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "line_number": "304",
                "start_date": "2026-02-01",
                "end_date": "2026-02-16",
                "max_route_delay": [
                    {
                        "trip_id": "block_781_trip_14_service_2",
                        "line_number": "304",
                        "vehicle_number": "DE638",
                        "first_stop": "Politechnika",
                        "last_stop": "Wieliczka Asnyka",
                        "first_planned_time": "2026-02-14 16:49:00",
                        "first_event_time": "2026-02-14 16:48:31",
                        "last_planned_time": "2026-02-14 17:27:00",
                        "last_event_time": "2026-02-14 17:44:56",
                        "start_delay_seconds": -29,
                        "end_delay_seconds": 1076,
                        "delay_generated_seconds": 1105,
                        "headsign": "Wieliczka Miasto",
                        "service_date": "2026-02-14",
                        "is_estimated": False,
                    },
                    {
                        "trip_id": "block_780_trip_23_service_2",
                        "line_number": "304",
                        "vehicle_number": "DE637",
                        "first_stop": "Wieliczka Asnyka",
                        "last_stop": "Politechnika",
                        "first_planned_time": "2026-02-14 17:30:00",
                        "first_event_time": "2026-02-14 17:31:58",
                        "last_planned_time": "2026-02-14 18:09:00",
                        "last_event_time": "2026-02-14 18:29:11",
                        "start_delay_seconds": 118,
                        "end_delay_seconds": 1211,
                        "delay_generated_seconds": 1093,
                        "headsign": "Dworzec Główny Zachód",
                        "service_date": "2026-02-14",
                        "is_estimated": False,
                    },
                ],
                "trips_analyzed": 36,
            }
        }
    )


class PunctualityResponse(BaseModel):
    line_number: str
    start_date: str
    end_date: str
    total_stops: int
    on_time_count: int
    on_time_percent: float
    slightly_delayed_count: int
    slightly_delayed_percent: float
    delayed_count: int
    delayed_percent: float

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "line_number": "169",
                "start_date": "2026-02-10",
                "end_date": "2026-02-14",
                "total_stops": 280,
                "on_time_count": 63,
                "on_time_percent": 22.5,
                "slightly_delayed_count": 69,
                "slightly_delayed_percent": 24.6,
                "delayed_count": 148,
                "delayed_percent": 52.9,
            }
        }
    )


class TrendResponse(BaseModel):
    line_number: str
    start_date: str
    end_date: str
    days: list[TrendDay]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "line_number": "304",
                "start_date": "2026-02-14",
                "end_date": "2026-02-15",
                "days": [
                    {"date": "2026-02-14", "avg_delay_seconds": 415.5, "trips_count": 23},
                    {"date": "2026-02-15", "avg_delay_seconds": 218.6, "trips_count": 6},
                ],
            }
        }
    )


class LiveVehicleResponse(BaseModel):
    count: int
    vehicles: list[LiveVehicle]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "count": 5,
                "vehicles": [
                    {
                        "trip_id": "block_675_trip_13_service_2",
                        "license_plate": "DN007",
                        "line_number": "179",
                        "headsign": "Dworzec Główny Zachód",
                        "shape_id": "shape_1234",
                        "latitude": 50.0322380065918,
                        "longitude": 19.94826316833496,
                        "bearing": 90,
                        "timestamp": "2026-02-15T17:07:00+00:00",
                    },
                    {
                        "trip_id": "block_622_trip_13_service_3",
                        "license_plate": "DN011",
                        "line_number": "164",
                        "headsign": "Piaski Nowe",
                        "shape_id": "shape_9024",
                        "latitude": 50.04066848754883,
                        "longitude": 19.874757766723633,
                        "bearing": 90,
                        "timestamp": "2026-02-15T17:07:02+00:00",
                    },
                    {
                        "trip_id": "block_635_trip_11_service_2",
                        "license_plate": "DN013",
                        "line_number": "503",
                        "headsign": "Nowy Bieżanów Południe",
                        "shape_id": "shape_8882",
                        "latitude": 50.01777648925781,
                        "longitude": 19.990068435668945,
                        "bearing": 135,
                        "timestamp": "2026-02-15T17:06:56+00:00",
                    },
                    {
                        "trip_id": "block_230_trip_4_service_3",
                        "license_plate": "DN017",
                        "line_number": "179",
                        "headsign": "Os. Kurdwanów",
                        "shape_id": "shape_7234",
                        "latitude": 50.00454330444336,
                        "longitude": 19.959930419921875,
                        "bearing": 90,
                        "timestamp": "2026-02-15T17:06:57+00:00",
                    },
                    {
                        "trip_id": "block_781_trip_14_service_2",
                        "license_plate": "DN021",
                        "line_number": "503",
                        "headsign": "Górka Narodowa P+R",
                        "shape_id": "shape_6254",
                        "latitude": 50.05740737915039,
                        "longitude": 19.926631927490234,
                        "bearing": 0,
                        "timestamp": "2026-02-15T17:06:53+00:00",
                    },
                ],
            }
        }
    )


class ShapePoint(BaseModel):
    latitude: float
    longitude: float
    sequence: int


class ShapeResponse(BaseModel):
    shape_id: str
    points: list[ShapePoint]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "shape_id": "shape_8882",
                "points": [
                    {"latitude": 50.061433, "longitude": 19.936586, "sequence": 1},
                    {"latitude": 50.061571, "longitude": 19.937014, "sequence": 2},
                    {"latitude": 50.061984, "longitude": 19.938119, "sequence": 3},
                ],
            }
        }
    )


class TripStop(BaseModel):
    stop_id: str
    stop_name: str
    stop_desc: str | None
    latitude: float | None
    longitude: float | None
    sequence: int


class TripStopsResponse(BaseModel):
    trip_id: str
    stops: list[TripStop]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trip_id": "block_675_trip_13_service_2",
                "stops": [
                    {
                        "stop_id": "stop_55_7904",
                        "stop_name": "Plac Inwalidów",
                        "stop_desc": "01",
                        "latitude": 50.075130462646484,
                        "longitude": 19.906492233276367,
                        "sequence": 1,
                    },
                    {
                        "stop_id": "stop_1626_311102",
                        "stop_name": "AGH / UR",
                        "stop_desc": "02",
                        "latitude": 50.09483337402344,
                        "longitude": 19.96756935119629,
                        "sequence": 2,
                    },
                    {
                        "stop_id": "stop_1654_314104",
                        "stop_name": "Muzeum Narodowe",
                        "stop_desc": "01",
                        "latitude": 50.06626892089844,
                        "longitude": 19.99996566772461,
                        "sequence": 3,
                    },
                ],
            }
        }
    )
