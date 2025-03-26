import requests
from .asset import BridgeableToken

OMNI_BRIDGE_RPC_URL = "https://bridge.chaindefuser.com/rpc"

class OmniBridge:
    """Fetch supported tokens"""

    def __init__(self, url=OMNI_BRIDGE_RPC_URL):
        self.url = url
        self._supported = dict()
        # Fetch supported bridgeable tokens
        body = {
            "id": "dontcare",
            "jsonrpc": "2.0",
            "method": "supported_tokens",
            "params": []
        }
        response = requests.post(url=url, json=body).json()
        for token in response.get('result').get('tokens'):
            if "-" in token['near_token_id']:
                blockchain = token['near_token_id'].split("-")[0]
            else:
                blockchain = token['asset_name'].lower()
            bridgeable_token = BridgeableToken(
                defuse_asset_id=token['defuse_asset_identifier'],
                symbol=token['asset_name'],
                blockchain=blockchain,
                **token)

            if self._supported.get(blockchain):
                self._supported[blockchain][token['asset_name']] = bridgeable_token
            else:
                self._supported[blockchain] = {
                    token['asset_name']: bridgeable_token}
        pass

    def get_token(self, symbol: str, chain: str) -> BridgeableToken:
        chain = self._supported.get(chain)
        if not chain:
            return None
        token = chain.get(symbol)
        if not token:
            return None
        return token

    def get_deposit_address(self, token: BridgeableToken, account_id: str) -> str:
        chain = ":".join(token.defuse_asset_id.split(":")[:-1])
        body = {
            "jsonrpc": "2.0",
            "id": "dontcare",
            "method": "deposit_address",
            "params": [
                {
                    "account_id": account_id,
                    "chain": chain 
                }
            ]
        }
        return requests.post(url=self.url, json=body).json()['result']['address']