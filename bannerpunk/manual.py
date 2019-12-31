import sys
from bannerpunk.pixel import Pixel

class ArgToPixels:
    def __init__(self, pixel_arg):
        self.pixel_arg = pixel_arg

    def iter_pixels(self):
        for pixel in self.pixel_arg:
            yield Pixel.from_string("(" + pixel + ")")
