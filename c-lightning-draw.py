#!/usr/bin/env python3
import time
import os
import uuid
import json
import pprint
import argparse
from lightning import LightningRpc, Millisatoshi

from bannerpunk.pixel_preimage import Pixel, Preimage
from bannerpunk.images import IMAGE_SIZES

BANNERPUNK_NODE = "02e389d861acd9d6f5700c99c6c33dd4460d6f1e2f6ba89d1f4f36be85fc60f8d7"

RISK_FACTOR = 10

SELF_PAYMENT = 1000

CLTV_FINAL = 10

class BannerpunkPayment(object):
    def __init__(self, lightning_rpc, preimage):
        self.n_pixels = preimage.n_pixels
        self.dst_payment = 1000 * self.n_pixels
        self.preimage = preimage.to_hex()
        self.rpc = LightningRpc(lightning_rpc)

    def print_dict(self, info):
        pprint.pprint(info)

    def get_myid(self):
        info = self.rpc.getinfo()
        return info['id']

    def create_invoice(self):
        msatoshi = SELF_PAYMENT
        label = str(uuid.uuid4())
        description = "circular payment for bannerpunk"
        return self.rpc.invoice(msatoshi, label, description,
                                preimage=self.preimage)

    def get_outgoing_route(self):
        try:
            return self.rpc.getroute(BANNERPUNK_NODE,
                                     SELF_PAYMENT + self.dst_payment,
                                     RISK_FACTOR)
        except:
            print("could not find route from self to %s" % (BANNERPUNK_NODE))
            return None

    def get_returning_route(self, myid):
        try:
            return self.rpc.getroute(myid, SELF_PAYMENT, RISK_FACTOR,
                                     fromid=BANNERPUNK_NODE)
        except:
            print("could not find route from %s to %s" % (BANNERPUNK_NODE,
                                                         myid))
            return None

    def setup_routing_fee(self, route):
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
            if ch['source'] == BANNERPUNK_NODE:
                fee += self.dst_payment
            msatoshi += fee
            delay += ch['delay']
            r['direction'] = int(ch['channel_flags']) % 2

    def assemble_circular(self, outgoing, returning):
        route = outgoing['route'] + returning['route']
        self.setup_routing_fee(route)
        return route

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
        myid = self.get_myid()
        print(myid)
        invoice = self.create_invoice()
        self.print_dict(invoice)
        payment_hash = invoice['payment_hash']
        bolt11 = invoice['bolt11']

        outgoing = self.get_outgoing_route()
        if not outgoing:
            return "could not get outgoing route"
        self.print_dict(outgoing)

        returning = self.get_returning_route(myid)
        if not returning:
            return "could not get returning route"
        self.print_dict(returning)

        try:
            circular = self.assemble_circular(outgoing, returning)
            err = self.send_pay_on_route(circular, payment_hash, bolt11)
            if err:
                return err
        except:
            return "problem paying circular"

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

    preimage = Preimage(settings.image_no, pixels)
    print(preimage)
    print(preimage.to_hex())
    bp = BannerpunkPayment(settings.lightning_rpc, preimage)
    err = bp.run()
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
    rgb_raw = img.convert("RGB")

    px_data = list(rgb_raw.getdata())

    pixels = []
    for h in range(height):
        for w in range(width):
            x = w + settings.x_offset
            if x > max_x:
                sys.exit("cannot draw on x coord %d, out of bounds" % x)
            y = h + settings.y_offset
            if y > max_y:
                sys.exit("cannot draw on y coord %d, out of bounds" % y)
            y = h + settings.y_offset
            rgb = "%02x%02x%02x" % px_data[(h * width) + w]
            pixels.append(Pixel(x, y, rgb))

    #print([str(p) for p in pixels])


    preimages = []
    for pixel_chunk in divide_chunks(pixels, 4):
        preimages.append(Preimage(settings.image_no, pixel_chunk))
    print(preimages)
    for preimage in preimages:
        bp = BannerpunkPayment(settings.lightning_rpc, preimage)
        err = bp.run()
        if err:
            sys.exit("something went wrong: %s" % err)


parser = argparse.ArgumentParser(prog="c-lightning-draw.py")

subparsers = parser.add_subparsers(title='subcommands',
                                   description='valid subcommands',
                                   help='additional help')
manual = subparsers.add_parser('manual', help="draw manually specified pixels")
png = subparsers.add_parser('png',
                            help="draw from a provided .png file "
                                 "(requires that you install pillow "
                                 "and dependencies)")

manual.add_argument("lightning_rpc", type=str,
                    help="pay to your c-lightning rpc file for sending calls")
manual.add_argument("image_no", type=int,
                    help="image number to draw to (0, 1, or 2)")
manual.add_argument('pixel', nargs='+',
                    help="a list of one, two, three or four pixels to draw "
                         "in the format x,y,rgb, eg. 10,20,44ffee",
                    )
manual.set_defaults(func=manual_func)


png.add_argument("lightning_rpc", type=str,
                  help="pay to your c-lightning rpc file for sending calls")
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

settings.func(settings)

