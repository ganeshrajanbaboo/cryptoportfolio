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

import logging
import cbor
import hashlib
import json

                
from sawtooth_sdk.processor.handler import TransactionHandler
from sawtooth_sdk.processor.exceptions import InvalidTransaction
from sawtooth_sdk.processor.exceptions import InternalError

LOGGER = logging.getLogger(__name__)

VALID_VERBS = 'insert'

MAX_NAME_LENGTH = 20

FAMILY_NAME = 'cryptoport'

CRYPTOPORT_ADDRESS_PREFIX = hashlib.sha512(
    FAMILY_NAME.encode('utf-8')).hexdigest()[0:6]


def make_cryptoport_address(name):
    return CRYPTOPORT_ADDRESS_PREFIX + hashlib.sha512(
        name.encode('utf-8')).hexdigest()[0:64]


class CrypoportTransactionHandler(TransactionHandler):
    
    @property
    def family_name(self):
        return FAMILY_NAME

    @property
    def family_versions(self):
        return ['1.0']

    @property
    def namespaces(self):
        return [CRYPTOPORT_ADDRESS_PREFIX]

    def apply(self, transaction, context):
        
        verb, name, value = _unpack_transaction(transaction)

        state = _get_state_data(name, context)

        updated_state = _do_cryptoport(verb, name, value, state)

        _set_state_data(name, updated_state, context)

def _unpack_transaction(transaction):
    verb, name, value = _decode_transaction(transaction)

    _validate_verb(verb)
    _validate_name(name)
    _validate_value(value)

    return verb, name, value


def _decode_transaction(transaction):
    try:
        content = cbor.loads(transaction.payload)
    except Exception as e:
        raise InvalidTransaction('Invalid payload serialization') from e

    try:
        verb = content['Verb']
    except AttributeError:
        raise InvalidTransaction('Verb is required') from AttributeError

    try:
        name = content['Name']
    except AttributeError:
        raise InvalidTransaction('Name is required') from AttributeError

    try:
        value = content['Value']
    except AttributeError:
        raise InvalidTransaction('Value is required') from AttributeError

    return verb, name, value


def _validate_verb(verb):
    if verb not in VALID_VERBS:
        raise InvalidTransaction('Verb must be "insert"')

def _validate_name(name):
    if not isinstance(name, str) or len(name) > MAX_NAME_LENGTH:
        raise InvalidTransaction(
            'Name must be a string of no more than {} characters'.format(
                MAX_NAME_LENGTH))

def _validate_value(value):
    try:
        json.loads(value)
    except ValueError as e:
        raise InvalidTransaction('Value must be JSON ')

def _get_state_data(name, context):
    address = make_cryptoport_address(name)

    state_entries = context.get_state([address])

    try:
        return cbor.loads(state_entries[0].data)
    except IndexError:
        return {}
    except Exception as e:
        raise InternalError('Failed to load state data') from e


def _set_state_data(name, state, context):
    address = make_cryptoport_address(name)

    encoded = cbor.dumps(state)

    addresses = context.set_state({address: encoded})

    if not addresses:
        raise InternalError('State error')

def _do_cryptoport(verb, name, value, state):
    
    verbs = {
        'insert': _do_insert,
    }
    try:
        return verbs[verb](name, value, state)
    except KeyError:
        # This would be a programming error.
        raise InternalError('Unhandled verb: {}'.format(verb)) from KeyError

def _do_insert(name, value, state):
    value   = json.loads(value)
    updated = dict(state.items())
    if name not in state:
        updated[name] = [value]
    else:
        updated[name].append(value)
    return updated
