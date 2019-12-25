import os
import time
import mmap


PIXEL_RECORD_SIZE = 3

class ArtDb(object):
    def __init__(self, width, height, image_no, art_db_dir):
        if not os.path.exists(art_db_dir):
            os.makedirs(art_db_dir)
        self.image_no = image_no
        self.art_db_dir = art_db_dir
        self.width = width
        self.height = height
        self.n_pixels = width * height
        self.size = PIXEL_RECORD_SIZE * self.n_pixels
        self.mmap_art_bin()


    def art_path(self):
        return os.path.join(self.art_db_dir, "image-%d.dat" % self.image_no)

    def update_log_path(self):
        return os.path.join(self.art_db_dir, "updates-%d.log" % self.image_no)

    ###########################################################################

    def mmap_file_init(self, path):
        file_ref = open(path, "wb")
        file_ref.write(bytearray(0xff.to_bytes(1, byteorder='big') * self.size))
        file_ref.close()

    ###########################################################################

    def mmap_art_bin(self):
        path = self.art_path()
        if not os.path.exists(path):
            self.mmap_file_init(path)
        self.file_ref = open(path, "r+b")
        self.bin = mmap.mmap(self.file_ref.fileno(), self.size)

    def unmap_art_bin(self):
        self.bin.flush()
        self.bin.close()
        self.file_ref.close()


    def log_new_preimage(self, preimage):
        path = self.update_log_path()
        s = "%0.4f preimage %s\n" % (time.time(), preimage.to_hex())
        f = open(path, "a")
        f.write(s)
        f.close()

    def log_payload(self, payload):
        path = self.update_log_path()
        s = "%0.4f payload %s\n" % (time.time(), payload)
        f = open(path, "a")
        f.write(s)
        f.close()

    def map_byte(self, x, y):
        return ((x * PIXEL_RECORD_SIZE * self.height) +
                (y * PIXEL_RECORD_SIZE))

    def record_new_preimage(self, preimage):
        for p in preimage.pixels:
            x = p.x
            y = p.y

            byte = self.map_byte(p.x, p.y)
            rgb = p.to_bin()[2:]
            assert len(rgb) == PIXEL_RECORD_SIZE
            self.bin[byte:byte + PIXEL_RECORD_SIZE] = rgb
        self.log_new_preimage(preimage)
        self.bin.flush()

    def record_pixels(self, payload, pixels):
        for p in pixels:
            x = p.x
            y = p.y

            byte = self.map_byte(p.x, p.y)
            rgb = p.to_bin()[2:]
            assert len(rgb) == PIXEL_RECORD_SIZE
            self.bin[byte:byte + PIXEL_RECORD_SIZE] = rgb
        self.log_payload(payload)
        self.bin.flush()

    def to_bin(self):
        return bytes(self.bin)
