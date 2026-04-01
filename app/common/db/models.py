from datetime import date, datetime

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    Date,
    Double,
    ForeignKey,
    Identity,
    Index,
    Integer,
    SmallInteger,
    Text,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class GtfsMeta(Base):
    __tablename__ = "gtfs_meta"
    __table_args__ = {"schema": "gtfs_static"}

    agency: Mapped[str] = mapped_column(Text, primary_key=True)
    current_hash: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False)


class CurrentRoute(Base):
    __tablename__ = "current_routes"

    route_id: Mapped[str] = mapped_column(Text, primary_key=True)
    agency_id: Mapped[str] = mapped_column(Text, nullable=False)
    route_short_name: Mapped[str] = mapped_column(Text, nullable=False)

    trips: Mapped[list["CurrentTrip"]] = relationship(back_populates="route")

    __table_args__ = (Index("idx_current_routes_agency", "agency_id"), {"schema": "gtfs_static"})


class CurrentStop(Base):
    __tablename__ = "current_stops"

    stop_id: Mapped[str] = mapped_column(Text, primary_key=True)
    agency_id: Mapped[str] = mapped_column(Text, nullable=False)
    stop_name: Mapped[str] = mapped_column(Text, nullable=False)
    stop_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    stop_desc: Mapped[str | None] = mapped_column(Text, nullable=True)
    stop_lat: Mapped[float | None] = mapped_column(Double, nullable=True)
    stop_lon: Mapped[float | None] = mapped_column(Double, nullable=True)

    stop_times: Mapped[list["CurrentStopTime"]] = relationship(back_populates="stop")

    __table_args__ = (Index("idx_current_stops_agency", "agency_id"), {"schema": "gtfs_static"})


class CurrentTrip(Base):
    __tablename__ = "current_trips"

    trip_id: Mapped[str] = mapped_column(Text, primary_key=True)
    route_id: Mapped[str] = mapped_column(Text, ForeignKey("gtfs_static.current_routes.route_id"), nullable=False)
    agency_id: Mapped[str] = mapped_column(Text, nullable=False)
    service_id: Mapped[str] = mapped_column(Text, nullable=False)
    direction_id: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    headsign: Mapped[str | None] = mapped_column(Text, nullable=True)
    shape_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    route: Mapped["CurrentRoute"] = relationship(back_populates="trips")
    stop_times: Mapped[list["CurrentStopTime"]] = relationship(back_populates="trip")

    __table_args__ = (
        Index("idx_current_trips_route", "route_id"),
        Index("idx_current_trips_shape", "shape_id"),
        Index("idx_current_trips_agency", "agency_id"),
        {"schema": "gtfs_static"},
    )


class CurrentStopTime(Base):
    __tablename__ = "current_stop_times"

    trip_id: Mapped[str] = mapped_column(Text, ForeignKey("gtfs_static.current_trips.trip_id"), primary_key=True)
    stop_sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    stop_id: Mapped[str] = mapped_column(Text, ForeignKey("gtfs_static.current_stops.stop_id"), nullable=False)
    agency_id: Mapped[str] = mapped_column(Text, nullable=False)
    arrival_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    departure_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    trip: Mapped["CurrentTrip"] = relationship(back_populates="stop_times")
    stop: Mapped["CurrentStop"] = relationship(back_populates="stop_times")

    __table_args__ = (
        Index("idx_current_stop_times_stop", "stop_id"),
        Index("idx_current_stop_times_agency", "agency_id"),
        {"schema": "gtfs_static"},
    )


class CurrentShape(Base):
    __tablename__ = "current_shapes"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    agency_id: Mapped[str] = mapped_column(Text, nullable=False)
    shape_id: Mapped[str] = mapped_column(Text, nullable=False)
    shape_pt_lat: Mapped[float] = mapped_column(Double, nullable=False)
    shape_pt_lon: Mapped[float] = mapped_column(Double, nullable=False)
    shape_pt_sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        Index("idx_current_shapes_agency", "agency_id"),
        Index("idx_current_shapes_shape_seq", "shape_id", "shape_pt_sequence"),
        {"schema": "gtfs_static"},
    )


class StopEventModel(Base):
    __tablename__ = "stop_events"
    __table_args__ = {"schema": "events"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    service_date: Mapped[date] = mapped_column(Date, primary_key=True)

    agency: Mapped[str] = mapped_column(Text, nullable=False)
    trip_id: Mapped[str] = mapped_column(Text, nullable=False)
    stop_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    stop_id: Mapped[str] = mapped_column(Text, nullable=False)
    line_number: Mapped[str] = mapped_column(Text, nullable=False)
    stop_name: Mapped[str] = mapped_column(Text, nullable=False)
    stop_desc: Mapped[str | None] = mapped_column(Text, nullable=True)
    direction_id: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    headsign: Mapped[str | None] = mapped_column(Text, nullable=True)
    planned_time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    event_time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    vehicle_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    license_plate: Mapped[str | None] = mapped_column(Text, nullable=True)
    detection_method: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    static_hash: Mapped[str] = mapped_column(Text, nullable=False)
    max_stop_sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))


class WeatherObservation(Base):
    __tablename__ = "hourly_observations"
    __table_args__ = {"schema": "weather"}

    observed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), primary_key=True)
    temperature_c: Mapped[float] = mapped_column(Double, nullable=False)
    precipitation_mm: Mapped[float] = mapped_column(Double, nullable=False)
    rain_mm: Mapped[float] = mapped_column(Double, nullable=False)
    snowfall_cm: Mapped[float] = mapped_column(Double, nullable=False)
    snow_depth_cm: Mapped[float] = mapped_column(Double, nullable=False)
    wind_speed_kmh: Mapped[float] = mapped_column(Double, nullable=False)
    wind_gusts_kmh: Mapped[float] = mapped_column(Double, nullable=False)
    cloud_cover_pct: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    visibility_m: Mapped[float] = mapped_column(Double, nullable=False)
    is_day: Mapped[bool] = mapped_column(Boolean, nullable=False)
    weather_code: Mapped[int] = mapped_column(SmallInteger, nullable=False)
