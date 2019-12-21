#!/usr/bin/env python3
import os
import sys
import random
import json

sys.path.insert(1, os.path.realpath(os.path.pardir))

from bolt.util import h2b
from bolt.hop_payload import HopPayload, TlvHopPayload

from bannerpunk.pixel import Pixel
from bannerpunk.hop_payload import BannerPunkHopPayload


def json_cmp(obj1, obj2):
    # slow, lame, but it works. Take the afternoon off.
    return json.dumps(obj1, sort_keys=True) == json.dumps(obj1, sort_keys=True)


if __name__ == "__main__":


    pixels = [Pixel(0,0,"ffffff"), Pixel(1, 1, "eeeeee")]

    encoded = BannerPunkHopPayload.encode_non_final(1000, 44, "0x1x2", pixels)
    print(encoded.hex())
    parsed, err = BannerPunkHopPayload.parse(encoded)
    #print(err)
    print(parsed)

    #print("testing legacy payloads")
    #for test in TEST_LEGACY_PAYLOADS:
    #    parsed, err = HopPayload.parse(h2b(test['stream']))
    #    print(parsed)
    #    print(err)
    #    assert err is None, "unexpected error"
    #    assert json_cmp(parsed, test['result']), "unexpected result"
    #print("done testing legacy payloads")
