#!/usr/bin/env python3
import time
import os
import sys
import uuid
import json
import pprint
import argparse
import math
from pyln.client import LightningRpc, Millisatoshi

from bannerpunk.print import chill_blue_str, chill_green_str, chill_yellow_str
from bannerpunk.print import chill_purple_str
from bannerpunk.pixel import Pixel
from bannerpunk.images import IMAGE_SIZES
from bannerpunk.hop_payload import BannerPunkHopPayload

from bolt.util import h2b
from bolt.hop_payload import LegacyHopPayload, TlvHopPayload

BANNERPUNK_NODE = "02e389d861acd9d6f5700c99c6c33dd4460d6f1e2f6ba89d1f4f36be85fc60f8d7"

JUKEBOX_NODE = "0379c41f28a38c49998fec42437db78a17af508fb19338e7360d7ffee2607ea036"

ROMPERT_NODE = "02ad6fb8d693dc1e4569bcedefadf5f72a931ae027dc0f0c544b34c1c6f3b9a02b"

BANNANA_NODE = "035c77dc0a10fe60e1304ae5b57d8fef87751add5d016b896d854fb706be6fc96c"

RISK_FACTOR = 10

SELF_PAYMENT = 1000 # in millisatoshis

CLTV_FINAL = 10

PIXEL_BYTES = 5
ONION_SIZE = 1300


class OnionDraw(object):
    def __init__(self, lightning_rpc, dst_node, art_no, pixel_draw_list):
        self.dst_node = dst_node
        self.art_no = art_no
        self.pixel_draw_list = pixel_draw_list
        self.rpc = LightningRpc(lightning_rpc)

    def estimate_routing_bytes(self, n_hops):
        # WARNING - this is a fudge, variable sizes can't easily be anticpated
        # hard to estmiate due to variable encoding
        # legacy payloads == 33 bytes + 32 byte hmac
        # tlv mid payloads ~= 18 bytes + 32 byte hmac
        # tlv final payloads ~= 46 bytes + 32 byte hmac
        if n_hops == 1:
            # destination is only hop
            return 46 + 32
        # assume along circular route, target mid hops and self is tlv
        # the rest are legacy
        est = 0
        # end tlv hop
        est += 46 + 32
        # target mid hop
        est += 18 + 32
        # other hops
        est += (33 + 32) * (n_hops - 2)
        return est + 10 # overestimate a bit

    def estimate_payload_pixels(self, n_hops):
        approx_bytes = ONION_SIZE - self.estimate_routing_bytes(n_hops)
        approx_pixels = math.floor(approx_bytes / PIXEL_BYTES)
        return approx_pixels - 3 # underestimate a bit

    def print_dict(self, info):
        pprint.pprint(info)

    def get_myid_blockheight(self):
        info = self.rpc.getinfo()
        return info['id'], info['blockheight']

    def create_invoice(self):
        msatoshi = SELF_PAYMENT
        label = str(uuid.uuid4())
        description = "circular onion payment for bannerpunk"
        invoice = self.rpc.invoice(msatoshi, label, description)
        invoice['payment_secret'] = self.get_payment_secret(invoice['bolt11'])
        return invoice

    def get_payment_secret(self, bolt11):
        decoded = self.rpc.decodepay(bolt11)
        return decoded['payment_secret']

    def get_outgoing_route(self, dst_payment):
        try:
            return self.rpc.getroute(self.dst_node, SELF_PAYMENT + dst_payment,
                                     RISK_FACTOR)
        except:
            print("could not find route from self to %s" % (self.dst_node))
            return None

    def get_returning_route(self, myid):
        try:
            return self.rpc.getroute(myid, SELF_PAYMENT, RISK_FACTOR,
                                     fromid=self.dst_node)
        except:
            print("could not find route from %s to %s" % (self.dst_node,
                                                         myid))
            return None

    def rework_routing_fees(self, route, pay_dst, pay_msat):
        # Thanks to sendinvoiceless.py plugin for this function!
        delay = int(CLTV_FINAL)
        msatoshi = Millisatoshi(SELF_PAYMENT)
        for r in reversed(route):
            r['msatoshi'] = msatoshi.millisatoshis
            r['amount_msat'] = msatoshi
            r['delay'] = delay
            channels = self.rpc.listchannels(r['channel'])
            ch = next(c for c in channels.get('channels') if
                      c['destination'] == r['id'])
            fee = Millisatoshi(ch['base_fee_millisatoshi'])
            # BOLT #7 requires fee >= fee_base_msat + ( amount_to_forward *
            # fee_proportional_millionths / 1000000 )
            fee += (msatoshi * ch['fee_per_millionth'] + 10**6 - 1) // 10**6
            # integer math trick to round up
            if ch['source'] == pay_dst:
                fee += pay_msat
            msatoshi += fee
            delay += ch['delay']
            r['direction'] = int(ch['channel_flags']) % 2

    def assemble_circular(self, outgoing, returning, dst_payment):
        route = outgoing['route'] + returning['route']
        self.rework_routing_fees(route, self.dst_node, dst_payment)
        return route

    def encode_non_final_payload(self, style, pubkey, channel, msatoshi,
                                 blockheight, delay, pixels):
        if style == "legacy":
            assert pubkey != self.dst_node, "can't send pixels to legacy hop"
            p = LegacyHopPayload.encode(channel, msatoshi, blockheight + delay)
            return {'style':   "legacy",
                    'pubkey':  pubkey,
                    'payload': p.hex()}

        else:
            if pubkey == self.dst_node:
                p = BannerPunkHopPayload.encode_non_final(msatoshi,
                                                          blockheight + delay,
                                                          channel, self.art_no,
                                                          pixels)
            else:
                p = TlvHopPayload.encode_non_final(msatoshi,
                                                   blockheight + delay,
                                                   channel)
            return {'style':   "tlv",
                    'pubkey':  pubkey,
                    'payload': p.hex()}

    def encode_final_payload(self, style, pubkey, channel, msatoshi,
                             blockheight, delay, payment_secret, pixels):
        if style == "legacy":
            assert pubkey != self.dst_node, "can't send pixels to legacy hop"
            p = LegacyHopPayload.encode(channel, msatoshi, blockheight + delay)
            return {'style':   "legacy",
                    'pubkey':  pubkey,
                    'payload': p.hex()}

        else:
            if pubkey == self.dst_node:
                p = BannerPunkHopPayload.encode_final(msatoshi,
                                                      blockheight + delay,
                                                      channel, payment_secret,
                                                      msatoshi, self.art_no,
                                                      pixels)
            else:
                p = TlvHopPayload.encode_final(msatoshi, blockheight + delay,
                                               payment_secret=payment_secret,
                                               total_msat=msatoshi)
            return {'style':   "tlv",
                    'pubkey':  pubkey,
                    'payload': p.hex()}

    def iter_hops(self, circular, blockheight, payment_secret, pixels):
        for i in range(len(circular) - 1):
            src = circular[i]
            dst = circular[i + 1]
            yield self.encode_non_final_payload(src['style'], src['id'],
                                                dst['channel'], dst['msatoshi'],
                                                blockheight, dst['delay'],
                                                pixels)
        dst = circular[-1]
        yield self.encode_final_payload(dst['style'], dst['id'], dst['channel'],
                                        dst['msatoshi'], blockheight,
                                        dst['delay'], payment_secret,
                                        pixels)

    def assemble_hops(self, circular, blockheight, payment_secret, pixels):
        return list(self.iter_hops(circular, blockheight, payment_secret,
                                   pixels))

    def create_onion(self, hops, assocdata):
        result = self.rpc.createonion(hops, assocdata)
        return result['onion'], result['shared_secrets']

    def send_onion(self, onion, circular, payment_hash, shared_secrets):
        first_hop = circular[0]
        label = str(uuid.uuid4())
        print("send params: %s %s %s %s %s" % (onion, first_hop, payment_hash,
                                               label, shared_secrets))
        result = self.rpc.sendonion(onion, first_hop, payment_hash, label,
                                    shared_secrets)
        return result

    def payment_status(self, payment_hash):
        return self.rpc.listsendpays(None,
                                     payment_hash)['payments'][0]['status']

    def calc_total_payload_size(self, hops):
        total = 0
        for hop in hops:
            payload_len = len(h2b(hop['payload']))
            hmac_len = 32
            total += payload_len + hmac_len
        return total

    def draw_attempt(self, myid, blockheight, invoice, hops, pixels,
                     pixel_underestimate):
        print("draw attempt")
        # get invoice that will be paid to self in circular route
        payment_hash = invoice['payment_hash']
        bolt11 = invoice['bolt11']
        payment_secret = invoice['payment_secret']
        print("bolt11: %s\npayment_secret: %s" % (
            chill_green_str(bolt11), chill_blue_str(payment_secret)))

        # estimate a route that will probably fit into an onion
        hop_estimation = hops
        will_fit = self.estimate_payload_pixels(hop_estimation)
        print("will_fit: %d" % will_fit)
        attempting_pixels = min(will_fit, len(pixels)) - pixel_underestimate
        dst_payment = 1000 * attempting_pixels
        print("to draw: %d" % attempting_pixels)
        attempting_pixel_list = pixels[:attempting_pixels]

        # try to make a route that fulfils the estimate
        outgoing = self.get_outgoing_route(dst_payment)
        if not outgoing:
            return {'status': "err",
                    'msg':    "could not get outgoing route"}
        print("outgoing:")
        self.print_dict(outgoing)
        returning = self.get_returning_route(myid)
        if not returning:
            return {'status': "err",
                    'msg':    "could not get returning route"}
        print("returning:")
        self.print_dict(returning)

        # check to see if the route compares to our estimate
        needed_hops = len(outgoing) + len(returning)
        if needed_hops != hops:
            print("different hop count than expected, need to recalculate...")
            return {'status':              "retry",
                    "needed_hops":         needed_hops,
                    "pixel_underestimate": pixel_underestimate}

        # build the hop data for the circular route
        circular = self.assemble_circular(outgoing, returning, dst_payment)
        print("assembled circular route:")
        self.print_dict(circular)
        hops = self.assemble_hops(circular, blockheight, payment_secret,
                                  attempting_pixel_list)
        print("hops:")
        self.print_dict(hops)

        # check to see if the hop payloads are too big
        if self.calc_total_payload_size(hops) > ONION_SIZE:
            print("payloads are too big, retrying with less pixels")
            return {'status':              "retry",
                    "needed_hops":         needed_hops,
                    "pixel_underestimate": pixel_underestimate + 3}

        # make the onion
        print("creating onion:")
        onion, shared_secrets = self.create_onion(hops, payment_hash)
        print("onion: %s" % chill_purple_str(onion))
        print("shared_secrets: %s" % chill_yellow_str(str(shared_secrets)))

        # send the onion
        send_result = self.send_onion(onion, circular, payment_hash,
                                      shared_secrets)
        print("send result: %s" % chill_yellow_str(str(send_result)))

        if send_result['status'] not in {"pending", "complete"}:
            return {"status": "err",
                    "msg":    "payment status is not pending"}

        if send_result['status'] == "complete":
            return {'status':       "success",
                    "pixels_sent":  attempting_pixels}

        # check to see if it will succeed.
        checks = 0
        while True:
            status = self.payment_status(payment_hash)
            if status == "complete":
                break
            checks += 1
            if checks == 10:
                return {"status": "err",
                        "msg":    "payment didn't complete"}
            print("sleeping waiting for payment to complete...")
            time.sleep(1.0)

        return {'status':       "success",
                "pixels_sent":  attempting_pixels}

    def draw_loop(self, myid, blockheight, invoice):
        hops = 4
        pixels = self.pixel_draw_list
        pixel_underestimate = 0
        retry_count = 0
        while True:
            result = self.draw_attempt(myid, blockheight, invoice, hops,
                                       pixels, pixel_underestimate)
            if result['status'] == "success":
                pixels = pixels[result['pixels_sent']:]
                pixel_underestimate = 0
            elif result['status'] == "retry":
                retry_count += 1
                hops = result['needed_hops']
                pixel_underestimate = result['pixel_underestimate']
            elif result['status'] == 'err':
                return result['msg']

            if retry_count == 5:
                return "too many retries, having trouble estimating..."
            #print("remaining: %s" % pixels)
            if len(pixels) == 0:
                return None

    def run(self):
        try:
            myid, blockheight = self.get_myid_blockheight()
            print("myid: %s, blockheight %s" % (chill_yellow_str(myid),
                                                chill_green_str(myid)))
            invoice = self.create_invoice()
        except Exception as e:
            return "could not get basics from rpc: %s" % e
        try:
            err = self.draw_loop(myid, blockheight, invoice)
            if err:
                return err
        except Exception as e:
            return None, "error while buying pixels: %s" % e
        return None

###############################################################################

def manual_func(settings):
    print("manual_func")
    if not os.path.exists(settings.lightning_rpc):
        sys.exit("no such file? %s" % settings.lightning_rpc)
    if settings.image_no not in {0, 1, 2}:
        sys.exit("invalid image_no: %d" % settings.image_no)
    if len(settings.pixel) > 4:
        sys.exit("too many pixels specified?")

    pixels = []
    for pixel in settings.pixel:
        p = Pixel.from_string("(" + pixel + ")")
        if not p:
            sys.exit("bad pixel? %s" % pixel)
        pixels.append(p)

    od = OnionDraw(settings.lightning_rpc, BANNANA_NODE, settings.image_no,
                   pixels)
    err = od.run()
    if err:
        sys.exit("something went wrong: %s" % err)

###############################################################################

def divide_chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]

def png_func(settings):
    try:
        from PIL import Image
    except:
        sys.exit("** could not import pillow library dependency\ntry:\n"
                 "   $ sudo apt-get install libopenjp2-7 libtiff5\n"
                 "   $ sudo pip3 install pillow")

    if not os.path.exists(settings.lightning_rpc):
        sys.exit("no such file? %s" % settings.lightning_rpc)
    if settings.image_no not in {0, 1, 2}:
        sys.exit("invalid image_no: %d" % settings.image_no)

    max_x = IMAGE_SIZES[settings.image_no]['width'] - 1
    max_y = IMAGE_SIZES[settings.image_no]['height'] - 1

    img = Image.open(settings.png_file)
    width, height = img.size
    rgb_raw = img.convert("RGBA")

    px_data = list(rgb_raw.getdata())

    pixels = []
    for h in range(height):
        for w in range(width):
            x = w + settings.x_offset
            if x > 255:
                continue
            y = h + settings.y_offset
            if y > 255:
                continue
            y = h + settings.y_offset
            idx = (h * width) + w
            r = px_data[idx][0]
            g = px_data[idx][1]
            b = px_data[idx][2]
            a = px_data[idx][3]
            # drop mostly transparent pixels
            if (a < 200):
                continue
            #print("r g b a: %d %d %d %d" % (r,g,b,a))
            rgb = "%02x%02x%02x" % (r, g, b)
            pixels.append(Pixel(x, y, rgb))

    #print([str(p) for p in pixels])

    print("total pixels: %d" % len(pixels))
    od = OnionDraw(settings.lightning_rpc, BANNANA_NODE, settings.image_no,
                   pixels)
    err = od.run()
    if err:
        sys.exit("something went wrong: %s" % err)
    print("success")


###############################################################################

parser = argparse.ArgumentParser(prog="onion-draw.py")

subparsers = parser.add_subparsers(title='subcommands',
                                   description='selects style of drawing',
                                   help='manually enter pixels or use .png')

manual = subparsers.add_parser('manual', help="draw manually specified pixels")
png = subparsers.add_parser('png',
                            help="draw from a provided .png file "
                                 "(requires that you install pillow "
                                 "and dependencies)")

manual.add_argument("lightning_rpc", type=str,
                    help="path to your c-lightning rpc file for sending calls")
manual.add_argument("image_no", type=int,
                    help="image number to draw to (0, 1, or 2)")
manual.add_argument('pixel', nargs='+',
                    help="a list of one, two, three or four pixels to draw "
                         "in the format x,y,rgb, eg. 10,20,44ffee",
                    )
manual.set_defaults(func=manual_func)


png.add_argument("lightning_rpc", type=str,
                  help="path to your c-lightning rpc file for sending calls")
png.add_argument("image_no", type=int,
                    help="image number to draw to (0, 1, or 2)")
png.add_argument("x_offset", type=int,
                 help="the x coordinate to begin drawing at")
png.add_argument("y_offset", type=int,
                 help="the y coordinate to begin drawing at")
png.add_argument("png_file", type=str, help="the path to the png file to use")
png.set_defaults(func=png_func)

settings = parser.parse_args()

print(settings)
if hasattr(settings, "func"):
    settings.func(settings)
else:
    sys.exit("no subcommand?")
