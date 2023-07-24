#!/usr/bin/python
#
# Copyright 2016 Intel Corporation
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

import hashlib
import logging
import random
import time
import cbor
import yaml
import json

from requestops import send_request 
from sawtooth_sdk.protobuf import batch_pb2
from sawtooth_sdk.protobuf import transaction_pb2
from exceptions import CryptoportClientException

LOGGER = logging.getLogger(__name__)

FAMILY_NAME = 'cryptoport'


def _sha512(data):
    return hashlib.sha512(data).hexdigest()

def _get_prefix():
    return _sha512('cryptoport'.encode('utf-8'))[0:6]

def _get_address(name):
    prefix = _get_prefix()
    game_address = _sha512(name.encode('utf-8'))[0:64]
    return prefix + game_address

class CryptoportPayload:
    def __init__(self, verb, name, value):
        self._verb = verb
        self._name = name
        self._value = json.dumps(value)

        self._cbor = None
        self._sha512 = None

    def to_hash(self):
        return {
            'Verb': self._verb,
            'Name': self._name,
            'Value': self._value
        }

    def to_cbor(self):
        if self._cbor is None:
            self._cbor = cbor.dumps(self.to_hash(), sort_keys=True)
        return self._cbor

    def sha512(self):
        if self._sha512 is None:
            self._sha512 = hashlib.sha512(self.to_cbor()).hexdigest()
        return self._sha512


class CryptoPort():

    def create_cryptoport_transactions(verb, name, value, signer, deps=[]):
        """Creates a signed Cryptoport transaction.
        """

        # The prefix should eventually be looked up from the
        # validator's namespace registry.
        addr = [[_get_address(name)]]
        
        transactions = []
        for a in addr:
            payload = CryptoportPayload(
                verb = verb, 
                name = name,
                value =value)

            header = transaction_pb2.TransactionHeader(
                signer_public_key=signer.get_public_key().as_hex(),
                family_name=FAMILY_NAME,
                family_version='1.0',
                inputs=a,
                outputs=a,
                dependencies=deps,
                payload_sha512=payload.sha512(),
                batcher_public_key=signer.get_public_key().as_hex(),
                nonce=hex(random.randint(0, 2**64)))

            header_bytes = header.SerializeToString()

            signature = signer.sign(header_bytes)

            transaction = transaction_pb2.Transaction(
                header=header_bytes,
                payload=payload.to_cbor(),
                header_signature=signature)
            transactions.append(transaction)
        return transactions

    def create_batch(transactions, signer):
        transaction_signatures = [t.header_signature for t in transactions]

        header = batch_pb2.BatchHeader(
            signer_public_key=signer.get_public_key().as_hex(),
            transaction_ids=transaction_signatures)

        header_bytes = header.SerializeToString()

        signature = signer.sign(header_bytes)

        batch = batch_pb2.Batch(
            header=header_bytes,
            transactions=transactions,
            header_signature=signature)

        return batch_pb2.BatchList(batches=[batch])

    def send_transaction(self, url, batch_list, wait=None):
        batch_id = batch_list.batches[0].header_signature

        response = send_request(url,
            "batches", batch_list.SerializeToString(),
            'application/octet-stream',
        )

        if self.wait_done(batch_id, wait):
            return response
                
    def wait_done(self, batch_id, wait, status='PENDING', start_time=None):
        args       = batch_id, wait
        localargs  = dict(status=status, start_time=start_time)
        
        if not wait or wait < 0:
            return True
        if not start_time:
            start_time = time.time()
        if status != 'PENDING':
            return True

        try:
            result, _ = send_request(self.url,
                'batch_statuses?id={}&wait={}'.format(batch_id, wait),)
            batch_data  = yaml.safe_load(result)['data']
            status_list = [batch_data[i]['status']
                          for i in batch_data]
            status = 'PENDING' if 'PENDING' in status_list else 'DONE' 
        except BaseException as err:
            raise CryptoportClientException(err) from err    

        wait -= time.time - start_time
        return self.wait_done(*args, **localargs)