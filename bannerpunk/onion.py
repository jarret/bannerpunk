


[
    {
        "name": "zero",
        "value": 0,
        "bytes": "00"
    },
    {
        "name": "one byte high",
        "value": 252,
        "bytes": "fc"
    },
    {
        "name": "two byte low",
        "value": 253,
        "bytes": "fd00fd"
    },
    {
        "name": "two byte high",
        "value": 65535,
        "bytes": "fdffff"
    },
    {
        "name": "four byte low",
        "value": 65536,
        "bytes": "fe00010000"
    },
    {
        "name": "four byte high",
        "value": 4294967295,
        "bytes": "feffffffff"
    },
    {
        "name": "eight byte low",
        "value": 4294967296,
        "bytes": "ff0000000100000000"
    },
    {
        "name": "eight byte high",
        "value": 18446744073709551615,
        "bytes": "ffffffffffffffffff"
    },
    {
        "name": "two byte not canonical",
        "value": 0,
        "bytes": "fd00fc",
        "exp_error": "decoded varint is not canonical"
    },
    {
        "name": "four byte not canonical",
        "value": 0,
        "bytes": "fe0000ffff",
        "exp_error": "decoded varint is not canonical"
    },
    {
        "name": "eight byte not canonical",
        "value": 0,
        "bytes": "ff00000000ffffffff",
        "exp_error": "decoded varint is not canonical"
    },
    {
        "name": "two byte short read",
        "value": 0,
        "bytes": "fd00",
        "exp_error": "unexpected EOF"
    },
    {
        "name": "four byte short read",
        "value": 0,
        "bytes": "feffff",
        "exp_error": "unexpected EOF"
    },
    {
        "name": "eight byte short read",
        "value": 0,
        "bytes": "ffffffffff",
        "exp_error": "unexpected EOF"
    },
    {
        "name": "one byte no read",
        "value": 0,
        "bytes": "",
        "exp_error": "EOF"
    },
    {
        "name": "two byte no read",
        "value": 0,
        "bytes": "fd",
        "exp_error": "unexpected EOF"
    },
    {
        "name": "four byte no read",
        "value": 0,
        "bytes": "fe",
        "exp_error": "unexpected EOF"
    },
    {
        "name": "eight byte no read",
        "value": 0,
        "bytes": "ff",
        "exp_error": "unexpected EOF"
    }
]

class BigSize():
    def __init__(self, value):
        self.value = value

    def hex_to_int(self, hex_string):
        return int(hex_string, 16)

    def pop_bigsize(self, hex_string):
        head = hex_string[0:2]
        if head == "fd":
            return self.hex_to_int(hex_string[2:6]), hex_string[6:]
        elif head == "fe":
            return self.hex_to_int(hex_string[2:10]),, hex_string[10:]
        elif head == "ff":
            return self.hex_to_int(hex_string[2:18]), hex_string[18:]
        else:
            return self.hex_to_int(hex_string[0:2]), hex_string[2:]

    def test_string(self, hex_string, expected):

    def from_hex(self, hex_bytes):
        if len(hex_bytes) == 0:
            raise ValueError("zero length string?")
        if len(hex_bytes) % 2 != 0:
            raise ValueError("odd number of digits in hex string?")

        head = hex_bytes[0:2]
        if head == "fd":
        elif head == "fe":
        elif head == "ff":
        else:
            if len(hex_bytes) != 2:
                raise ValueError("odd number of digits in hex string?")

class LegacyOnionPayload():
    def __init__(self, amt_to_forward, outgoing_cltv_value, short_channel_id):
        self.amt_to_forward = amt_to_forward
        self.outgoing_cltv_value = outgoing_cltv_value
        self.short_channel_id = short_channel_id

    def to_hex(self):

        # 0x00 length
        # short chennel id, 8 bytes
        # u64 amt_to_forward
        # u32 outgoing_cltv_value (blocheight + delay)
        # 12 bytes padding

        pass

    def from_hex(self):
        pass


class TlvPayload():
    def __init__(self, amt_to_forward, outgoing_cltv_value, short_channel_id):
        self.tlvs = []
        pass

    def add_field(self, tag, value):
        length = len(value)
        self.tlvs.append((tag, length, value))


    def to_hex(self):
        # type 2 = amt_to_forward = tu64
        # type 4 = outgoing_cltv_value = tu32
        # type 6 = short_channel_id = 8 bytes
        # type 8 = payment_data = 32 byte payment_secret tu64 total_msat



