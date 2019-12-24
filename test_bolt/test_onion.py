#!/usr/bin/env python3
import os
import sys
import random

sys.path.insert(1, os.path.realpath(os.path.pardir))

from bolt.util import h2b
from bolt.onion import Onion


# via:  $ ./onion generate 02e389d861acd9d6f5700c99c6c33dd4460d6f1e2f6ba89d1f4f36be85fc60f8d7 0331f80652fb840239df8dc99205792bba2e559a05469915804c08420230e23c7c

TEST_ONION = "0002eec7245d6b7d2ccb30380bfbe2a3648cd7a942653f5aa340edcea1f2836866196a40b084beaf96f13e780ec101fbc8337630e8c83911b19261b986cee03af45e798bb234ea11312d4b8b5648ce0deebc8d9ab18e8fccd1f3a049c2bf774d85cb41aa70429889e3728b9a2bfb795eb3d2573dd9a54807e3e781e2b8d29560c52d2481be7c3d78ba5036c068a94e8c1c5f15b669f2c7bac08356fb384ac0f3e1bb5e9931a69ba8972a6093d362b9d25ea1d4d15a289cbccdd82740f5ba17eb101086893e3f5e4e7a8e902ea8b292326d8db4c8bb7de5472cbcbd081751ed283d098f148752eed4090975a0c513ab4966cca41c9a432e6c66d46b9842522745a05e1eafa6ebde06fc6d924c81d0b6a8a9c095629f7c4d534d295536b5be766324ebfc10f2807c11b2040fa90f751df217ff9d356ea79db1d5b6a52f74b5c12f3edffe36063535fe8fdf9d2210fbe31bf8363982b00e74cf4cb2985227ea885a3ec8c27833f15f783666d74e1922d327433f0896117750d71f008f35d6701440f597af164fb697f0577d8b27c103e7b316c61c93ea4d54fbf190dd180746c1c83a7d6698af4f6ab62776a2a3c63172cd038e2be6c0fc78dcf4e11bed90737c95ec4e30259aade3049aa12966c15c091d8fb6091a8b9866b0177730c8cb8e7c3a58d04c27df54151f80b0fac52b0a0a34317be1b0647056ed3d550f4c22f3b2e1682eb03010c6f47dceddbd1a558b772a2a7b6bec6f6efe87c62f61ca2dd87fa60eb3fc697e3ba11ba0f229efc352b1cbb9d116e2ac7ca829f23954fcd498d8978964b98b718aa05cc1541b3e378283a982fdd851f2ea5c60ee3ca77c986b1643845052aabf1686502e214b71a6958ab7e5f42d5f5457fef03dfd4e2775b412dc7aad1bce33d4a9c453e6b4fb1b3bfae0fe26ae70bad73f72a75c0684c7b85f6a64d92bb168575640f80b566846effeb497e65b77fed808aa0ca323e5da2bcf9abdb29c09818a6b4295e40dff5ad6936682f02a9b306841e4be18e10fb1bb108984e8394a44ddb9b144250fcecb895331a30a23574d248c7db532f8f086d6befd0b31873ba1cc0ab2e69b77e99d863d6906d5381a1a7afdb772f4d9b43f1dd172b4daa28cd4dcbe4047418a31b20c640c0a69c0b05ff7a76bb231a77e6cbc6bf236d9510212ca88da5950dd8d5557bc38a542801ab2244055a0eb0b7fac9d86168eb77f165841b579c52df66de259f9ad7ea03639a41ea5ce412b5522708c80aa279199a808e4fd8530ea4fe62dbaea3b317d989631db47ba7510c1b27977c440d18f8ba2310d7dd75095acaba5a6cf9a44ff8c481e55bbd1597593483a019d379f8dfeb3678ca2959ff21627d250a4c3c40a5528b540f77950dabe80803d6f84e2555aea717c9b6d9399dda0701a3a28be58c6b6d758b477e2b6f8cffb369778f14486263c54df7d1df91a8de3e248d8f35b79f5e5715882e9e254e3802dde0c688459c20be9d6bbfc676f89cfadde528d8197a2daf2aef6dc75290b959af822d128e5cb34a9f54f63826df2647d82344c8317df72826713281f861915d4d12917ba30a999e9a7f6160635818944db4638be9640f5ff16ec97b1ded7ab499cd929d9252bc8259ba557472a28e1c61931bfd8aeb46cc8460fbdeba0dff90e54ad5cbf6c57ce2b137a89cd77fad028d2339313198a91cbac11313938929142c66dcb8e481b209c9b7f5e4143295714f063edd7924d45c4057d8ec90be103c0c11d32331ad118aad5ff1d9347b2540571094a4fbdc05ca9e17dcc50d7f16c23654cc1fbc1741eb39e2442e6b54931da0088d993a5941aba6ceae34c1b585564000faade7920209694cb0022b43a1a3ee1402e14cfe4a865b5f1b29f3ac5d7460be4204dbe72350e2256b855f2243c1078c63e97070ba898"


if __name__ == "__main__":
    parsed, err = Onion.parse_fixed(h2b(TEST_ONION))
    print(parsed)