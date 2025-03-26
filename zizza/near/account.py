from .asset import AvailableToken, Token
from .nep413_signer import serialize_intent
from datetime import datetime, timedelta, timezone
import near_api
import base58
import base64
import json
import secrets

NEAR_RPC_NODE_URL = 'https://rpc.mainnet.near.org'
MAX_GAS = 300 * 10 ** 12

def generate_nonce():
    return base64.b64encode(secrets.token_bytes(32)).decode('utf-8')


def generate_deadline(minutes_from_now=1):
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes_from_now)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class NEARAccount:
    def __init__(self, account_id: str, prv_key: str, rpc_url=NEAR_RPC_NODE_URL):
        self.provider = near_api.providers.JsonProvider(rpc_url)
        key_pair = near_api.signer.KeyPair(prv_key)
        self.signer = near_api.signer.Signer(account_id, key_pair)
        self.account_id = account_id
        self._account = near_api.account.Account(
            self.provider, self.signer, self.account_id)

    def function_call(self, *args, **kwargs):
        try:
            return self._account.function_call(*args, **kwargs)
        except Exception as e:
            error = e.args[0]['data']['TxExecutionError']['InvalidTxError']['NotEnoughBalance']
            error_str = "{} has {} yoctaNEAR, not enough to cover the tx cost of {} yoctaNEAR".format(
                error['signer_id'],
                error['balance'],
                error['cost']
            )
            raise RuntimeError(error_str)

    def view_function(self, *args, **kwargs):
        return self._account.view_function(*args, **kwargs)

    def view_account(self, account_id):
        return self.provider.query({
            "request_type": "view_account",
            "finality": "final",
            "account_id": account_id
        })

    def get_account_balance(self) -> dict:
        return {
            "address": self.account_id,
            "balance": int(self.view_account(account_id=self.account_id)['amount']) / 10 ** 24
        }

    def _register_intent_public_key(self, contract_address: str):
        pub_key = "ed25519:" + \
            base58.b58encode(self.signer.public_key).decode('utf-8')
        result = self.function_call(contract_address, "has_public_key", {
            "account_id": self.account_id,
            "public_key": pub_key
        })
        if not result.get('status').get('SuccessValue') == "dHJ1ZQ==":  # sucess = true
            self.function_call(contract_address, "add_public_key", {
                "public_key": pub_key
            }, MAX_GAS, 1)

    def _has_storage_balance(self,  asset: AvailableToken, target_account_id: str = None):
        account_id = self.account_id if not target_account_id else target_account_id
        result = self.view_function(asset.contract_address, 'storage_balance_of', {
                                    'account_id': account_id}).get('result')
        if not result:
            return False
        return True if int(result.get("total")) > 0 else False

    def _register_token_storage(self, asset: AvailableToken, target_account_id=None):
        account_id = self.account_id if not target_account_id else target_account_id
        return self.function_call(asset.contract_address, 'storage_deposit',
                                  {"account_id": account_id}, MAX_GAS, 1250000000000000000000)

    def _sign_intent(self, message: dict) -> dict:
        standard = "nep413"
        recipient = "intents.near"
        nonce = generate_nonce()

        msg_str = json.dumps(message, separators=(',', ':'))
        signature = 'ed25519:' + base58.b58encode(
            self.signer.sign(serialize_intent(
                msg_str, recipient, nonce, standard))
        ).decode('utf-8')

        public_key = 'ed25519:' + \
            base58.b58encode(self.signer.public_key).decode('utf-8')

        return {
            "standard": standard,
            "payload": {
                "message": msg_str,
                "nonce": nonce,
                "recipient": recipient,
            },
            "signature": signature,
            "public_key": public_key,
        }

    def sign_swap(self, quote: dict) -> dict:
        message = {
            "signer_id": self.account_id,
            "deadline": quote["expiration_time"],
            "intents": [
                {
                    "intent": "token_diff",
                    "diff": {
                        quote["defuse_asset_identifier_in"]: f"-{quote['amount_in']}",
                        quote["defuse_asset_identifier_out"]: quote["amount_out"],
                    },
                },
            ],
        }
        return {
            "quote_hashes": [quote["quote_hash"]],
            "signed_data": self._sign_intent(message)
        }

    def sign_withdraw(self, asset: Token, amount: float, native_dest_address: str) -> dict:
        intent = {"amount": asset.to_decimals(amount)}
        if asset.symbol == "NEAR":
            intent.update({
                "intent": "native_withdraw",
                "receiver_id": self.account_id,
            })
        else:
            intent.update({
                "intent": "ft_withdraw",
            })
            if asset.blockchain == "near":
                if not self._has_storage_balance(asset=asset, target_account_id=self.account_id):
                    self._register_token_storage(
                        asset=asset, target_account_id=self.account_id)
                intent.update({
                    "token": asset.contract_address,
                    "receiver_id": self.account_id,
                })
            else:
                intent.update({
                    "token": asset.near_token_id,
                    "receiver_id": asset.near_token_id,
                    "memo": f"WITHDRAW_TO:{native_dest_address}"
                })

        message = {
            "signer_id": self.account_id,
            "deadline": generate_deadline(),
            "intents": [intent],
        }
        return {
            "quote_hashes": [],
            "signed_data": self._sign_intent(message)
        }

    def send(self, asset: AvailableToken, to_account_id: str, amount: float) -> str:
        if not self._has_storage_balance(asset=asset, target_account_id=to_account_id):
            self._register_token_storage(
                asset=asset, target_account_id=to_account_id)
        try:
            return self.function_call(asset.contract_address,
                                      'ft_transfer', {
                                          'account_id': self.account_id,
                                          'receiver_id': to_account_id,
                                          'amount': asset.to_decimals(amount=amount),
                                          'msg': ""
                                      }, MAX_GAS, 1)['transaction']['hash']
        except KeyError:
            raise Exception('failed to send transaction')

    def send_near(self, target_account_id: str, amount: float):
        return self._account.send_money(target_account_id, int(amount * 10 ** 24))['transaction']['hash']
