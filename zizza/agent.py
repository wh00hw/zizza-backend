from typing import List
from .near.asset import AvailableToken, BridgeableToken
from .near.intent_contract import IntentContract
from .near.omni_bridge import OmniBridge
from .near.solver import Solver
from .near.account import NEARAccount
from .zcash.wallet import ZcashWallet

class Agent:
    def __init__(self, near_account_id: str, near_ed25519_key: str, zec_mnemonics: str, zec_wallet_birthday: int):
        self._zec_wallet = ZcashWallet(mnemonics=zec_mnemonics, birthday=zec_wallet_birthday)
        self._near_account = NEARAccount(account_id=near_account_id, prv_key=near_ed25519_key)
        self._intent_contract = IntentContract()
        self._near_account._register_intent_public_key(contract_address=self._intent_contract.contract_id)
        self._omni_bridge = OmniBridge()
        self._solver = Solver()
    
    def get_wallet_summary(self) -> dict:
        return {
            "ZEC": self._zec_wallet.get_wallet_summary(),
            "NEAR": self._near_account.get_account_balance()
            }
    
    def get_deposited_tokens(self) -> dict:
        deposited = {}
        for chain in self._intent_contract.available_tokens:
            for asset in self._intent_contract.available_tokens[chain].values():
                balance = self._intent_contract.balance_of(asset=asset, account=self._near_account)
                if balance > 0.0:
                    deposited[asset.defuse_asset_id] = balance
        return deposited
    
    def get_token_price(self, asset_symbol: str, asset_chain: str) -> tuple[float, str]:
        return self._intent_contract.get_token_price(symbol=asset_symbol, chain=asset_chain)
    
    def get_chains(self) -> List[str]:
        return self._intent_contract.get_chains()  
    
    def get_tokens_by_chain(self, chain: str) -> List[str]:
        return self._intent_contract.get_tokens_by_chain(chain=chain) 
    
    def get_chains_by_token(self, symbol: str) -> List[str]:
        return self._intent_contract.get_chains_by_token(symbol=symbol)
    
    def get_balance(self, asset_symbol: str, asset_chain: str, on_intent_contract: bool) -> float:
        if asset_symbol == "NEAR":
            if on_intent_contract:
                raise ValueError("only wNEAR exists in intents.near")
            return int(self._near_account.view_account(self._near_account.account_id)['amount']) / 10 ** 24
        asset: AvailableToken = self._intent_contract.get_token(symbol=asset_symbol, chain=asset_chain)
        if on_intent_contract:
            deposited = self.get_deposited_tokens()
            balance = deposited.get(asset.defuse_asset_id)
            if not balance:
                raise ValueError(f"{asset.symbol} has not been deposited yet")
            return balance
        elif asset.symbol == "ZEC":
            return self._zec_wallet.get_balance()
        else:
            return asset.balance_of(account=self._near_account)

    def get_best_quote(self, asset_in_symbol: str, asset_in_chain: str, asset_out_symbol: str, asset_out_chain: str, amount_in: float) -> tuple[str,float, str, dict]:
        asset_in: AvailableToken = self._intent_contract.get_token(symbol=asset_in_symbol, chain=asset_in_chain)
        asset_out: AvailableToken =self._intent_contract.get_token(symbol=asset_out_symbol, chain=asset_out_chain)
        return self._solver.get_best_quote(asset_in, asset_out, amount_in)
    
    def swap(self, asset_in_symbol: str, asset_in_chain: str, asset_out_symbol: str, asset_out_chain: str, amount_in: float) -> tuple:
        asset_in: AvailableToken = self._intent_contract.get_token(symbol=asset_in_symbol, chain=asset_in_chain)
        asset_out: AvailableToken =self._intent_contract.get_token(symbol=asset_out_symbol, chain=asset_out_chain)
        asset_in_balance = self.get_balance(asset_symbol=asset_in.symbol, asset_chain=asset_in_chain, on_intent_contract=True)
        if asset_in_balance < amount_in:
            raise ValueError(f"{self._near_account.account_id} has not enough {asset_in_symbol} balance")
        _, amount_out, _, best_quote = self.get_best_quote(asset_in.symbol, asset_in_chain, asset_out.symbol, asset_out.blockchain, amount_in=amount_in)
        signed_intent = self._near_account.sign_swap(best_quote)
        intent_hash = self._solver.publish_intent(signed_intent)
        status, tx_hash = self._solver.wait_for_intent_confirmed(intent_hash=intent_hash) 
        if not tx_hash:
            raise RuntimeError(f"swap of {amount_in} {asset_in.symbol} to {asset_out.symbol} resulted in {status}")
        return status, intent_hash, tx_hash, amount_out
    
    def withdraw(self, asset_symbol: str, asset_chain: str, amount: float, native_dest_address: str = None) -> tuple:
        deposited = self.get_deposited_tokens()
        if asset_chain == "near":
            symbol = asset_symbol
            if symbol == "NEAR":
                # The user wants to execute a native_withdraw
                symbol = "wNEAR" # We check the balance in wNEAR
            asset: AvailableToken =self._intent_contract.get_token(symbol=symbol, chain=asset_chain)
            asset_balance = deposited.get(asset.defuse_asset_id)
        else:
            asset: BridgeableToken = self._omni_bridge.get_token(symbol=asset_symbol, chain=asset_chain)
            asset_balance = deposited.get(asset.get_asset_id())
            if not native_dest_address:
                if asset.symbol == "ZEC":
                    native_dest_address = self._zec_wallet.get_address(shielded=False)
                else:
                    raise ValueError(f"native_dest_address must be provided in order to withdraw {asset.symbol}")
            min_withdraw = asset.min_withdrawal_amount / 10 ** asset.decimals
            if amount < min_withdraw:
                raise ValueError(f"can not withdraw such small amount of {asset.symbol}, min {min_withdraw}")
            
        if not asset_balance:
            raise ValueError(f"{asset_symbol} has not been deposited yet")
        if asset_balance < amount:
            raise ValueError(f"{self._near_account.account_id} has not enough {asset_symbol} balance on {self._intent_contract.contract_id}")   
        if asset_symbol == "NEAR":
            # To perform a native_withdraw, we need to restore the symbol in NEAR
            asset.symbol = "NEAR"
        signed_intent = self._near_account.sign_withdraw(asset, amount, native_dest_address)
        intent_hash = self._solver.publish_intent(signed_intent)
        status, tx_hash = self._solver.wait_for_intent_confirmed(intent_hash=intent_hash) 
        if not tx_hash:
            raise RuntimeError(f"withdraw of {amount} {asset.symbol} resulted in {status}")
        tx_chain = "near"
        if asset.symbol == "ZEC":
            if native_dest_address in self._zec_wallet._addresses.get('t_addresses'):
                # Auto shield tx
                ua_address = self._zec_wallet.get_address(shielded=True)
                tx_hash = self._zec_wallet.shield(to=ua_address)
                tx_chain = "zec"
        return status, intent_hash, tx_hash, tx_chain
    
    def deposit(self, asset_symbol: str, asset_chain: str, amount: float) -> str:
        if asset_symbol == "NEAR":
            return self._intent_contract.deposit_near(amount=amount, account=self._near_account)          
        elif asset_symbol == "ZEC":
            asset: BridgeableToken = self._omni_bridge.get_token(symbol=asset_symbol, chain=asset_chain)
            min_deposit = asset.min_deposit_amount / 10 ** asset.decimals
            if amount < min_deposit:
                raise ValueError(f"can not deposit such small amount, min {min_deposit}")
            asset_balance = self._zec_wallet.get_balance()
            if asset_balance < min_deposit:
                raise ValueError(f"not enough ZEC balance, you have {asset_balance} and you want to send {amount}")
            deposit_address = self._omni_bridge.get_deposit_address(token=asset, account_id=self._near_account.account_id)
            tx_hash = self.send(asset_symbol=asset.symbol, asset_chain=asset.blockchain, to_address=deposit_address, amount=amount)
            self._zec_wallet.wait_tx_confirmed(tx_hash=tx_hash)
            return tx_hash
        elif asset_chain == "near":
            asset: AvailableToken = self._intent_contract.get_token(symbol=asset_symbol, chain=asset_chain)
            if asset.balance_of(account=self._near_account) < amount:
                raise ValueError('not enough balance')
            return self._intent_contract.deposit(asset=asset, amount=amount, account=self._near_account)
        else:
            raise NotImplementedError("deposit for non-NEAR assets aside ZEC has not been implemented yet, you can do it manually on https://app.near-intents.org/")
        
    def send(self, asset_symbol: str, asset_chain: str, to_address: str, amount: float) -> str:
        if asset_symbol == "NEAR":
            return self._near_account.send_near(target_account_id=to_address, amount=amount)
        asset: AvailableToken =self._intent_contract.get_token(symbol=asset_symbol, chain=asset_chain)
        if asset.symbol == "ZEC":
            balance = self._zec_wallet.get_balance()
            fees = self._zec_wallet.default_fee()
            if balance < amount + fees:
                raise ValueError(f"not enough balance, you are trying to send {amount} + {fees} of fee but your spendable balance is {balance}")
            return self._zec_wallet.send(to=to_address, value=amount)
        else:
            balance = asset.balance_of(account=self._near_account)
            if balance < amount:
                raise ValueError("not enough balance")
            return self._near_account.send(asset=asset, to_account_id=to_address, amount=amount)