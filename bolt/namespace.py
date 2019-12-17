from util import b2i, b2h
from tlv import Tlv

class Namespace:
    """
    Represents a specific namespace of TLVs as referred to in BOLT 1 and
    provides generic pop helpers for the fundamental types defined here:
    https://github.com/lightningnetwork/lightning-rfc/blob/master/01-messaging.md#fundamental-types
    """
    @staticmethod
    def pop_tlv(byte_string):
        return Tlv.pop(byte_string)

    @staticmethod
    def tlvs_are_valid(byte_string):
        while len(byte_string) > 0:
            _, byte_string, err = Namespace.pop_tlv(byte_string)
            if err:
                return False
        return True

    @staticmethod
    def iter_tlvs(byte_string):
        assert Namespace.tlvs_are_valid(byte_string), "bad byte_string?"
        while len(byte_string) > 0:
            tlv, byte_string, _ = Tlv.pop(byte_string)
            yield tlv

    ###########################################################################

    @staticmethod
    def pop_u8(byte_string):
        if len(byte_string) < 1:
            return None, None, "underrun while popping a u8"
        return b2i(byte_string[:1]), byte_string[1:], None

    @staticmethod
    def pop_u16(byte_string):
        if len(byte_string) < 2:
            return None, None, "underrun while popping a u16"
        return b2i(byte_string[:2]), byte_string[2:], None

    @staticmethod
    def pop_u32(byte_string):
        if len(byte_string) < 4:
            return None, None, "underrun while popping a u32"
        return b2i(byte_string[:4]), byte_string[4:], None

    @staticmethod
    def pop_u64(byte_string):
        if len(byte_string) < 8:
            return None, None, "underrun while popping a u64"
        return b2i(byte_string[:8]), byte_string[8:], None

    ###########################################################################

    @staticmethod
    def pop_tu16(n_bytes, byte_string):
        assert n_bytes <= 2, "cannot pop more than 2 bytes for a tu16"
        if len(byte_string) < n_bytes:
            return None, None, "underrun while popping tu16"
        if n_bytes == 0:
            return 0, byte_string, None
        return b2i(byte_string[:n_bytes]), byte_string[n_bytes:], None

    @staticmethod
    def pop_tu32(n_bytes, byte_string):
        assert n_bytes <= 4, "cannot pop more than 4 bytes for a tu32"
        if len(byte_string) < n_bytes:
            return None, None, "underrun while popping tu32"
        if n_bytes == 0:
            return 0, byte_string, None
        return b2i(byte_string[:n_bytes]), byte_string[n_bytes:], None

    @staticmethod
    def pop_tu64(n_bytes, byte_string):
        assert n_bytes <= 8, "cannot pop more than 8 bytes for a tu64"
        if len(byte_string) < n_bytes:
            return None, None, "underrun while popping tu62"
        if n_bytes == 0:
            return 0, byte_string, None
        return b2i(byte_string[:n_bytes]), byte_string[n_bytes:], None

    ###########################################################################

    @staticmethod
    def pop_chain_hash(byte_string):
        if not len(byte_string) >= 32:
            return None, None, "underrun while popping chain_hash"
        return b2h(byte_string)[:32], byte_string[32:], None

    @staticmethod
    def pop_channel_id(byte_string):
        if not len(byte_string) >= 32:
            return None, None, "underrun while popping channel_id"
        return b2h(byte_string[:32]), byte_string[32:], None

    @staticmethod
    def pop_sha256(byte_string):
        if not len(byte_string) >= 64:
            return None, None, "underrun while popping signature"
        return b2h(byte_string[:64]), byte_string[64:], None

    @staticmethod
    def pop_signature(byte_string):
        if not len(byte_string) >= 64:
            return None, None, "underrun while popping signature"
        return b2h(byte_string[:64]), byte_string[64:], None

    @staticmethod
    def pop_point(byte_string):
        if not len(byte_string) >= 33:
            return None, None, "underrun wihle popping point"
        return b2h(byte_string[:33]), byte_string[33:], None

    @staticmethod
    def pop_short_channel_id(byte_string):
        if not len(byte_string) >= 8:
            return None, None, "underrun while popping short_channel_id"
        block_height = b2i(byte_string[:3])
        tx_index = b2i(byte_string[3:6])
        output_index = b2i(byte_string[6:8])
        formatted = "%dx%dx%d" % (block_height, tx_index, output_index)
        return formatted, byte_string[8:], None

    ###########################################################################

    def parse_tlv(self, tlv):
        if tlv.t not in self.tlv_parsers:
            return False, "TLV type has no defined parser function"
        parsed_tlv, err = self.tlv_parsers[tlv.t]](tlv)
        if err:
            return False, err
        assert 'tlv_type_name' in parsed_tlv, ("subclass parser must name the "
                                               "parsed tlv type")
        return parsed_tlv, None

    def parse_tlvs(self, tlvs):
        parsed_tlvs = []
        for tlv in tlvs:
            parsed_tlv, err = self.parse_tlv(tlv)
            if err:
                return None, err
            parsed_tlvs.append(parsed_tlv)
        return parsed_tlvs, None

    def parse(self, byte_string):
        if not Namespace.tlvs_are_valid(byte_string):
            return None, "tlvs are not valid"
        tlvs = list(Namespace.iter_tlvs(byte_string))
        types = set(tlv.t for tlv in tlvs)
        if not types.issubset(set(self.tlv_persers.keys()))
            return None, "got unknown tlv types for Namespace"
        parsed_tlvs, err = self.parse_tlvs(tlvs)
        if err:
            return None, err
        return parsed_tlvs, None
