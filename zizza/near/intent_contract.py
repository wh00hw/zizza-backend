from typing import List
from .account import NEARAccount
from .asset import AvailableToken
from near_api import transactions
import requests
import json

AVAILABLE_TOKENS_URL = "https://api-mng-console.chaindefuser.com/api/tokens"

class IntentContract:
    def __init__(self):
        self.contract_id = "intents.near"
        self.available_tokens = dict()
        self._fetch_available_tokens()
        pass

    def _fetch_available_tokens(self):
        items = requests.get(
            url=AVAILABLE_TOKENS_URL).json().get('items')
        for item in items:
            token = AvailableToken(**item)
            if self.available_tokens.get(item['blockchain']):
                self.available_tokens[item['blockchain']
                                      ][item['symbol']] = token
            else:
                self.available_tokens[item['blockchain']] = {
                    item['symbol']: token}


    def get_chains(self) -> List[str]:
        return list(self.available_tokens.keys())
    
    def get_token_price(self, symbol: str, chain: str) -> tuple[float, str]:
        self._fetch_available_tokens()
        asset: AvailableToken = self.get_token(symbol=symbol, chain=chain)
        return asset.price, asset.price_updated_at

    def get_tokens_by_chain(self, chain: str) -> List[str]:
        try:
            tokens: list = self.available_tokens.get(chain)
            if not tokens:
                return []
            return [token for token in tokens]
        except KeyError:
            raise ValueError(f"chain '{chain}' is not supported")

    def get_chains_by_token(self, symbol: str) -> List[str]:
        try:
            chains = []
            for chain in self.available_tokens:
                if not self.available_tokens[chain].get(symbol):
                    continue
                chains.append(chain) 
            return chains
        except KeyError:
            raise ValueError(f"token '{symbol}' is not deployed in any chain")

    def get_token(self, symbol: str, chain: str) -> AvailableToken:
        try:
            return self.available_tokens[chain][symbol]
        except KeyError:
            raise ValueError(f"token '{symbol}' on chain '{chain}' not found")
    
    def balance_of(self, asset: AvailableToken, account: NEARAccount) -> float:
        response = account.view_function(self.contract_id, 'mt_batch_balance_of', {
                                         'account_id': account.account_id, 'token_ids': [asset.get_asset_id()]}).get('result')
        return int(response[0]) / 10 ** asset.decimals

    def deposit(self, asset: AvailableToken, amount: float, account: NEARAccount) -> str:
        return account.function_call(asset.contract_address,
                                     'ft_transfer_call', {
                                         'account_id': account.account_id,
                                         'receiver_id': self.contract_id,
                                         'amount': asset.to_decimals(amount=amount),
                                         'msg': ""
                                     }, 300000000000000, 1)['transaction']['hash']

    def deposit_near(self, amount: float, account: NEARAccount) -> str:
        wnear_asset: AvailableToken = self.get_token(symbol="wNEAR", chain="near")
        account._register_token_storage(asset=wnear_asset)
        yoctoamount = int(amount * 10 ** 24)
        actions = [
            transactions.create_function_call_action(
                methodName="near_deposit",
                args={},
                gas=30000000000000,
                deposit=yoctoamount
            ),
            transactions.create_function_call_action(
                methodName="ft_transfer_call",
                args=json.dumps({
                    "receiver_id": self.contract_id,
                    "amount": str(yoctoamount),
                    "msg": "",
                }).encode('utf8'),
                gas=50000000000000,
                deposit=1
            )
        ]
        return account._account._sign_and_submit_tx("wrap.near", actions)['transaction']['hash']