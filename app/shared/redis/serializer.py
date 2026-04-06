import msgspec

from app.shared.redis.schemas import (
    LiveVehiclePosition,
    SavedSequenceData,
    TripUpdateCache,
    VehiclePositionMessage,
    VehicleState,
)

_encoder = msgspec.msgpack.Encoder()

_vehicle_state_decoder = msgspec.msgpack.Decoder(VehicleState)
_trip_update_decoder = msgspec.msgpack.Decoder(TripUpdateCache)
_live_vehicle_decoder = msgspec.msgpack.Decoder(LiveVehiclePosition)
_saved_seq_decoder = msgspec.msgpack.Decoder(SavedSequenceData)
_vp_message_encoder = msgspec.json.Encoder()
_vp_message_decoder = msgspec.json.Decoder(VehiclePositionMessage)


def encode(obj: msgspec.Struct) -> bytes:
    return _encoder.encode(obj)


def decode_vehicle_state(data: bytes) -> VehicleState:
    return _vehicle_state_decoder.decode(data)


def decode_trip_update(data: bytes) -> TripUpdateCache:
    return _trip_update_decoder.decode(data)


def decode_live_vehicle_position(data: bytes) -> LiveVehiclePosition:
    return _live_vehicle_decoder.decode(data)


def encode_saved_sequence(obj: SavedSequenceData) -> bytes:
    return _encoder.encode(obj)


def decode_saved_sequence(data: bytes) -> SavedSequenceData:
    return _saved_seq_decoder.decode(data)


def encode_vp_message(msg: VehiclePositionMessage) -> bytes:
    return _vp_message_encoder.encode(msg)


def decode_vp_message(data: bytes) -> VehiclePositionMessage:
    return _vp_message_decoder.decode(data)
