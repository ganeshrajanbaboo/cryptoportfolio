# Copyright 2016, 2017 Intel Corporation
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
from collections import defaultdict
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin

import getpass
import os
import requests

from cryptoport_client import CryptoportClient

DEFAULT_URL = 'http://127.0.0.1:8008'
LIVE_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"

# * Transaction Types
BOUGHT = 1
SOLD = 0

app = Flask(__name__)
cors = CORS(app)

url      = 'http://rest-api:8008'
keyfile  = None    

class dict2class(object):
    def __init__(self, d):
        for k in d:
            setattr(self, k, d[k])

@app.route("/")
def health_check():
    return "I am cool!"

@app.route("/transactions")
@cross_origin()
def get_transactions():
    args_dict     = {"url":url, "keyfile":keyfile}    
    args          = dict2class(args_dict)
    client        = _get_client(args, False)
    value_list    = client.list()
    return jsonify(value_list)

@app.route("/transactions", methods=["POST"])
def new_transaction():

    print('name               = {}'.format(request.json["name"]))
    print('symbol             = {}'.format(request.json["symbol"]))
    print('type               = {}'.format(request.json["type"]))
    print('amount             = {}'.format(request.json["amount"]))
    print('time_transacted    = {}'.format(request.json["time_transacted"]))
    print('time_created       = {}'.format(request.json["time_created"]))
    print('price_purchased_at = {}'.format(request.json["price_purchased_at"]))
    print('no_of_coins        = {}'.format(request.json.get("no_of_coins")))

    value = {
    'name'               : request.json["name"],
    'symbol'             : request.json["symbol"],
    'type'               : int(request.json["type"]),
    'amount'             : request.json["amount"],
    'time_transacted'    : datetime.fromtimestamp(request.json["time_transacted"]).strftime("%m-%d-%Y"),
    'time_created'       : datetime.fromtimestamp(request.json["time_created"]).strftime("%m-%d-%Y"),
    'price_purchased_at' : float(request.json["price_purchased_at"]),
    'no_of_coins'        : float(request.json.get("no_of_coins"))
    }
    wait = None
    args_dict   = {"url":url, "keyfile":keyfile}    
    args     = dict2class(args_dict)
    client = _get_client(args, False) 
    response = client.insert(value, wait)

    request.json["id"] = response
    return jsonify(request.json)

@app.route("/get_rollups_by_coin")
def get_rollups_by_coin():
    args_dict   = {"url":url, "keyfile":keyfile}    
    args     = dict2class(args_dict)
    client   = _get_client(args, False)
    rows    = client.rollups()

    if not rows:
        return jsonify(rows)

    portfolio = defaultdict(
        lambda: {
            "coins": 0,
            "total_cost": 0,
            "total_equity": 0,
            "live_price": 0
        }
    )

    for row in rows:
        coin = row[0]
        transaction_type = row[1]
        transaction_amount = row[2]/100
        transaction_coins = row[3]

        # This is a purchase
        if transaction_type == 1:
            portfolio[coin]['total_cost'] += transaction_amount
            portfolio[coin]['coins'] += transaction_coins
        else:
            # This is a sell
            portfolio[coin]['total_cost'] -= transaction_amount
            portfolio[coin]['coins'] -= transaction_coins

    symbol_to_coin_id_map = {
        "BTC": "bitcoin",
        "SOL": "solana",
        "LINK": "chainlink",
        "ETH": "ethereum",
        "ADA": "cardano",
        "MANA": "decentraland",
    }
    rollups_response = []
    for symbol in portfolio:
        response = requests.get(
            f"{LIVE_PRICE_URL}?ids={symbol_to_coin_id_map[symbol]}&vs_currencies=usd").json()
        live_price = response[symbol_to_coin_id_map[symbol]]['usd']

        portfolio[symbol]['live_price'] = live_price
        portfolio[symbol]['total_equity'] = float(
            portfolio[symbol]['coins']) * live_price

        rollups_response.append(
            {
                "symbol": symbol,
                "live_price": portfolio[symbol]['live_price'],
                "total_equity": portfolio[symbol]['total_equity'],
                "coins": portfolio[symbol]['coins'],
                "total_cost": portfolio[symbol]["total_cost"]
            }
        )
    return jsonify(rollups_response)

def _get_client(args, read_key_file=True):
    return CryptoportClient(
        url=DEFAULT_URL if args.url is None else args.url,
        keyfile=_get_keyfile(args) if read_key_file else None)

def _get_keyfile(args):
    try:
        if args.keyfile is not None:
            return args.keyfile
    except AttributeError:
        return None

    real_user = getpass.getuser()
    home = os.path.expanduser("~")
    key_dir = os.path.join(home, ".sawtooth", "keys")
  
    return '{}/{}.priv'.format(key_dir, real_user)




