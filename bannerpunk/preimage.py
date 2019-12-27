import os
import hashlib
import string

from bannerpunk.images import IMAGE_SIZES
from bannerpunk.pixel import Pixel

class Preimage(object):
    def __init__(self, image_no, pixels):
        assert image_no >= 0
        assert image_no <= 2
        assert len(pixels) > 0
        assert len(pixels) <= 4
        self.image_no = image_no
        self.pixels = pixels
        self.n_pixels = len(pixels)

    def __str__(self):
        return ("image_no: %d, " % self.image_no +
                "[" + ",".join(str(p) for p in self.pixels) + "]")

    def from_bin(preimage_bin):
        first = int.from_bytes(preimage_bin[0:1], byteorder="big")
        image_no = (first & 0xf0) >> 4
        n_pixels = first & 0x0f
        if n_pixels == 0:
            #print("zero pixels")
            return None

        payload = preimage_bin[0:21]
        #print("payload: %s" % payload.hex())
        checksum = preimage_bin[21:24]
        #print("checksum: %s" % checksum.hex())
        if not Preimage.checksum_matches(payload, checksum):
            #print("bad preimage_bin checksum")
            return None


        pixels = []
        pixels = [Pixel.from_bin(preimage_bin[1:6])]
        if n_pixels > 1:
            pixels.append(Pixel.from_bin(preimage_bin[6:11]))
        if n_pixels > 2:
            pixels.append(Pixel.from_bin(preimage_bin[11:16]))
        if n_pixels == 4:
            pixels.append(Pixel.from_bin(preimage_bin[16:21]))

        if not Preimage.pixels_inside_image(image_no, pixels):
            print("pixels outside image dimensions")
            return None
        #for p in pixels:
        #    print("pixel: %s" % str(p))
        return Preimage(image_no, pixels)

    def pixels_inside_image(image_no, pixels):
        width = IMAGE_SIZES[image_no]['width']
        height = IMAGE_SIZES[image_no]['height']

        for p in pixels:
            if p.x >= width:
                return False
            if p.y >= height:
                return False
        return True

    def from_hex(preimage_hex):
        return Preimage.from_bin(bytearray.fromhex(preimage_hex))

    def do_checksum(payload):
        digest = hashlib.sha256(payload).digest()
        return digest[0:3]

    def checksum_matches(payload, checksum):
        #print("payload: %s" % payload.hex())
        #print("checksum: %s" % checksum.hex())
        calc_checksum = Preimage.do_checksum(payload)
        #print("calc_checksum: %s" % calc_checksum.hex())
        return calc_checksum == checksum

    def first_byte(self):
        #print("image_no: %d" % self.image_no)
        #print("n_pixels: %d" % self.n_pixels)
        val = (self.image_no << 4) + self.n_pixels
        #print("val: %d" % val)
        return val.to_bytes(1, byteorder='big')

    def noise_slug(self, n_bytes):
        return os.urandom(n_bytes)

    def to_bin(self):
        first = self.first_byte()
        p1_slug = self.pixels[0].to_bin()
        p2_slug = (self.pixels[1].to_bin() if self.n_pixels > 1 else
                   self.noise_slug(5))
        p3_slug = (self.pixels[2].to_bin() if self.n_pixels > 2 else
                   self.noise_slug(5))
        p4_slug = (self.pixels[3].to_bin() if self.n_pixels > 3 else
                   self.noise_slug(5))
        payload = first + p1_slug + p2_slug + p3_slug + p4_slug
        #print("len payload: %d" % len(payload))
        checksum = Preimage.do_checksum(payload)
        #print("len checksum: %d" % len(checksum))
        end_slug = self.noise_slug(8)
        #print("len end_slug: %d" % len(end_slug))
        return payload + checksum + end_slug

    def to_hex(self):
        return self.to_bin().hex()

