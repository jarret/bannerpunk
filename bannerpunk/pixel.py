import string

MAX_X = 255
MAX_Y = 255

class Pixel(object):
    def __init__(self, x, y, rgb):
        assert x <= MAX_X
        assert x >= 0
        assert y <= MAX_Y
        assert y >= 0
        assert len(rgb) == 6
        for c in rgb:
            assert c in string.hexdigits

        self.x = x
        self.y = y
        self.rgb = rgb

    def __str__(self):
        return "(%d,%d,%s)" % (self.x, self.y, self.rgb)

    def from_string(pixel_str):
        if pixel_str[0] != "(":
            return None
        if pixel_str[-1] != ")":
            return None
        l = pixel_str[1:-1].split(",")
        if len(l) != 3:
            return None
        try:
            x = int(l[0])
            y = int(l[1])
        except:
            return None
        rgb = l[2]
        if x < 0:
            return None
        if x > MAX_X:
            return None
        if y < 0:
            return None
        if y > MAX_Y:
            return None
        if len(rgb) != 6:
            return None
        for c in rgb:
            if c not in string.hexdigits:
                return None
        return Pixel(x, y, rgb)

    def from_bin(pixel_bin):
        x_bin = pixel_bin[0:1]
        x = int.from_bytes(x_bin, byteorder='big')
        y_bin = pixel_bin[1:2]
        y = int.from_bytes(y_bin, byteorder='big')
        rgb_bin = pixel_bin[2:5]
        rgb = rgb_bin.hex()
        return Pixel(x, y, rgb)

    def to_bin(self):
        x_bin = self.x.to_bytes(1, byteorder='big')
        y_bin = self.y.to_bytes(1, byteorder='big')
        rgb_bin = bytearray.fromhex(self.rgb)
        return x_bin + y_bin + rgb_bin
