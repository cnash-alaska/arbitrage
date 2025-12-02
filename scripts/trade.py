
import requests
import datetime
import base64
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature



###########KALSHI####################################################################################
# -------------------------------
# 1. Load private key
# -------------------------------
def load_private_key_from_file(file_path):
    with open(file_path, "rb") as key_file:
        return serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )


# -------------------------------
# 2. Sign text with PSS
# -------------------------------
def sign_pss_text(private_key: rsa.RSAPrivateKey, text: str) -> str:
    try:
        signature = private_key.sign(
            text.encode("utf-8"),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH
            ),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode("utf-8")
    except InvalidSignature:
        raise ValueError("RSA PSS signing failed")


# -------------------------------
# 3. Build headers with debug info
# -------------------------------
def build_signed_headers_debug(private_key, api_key_id, method, path):
    timestamp_ms = str(int(datetime.datetime.now().timestamp() * 1000))
    path_no_query = path.split("?")[0]
    string_to_sign = timestamp_ms + method + path_no_query
    signature = sign_pss_text(private_key, string_to_sign)

    headers = {
        "KALSHI-ACCESS-KEY": api_key_id,
        "KALSHI-ACCESS-SIGNATURE": signature,
        "KALSHI-ACCESS-TIMESTAMP": timestamp_ms
    }

    print("===== DEBUG INFO =====")
    print("Timestamp (ms):", timestamp_ms)
    print("String to sign:", string_to_sign)
    print("Base64 signature:", signature)
    print("Request headers:", headers)
    print("======================\n")

    return headers


# -------------------------------
# 4. Make request with debug
# -------------------------------
PRIVATE_KEY_PATH = "../keys/api_key_trading.txt"  # Your downloaded PEM file
API_KEY_ID = "1ba73b4e-c794-4516-8e29-45c9f43a07ad"  # Your key ID
BASE_URL = "https://api.elections.kalshi.com/" # or demo
path = "/trade-api/v2/portfolio/balance"


def get_balance_debug():
    method = "GET"
    path = "/trade-api/v2/portfolio/balance"
    private_key = load_private_key_from_file(PRIVATE_KEY_PATH)
    headers = build_signed_headers_debug(private_key, API_KEY_ID, method, path)

    response = requests.get(BASE_URL + path, headers=headers)
    print("HTTP Status:", response.status_code)
    try:
        print("Response JSON:", response.json())
    except Exception:
        print("Raw response:", response.text)


import uuid
import json
import requests


def place_trade(market_id, action, side, count, price_cents, private_key, api_key_id,
                base_url="https://api.elections.kalshi.com"):
    """
    Place a trade on Kalshi.

    Parameters:
    - market_id: string, the market ticker/id
    - action: "buy" or "sell" (lowercase)
    - side: "yes" or "no" (lowercase)
    - count: int, number of units
    - price_cents: int, price per contract (1-99)
    - private_key: RSAPrivateKey object from load_private_key_from_file()
    - api_key_id: string, your API key ID
    """
    method = "POST"
    path = "/trade-api/v2/portfolio/orders"

    # Generate timestamp and signature
    timestamp_ms = str(int(datetime.datetime.now().timestamp() * 1000))
    string_to_sign = timestamp_ms + method + path
    signature = sign_pss_text(private_key, string_to_sign)

    headers = {
        "KALSHI-ACCESS-KEY": api_key_id,
        "KALSHI-ACCESS-SIGNATURE": signature,
        "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
        "Content-Type": "application/json"
    }

    # Client order ID for deduplication
    client_order_id = str(uuid.uuid4())

    payload = {
        "ticker": market_id,
        "action": action,  # "buy" or "sell"
        "side": side,  # "yes" or "no"
        "count": count,
        "type": "limit",
        "yes_price" if side == "yes" else "no_price": price_cents,
        "client_order_id": client_order_id
    }

    response = requests.post(base_url + path, headers=headers, json=payload)

    print("HTTP Status:", response.status_code)
    try:
        print("Response JSON:", response.json())
    except Exception:
        print("Raw response:", response.text)

    return response



polymarket_key = '0xcfe45d69be5b4a3479c47d763cf0aa8d98ba03f7f7f460cfdce1cdce579f26c6'


from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY

host: str = "https://clob.polymarket.com"
key: str = "0xcfe45d69be5b4a3479c47d763cf0aa8d98ba03f7f7f460cfdce1cdce579f26c6" #This is your Private Key. Export from https://reveal.magic.link/polymarket or from your Web3 Extension
chain_id: int = 137 #No need to adjust this
POLYMARKET_PROXY_ADDRESS: str = '0xb02592F33EE3c97e4649bEeF7bfF1897B384314a' #This is the address listed below your profile picture when using the Polymarket site.

#Select from the following 3 initialization options to match your login method, and remove any unused lines so only one client is initialized.


### Initialization of a client using a Polymarket Proxy associated with an Email/Magic account. If you login with your email use this example.
client = ClobClient(host, key=key, chain_id=chain_id, signature_type=1, funder=POLYMARKET_PROXY_ADDRESS)

## Create and sign a limit order buying 5 tokens for 0.010c each
#Refer to the API documentation to locate a tokenID: https://docs.polymarket.com/developers/gamma-markets-api/fetch-markets-guide

client.set_api_creds(client.create_or_derive_api_creds())



import requests

BASE_URL = "https://data-api.polymarket.com"

def get_total_value(wallet_address: str):
    """
    Returns the total USD‑value of all positions for the given Polymarket wallet.
    """
    resp = requests.get(f"{BASE_URL}/value", params={"user": wallet_address})
    resp.raise_for_status()
    data = resp.json()
    if not data:
        return None
    # data is a list like: [{ "user": "...", "value": 123.45 }]
    return data[0].get("value")

def get_positions(wallet_address: str, size_threshold: float = 0.0):
    """
    Returns a list of open positions for the given Polymarket wallet.
    """
    resp = requests.get(
        f"{BASE_URL}/positions",
        params={
            "user": wallet_address,
            "sizeThreshold": size_threshold,
            # you can add other params like limit, mergeable, redeemable per docs
        }
    )
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    proxy_wallet = "0xb02592F33EE3c97e4649bEeF7bfF1897B384314a"  # your proxy wallet address

    total = get_total_value(proxy_wallet)
    print("Total account value (USD):", total)

    positions = get_positions(proxy_wallet)
    print("Open positions:")
    for pos in positions:
        print(pos)












# -------------------------------
# 5. Run
# -------------------------------
if __name__ == "__main__":
    kalshi_balances = get_balance_debug()

    # Fetch account info
    account_info = client.get_account()

    # account_info is a dict, with a "balances" key containing a list of tokens
    balances = account_info['balances']

    # Print balances
    for token in balances:
        print(f"{token['mint']} | {token['symbol']} | Balance: {token['balance'] / (10 ** token['decimals'])}")

#    place_trade(
#        market_id="KXTOPSONG-25DEC13-ORD",
#        action="buy",
#        side="yes",
#        count=1,  # 1 contract
#        price_cents=1,  # 1 cent
#        private_key=private_key,
#        api_key_id=API_KEY_ID
#    )

    #order_args = OrderArgs(
    #    price=0.01,
    #    size=5.0,
    #    side=BUY,
    #    token_id="", #Token ID you want to purchase goes here. Example token: 114304586861386186441621124384163963092522056897081085884483958561365015034812 ( Xi Jinping out in 2025, YES side )
    #)
    #signed_order = client.create_order(order_args)
    #
    ### GTC(Good-Till-Cancelled) Order
    #resp = client.post_order(signed_order, OrderType.GTC)
    #print(resp)
    #

###########################################################################
