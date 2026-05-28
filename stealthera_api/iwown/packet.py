from dataclasses import dataclass


PACKET_PREFIX = b"DT"
DEVICE_ID_BYTES = 15


class PacketParseError(Exception):
    def __init__(self, message, reply_code):
        super().__init__(message)
        self.reply_code = reply_code


@dataclass
class IwownPacket:
    protocol_code: int
    length: int
    crc: int
    payload: bytes
    offset: int

    @property
    def protocol_name(self):
        return {
            0x0A: "realtime",
            0x80: "history",
            0x12: "alarm",
        }.get(self.protocol_code, "unknown")


@dataclass
class IwownUpload:
    device_id: str
    packets: list[IwownPacket]


def parse_upload(payload):
    if len(payload) < DEVICE_ID_BYTES + 8:
        raise PacketParseError("data length below minimum packet size", 0x02)

    device_id = payload[:DEVICE_ID_BYTES].decode("ascii", errors="ignore").strip("\x00 ")
    packets = []
    cursor = DEVICE_ID_BYTES

    while cursor < len(payload):
        if len(payload) < cursor + 8:
            raise PacketParseError(f"data length below packet header at {cursor}", 0x02)

        prefix = payload[cursor : cursor + 2]
        if prefix != PACKET_PREFIX:
            raise PacketParseError(f"invalid packet header at {cursor}", 0x03)

        length = int.from_bytes(payload[cursor + 2 : cursor + 4], "little")
        crc = int.from_bytes(payload[cursor + 4 : cursor + 6], "little")
        protocol_code = int.from_bytes(payload[cursor + 6 : cursor + 8], "little")
        payload_start = cursor + 8
        payload_end = payload_start + length

        if len(payload) < payload_end:
            raise PacketParseError(f"data length below payload end at {payload_end}", 0x02)

        packets.append(
            IwownPacket(
                protocol_code=protocol_code,
                length=length,
                crc=crc,
                payload=payload[payload_start:payload_end],
                offset=cursor,
            )
        )
        cursor = payload_end

    return IwownUpload(device_id=device_id, packets=packets)
