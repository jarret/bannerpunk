#!/usr/bin/env python3

import time
import random
import hashlib
import os
import sys
import json
import argparse

from PIL import Image

from twisted.internet import reactor

from txzmq import ZmqEndpoint, ZmqEndpointType
from txzmq import ZmqFactory
from txzmq import ZmqSubConnection, ZmqPubConnection

sys.path.insert(1, os.path.realpath(os.path.pardir))

from bannerpunk.pixel_preimage import Pixel, Preimage


# This module publishes a script of messages to a ZMQ endpoint

PUBLISH_ENDPOINT = "tcp://127.0.0.1:5557"

TAG = "invoice_payment".encode("utf8")

factory = ZmqFactory()

pub_endpoint = ZmqEndpoint(ZmqEndpointType.bind, PUBLISH_ENDPOINT)
pub_connection = ZmqPubConnection(factory, pub_endpoint)

MAX_X = 255
MAX_Y = 255

parser = argparse.ArgumentParser(prog="mock-png.py")
parser.add_argument("image_no", type=int)
parser.add_argument("x_offset", type=int)
parser.add_argument("y_offset", type=int)
parser.add_argument("png_file", type=str)
s = parser.parse_args()

img = Image.open(s.png_file)
width, height = img.size
rgb_raw = img.convert("RGB")

px_data = list(rgb_raw.getdata())

pixels = []
for h in range(height):
    for w in range(width):
        x = w + s.x_offset
        if x > MAX_X:
            continue
        y = h + s.y_offset
        if y > MAX_Y:
            continue
        y = h + s.y_offset
        rgb = "%02x%02x%02x" % px_data[(h * width) + w]
        pixels.append(Pixel(x, y, rgb))

print([str(p) for p in pixels])


def divide_chunks(l, n):
    # looping till length l
    for i in range(0, len(l), n):
        yield l[i:i + n]


TEST_PREIMAGES = []
for chunk in divide_chunks(pixels, 4):
    print("chunk: %s" % [str(p) for p in chunk])
    TEST_PREIMAGES.append(Preimage(s.image_no, chunk).to_hex())

#N_TEST_PREIMAGES = 100
#
#TEST_PREIMAGES = [random_preimage().to_hex() for _ in range(N_TEST_PREIMAGES)]
#
def publish():
    print("starting to publish to %s" % PUBLISH_ENDPOINT)
    for p in TEST_PREIMAGES:
        print("preimage to str: %s" % Preimage.from_hex(p))
        m = {'preimage': p,
             'status':  "settled",
             'fee':     4000}
        msg = json.dumps(m).encode("utf8")
        print("publishing: %s" % msg)
        pub_connection.publish(msg, tag=TAG)
        time.sleep(0.02)
    reactor.stop()

reactor.callLater(1.0, publish)
reactor.run()
