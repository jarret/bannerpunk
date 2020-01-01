from bolt.util import h2b
from bolt.bigsize import BigSize
from bolt.tlv import Tlv
from bolt.namespace import Namespace
from bolt.hop_payload import HopPayload, TlvHopPayload

from bannerpunk.pixel import Pixel

PIXEL_TLV_TYPE = 44445
ART_TLV_TYPE = 44443

class Extension:
    def _encode_pixels(pixels):
        encoded = b''.join([p.to_bin() for p in pixels])
        return Tlv(PIXEL_TLV_TYPE, encoded).encode()

    def _encode_art_no(art_no):
        encoded = Namespace.encode_tu16(art_no)
        return Tlv(ART_TLV_TYPE, encoded).encode()

    def encode_non_final(amt_to_forward, outgoing_cltv_value, short_channel_id,
                         art_no, pixels):
        unextended = TlvHopPayload.encode_non_final(amt_to_forward,
                                                    outgoing_cltv_value,
                                                    short_channel_id)
        old_len, content, err = BigSize.pop(unextended)
        assert err is None
        art_no_content = Extension._encode_art_no(art_no)
        pixel_content = Extension._encode_pixels(pixels)
        new_content = content + art_no_content + pixel_content
        return BigSize.encode(len(new_content)) + new_content


    def encode_final(amt_to_forward, outgoing_cltv_value, payment_secret,
                     total_msat, art_no, pixels):
        unextended = TlvHopPayload.encode_final(amt_to_forward,
                                                outgoing_cltv_value,
                                                pament_secret=payment_secret,
                                                totol_msat= total_msat)
        old_len, content, err = BigSize.pop(unextended)
        assert err is None
        art_no_content = Extension._encode_art_no(art_no)
        pixel_content = Extension._encode_pixels(pixels)
        new_content = content + art_no_content + pixel_content
        return BigSize.encode(len(new_content)) + new_content

    ###########################################################################

    def parse_pixels(tlv):
        pixels = []
        if tlv.l % 5 != 0:
            return None, "unexpected length"
        remainder = tlv.v
        while len(remainder) > 0:
            pixel_hex, remainder, err = Namespace.pop_bytes(5, remainder)
            if err:
                return None, err
            pixels.append(Pixel.from_bin(h2b(pixel_hex)))
        return {'tlv_type_name': "bannerpunk_pixels",
                'pixels':         pixels}, None

    def parse_art_no(tlv):
        art_no, remainder, err = Namespace.pop_tu16(tlv.l, tlv.v)
        if err:
            return None, err
        if len(remainder) > 0:
            return None, "unexpected extra bytes"
        return {'tlv_type_name': "bannerpunk_art_no",
                'art_no':         art_no}, None

    def parse(byte_string):
        extension_parsers = {PIXEL_TLV_TYPE: Extension.parse_pixels,
                             ART_TLV_TYPE:   Extension.parse_art_no}
        parsed, err = HopPayload.parse(byte_string,
                                       extension_parsers=extension_parsers)
        if err:
            return None, err
        if parsed['format'] != "tlv":
            return None, "non-tlv payload byte string"
        if ART_TLV_TYPE not in parsed['tlvs']:
            return None, "no art tlv in payload"
        if PIXEL_TLV_TYPE not in parsed['tlvs']:
            return None, "no pixel data tlv in payload"
        return parsed, None
