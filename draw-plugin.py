#!/usr/bin/env python3
import os
from pyln.client import Plugin

from bannerpunk.pixel import Pixel
from bannerpunk.png import PngToPixels
from bannerpunk.draw import Draw


plugin = Plugin()

@plugin.init()
def init(options, configuration, plugin, **kwargs):
    node = plugin.get_option("bannerpunk_node")
    plugin.log("initialzed to draw to %s" % node)


###############################################################################

def parse_pixel_args(image_no_string, pixels_string):
    try:
        image_no = int(image_no_string)
    except:
        return None, None, "could not parse %s" % image_no_string

    string_tokens = pixels_string.split("_")
    if len(string_tokens) == 0:
        return None, None, "no pixels given"
    if len(string_tokens) % 3 != 0:
        return None, None, "could not parse %s as pixels" % pixels
    pixels = []
    for i in range(0, len(string_tokens), 3):
        pixel_tokens = string_tokens[i:i+3]
        try:
            x = int(pixel_tokens[0])
            y = int(pixel_tokens[1])
            rgb = pixel_tokens[2]
            pixel = Pixel(x, y, rgb)
        except:
            return None, None, "could not interpret %s as pixel" % pixel_tokens
        pixels.append(pixel)
    return image_no, pixels, None

@plugin.method("draw_pixels")
def draw_pixels(plugin, image_no, pixels):
    """Draws manually-specified pixels to BannerPunk
        image_no - specifies the image number to draw to
        pixels - is a string that specifies the x,y cordinates and RGB colors
            eg. 1_1_ffffff will set the pixel at coordinate at (1, 1) to
                white #ffffff
                1_1_00ff00_2_2_00ff00 will set the pixels at coordinates
                (1, 1) and (2,2) to green #00ff00
    """
    image_no, pixels, err = parse_pixel_args(image_no, pixels)
    if err:
        return err

    plugin.log("image_no: %s" % image_no)
    plugin.log("pixels: %s" % [str(p) for p in pixels])

    node = plugin.get_option("bannerpunk_node")
    d = Draw(plugin.rpc, node, image_no, pixels)
    err = d.run()
    if err:
        return err
    return "finished drawing %d pixels" % len(pixels)

###############################################################################

def parse_png_args(image_no_string, x_offset_string, y_offset_string,
                   png_filename):
    try:
        image_no = int(image_no_string)
        x_offset = int(x_offset_string)
        y_offset = int(y_offset_string)
    except:
        return None, None, "could not parse args"
    if not os.path.exists(png_filename):
        return None, None, None, None, "no file at path: %s" % png_filename
    if not png_filename.endswith(".png"):
        return None, None, None, None, "not a png file: %s" % png_filename
    return image_no, x_offset, y_offset, png_filename, None

@plugin.method("draw_png")
def draw_png(plugin, image_no, x_offset, y_offset, png_filename):
    image_no, x_offset, y_offset, png_filename, err = parse_png_args(
        image_no, x_offset, y_offset, png_filename)
    if err:
        return err

    pp = PngToPixels(image_no, png_filename)
    pixels = list(pp.iter_at_offset(x_offset, y_offset))
    node = plugin.get_option("bannerpunk_node")
    d = Draw(plugin.rpc, node, image_no, pixels)
    err = d.run()
    if err:
        return err
    return "finished drawing %d pixels" % len(pixels)

###############################################################################

NODE = "02e389d861acd9d6f5700c99c6c33dd4460d6f1e2f6ba89d1f4f36be85fc60f8d7"

plugin.add_option("bannerpunk_node", NODE, "the node we are paying to draw to")
plugin.run()
