from bolt.namespace import Namespace

ONION_BYTE_LENGTH = 1366
HOP_PAYLOADS_LENGTH = 1300
HMAC_LENGTH = 32

class Onion:
    @staticmethod
    def parse_fixed(byte_string):
        if len(byte_string) != ONION_BYTE_LENGTH:
            return None, "onion is the wrong length"
        version, remainder, err = Namespace.pop_u8(byte_string)
        if err:
            return None, "could not pop version byte"
        if version != 0:
            return None, "unsupported onion packet version"
        public_key, remainder, err = Namespace.pop_point(remainder)
        if err:
            return None, "could not pop public key: %s" % err

        hop_payloads, remainder, err = Namespace.pop_bytes(HOP_PAYLOADS_LENGTH,
                                                           remainder)
        if err:
            return None, "could not pop hops_payloads: %s" % err
        hmac, remainder, err =  Namespace.pop_bytes(HMAC_LENGTH, remainder)
        if err:
            return None, "could not pop hmac: %s" % err
        if len(remainder) != 0:
            return None, "unexpected remaining bytes"
        # TODO Check hmac for validity, need assocdata
        return {'version':      version,
                'public_key':   public_key,
                'hop_payloads': hop_payloads,
                'hmac':         hmac}, None
