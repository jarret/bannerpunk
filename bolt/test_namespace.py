from namespace import Namespace

# test namespaces as defined by:
# https://github.com/lightningnetwork/lightning-rfc/blob/master/01-messaging.md#appendix-b-type-length-value-test-vectors


class TestNamespace1(Namespace):
    def __init__(self):
        self.tlv_parsers = {1:   self.parse_tlv1,
                            2:   self.parse_tlv2,
                            3:   self.parse_tlv3,
                            254: self.parse_tlv4}

    def parse_tlv1(self, tlv):
        amount_msat, _, err = Namespace.pop_tu64(tlv.l, tlv.v)
        if err:
            return None, err
        return {'tlv_type_name':   "tlv1",
                'amount_msat':     amount_msat}, None

    def parse_tlv2(self, tlv):
        short_channel_id, _, err = Namespace.pop_short_channel_id(tlv.l, tlv.v)
        if err:
            return None, err
        return {'tlv_type_name':    "tlv2",
                'short_channel_id': short_channel_id}, None

    def parse_tlv3(self, tlv):
        node_id, remainder, err = Namespace.pop_point(tlv.l, tlv.v)
        if err:
            return None, err
        amount_msat_1, remainder, err = Namespace.pop_u64(remainder)
        if err:
            return None, err
        amount_msat_2, remainder, err = Namespace.pop_u64(remainder)
        if err:
            return None, err
        return {'tlv_type_name': "tlv3",
                'node_id':       node_id,
                'amount_msat_1': amount_msat_1,
                'amount_msat_2':   amount_msat_2}, None

    def parse_tlv4(self, tlv):
        cltv_delta, _, err = Namespace.pop_u16(tlv.v)
        if err:
            return None, err
        return {'tlv_type_name': "tlv4",
                'cltv_delta':    cltv_delta}, None


class TestNamespace2(Namespace):
    def __init__(self):
        self.tlv_parsers = {0:  self.parse_tlv1,
                            11: self.parse_tlv2}

    def parse_tlv1(self, tlv):
        amount_msat, _, err = Namespace.pop_tu64(tlv.l, tlv.v)
        if err:
            return None, err
        return {'tlv_type_name': "tlv1",
                'amount_msat':   amount_msat}, None

    def parse_tlv2(self, tlv):
        cltv_expiry, _, err = Namespace.pop_tu32(tlv.l, tlv.v)
        if err:
            return None, err
        return {'tlv_type_name': "tlv2",
                'cltv_expiry':   cltv_expiry}, None



# test cases defined in:
# https://github.com/lightningnetwork/lightning-rfc/blob/master/01-messaging.md#tlv-decoding-failures

TEST_BOTH_NAMESPACES_INVALID = [
    "1200",
    "fd010200",
    "fe0100000200",
    "ff010000000000000200",
]

TEST_NAMESPACE1_INVALID = [
    "0109ffffffffffffffffff",
    "010100",
    "01020001",
    "0103000100",
    "010400010000",
    "01050001000000",
    "0106000100000000",
    "010700010000000000",
    "01080001000000000000",
    "020701010101010101",
    "0209010101010101010101",
    "0321023da092f6980e58d2c037173180e9a465476026ee50f96695963e8efe436f54eb",
    "0329023da092f6980e58d2c037173180e9a465476026ee50f96695963e8efe436f54eb0000000000000001",
    "0330023da092f6980e58d2c037173180e9a465476026ee50f96695963e8efe436f54eb000000000000000100000000000001",
    "0331043da092f6980e58d2c037173180e9a465476026ee50f96695963e8efe436f54eb00000000000000010000000000000002",
    "0332023da092f6980e58d2c037173180e9a465476026ee50f96695963e8efe436f54eb0000000000000001000000000000000001",
    "fd00fe00",
    "fd00fe0101",
    "fd00fe03010101",
    "0000",
]


TEST_VALID_IGNORED = [
]
