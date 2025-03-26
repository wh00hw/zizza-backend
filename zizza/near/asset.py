from abc import ABC, abstractmethod

class Token(ABC):
    def __init__(self, **kwargs):
        self.defuse_asset_id = kwargs.get("defuse_asset_id")
        self.symbol = kwargs.get("symbol")
        self.decimals = kwargs.get("decimals")
        self.blockchain = kwargs.get("blockchain")
    
    @abstractmethod
    def get_asset_id(self):
        pass
    
    def to_decimals(self, amount: float) -> str:
        return str(int(amount * 10 ** self.decimals))

class AvailableToken(Token):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.contract_address = kwargs.get('contract_address')
        self.price = float(kwargs.get('price'))
        self.price_updated_at = kwargs.get('price_updated_at')
    
    def get_asset_id(self):
        """Get the asset identifier in the format expected by the solver bus."""
        return self.defuse_asset_id
    
    def balance_of(self, account) -> float:
        return int(account.view_function(self.contract_address, 'ft_balance_of', {'account_id': account.account_id}).get('result')) / 10 ** self.decimals

class BridgeableToken(Token):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.near_token_id = kwargs.get("near_token_id")
        min_deposit_amount = kwargs.get("min_deposit_amount")
        self.min_deposit_amount = int(min_deposit_amount) if min_deposit_amount else 0
        min_withdrawal_amount = kwargs.get("min_withdrawal_amount")
        self.min_withdrawal_amount = int(min_withdrawal_amount) if min_withdrawal_amount else 0
        
    def get_asset_id(self):
        """Get the asset identifier in the format expected by the solver bus."""
        return f"nep141:{self.near_token_id}"