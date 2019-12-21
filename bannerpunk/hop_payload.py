from bigsize import BigSize
from tlv import Tlv
from hop_payload import HopPayload, TlvHopPayload


PIXEL_TLV_TYPE = 44445

class BannerPunkHopPayload:

    def encode_pixels(pixels):
        encoded = b''.join([p.to_bin() for p in pixels])
        return Tlv(PIXEL_TLV_TYPE, encoded).encode()

    def encode_non_final(amt_to_forward, outgoing_cltv_value, short_channel_id,
                         pixels):
        unextended = TlvHopPayload.encode_non_final(amt_to_forward,
                                                    outgoing_cltv_value,
                                                    short_channel_id)
        old_len, content, err = BigSize.pop(unextended)
        assert err is None
        pixel_content = BannerPunkHopPayload.encode_pixels(pixels)
        new_content = content + pixel_content
        return BigSize.encode(len(new_content)) + new_content


    def encode_final(amt_to_forward, outgoing_cltv_value, payment_secret,
                     total_msat, pixels):
        unextended = TlvHopPayload.encode_final(amt_to_forward,
                                                outgoing_cltv_value,
                                                pament_secret=payment_secret,
                                                totol_msat= total_msat)
        old_len, content, err = BigSize.pop(unextended)
        assert err is None
        pixel_content = BannerPunkHopPayload.encode_pixels(pixels)
        new_content = content + pixel_content
        return BigSize.encode(len(new_content)) + new_content


    def parse(byte_string):
        parsed, err = HopPayload.parse(byte_string)
        if err:
            return None, err
        if parsed['type'] != "tlv":
            return None, "non-tlv payload byte string"
        if PIXEL_TLV_TYPE not in parsed['tlvs']:
            return None, "no pixel data tlv in payload"
        return parsed, None
