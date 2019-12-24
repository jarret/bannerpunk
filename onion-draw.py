#!/usr/bin/env python3
import time
import os
import sys
import uuid
import json
import pprint
import argparse
from pyln.client import LightningRpc, Millisatoshi

from bannerpunk.print import chill_blue_str, chill_green_str, chill_yellow_str
from bannerpunk.print import chill_purple_str
from bannerpunk.pixel import Pixel
from bannerpunk.images import IMAGE_SIZES
from bannerpunk.hop_payload import BannerPunkHopPayload

from bolt.hop_payload import LegacyHopPayload, TlvHopPayload

BANNERPUNK_NODE = "02e389d861acd9d6f5700c99c6c33dd4460d6f1e2f6ba89d1f4f36be85fc60f8d7"

JUKEBOX_NODE = "0379c41f28a38c49998fec42437db78a17af508fb19338e7360d7ffee2607ea036"

ROMPERT_NODE = "02ad6fb8d693dc1e4569bcedefadf5f72a931ae027dc0f0c544b34c1c6f3b9a02b"

RISK_FACTOR = 10

SELF_PAYMENT = 1000 # in millisatoshis

CLTV_FINAL = 10

class OnionDraw(object):
    def __init__(self, lightning_rpc, dst_node, pixels):
        self.dst_node = dst_node
        self.pixels = pixels
        self.n_pixels = len(self.pixels)
        self.dst_payment = 1000 * self.n_pixels

        self.rpc = LightningRpc(lightning_rpc)

    def print_dict(self, info):
        pprint.pprint(info)

    def get_myid_blockheight(self):
        info = self.rpc.getinfo()
        return info['id'], info['blockheight']

    def create_invoice(self):
        msatoshi = SELF_PAYMENT
        label = str(uuid.uuid4())
        description = "circular onion payment for bannerpunk"
        return self.rpc.invoice(msatoshi, label, description)

    def get_payment_secret(self, bolt11):
        decoded = self.rpc.decodepay(bolt11)
        return decoded['payment_secret']

    def get_outgoing_route(self):
        try:
            return self.rpc.getroute(self.dst_node,
                                     SELF_PAYMENT + self.dst_payment,
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

    def assemble_circular(self, outgoing, returning):
        route = outgoing['route'] + returning['route']
        self.rework_routing_fees(route, self.dst_node, self.dst_payment)
        return route

    def encode_non_final_payload(self, style, pubkey, channel, msatoshi,
                                 blockheight, delay):
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
                                                          channel, self.pixels)
            else:
                p = TlvHopPayload.encode_non_final(msatoshi,
                                                   blockheight + delay,
                                                   channel)
            return {'style':   "tlv",
                    'pubkey':  pubkey,
                    'payload': p.hex()}

    def encode_final_payload(self, style, pubkey, channel, msatoshi,
                             blockheight, delay, payment_secret):
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
                                                      msatoshi, self.pixels)
            else:
                p = TlvHopPayload.encode_final(msatoshi, blockheight + delay,
                                               payment_secret=payment_secret,
                                               total_msat=msatoshi)
            return {'style':   "tlv",
                    'pubkey':  pubkey,
                    'payload': p.hex()}

    def iter_hops(self, circular, blockheight, payment_secret):
        for i in range(len(circular) - 1):
            src = circular[i]
            dst = circular[i + 1]
            yield self.encode_non_final_payload(src['style'], src['id'],
                                                dst['channel'], dst['msatoshi'],
                                                blockheight, dst['delay'])
        dst = circular[-1]
        yield self.encode_final_payload(dst['style'], dst['id'], dst['channel'],
                                        dst['msatoshi'], blockheight,
                                        dst['delay'], payment_secret)

    def assemble_hops(self, circular, blockheight, payment_secret):
        return list(self.iter_hops(circular, blockheight, payment_secret))

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

    def send_pay_on_route(self, route, payment_hash, bolt11):
        self.print_dict(route)
        pay_result = self.rpc.sendpay(route, payment_hash)
        self.print_dict(pay_result)
        for _ in range(3):
            pay = self.rpc.listsendpays(bolt11)['payments'][0]
            if pay['status'] != "complete":
                return None
            time.sleep(1)
        return "payment did not complete"

    def run(self):
        myid, blockheight = self.get_myid_blockheight()
        print("myid: %s, blockheight %s" % (chill_yellow_str(myid),
                                            chill_green_str(myid)))
        invoice = self.create_invoice()
        payment_hash = invoice['payment_hash']
        bolt11 = invoice['bolt11']
        payment_secret = self.get_payment_secret(bolt11)
        print("bolt11: %s\npayment_secret: %s" % (
            chill_green_str(bolt11), chill_blue_str(payment_secret)))

        outgoing = self.get_outgoing_route()
        if not outgoing:
            return "could not get outgoing route"
        print("outgoing:")
        self.print_dict(outgoing)

        returning = self.get_returning_route(myid)
        if not returning:
            return "could not get returning route"
        print("returning:")
        self.print_dict(returning)

        circular = self.assemble_circular(outgoing, returning)
        print("circular:")
        self.print_dict(circular)

        hops = self.assemble_hops(circular, blockheight, payment_secret)
        print("hops:")
        self.print_dict(hops)

        onion, shared_secrets = self.create_onion(hops, payment_hash)
        print("onion: %s" % chill_purple_str(onion))
        print("shared_secrets: %s" % chill_yellow_str(str(shared_secrets)))

        send_result = self.send_onion(onion, circular, payment_hash,
                                      shared_secrets)
        print("send result: %s" % chill_yellow_str(str(send_result)))

        #try:
        #    circular = self.assemble_circular(outgoing, returning)
        #    err = self.send_pay_on_route(circular, payment_hash, bolt11)
        #    if err:
        #        return err
        #except:
        #    return "problem paying circular"

        print("payment succeded!")
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


    bp = OnionDraw(settings.lightning_rpc, BANNERPUNK_NODE, pixels)
    err = bp.run()
    if err:
        sys.exit("something went wrong: %s" % err)

###############################################################################

#def divide_chunks(l, n):
#    for i in range(0, len(l), n):
#        yield l[i:i + n]
#
#def png_func(settings):
#    try:
#        from PIL import Image
#    except:
#        sys.exit("** could not import pillow library dependency\ntry:\n"
#                 "   $ sudo apt-get install libopenjp2-7 libtiff5\n"
#                 "   $ sudo pip3 install pillow")
#
#    if not os.path.exists(settings.lightning_rpc):
#        sys.exit("no such file? %s" % settings.lightning_rpc)
#    if settings.image_no not in {0, 1, 2}:
#        sys.exit("invalid image_no: %d" % settings.image_no)
#
#    max_x = IMAGE_SIZES[settings.image_no]['width'] - 1
#    max_y = IMAGE_SIZES[settings.image_no]['height'] - 1
#
#    img = Image.open(settings.png_file)
#    width, height = img.size
#    rgb_raw = img.convert("RGB")
#
#    px_data = list(rgb_raw.getdata())
#
#    pixels = []
#    for h in range(height):
#        for w in range(width):
#            x = w + settings.x_offset
#            if x > max_x:
#                sys.exit("cannot draw on x coord %d, out of bounds" % x)
#            y = h + settings.y_offset
#            if y > max_y:
#                sys.exit("cannot draw on y coord %d, out of bounds" % y)
#            y = h + settings.y_offset
#            rgb = "%02x%02x%02x" % px_data[(h * width) + w]
#            pixels.append(Pixel(x, y, rgb))
#
#    #print([str(p) for p in pixels])
#
#
#    preimages = []
#    for pixel_chunk in divide_chunks(pixels, 4):
#        preimages.append(Preimage(settings.image_no, pixel_chunk))
#    print(preimages)
#    for preimage in preimages:
#        bp = BannerpunkCLightningPayment(settings.lightning_rpc, preimage)
#        err = bp.run()
#        if err:
#            sys.exit("something went wrong: %s" % err)


parser = argparse.ArgumentParser(prog="c-lightning-draw.py")

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


#png.add_argument("lightning_rpc", type=str,
#                  help="path to your c-lightning rpc file for sending calls")
#png.add_argument("image_no", type=int,
#                    help="image number to draw to (0, 1, or 2)")
#png.add_argument("x_offset", type=int,
#                 help="the x coordinate to begin drawing at")
#png.add_argument("y_offset", type=int,
#                 help="the y coordinate to begin drawing at")
#png.add_argument("png_file", type=str, help="the path to the png file to use")
#png.set_defaults(func=png_func)

settings = parser.parse_args()

print(settings)
if hasattr(settings, "func"):
    settings.func(settings)
else:
    sys.exit("no subcommand?")
