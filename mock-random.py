#!/usr/bin/env python3

import time
import random
import hashlib
import os
import sys
import json

from twisted.internet import reactor

from txzmq import ZmqEndpoint, ZmqEndpointType
from txzmq import ZmqFactory
from txzmq import ZmqSubConnection, ZmqPubConnection

from lib.pixel_preimage import Pixel, Preimage

# This module publishes a script of messages to a ZMQ endpoint

PUBLISH_ENDPOINT = "tcp://127.0.0.1:5556"

TAG = "invoice_payment".encode("utf8")

factory = ZmqFactory()

pub_endpoint = ZmqEndpoint(ZmqEndpointType.bind, PUBLISH_ENDPOINT)
pub_connection = ZmqPubConnection(factory, pub_endpoint)

MAX_X = 255
MAX_Y = 255

###############################################################################

def random_coord():
    x = random.randint(0, MAX_X)
    y = random.randint(0, MAX_Y)
    return x, y

def random_color():
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    return "%02x%02x%02x" % (r, g, b)

def random_pixel():
    x, y = random_coord()
    rgb = random_color()
    return Pixel(x, y, rgb)

def random_preimage():
    image_no = random.randint(0, 3)
    n_pixels = random.randint(1, 4)
    #n_pixels = 4
    pixels = [random_pixel() for _ in range(n_pixels)]
    return Preimage(image_no, pixels)

###############################################################################

N_TEST_PREIMAGES = 100

TEST_PREIMAGES = [random_preimage().to_hex() for _ in range(N_TEST_PREIMAGES)]

def publish():
    print("starting to publish")
    for p in TEST_PREIMAGES:
        print("preimage to str: %s" % Preimage.from_hex(p))
        m = {'preimage': p,
             'status':  "settled",
             'fee':     4000}
        msg = json.dumps(m).encode("utf8")
        print("publishing: %s" % msg)
        pub_connection.publish(msg, tag=TAG)
        time.sleep(0.1)
    reactor.stop()


reactor.callLater(1.0, publish)
reactor.run()
