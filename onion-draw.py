#!/usr/bin/env python3
import os
import sys
import argparse

from bannerpunk.draw import Draw
from bannerpunk.png import PngToPixels
from bannerpunk.manual import ManualToPixels

from pyln.client import LightningRpc


NODE = "02e389d861acd9d6f5700c99c6c33dd4460d6f1e2f6ba89d1f4f36be85fc60f8d7"
#NODE = "035c77dc0a10fe60e1304ae5b57d8fef87751add5d016b896d854fb706be6fc96c"

###############################################################################

def manual_func(s, rpc):
    ap = ManualToPixels(s.pixels)
    pixels, err = ap.parse_pixels()
    if err:
        return err
    d = Draw(rpc, NODE, s.image_no, pixels)
    return d.run()

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
    d = Draw(rpc, NODE, s.image_no, pixels)
    return d.run()

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

manual.add_argument('pixels', type=str,
                    help="a string specifying coordinates and colors of "
                         "pixels to draw separated by underscores. "
                         "Eg. 1_1_ffffff_2_2_00ff00 will set pixel "
                         "(1,1) white (#ffffff) and (2,2) green (#00ff00)")
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
