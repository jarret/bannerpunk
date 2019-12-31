#!/usr/bin/env python3
import os
import sys
import argparse

from bannerpunk.onion_draw import OnionDraw
from bannerpunk.png import PngToPixels
from bannerpunk.manual import ArgToPixels

from pyln.client import LightningRpc


NODE = "02e389d861acd9d6f5700c99c6c33dd4460d6f1e2f6ba89d1f4f36be85fc60f8d7"
#NODE = "035c77dc0a10fe60e1304ae5b57d8fef87751add5d016b896d854fb706be6fc96c"

###############################################################################

def manual_func(s, rpc):
    ap = ArgToPixels(s.pixel)
    pixels = list(ap.iter_pixels())
    if len([p for p in pixels if p != None]) != len(pixels):
        return "could not parse pixels"
    od = OnionDraw(rpc, NODE, s.image_no, pixels)
    return od.run()

def png_func(s, rpc):
    try:
        from PIL import Image
    except:
        return ("\n*** couldn't find pillow library dependency for png images\n"
                "try:\n"
                "  $ sudo apt-get install libopenjp2-7 libtiff5\n"
                "  $ sudo pip3 install pillow")
    if not os.path.exists(s.png_file):
        return "no such file? %s" % s.png_file

    pp = PngToPixels(s.image_no, s.png_file)
    pixels = list(pp.iter_at_offset(s.x_offset, s.y_offset))
    od = OnionDraw(rpc, NODE, s.image_no, pixels)
    return od.run()

###############################################################################

parser = argparse.ArgumentParser(prog="onion-draw.py")
parser.add_argument("lightning_rpc", type=str,
                    help="path to your c-lightning rpc file for sending calls")
parser.add_argument("image_no", type=int,
                    help="image number to draw to (0, 1, or 2)")
parser.add_argument("-n", "--node", type=str,
                    help="destination node for pixel payload"
                         "(default = the 'official' BannerPunk node")

subparsers = parser.add_subparsers(title='subcommands',
                                   description='selects style of drawing',
                                   help='manually enter pixels or use .png')

manual = subparsers.add_parser('manual', help="draw manually specified pixels")
png = subparsers.add_parser('png',
                            help="draw from a provided .png file "
                                 "(requires that you install pillow "
                                 "and dependencies)")

manual.add_argument('pixel', nargs='+',
                    help="a list of one, two, three or four pixels to draw "
                         "in the format x,y,rgb, eg. 10,20,44ffee")
manual.set_defaults(func=manual_func)

png.add_argument("x_offset", type=int,
                 help="the x coordinate to begin drawing at")
png.add_argument("y_offset", type=int,
                 help="the y coordinate to begin drawing at")
png.add_argument("png_file", type=str, help="the path to the png file to use")
png.set_defaults(func=png_func)

settings = parser.parse_args()


if settings.image_no not in {0, 1, 2}:
    sys.exit("invalid image_no: %d" % settings.image_no)
if not os.path.exists(settings.lightning_rpc):
    sys.exit("no such file? %s" % settings.lightning_rpc)

rpc = LightningRpc(settings.lightning_rpc)

err = settings.func(settings, rpc)
if err:
    sys.exit(err)
