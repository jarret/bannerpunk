#!/usr/bin/env python3
import time
import os
import uuid
import json
import pprint
from lightning import LightningRpc, Millisatoshi

#PAY_DST = "0379c41f28a38c49998fec42437db78a17af508fb19338e7360d7ffee2607ea036"
PAY_DST = "02e389d861acd9d6f5700c99c6c33dd4460d6f1e2f6ba89d1f4f36be85fc60f8d7"
RPC_FILE = "/home/jarret/lightningd-run/lightning-dir/lightning-rpc"

RISK_FACTOR = 10

DST_PAYMENT = 1000
SELF_PAYMENT = 1000

CLTV_FINAL = 10

class Circular(object):
    def __init__(self):
        self.rpc = LightningRpc(RPC_FILE)

    def print_dict(self, info):
        pprint.pprint(info)

    def gen_preimage(self):
        return (bytearray.fromhex("deadbeef" * 6) + os.urandom(8)).hex()

    def get_myid(self):
        info = self.rpc.getinfo()
        return info['id']

    def create_invoice(self):
        msatoshi = SELF_PAYMENT
        label = str(uuid.uuid4())
        description = "circular payment"
        preimage = self.gen_preimage()
        return self.rpc.invoice(msatoshi, label, description,
                                preimage=preimage)

    def get_outgoing_route(self):
        try:
            return self.rpc.getroute(PAY_DST, SELF_PAYMENT + DST_PAYMENT,
                                     RISK_FACTOR)
        except:
            print("could not find route from self to %s" % (PAY_DST))
            return None

    def get_returning_route(self, myid):
        try:
            return self.rpc.getroute(myid, SELF_PAYMENT, RISK_FACTOR,
                                     fromid=PAY_DST)
        except:
            print("could not find route from %s to %s" % (PAY_DST, myid))
            return None

    def setup_routing_fee(self, route):
        # Thanks to sendinvoiceless.py plugin for this function!
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
            if ch['source'] == PAY_DST:
                fee += DST_PAYMENT
            msatoshi += fee
            delay += ch['delay']
            r['direction'] = int(ch['channel_flags']) % 2

    def assemble_circular(self, outgoing, returning):
        route = outgoing['route'] + returning['route']
        self.setup_routing_fee(route)

#        for r in route:
#            c = r['channel']
#            info = self.rpc.listchannels(c)
#            self.print_dict(info)

        return route

    def send_pay_on_route(self, route, payment_hash, bolt11):
        self.print_dict(route)
        print(payment_hash)
        pay_result = self.rpc.sendpay(route, payment_hash)
        self.print_dict(pay_result)
        for _ in range(3):
            l = self.rpc.listsendpays(bolt11)
            self.print_dict(l)
            time.sleep(1)

    def run(self):
        myid = self.get_myid()
        print(myid)
        invoice = self.create_invoice()
        self.print_dict(invoice)
        payment_hash = invoice['payment_hash']
        bolt11 = invoice['bolt11']

        outgoing = self.get_outgoing_route()
        if not outgoing:
            return
        self.print_dict(outgoing)

        returning = self.get_returning_route(myid)
        if not returning:
            return
        self.print_dict(returning)

        circular = self.assemble_circular(outgoing, returning)

        self.send_pay_on_route(circular, payment_hash, bolt11)


c = Circular()

c.run()
