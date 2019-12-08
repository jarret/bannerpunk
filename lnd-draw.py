#!/usr/bin/env python3
import time
import sys
import os
import uuid
import json
import pprint
import argparse
import subprocess
from lightning import LightningRpc, Millisatoshi

from bannerpunk.pixel_preimage import Pixel, Preimage
from bannerpunk.images import IMAGE_SIZES

BANNERPUNK_NODE = "02e389d861acd9d6f5700c99c6c33dd4460d6f1e2f6ba89d1f4f36be85fc60f8d7"

#BANNERPUNK_NODE = "0379c41f28a38c49998fec42437db78a17af508fb19338e7360d7ffee2607ea036"

SELF_PAYMENT = 1 # in satoshis

class BannerpunkLndPayment(object):
    def __init__(self, lncli_executable, preimage):
        self.n_pixels = preimage.n_pixels
        self.dst_payment = 1 * self.n_pixels
        self.preimage = preimage.to_hex()
        self.lncli = os.path.abspath(lncli_executable)

    def send_to_route(self, route, payment_hash):
        route_str = json.dumps(route)
        arg_list = [self.lncli, "sendtoroute", "--payment_hash", payment_hash,
                    "--routes", route_str]
        p = subprocess.Popen(arg_list, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        outs, errs = p.communicate(timeout=15)
        if errs:
            return None, "error: %s" % errs
        else:
            return json.loads(outs), None

    def create_invoice(self):
        arg_list = [self.lncli, "addinvoice", str(SELF_PAYMENT), self.preimage]
        p = subprocess.Popen(arg_list, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        outs, errs = p.communicate(timeout=15)
        if errs:
            return None, "error: %s" % errs
        else:
            return json.loads(outs), None


    def rework_routing_fees(self, route, target, target_fee):
        for hop in reversed(route['route']['hops']):
            hop['amt_to_forward_msat'] -= (target_fee * 1000)
            hop['amt_to_forward'] -= target_fee
            #print("hop: %s" % hop)
            if hop['pub_key'] == target:
                break
        return route

    def build_route(self, hops, amount):
        arg_list = [self.lncli, "buildroute", "--amt", str(amount), "--hops",
                    ",".join(hops)]
        p = subprocess.Popen(arg_list, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        outs, errs = p.communicate(timeout=15)
        if errs:
            return None, "error: %s" % errs
        else:
            return json.loads(outs), None


    def get_my_id(self):
        arg_list = [self.lncli, "getinfo"]
        p = subprocess.Popen(arg_list, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        outs, errs = p.communicate(timeout=15)
        if errs:
            return None, "error: %s" % errs
        else:
            return json.loads(outs)['identity_pubkey'], None

    def queryroutes(self, dst, amount):
        arg_list = [self.lncli, "queryroutes", str(dst), str(amount)]
        p = subprocess.Popen(arg_list, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        outs, errs = p.communicate(timeout=15)
        if errs:
            return None, "error: %s" % errs
        else:
            return json.loads(outs), None

    def get_outgoing_route(self, dst, amount):
        try:
            q, err = self.queryroutes(dst, amount)
            if err:
                print("could not find route to %s" % (dst))
                return None
            #print("q r: %s" % q['routes'])
            routes = sorted(q['routes'],key=lambda x: int(x['total_fees_msat']))
            if len(routes) == 0:
                print("could not find route to %s" % (dst))
                return None
            cheapest_route = routes[0]
            return cheapest_route
        except Exception as e:
            print(e)
            print("could not find route from self to %s" % (dst))
            return None

    def get_circular_hops(self, cheap_route):
        my_id, err = self.get_my_id()
        if err:
            return None
        hop_ids = [h['pub_key'] for h in cheap_route['hops']]
        return_ids = list(reversed(hop_ids[:-1])) + [my_id]
        return hop_ids + return_ids

    def run(self):
        invoice, err = self.create_invoice()
        if err:
            return "could not create index"
        print(invoice)
        payment_hash = invoice['r_hash']
        #sys.exit("pause")

        amount = SELF_PAYMENT + self.dst_payment
        outgoing = self.get_outgoing_route(BANNERPUNK_NODE, amount)
        if not outgoing:
            return "could not get outgoing"
        #print("outgoing: %s" % json.dumps(outgoing, indent=1))

        circular_hops = self.get_circular_hops(outgoing)
        if circular_hops is None:
            return "could not get circular hops"
        #print("circular hops: %s" % json.dumps(circular_hops, indent=1))
        built_route, err = self.build_route(circular_hops, amount)
        if err:
            return err
        #print("built_route: %s" % json.dumps(built_route, indent=1))
        reworked_route = self.rework_routing_fees(built_route, BANNERPUNK_NODE,
                                                  self.dst_payment)
        #print("reworked_route: %s" % json.dumps(reworked_route, indent=1))

        send, err = self.send_to_route(reworked_route, payment_hash)
        if err:
            return err
        #print("send: %s" % json.dumps(send, indent=1))
        print("payment succeeded!")
        return None

###############################################################################

def manual_func(settings):
    print("manual_func")
    if not os.path.exists(settings.lncli_executable):
        sys.exit("no such file? %s" % settings.lncli_executable)
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
    bp = BannerpunkLndPayment(settings.lncli_executable, preimage)
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

    if not os.path.exists(settings.lncli_executable):
        sys.exit("no such file? %s" % settings.lncli_executable)
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
    #print(preimages)
    for preimage in preimages:
        bp = BannerpunkLndPayment(settings.lncli_executable, preimage)
        err = bp.run()
        if err:
            sys.exit("something went wrong: %s" % err)


parser = argparse.ArgumentParser(prog="lnd-draw.py")

subparsers = parser.add_subparsers(title='subcommands',
                                   description='selects style of drawing',
                                   help='manually enter pixels or use .png')

manual = subparsers.add_parser('manual', help="draw manually specified pixels")
png = subparsers.add_parser('png',
                            help="draw from a provided .png file "
                                 "(requires that you install pillow "
                                 "and dependencies)")

manual.add_argument("lncli_executable", type=str,
                    help="path to the lncli executable for interfacing "
                         "with lnd")
manual.add_argument("image_no", type=int,
                    help="image number to draw to (0, 1, or 2)")
manual.add_argument('pixel', nargs='+',
                    help="a list of one, two, three or four pixels to draw "
                         "in the format x,y,rgb, eg. 10,20,44ffee",
                    )
manual.set_defaults(func=manual_func)


png.add_argument("lncli_executable", type=str,
                    help="path to the lncli executable for interfacing "
                         "with lnd")
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

