#!/usr/bin/env python3
import os
import sys
import argparse

from bannerpunk.pixel import Pixel
from bannerpunk.onion_draw import OnionDraw


BANNERPUNK_NODE = "02e389d861acd9d6f5700c99c6c33dd4460d6f1e2f6ba89d1f4f36be85fc60f8d7"

JUKEBOX_NODE = "0379c41f28a38c49998fec42437db78a17af508fb19338e7360d7ffee2607ea036"

ROMPERT_NODE = "02ad6fb8d693dc1e4569bcedefadf5f72a931ae027dc0f0c544b34c1c6f3b9a02b"

BANNANA_NODE = "035c77dc0a10fe60e1304ae5b57d8fef87751add5d016b896d854fb706be6fc96c"

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

    od = OnionDraw(settings.lightning_rpc, BANNERPUNK_NODE, settings.image_no,
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
    od = OnionDraw(settings.lightning_rpc, BANNERPUNK_NODE, settings.image_no,
                   pixels)
    err = od.run()
    if err:
        sys.exit("something went wrong: %s" % err)
    print("success")


###############################################################################

parser = argparse.ArgumentParser(prog="onion-draw.py")


parser.add_argument("lightning_rpc", type=str,
                    help="path to your c-lightning rpc file for sending calls")
parser.add_argument("image_no", type=int,
                    help="image number to draw to (0, 1, or 2)")

subparsers = parser.add_subparsers(title='subcommands',
                                   description='selects style of drawing',
                                   help='manually enter pixels or use .png')

manual = subparsers.add_parser('manual', help="draw manually specified pixels")
png = subparsers.add_parser('png',
                            help="draw from a provided .png file "
                                 "(requires that you install pillow "
                                 "and dependencies)")

#manual.add_argument("lightning_rpc", type=str,
#                    help="path to your c-lightning rpc file for sending calls")
manual.add_argument('pixel', nargs='+',
                    help="a list of one, two, three or four pixels to draw "
                         "in the format x,y,rgb, eg. 10,20,44ffee",
                    )
manual.set_defaults(func=manual_func)


#png.add_argument("image_no", type=int,
#                    help="image number to draw to (0, 1, or 2)")

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
