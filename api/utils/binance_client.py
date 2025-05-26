import time
import os
import django
import hmac
from decouple import config
import hashlib
import requests
from urllib.parse import urlencode
from requests.exceptions import RequestException
import logging

logger = logging.getLogger(__name__)



# BINANCE_API_KEY = '5MDgDlM7jGial7HTE3qx2WkD9z9eEKYw6HLvEJCgM1L1yfKGuLK5aLAMO1op1Nqc'
# BINANCE_SECRET = 'G0pGJTqgoa27CT8HAxow2bq7WrjOKruTPYM57FvHncYu3XsthdWk0hMjyIrtXzs9'

# production API Keys
# BINANCE_API_KEY = 'lHxRqsX0jkw8wsbSPG0tKmqTKA6pONcd7ihV3VqUvQmAayAq8Qz3RruMjOqZRvB0'
# BINANCE_SECRET = 'uPvbk01bNJKlKcrDzrgiFgMKigGsUy9j8EOJrE42XgTtcvepZwhyF46mcnMj6ZFm'

BINANCE_API_KEY = 'CclbtRl8Z4yQd5Q4tvoyo32OLecrmUrKqoAErEwCPEzglxZwDNoL1RasKbUasYMh'
BINANCE_SECRET = '3Kq2nwLKnSsGN4bzDkPqI8yv5E9BwGposj1tvBsOkTocunxFM7pxCwPSdMYr9pig'


# BINANCE_API_KEY = config('BINANCE_API_KEY')
# BINANCE_SECRET = config('BINANCE_SECRET')

def binance_signed_request(endpoint: str, params: dict) -> dict:
    base_url = 'https://api.binance.com'
    timestamp = int(time.time() * 1000)
    params['timestamp'] = timestamp

    query_string = urlencode(params)
    signature = hmac.new(BINANCE_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    headers = {'X-MBX-APIKEY': BINANCE_API_KEY}
    url = f'{base_url}{endpoint}?{query_string}&signature={signature}'

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        # Log full response content if available
        if e.response is not None:
            logger.error("Binance API error: %s", e.response.text)
            raise Exception(f"Binance API returned error: {e.response.text}") from e
        else:
            logger.exception("Binance API connection failed")
            raise

