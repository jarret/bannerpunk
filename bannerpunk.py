#!/usr/bin/env python3
import json
import argparse

from twisted.internet import reactor

from autobahn.twisted.websocket import WebSocketServerProtocol
from autobahn.twisted.websocket import WebSocketServerFactory

from txzmq import ZmqEndpoint, ZmqEndpointType
from txzmq import ZmqFactory
from txzmq import ZmqSubConnection

from bannerpunk.pixel_preimage import Pixel, Preimage
from bannerpunk.art_db import ArtDb
from bannerpunk.compressor import compressor
from bannerpunk.images import IMAGE_SIZES

###############################################################################

class AppClient(WebSocketServerProtocol):
    def onConnect(self, request):
        print("Client connecting: {0}".format(request.peer))

    def onOpen(self):
        print("WebSocket client connection open.")
        self.server.clients.append(self)
        art_bin_0 = self.server.app.art_db_0.to_bin()
        art_bin_1 = self.server.app.art_db_1.to_bin()
        art_bin_2 = self.server.app.art_db_2.to_bin()
        art_bin = art_bin_0 + art_bin_1 + art_bin_2
        print("art bin len: %d" % len(art_bin))
        compressed_bin = compressor(art_bin)
        print("compressed art bin len: %d" % len(compressed_bin))
        self.sendMessage(compressed_bin, isBinary=True)

    def onMessage(self, payload, isBinary):
        print("got message?")

    def onClose(self, wasClean, code, reason):
        print("WebSocket connection closed: {0}".format(reason))

###############################################################################

class AppServer(WebSocketServerFactory):
    def __init__(self, port, app):
        ws_url = u"ws://0.0.0.0:%d" % port
        super().__init__(ws_url)
        self.protocol = AppClient
        self.protocol.server = self
        self.clients = []
        reactor.listenTCP(port, self)
        self.app = app

    def echo_to_clients(self, image_no, pixels):
        pixels = [{'x': p.x, 'y': p.y, 'rgb': p.rgb} for p in pixels]
        message = {'image_no': image_no,
                   'pixels':   pixels}
        message = json.dumps(message)
        print("echoing to clients: %s" % message)
        for c in self.clients:
            c.sendMessage(message.encode("utf8"))

###############################################################################

class App(object):
    def __init__(self, endpoint, port, art_db_dir):
        self.endpoint = endpoint
        self.port = port
        self.art_db_dir = art_db_dir

    ###########################################################################

    def setup_art_dbs(self):
        self.art_db_0 = ArtDb(IMAGE_SIZES[0]['width'],
                              IMAGE_SIZES[0]['height'], 0, self.art_db_dir)
        self.art_db_1 = ArtDb(IMAGE_SIZES[1]['width'],
                              IMAGE_SIZES[1]['height'], 1, self.art_db_dir)
        self.art_db_2 = ArtDb(IMAGE_SIZES[2]['width'],
                              IMAGE_SIZES[2]['height'], 2, self.art_db_dir)

    ###########################################################################

    def setup_websocket(self):
        self.ws_server = AppServer(self.port, self)

    ###########################################################################

    def setup_zmq(self):
        zmq_factory = ZmqFactory()
        sub_endpoint = ZmqEndpoint(ZmqEndpointType.connect, self.endpoint)
        sub_connection = ZmqSubConnection(zmq_factory, sub_endpoint)
        sub_connection.gotMessage = self.zmq_message
        sub_connection.subscribe("invoice_payment".encode("utf8"))

    def fee_adequate(self, fee, pixel_preimage):
        n_pixels = pixel_preimage.n_pixels
        min_fee = 1000 * n_pixels
        return fee >= min_fee

    def zmq_message(self, message, tag):
        d = json.loads(message.decode('utf8'))

        if d['status'] != 'settled':
            print("invoice is not settled")
            return

        p = Preimage.from_hex(d['preimage'])
        if not p:
            print("could not interpret, discarding %s" % d['preimage'])
            return
        if p.image_no > 2:
            print("unknown image_no discarding %s" % d['preimage'])
            return

        if not self.fee_adequate(d['fee'], p):
            print("not high enough forward fee, discarding %s" % d['preimage'])
            return

        image_no = p.image_no
        if image_no == 0:
            self.art_db_0.record_new_preimage(p)
        if image_no == 1:
            self.art_db_1.record_new_preimage(p)
        if image_no == 2:
            self.art_db_2.record_new_preimage(p)

        self.ws_server.echo_to_clients(image_no, p.pixels)

    ###########################################################################

    def run(self):
        self.setup_websocket()
        self.setup_zmq()
        self.setup_art_dbs()

    def stop(self):
        self.art_db_0.unmap_art_bin()
        self.art_db_1.unmap_art_bin()
        self.art_db_2.unmap_art_bin()


###############################################################################

DEFAULT_WEBSOCKET_PORT = 9000

DEFAULT_ZMQ_SUBSCRIBE_ENDPOINT = "tcp://127.0.0.1:5556"

DEFAULT_ART_DB_DIR = "/tmp/bannerpunk/"

parser = argparse.ArgumentParser(prog="app.py")
parser.add_argument("-e", "--endpoint", type=str,
                    default=DEFAULT_ZMQ_SUBSCRIBE_ENDPOINT)
parser.add_argument("-w", "--websocket-port", type=int,
                    default=DEFAULT_WEBSOCKET_PORT)
parser.add_argument("-a", "--art-db-dir", type=str, default=DEFAULT_ART_DB_DIR)
settings = parser.parse_args()

a = App(settings.endpoint, settings.websocket_port, settings.art_db_dir)
a.run()


reactor.addSystemEventTrigger("before", "shutdown", a.stop)

reactor.run()
