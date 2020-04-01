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

server_url = 'https://api.upbit.com'

g_api_key = ""
g_api_secret = ""

def set_key(api_key, secret_key):
    global g_api_key, g_api_secret
    g_api_key = api_key
    g_api_secret = secret_key


def get_price(ticker, currency):
    url = server_url + "/v1/orderbook"
    querystring = {"markets":"{}-{}".format(currency, ticker)}
    response = requests.request("GET", url, params=querystring)
    j = json.loads(response.text)
    ask1 = float(j[0]["orderbook_units"][0]["ask_price"])
    bid1 = float(j[0]["orderbook_units"][0]["bid_price"])
    return (ask1+bid1)/2

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

def order_new_sub(ticker, price, cnt, askbid):
    rgParams = {
        "order_currency" : ticker,
        "payment_currency" : "KRW",
        "units" : float(cnt),
        "price" : int(price),
        "type" : askbid,
    };
    while True:
        try:
            result = api.xcoinApiCall("/trade/place/", rgParams);
            print_err(result)
            r = int(result['status'])
            # if r == 0: print(result)
            m = None
            if 'message' in result:
                m = result['message']
            if m is not None and m == '매수금액이 사용가능 KRW 를 초과하였습니다.':
                r = -1
            elif m is not None and m == '주문량이 사용가능 EOS을 초과하였습니다.':
                r = -2
            return r
        except:
            print('e')
            time.sleep(0.05)
            pass 


def order_new(ticker, price, cnt, askbid, ord_type):
    print('order_new...', ticker, price, cnt, askbid)
    if ticker=='BTC':
        price = round(price, -3) # minimum 1000 won

    query = {
        'market': 'KRW-{}'.format(ticker),
        'side': askbid,
        'volume': cnt,
        'price': price,
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
    oid = json.loads(res.content)['uuid']
    return oid

def limit_buy(ticker, price, cnt):
    return order_new(ticker, price, cnt, 'bid', 'limit')

def limit_sell(ticker, price, cnt):
    return order_new(ticker, price, cnt, 'ask', 'limit')