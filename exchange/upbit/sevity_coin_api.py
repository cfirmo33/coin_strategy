# -*- coding: utf-8 -*-
#! /usr/bin/env python
from __future__ import absolute_import
import sys
import pprint
import time
import json
import requests
import os
import jwt
import uuid
import hashlib
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta
from multipledispatch import dispatch # https://www.geeksforgeeks.org/python-method-overloading/

server_url = 'https://api.upbit.com'

g_api_key = ""
g_api_secret = ""
g_ask_fee = -1
g_bid_fee = -1

def set_key(api_key, secret_key):
    global g_api_key, g_api_secret
    g_api_key = api_key
    g_api_secret = secret_key


def get_price(ticker, currency):
    while True:
        try:
            url = server_url + "/v1/orderbook"
            querystring = {"markets":"{}-{}".format(currency, ticker)}
            response = requests.request("GET", url, params=querystring)
            if response.ok == False:
                if response.status_code != 429:  # too many api requeists
                    print(  response.url, response.text)
            j = json.loads(response.text)
            ask1 = float(j[0]["orderbook_units"][0]["ask_price"])
            bid1 = float(j[0]["orderbook_units"][0]["bid_price"])
            return (ask1+bid1)/2
        except:
            time.sleep(1.0)

def get_info(ticker, currency):
    query = {
        'market': '{}-{}'.format(currency, ticker),
    }
    query_string = urlencode(query).encode()

    m = hashlib.sha512()
    m.update(query_string)
    query_hash = m.hexdigest()

    payload = {
        'access_key': g_api_key,
        'nonce': str(uuid.uuid4()),
        'query_hash': query_hash,
        'query_hash_alg': 'SHA512',
    }

    jwt_token = jwt.encode(payload, g_api_secret).decode('utf-8')
    authorize_token = 'Bearer {}'.format(jwt_token)
    headers = {"Authorization": authorize_token}

    res = requests.get(server_url + "/v1/orders/chance", params=query, headers=headers)
    a = res.json()
    r = {}
    r['ask_fee'] = float(a['ask_fee'])
    r['bid_fee'] = float(a['bid_fee'])
    r['tick_size'] = a['market']['ask']['price_unit']
    return r

def get_asset_info(currency):
    url = server_url + "/v1/accounts"

    payload = {
        'access_key': g_api_key,
        'nonce': str(uuid.uuid4()),
    }

    jwt_token = jwt.encode(payload, g_api_secret).decode('utf-8')
    authorize_token = 'Bearer {}'.format(jwt_token)
    headers = {"Authorization": authorize_token}
    res = requests.get(url, headers=headers)
    a = res.json()
    r = {}
    for i in range(len(a)):
        if a[i]['currency']==currency:
            r['free'] = float(a[i]['balance'])
            r['inuse'] = float(a[i]['locked'])
            r['total'] = r['free'] + r['inuse']
            break
    return r



def order_new(ticker, price, cnt, askbid, ord_type):
    print('  order_new...', ticker, 'price:{:,.2f}'.format(price), 'cnt:{:,.4f}'.format(cnt), askbid)
    if ticker=='BTC':
        price = round(price, -3) # minimum 1000 won

    query = {
        'market': 'KRW-{}'.format(ticker),
        'side': askbid,
        'volume': cnt,
        'price': price,
        'ord_type': ord_type,
    }
    if ord_type=='market':
        query = {
            'market': 'KRW-{}'.format(ticker),
            'side': askbid,
            'volume': cnt,
            'ord_type': ord_type,
        }
    query_string = urlencode(query).encode()

    m = hashlib.sha512()
    m.update(query_string)
    query_hash = m.hexdigest()

    payload = {
        'access_key': g_api_key,
        'nonce': str(uuid.uuid4()),
        'query_hash': query_hash,
        'query_hash_alg': 'SHA512',
    }

    jwt_token = jwt.encode(payload, g_api_secret).decode('utf-8')
    authorize_token = 'Bearer {}'.format(jwt_token)
    headers = {"Authorization": authorize_token}

    res = requests.post(server_url + "/v1/orders", params=query, headers=headers)
    if res.ok == False:
        print(  res, res.text)
    oid = json.loads(res.content)['uuid']
    return (oid,res)

def limit_buy(ticker, price, cnt):
    return order_new(ticker, price, cnt, 'bid', 'limit')[0]

def limit_sell(ticker, price, cnt):
    return order_new(ticker, price, cnt, 'ask', 'limit')[0]

def market_buy(ticker, cnt):
    (oid, res) =  order_new(ticker, 0, cnt, 'bid', 'price')
    a = json.loads(res.content)
    r = {}
    r['price'] = 0
    r['volume'] = float(a['volume'])
    return r

def market_sell(ticker, cnt):
    (oid, res) = order_new(ticker, 0, cnt, 'ask', 'market')
    r = {}
    while 'final_amount' not in r:
        r = get_fill_order(oid)
    return r['final_amount']

def cancel(oid):
    print('  order_cancel...', oid)
    query = {
        'uuid': oid,
    }
    query_string = urlencode(query).encode()

    m = hashlib.sha512()
    m.update(query_string)
    query_hash = m.hexdigest()

    payload = {
        'access_key': g_api_key,
        'nonce': str(uuid.uuid4()),
        'query_hash': query_hash,
        'query_hash_alg': 'SHA512',
    }

    jwt_token = jwt.encode(payload, g_api_secret).decode('utf-8')
    authorize_token = 'Bearer {}'.format(jwt_token)
    headers = {"Authorization": authorize_token}

    res = requests.delete(server_url + "/v1/order", params=query, headers=headers)
    if res.ok == False:
        print(  res, res.text)
    return res

@dispatch(str, str) 
def get_live_orders(ticker, currency):
    query = {
        'market': '{}-{}'.format(currency, ticker),  # 왠일인지 이게 안먹네
        'state': 'wait',
    }
    query_string = urlencode(query)

    uuids = [
        '9ca023a5-851b-4fec-9f0a-48cd83c2eaae',
        #...
    ]
    uuids_query_string = '&'.join(["uuids[]={}".format(uuid) for uuid in uuids])

    #query['uuids[]'] = uuids
    #query_string = "{0}&{1}".format(query_string, uuids_query_string).encode()

    m = hashlib.sha512()
    m.update(query_string.encode())
    query_hash = m.hexdigest()

    payload = {
        'access_key': g_api_key,
        'nonce': str(uuid.uuid4()),
        'query_hash': query_hash,
        'query_hash_alg': 'SHA512',
    }

    jwt_token = jwt.encode(payload, g_api_secret).decode('utf-8')
    authorize_token = 'Bearer {}'.format(jwt_token)
    headers = {"Authorization": authorize_token}

    res = requests.get(server_url + "/v1/orders", params=query, headers=headers)
    r = []
    for ord in res.json():
        ct = dt = datetime.strptime(ord['created_at'], '%Y-%m-%dT%H:%M:%S%z')
        r.append((ord['uuid'], ord['side'], ord['price'], ct))
    return r

@dispatch(str) 
def get_live_orders(currency):
    query = {
        'state': 'wait',
    }
    query_string = urlencode(query)

    uuids = [
        '9ca023a5-851b-4fec-9f0a-48cd83c2eaae',
        #...
    ]
    uuids_query_string = '&'.join(["uuids[]={}".format(uuid) for uuid in uuids])

    #query['uuids[]'] = uuids
    #query_string = "{0}&{1}".format(query_string, uuids_query_string).encode()

    m = hashlib.sha512()
    m.update(query_string.encode())
    query_hash = m.hexdigest()

    payload = {
        'access_key': g_api_key,
        'nonce': str(uuid.uuid4()),
        'query_hash': query_hash,
        'query_hash_alg': 'SHA512',
    }

    jwt_token = jwt.encode(payload, g_api_secret).decode('utf-8')
    authorize_token = 'Bearer {}'.format(jwt_token)
    headers = {"Authorization": authorize_token}

    res = requests.get(server_url + "/v1/orders", params=query, headers=headers)
    r = []
    for ord in res.json():
        ct = dt = datetime.strptime(ord['created_at'], '%Y-%m-%dT%H:%M:%S%z')
        ticker = ord['market'].split('-')[1]
        r.append((ticker, ord['uuid'], ord['side'], ord['price'], ct))
    return r

def get_fill_order(oid):
    query = {
        'state': 'done',
    }
    query_string = urlencode(query)

    uuids = [
        oid,
        #...
    ]
    uuids_query_string = '&'.join(["uuids[]={}".format(uuid) for uuid in uuids])

    query['uuids[]'] = uuids
    query_string = "{0}&{1}".format(query_string, uuids_query_string).encode()

    m = hashlib.sha512()
    m.update(query_string)
    query_hash = m.hexdigest()

    payload = {
        'access_key': g_api_key,
        'nonce': str(uuid.uuid4()),
        'query_hash': query_hash,
        'query_hash_alg': 'SHA512',
    }

    jwt_token = jwt.encode(payload, g_api_secret).decode('utf-8')
    authorize_token = 'Bearer {}'.format(jwt_token)
    headers = {"Authorization": authorize_token}

    res = requests.get(server_url + "/v1/orders", params=query, headers=headers)
    j = res.json()
    if len(j) == 0:
        return {}

    r = {}
    r['askbid'] = j[0]['side']
    r['volume'] = float(j[0]['executed_volume'])
    r['fee'] = float(j[0]['paid_fee'])
    global g_ask_fee, g_bid_fee
    if g_ask_fee == -1 or g_bid_fee == -1:
        ticker = j[0]['market'].split('-')[1]
        info = get_info(ticker, 'KRW')
        g_ask_fee = info['ask_fee']
        g_bid_fee = info['bid_fee']
    fee = g_ask_fee if r['askbid']=='ask' else g_bid_fee
    r['price'] = r['fee']/fee/r['volume'] if j[0]['price'] is None else float(j[0]['price'])
    if r['askbid']=='ask':
        r['final_amount'] = r['price'] * r['volume'] - r['fee']
    else:
        r['final_amount'] = r['price'] * r['volume'] + r['fee']
    return r