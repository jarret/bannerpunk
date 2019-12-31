import math
import time
import uuid
import pprint

from pyln.client import Millisatoshi

from bannerpunk.print import chill_blue_str, chill_green_str, chill_yellow_str
from bannerpunk.print import chill_purple_str
from bannerpunk.pixel import Pixel
from bannerpunk.hop_payload import BannerPunkHopPayload

from bolt.util import h2b
from bolt.hop_payload import LegacyHopPayload, TlvHopPayload


###############################################################################

INVOICE_DESCRIPTION = ("circular payment invoice to deliver BannerPunk "
                       "extension payload")
SELF_PAYMENT = 1000 # in millisatoshis

class Invoice:
    def __init__(self, rpc):
        self.rpc = rpc

    def get_payment_secret(self, bolt11):
        decoded = self.rpc.decodepay(bolt11)
        return decoded['payment_secret']

    def create_invoice(self):
        msatoshi = SELF_PAYMENT
        label = str(uuid.uuid4())
        description = INVOICE_DESCRIPTION
        invoice = self.rpc.invoice(msatoshi, label, description)
        invoice['payment_secret'] = self.get_payment_secret(invoice['bolt11'])
        return invoice


###############################################################################

RISK_FACTOR = 10
CLTV_FINAL = 10
PIXEL_BYTES = 5
ONION_SIZE = 1300
INITIAL_HOP_GUESS = 4

FIT_ONION_TRIES = 5

class Onion:
    def __init__(self, rpc, myid, dst_node, block_height, invoice, art_no,
                 available_pixels):
        self.rpc = rpc
        self.myid = myid
        self.dst_node = dst_node
        self.block_height = block_height
        self.invoice = invoice
        self.payment_secret = self.invoice['payment_secret']
        self.payment_hash = self.invoice['payment_hash']
        self.art_no = art_no
        self.available_pixels = available_pixels

    def estimate_routing_bytes(self, n_hops):
        # WARNING - this is a fudge, variable sizes can't easily be anticpated
        # hard to estmiate due to variable encoding
        # legacy payloads == 33 bytes + 32 byte hmac
        # tlv mid payloads ~= 18 bytes + 32 byte hmac
        # tlv final payloads ~= 46 bytes + 32 byte hmac
        if n_hops == 1:
            # destination is only hop
            return 46 + 32
        # assume along circular route, target mid hops and self is tlv
        # the rest are legacy
        est = 0
        # end tlv hop
        est += 46 + 32
        # target mid hop
        est += 18 + 32
        # other hops
        est += (33 + 32) * (n_hops - 2)
        return est + 10 # overestimate a bit

    def estimate_payload_pixels(self, n_hops):
        approx_bytes = ONION_SIZE - self.estimate_routing_bytes(n_hops)
        approx_pixels = math.floor(approx_bytes / PIXEL_BYTES)
        return approx_pixels - 3 # underestimate a bit

    def get_outgoing_route(self, dst_payment):
        try:
            return self.rpc.getroute(self.dst_node, SELF_PAYMENT + dst_payment,
                                     RISK_FACTOR)
        except:
            print("could not find route from self to %s" % (self.dst_node))
            return None

    def get_returning_route(self, myid):
        try:
            return self.rpc.getroute(myid, SELF_PAYMENT, RISK_FACTOR,
                                     fromid=self.dst_node)
        except:
            print("could not find route from %s to %s" % (self.dst_node,
                                                         myid))
            return None

    def rework_routing_fees(self, route, pay_dst, pay_msat):
        # Thanks to sendinvoiceless.py plugin for this logic!
        delay = int(CLTV_FINAL)
        msatoshi = Millisatoshi(SELF_PAYMENT)
        for r in reversed(route):
            r['msatoshi'] = msatoshi.millisatoshis
            r['amount_msat'] = msatoshi
            r['delay'] = delay
            channels = self.rpc.listchannels(r['channel'])
            ch = next(c for c in channels.get('channels') if
                      c['destination'] == r['id'])
            fee = Millisatoshi(ch['base_fee_millisatoshi'])
            # BOLT #7 requires fee >= fee_base_msat + ( amount_to_forward *
            # fee_proportional_millionths / 1000000 )
            fee += (msatoshi * ch['fee_per_millionth'] + 10**6 - 1) // 10**6
            # integer math trick to round up
            if ch['source'] == pay_dst:
                fee += pay_msat
            msatoshi += fee
            delay += ch['delay']
            r['direction'] = int(ch['channel_flags']) % 2

    def assemble_circular(self, outgoing, returning, dst_payment):
        route = outgoing['route'] + returning['route']
        self.rework_routing_fees(route, self.dst_node, dst_payment)
        return route

    def encode_non_final_payload(self, style, pubkey, channel, msatoshi,
                                 blockheight, delay, pixels):
        if style == "legacy":
            assert pubkey != self.dst_node, "can't send pixels to legacy hop"
            p = LegacyHopPayload.encode(channel, msatoshi, blockheight + delay)
            return {'style':   "legacy",
                    'pubkey':  pubkey,
                    'payload': p.hex()}

        else:
            if pubkey == self.dst_node:
                p = BannerPunkHopPayload.encode_non_final(msatoshi,
                                                          blockheight + delay,
                                                          channel, self.art_no,
                                                          pixels)
            else:
                p = TlvHopPayload.encode_non_final(msatoshi,
                                                   blockheight + delay,
                                                   channel)
            return {'style':   "tlv",
                    'pubkey':  pubkey,
                    'payload': p.hex()}

    def encode_final_payload(self, style, pubkey, channel, msatoshi,
                             blockheight, delay, payment_secret, pixels):
        if style == "legacy":
            assert pubkey != self.dst_node, "can't send pixels to legacy hop"
            p = LegacyHopPayload.encode(channel, msatoshi, blockheight + delay)
            return {'style':   "legacy",
                    'pubkey':  pubkey,
                    'payload': p.hex()}

        else:
            if pubkey == self.dst_node:
                p = BannerPunkHopPayload.encode_final(msatoshi,
                                                      blockheight + delay,
                                                      channel, payment_secret,
                                                      msatoshi, self.art_no,
                                                      pixels)
            else:
                p = TlvHopPayload.encode_final(msatoshi, blockheight + delay,
                                               payment_secret=payment_secret,
                                               total_msat=msatoshi)
            return {'style':   "tlv",
                    'pubkey':  pubkey,
                    'payload': p.hex()}

    def iter_hops(self, circular, blockheight, payment_secret, pixels):
        for i in range(len(circular) - 1):
            src = circular[i]
            dst = circular[i + 1]
            yield self.encode_non_final_payload(src['style'], src['id'],
                                                dst['channel'], dst['msatoshi'],
                                                blockheight, dst['delay'],
                                                pixels)
        dst = circular[-1]
        yield self.encode_final_payload(dst['style'], dst['id'], dst['channel'],
                                        dst['msatoshi'], blockheight,
                                        dst['delay'], payment_secret, pixels)

    def assemble_hops(self, circular, blockheight, payment_secret, pixels):
        return list(self.iter_hops(circular, blockheight, payment_secret,
                                   pixels))

    def calc_total_payload_size(self, hops):
        total = 0
        for hop in hops:
            payload_len = len(h2b(hop['payload']))
            hmac_len = 32
            total += payload_len + hmac_len
        return total

    def create_onion(self, hops, assocdata):
        result = self.rpc.createonion(hops, assocdata)
        return result['onion'], result['shared_secrets']

    def print_dict(self, info):
        pprint.pprint(info)

    def try_fit(self, hop_count, pixel_underestimate):
        # estimate a route that will probably fit into an onion
        will_fit = self.estimate_payload_pixels(hop_count)
        print("will_fit: %d" % will_fit)
        attempting_pixels = (min(will_fit, len(self.available_pixels)) -
                             pixel_underestimate)
        dst_payment = 1000 * attempting_pixels
        print("to draw: %d" % attempting_pixels)
        attempting_pixel_list = self.available_pixels[:attempting_pixels]

        # try to make a route that fulfils the estimate
        outgoing = self.get_outgoing_route(dst_payment)
        if not outgoing:
            return {'status': "err",
                    'msg':    "could not get outgoing route"}
        print("outgoing:")
        self.print_dict(outgoing)
        returning = self.get_returning_route(self.myid)
        if not returning:
            return {'status': "err",
                    'msg':    "could not get returning route"}
        print("returning:")
        self.print_dict(returning)

        # check to see if the route compares to our estimate
        needed_hops = len(outgoing) + len(returning)
        if needed_hops != hop_count:
            print("different hop count than expected, need to recalculate...")
            return {'status':              "retry",
                    "needed_hops":         needed_hops,
                    "pixel_underestimate": pixel_underestimate}

        # build the hop data for the circular route
        circular = self.assemble_circular(outgoing, returning, dst_payment)
        print("assembled circular route:")
        self.print_dict(circular)
        hops = self.assemble_hops(circular, self.block_height,
                                  self.payment_secret, attempting_pixel_list)
        print("hops:")
        self.print_dict(hops)

        # check to see if the hop payloads are too big
        if self.calc_total_payload_size(hops) > ONION_SIZE:
            print("payloads are too big, retrying with less pixels")
            return {'status':              "retry",
                    "needed_hops":         needed_hops,
                    "pixel_underestimate": pixel_underestimate + 3}

        # make the onion
        print("creating onion:")
        onion, shared_secrets = self.create_onion(hops, self.payment_hash)
        print("onion: %s" % chill_purple_str(onion))
        print("shared_secrets: %s" % chill_yellow_str(str(shared_secrets)))
        return {'status':         "success",
                'onion':          onion,
                'first_hop':      circular[0],
                'assoc_data':     self.invoice['payment_hash'],
                'payment_hash':   self.invoice['payment_hash'],
                'shared_secrets': shared_secrets,
                'fitted_pixels':  attempting_pixels}

    def fit_onion(self):
        hop_count = INITIAL_HOP_GUESS
        pixel_underestimate = 0
        retry_count = 0
        while retry_count < FIT_ONION_TRIES:
            result = self.try_fit(hop_count, pixel_underestimate)
            if result['status'] == "success":
                return result
            elif result['status'] == "retry":
                retry_count += 1
                hop_count = result['needed_hops']
                pixel_underestimate = result['pixel_underestimate']
            elif result['status'] == 'err':
                return result
        return {'status': "err",
                'msg': "could not fit onion after %d tries" % FIT_ONION_TRIES}


###############################################################################


class OnionDraw:
    def __init__(self, rpc, dst_node, art_no, pixels):
        self.rpc = rpc
        self.dst_node = dst_node
        self.art_no = art_no
        self.pixels = pixels

    def print_dict(self, info):
        pprint.pprint(info)

    def get_myid_blockheight(self):
        info = self.rpc.getinfo()
        return info['id'], info['blockheight']

    def send_onion(self, onion, first_hop, assoc_data, shared_secrets):
        label = str(uuid.uuid4())
        print("send params: %s %s %s %s %s" % (onion, first_hop, assoc_data,
                                               label, shared_secrets))
        result = self.rpc.sendonion(onion, first_hop, assoc_data, label,
                                    shared_secrets)
        return result

    def payment_status(self, payment_hash):
        return self.rpc.listsendpays(None,
                                     payment_hash)['payments'][0]['status']

    def draw_pixel_set(self, myid, block_height, pixels):
        invoice = Invoice(self.rpc).create_invoice()

        onion_creator = Onion(self.rpc, myid, self.dst_node, block_height,
                              invoice, self.art_no, self.pixels)

        onion_result = onion_creator.fit_onion()
        if onion_result['status'] != "success":
            return None, onion_result['msg']

        fitted_pixels = onion_result['fitted_pixels']

        result = self.send_onion(onion_result['onion'],
                                 onion_result['first_hop'],
                                 onion_result['assoc_data'],
                                 onion_result['shared_secrets'])

        if result['status'] not in {"pending", "complete"}:
            return None, "payment status not as expected after send"

        if result['status'] == "complete":
            return result['fitted_pixels'], None

        # check to see if it will succeed.
        checks = 0
        while True:
            status = self.payment_status(onion_result['payment_hash'])
            if status == "complete":
                break
            checks += 1
            if checks == 10:
                return None, "payment didn't complete"
            print("sleeping waiting for payment to complete...")
            time.sleep(2.0)
        return onion_result['fitted_pixels'], None

    def draw_loop(self, myid, blockheight):
        pixels = self.pixels
        while True:
            fitted_pixels, err = self.draw_pixel_set(myid, blockheight, pixels)
            if err:
                return err
            if fitted_pixels:
                pixels = pixels[fitted_pixels:]
            if len(pixels) == 0:
                print("all pixels drawn")
                return None

    def run(self):
        try:
            myid, blockheight = self.get_myid_blockheight()
            print("myid: %s, blockheight %s" % (chill_yellow_str(myid),
                                                chill_green_str(myid)))
        except Exception as e:
            return "could not get basics from rpc: %s" % e
        try:
            err = self.draw_loop(myid, blockheight)
            if err:
                return err
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return None, "error while buying pixels: %s" % e
        return None
