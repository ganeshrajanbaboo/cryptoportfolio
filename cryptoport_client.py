# Copyright 2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ------------------------------------------------------------------------------

import yaml
import base64
import cbor
import hashlib
import json

import pandas as pd
from tranops    import CryptoPort
from requestops import send_request

from exceptions import CryptoportClientException

from sawtooth_signing import create_context
from sawtooth_signing import CryptoFactory
from sawtooth_signing import ParseError
from sawtooth_signing.secp256k1 import Secp256k1PrivateKey


def _sha512(data):
    return hashlib.sha512(data).hexdigest()

class CryptoportClient:
    def __init__(self, url, keyfile=None):
        self.url = url
        if keyfile is not None:
            try:
                with open(keyfile) as fd:
                    private_key_str = fd.read().strip()
                    fd.close()
            except OSError as err:
                raise CryptoportClientException(
                    'Failed to read private key: {}'.format(str(err))) from err

            try:
                private_key = Secp256k1PrivateKey.from_hex(private_key_str)
            except ParseError as e:
                raise CryptoportClientException(
                    'Unable to load private key: {}'.format(str(e))) from e

            self._signer = CryptoFactory(
                create_context('secp256k1')).new_signer(private_key)
        else:
            #A default key is provided in case of no key in input
            self._signer = CryptoFactory(create_context('secp256k1')). \
            new_signer(create_context('secp256k1').new_random_private_key())    

    def _get_prefix(self):
        return _sha512('cryptoport'.encode('utf-8'))[0:6]

    def _get_address(self, name):
        prefix = self._get_prefix()
        game_address = _sha512(name.encode('utf-8'))[0:64]
        return prefix + game_address

    def _get_state_data(self):
        address = self._get_address('name')
        result, _ = send_request(self.url,
            "state?address={}".format(address))
        
        if "data" not in yaml.safe_load(result):
            return None
        
        try:
            encoded_entries = yaml.safe_load(result)["data"]
            
            return [[entry["address"],
                    cbor.loads(base64.b64decode(entry["data"]))] for entry in encoded_entries][0][1]
        except BaseException:
            return None

    def list(self):
        data = self._get_state_data()
        if data:
            return data['name']
        else:
            return []
    
    def rollups(self):
        data = self._get_state_data()
        if data:
            df   = pd.json_normalize(data['name'])
            return df.groupby(['symbol', 'type']).agg(
                total_amount = ('amount','sum'), 
                total_coins  = ('no_of_coins','sum'),
                ).reset_index().values.tolist()
        else:
            return []

    def insert(self, value, wait=None):
        if not value:
            raise CryptoportClientException("no value provided")
        
        return self.tran_ops('insert', 'name',
                             value, self._signer, wait)
    
    #Build the transactions and their batches for transporting to processor.
    def tran_ops(self,verb, name, value, signer, wait):
        data_tran_list      = CryptoPort.create_cryptoport_transactions(
                                verb,
                                name,
                                value,
                                signer)

        data_batchlist = CryptoPort.create_batch(data_tran_list, signer)

        return CryptoPort().send_transaction(self.url,
                                              data_batchlist, wait=wait)[0]