import requests
from .asset import AvailableToken
from time import sleep

SOLVER_BUS_URL = "https://solver-relay-v2.chaindefuser.com/rpc"

class Solver:
    def __init__(self, url=SOLVER_BUS_URL):
        self.url = url

    def _get_quotes(self, asset_in: AvailableToken, asset_out: AvailableToken, amount_in):
        """Fetches the trading options from the solver bus."""
        rpc_request = {
            "id": "dontcare",
            "jsonrpc": "2.0",
            "method": "quote",
            "params": [
                {
                    "defuse_asset_identifier_in": asset_in.get_asset_id(),
                    "defuse_asset_identifier_out": asset_out.get_asset_id(),
                    "exact_amount_in": str(amount_in),
                },
            ]
        }
        response = requests.post(self.url, json=rpc_request)
        response_json = response.json()
        return response_json.get("result", [])
    
    def get_best_quote(self, asset_in: AvailableToken, asset_out: AvailableToken, amount_in: float) -> tuple[str,float, str, dict]:
        quotes = self._get_quotes(asset_in, asset_out, asset_in.to_decimals(amount_in))
        if not quotes:
            raise Exception(f"unable to find a quote to swap {amount_in} {asset_in.symbol} to {asset_out.symbol}")
        if any(q.get('type') == 'INSUFFICIENT_AMOUNT' for q in quotes):
            raise ValueError(f"{amount_in} for {asset_in.symbol} results in INSUFFICIENT_AMOUNT to get a quote")
        best_quote = max(quotes, key=lambda x: int(x['amount_out']))
        amount_out = int(best_quote['amount_out']) / 10 ** asset_out.decimals
        return best_quote['quote_hash'], amount_out, best_quote['expiration_time'],  best_quote
    

    def get_intent_status(self, intent_hash: str) -> tuple:
        rpc_request = {
            "id": "dontcare",
            "jsonrpc": "2.0",
            "method": "get_status",
            "params": [
                {"intent_hash": intent_hash}
            ]
        }
        res = requests.post(self.url, json=rpc_request).json()['result']
        if res.get('data'):
            return res['status'], res['data'].get('hash')
        return res['status'], None

    def publish_intent(self, signed_intent) -> str:
        """Publishes the signed intent to the solver bus."""
        rpc_request = {
            "id": "dontcare",
            "jsonrpc": "2.0",
            "method": "publish_intent",
            "params": [signed_intent]
        }
        try:
            res = requests.post(self.url, json=rpc_request).json()['result']
            return res['intent_hash']
        except Exception as e:
            raise RuntimeError(f"Publish intent smart contract failed: {str(e)}")

    def wait_for_intent_confirmed(self, intent_hash):
        while True:
            status, tx_hash = self.get_intent_status(intent_hash=intent_hash)
            if status not in ["SETTLED", "PENDING", "TX_BROADCASTED"]:
                return (status, None) 
            elif tx_hash:
                return (status, tx_hash) 
            sleep(1)