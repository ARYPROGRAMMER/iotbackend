import unittest

from stealthera_api.iwown.packet import PacketParseError, parse_upload


class PacketParserTests(unittest.TestCase):
    def test_parses_single_packet(self):
        payload = b"984612114945605" + b"DT" + (3).to_bytes(2, "little") + (9).to_bytes(2, "little") + (0x80).to_bytes(2, "little") + b"abc"
        upload = parse_upload(payload)
        self.assertEqual(upload.device_id, "984612114945605")
        self.assertEqual(len(upload.packets), 1)
        self.assertEqual(upload.packets[0].protocol_code, 0x80)
        self.assertEqual(upload.packets[0].payload, b"abc")

    def test_rejects_short_payload(self):
        with self.assertRaises(PacketParseError) as error:
            parse_upload(b"short")
        self.assertEqual(error.exception.reply_code, 0x02)

    def test_rejects_bad_header(self):
        payload = b"984612114945605" + b"NO" + (0).to_bytes(2, "little") + (0).to_bytes(2, "little") + (0x80).to_bytes(2, "little")
        with self.assertRaises(PacketParseError) as error:
            parse_upload(payload)
        self.assertEqual(error.exception.reply_code, 0x03)


if __name__ == "__main__":
    unittest.main()
