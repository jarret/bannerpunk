from bigsize import BigSize
from namespace import Namespace

###############################################################################

class LegacyPayload:
    """ encodes/decodes legacy payload as described in:
    https://github.com/lightningnetwork/lightning-rfc/blob/master/04-onion-routing.md
    """

    def encode(short_channel_id, amt_to_forward, outgoing_cltv_value):
        encoded_version = Namespace.encode_u8(0)
        encoded_scid = Namespace.encode_sort_channel_id(short_channel_id)
        encoded_amt = Namespace.encode_u64(amt_to_forward)
        encoded_outgoing = Namespace.encode_u32(outgoing_cltv_value)
        padding = 12 * Namespace.encode_u8(0)
        return (encoded_version + encoded_scid + encoded_amt +
                encoded_outgoing + padding)

    def parse(byte_string):
        scid, remainder, err = Namespace.pop_short_channel_id(byte_string)
        if err:
            return None, err
        #print("scid: %s, remainder: %s\n" % (scid, remainder.hex()))
        amt_to_forward, remainder, err = Namespace.pop_u64(remainder)
        if err:
            return None, err
        #print("amt: %s, remainder: %s\n" % (amt_to_forward, remainder.hex()))
        outgoing_cltv_value, remainder, err = Namespace.pop_u32(remainder)
        if err:
            return None, err
        #print("outgoing: %s,  remainder: %s\n" % (outgoing_cltv_value,
        #                                          remainder.hex()))
        padding, remainder, err = Namespace.pop_bytes(remainder, 12)
        if err:
            return None, err
        #print("padding %s, remainder: %s\n" % (padding, remainder.hex()))
        if len(remainder) != 0:
            return None, "unexpected remaining bytes"
        return {'short_channel_id':    scid,
                'amt_to_forward':      amt_to_forward,
                'outgoing_cltv_value': outgoing_cltv_value,
                'padding':             padding}, None


###############################################################################

class TlvPayload(Namespace):
    """ encodes/decodes tlv payload as described in:
    https://github.com/lightningnetwork/lightning-rfc/blob/master/04-onion-routing.md
    """
    def __init__(self):
        self.tlv_parsers = {2: self.parse_amt_to_forward,
                            4: self.parse_outgoing_cltv_value,
                            6: self.parse_short_channel_id,
                            8: self.parse_payment_data}
        self.tlv_encoders = {2: self.encode_amt_to_forward,
                             4: self.encode_outgoing_cltv_value,
                             6: self.encode_short_channel_id,
                             8: self.encode_payment_data}

    def parse_amt_to_forward(self, tlv):
        amt_to_forward, remainder, err = Namespace.pop_tu64(tlv.l, tlv.v)
        if err:
            return None, err
        if len(remainder) != 0:
            return None, "unexpected remaining bytes"
        return {'tlv_type_name': 'amt_to_forward',
                'amt_to_forward': amt_to_forward}, None

    def parse_outgoing_cltv_value(self, tlv):
        outgoing_cltv_value, remainder, err = Namespace.pop_tu32(tlv.l, tlv.v)
        if err:
            return None, err
        if len(remainder) != 0:
            return None, "unexpected remaining bytes"
        return {'tlv_type_name':      'outgoing_cltv_value',
                'outgoing_cltv_value': outgoing_cltv_value}, None

    def parse_short_channel_id(self, tlv):
        scid, remainder, err = Namespace.pop_short_channel_id(tlv.l, tlv.v)
        if err:
            return None, err
        if len(remainder) != 0:
            return None, "unexpected remaining bytes"
        return {'tlv_type_name':   'short_channel_id',
                'short_channel_id': scid}

    def parse_payment_data(self, tlv):
        payment_secret, remainder, err = Namespace.pop_bytes(tlv.v, 32)
        if err:
            return None, err
        total_msat, remainder, err = Namespace.pop_bytes(len(remainder),
                                                         remainder)
        if err:
            return None, err
        if len(remainder) != 0:
            return None, "unexpected remaining bytes"
        return {'tlv_type_name':  'payment_data',
                'payment_secret': payment_secret,
                'total_msat':     total_msat}
    ###########################################################################

    def parse(self):
        pass

    ###########################################################################

    def encode_amt_to_forward(self):
        return Namespace.encode_tu64(self.amt_to_forward)

    def encode_outgoing_cltv_value(self):
        return Namespace.encode_tu32(self.outgoing_cltv_value)

    def encode_short_channel_id(self):
        return Namespace.encode_short_channel_id(self.short_channel_id)

    def encode_payment_data(self):
        return (Namespace.encode_bytes(self.payment_secret) +
                Namespace.encode_tu64(self.total_msat))

    def encode(amt_to_forward, outgoing_cltv_value, short_channel_id,
               payment_secret, total_msat):
        self.amt_to_forward = amt_to_forward
        self.outgoing_cltv_value = outgoing_cltv_value
        self.short_channel_id = short_channel_id
        self.payment_secret = payment_secret
        self.total_msat = total_msat
        encoded_tlvs = super().__encode__()
        length = len(encoded_tlvs)
        return BigSize.encode(length) + encoded_tlvs


class Payload:
    def parse(byte_string):
        length, remainder, err = BigSize.pop(byte_string)
        if err:
            return None, err
        if length == 1:
            return None, "unknown version"
        if length == 0:
            return LegacyPayload.parse(remainder)
        if len(remainder) != length:
            return None, "remainder length does not match state length"
        print("len: %d" % length)
        print("remainder: %s" % remainder.hex())
        t = TlvPayload()
        return t.parse(remainder)
