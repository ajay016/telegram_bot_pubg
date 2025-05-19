import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode

BINANCE_API_KEY = '5MDgDlM7jGial7HTE3qx2WkD9z9eEKYw6HLvEJCgM1L1yfKGuLK5aLAMO1op1Nqc'
BINANCE_SECRET = 'G0pGJTqgoa27CT8HAxow2bq7WrjOKruTPYM57FvHncYu3XsthdWk0hMjyIrtXzs9'

def binance_signed_request(endpoint: str, params: dict) -> dict:
    base_url = 'https://api.binance.com'
    timestamp = int(time.time() * 1000)
    params['timestamp'] = timestamp

    query_string = urlencode(params)
    signature = hmac.new(BINANCE_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    headers = {'X-MBX-APIKEY': BINANCE_API_KEY}
    url = f'{base_url}{endpoint}?{query_string}&signature={signature}'

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()