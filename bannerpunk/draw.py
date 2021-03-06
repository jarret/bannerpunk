import time
import uuid
import pprint

from bannerpunk.invoice import Invoice
from bannerpunk.onion import Onion


class Draw:
    def __init__(self, rpc, dst_node, art_no, pixels):
        self.rpc = rpc
        self.dst_node = dst_node
        self.art_no = art_no
        self.pixels = pixels

    ###########################################################################

    def _get_myid_blockheight(self):
        try:
            info = self.rpc.getinfo()
            return info['id'], info['blockheight'], None
        except:
            return None, None, "could not get id, block_height"

    def _payment_status(self, payment_hash):
        try:
            l = self.rpc.listsendpays(None, payment_hash)
            status = l['payments'][0]['status']
            return status
        except:
            return "error"

    def _send_onion(self, onion, first_hop, assoc_data, shared_secrets):
        label = str(uuid.uuid4())
        #print("send params: %s %s %s %s %s" % (onion, first_hop, assoc_data,
        #                                       label, shared_secrets))
        try:
            result = self.rpc.sendonion(onion, first_hop, assoc_data, label,
                                        shared_secrets)
            return result, None
        except:
            return None, "could not send onion"

    ###########################################################################

    def _draw_pixels(self, myid, block_height, pixels):
        invoice, err = Invoice(self.rpc).create_invoice()
        if err:
            return None, err
        onion_creator = Onion(self.rpc, myid, self.dst_node, block_height,
                              invoice, self.art_no, pixels)
        onion_result = onion_creator.fit_onion()
        if onion_result['status'] != "success":
            return None, onion_result['msg']
        fitted_pixels = onion_result['fitted_pixels']
        result, err = self._send_onion(onion_result['onion'],
                                       onion_result['first_hop'],
                                       onion_result['assoc_data'],
                                       onion_result['shared_secrets'])
        if err:
            return None, err
        if result['status'] not in {"pending", "complete"}:
            return None, "payment status not as expected after send"
        if result['status'] == "complete":
            return result['fitted_pixels'], None
        print("waiting for payment completion")
        checks = 0
        while True:
            status = self._payment_status(onion_result['payment_hash'])
            if status == "complete":
                break
            checks += 1
            if checks == 10:
                return None, "payment didn't complete"
            print("sleeping waiting for payment to complete...")
            time.sleep(2.0)
        return onion_result['fitted_pixels'], None

    def _draw_loop(self, myid, block_height):
        pixels = self.pixels
        while True:
            pixels_drawn, err = self._draw_pixels(myid, block_height, pixels)
            if err:
                return err
            if pixels_drawn:
                pixels = pixels[pixels_drawn:]
            if len(pixels) == 0:
                print("all pixels drawn")
                return None

    ###########################################################################

    def run(self):
        myid, block_height, err = self._get_myid_blockheight()
        if err:
            return err
        print("myid: %s, block_height %s" % (myid, block_height))
        try:
            err = self._draw_loop(myid, block_height)
            if err:
                return err
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return None, "error while buying pixels: %s" % e
        return None
