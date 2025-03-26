"""
API Module
===============
This module defines the `API` class, which acts as a wrapper around the `Agent` class. 
It provides various methods for managing cryptocurrency operations such as deposits, withdrawals, swaps, and balance checks.

"""
from .agent import Agent
from .middleware import *

class API:
    """
    A class that interfaces with the Agent to facilitate cryptocurrency operations.
    """
    
    def __init__(self):
        """
        Initializes the API instance with no agent set.
        """
        self.agent = None

    def set_agent(self, near_account_id: str, near_ed25519_key: str, zec_mnemonics: str, zec_wallet_birthday: int) -> dict:
        """
        Initializes and sets the Agent instance with the provided credentials.
        
        Args:
            near_account_id (str): The NEAR account ID.
            near_ed25519_key (str): The NEAR Ed25519 private key.
            zec_mnemonics (str): The mnemonic phrase for the Zcash wallet.
            zec_wallet_birthday (int): The birthday height of the Zcash wallet.
        
        Returns:
            dict: Wallet information containing:
                - "ZEC":
                    - "ua_addresses": {"address": str, "balance": float}
                    - "z_addresses": list[dict{"address": str, "balance": float}]
                    - "t_addresses": list[dict{"address": str, "balance": float}]
                - "NEAR": {"address": str, "balance": float}
        """
        self.agent = Agent(near_account_id, near_ed25519_key, zec_mnemonics, zec_wallet_birthday)
        return self.agent.get_wallet_summary()
    
    @is_agent_set
    def get_wallet_summary(self) -> dict:
        """
        Retrieves addresses and balances of the wallet.
        
        Returns:
            dict: {"ZEC": dict, "NEAR": dict} addresses and balances of the wallet..
        """
        return self.agent.get_wallet_summary()

    @is_agent_set
    @normalize_chain_params
    @normalize_amount_params
    def get_balance(self, asset_symbol: str, asset_chain: str, on_intent_contract: bool) -> dict[float]:
        """
        Retrieves the balance of a specified asset.
        
        Args:
            asset_symbol (str): The symbol of the asset (e.g., NEAR, ETH).
            asset_chain (str): The blockchain where the asset is stored.
            on_intent_contract (bool): Whether to check the balance on the intent contract.
        
        Returns:
            dict: {"balance": float} The balance of the specified asset.
        """
        return {"balance": self.agent.get_balance(asset_symbol, asset_chain, on_intent_contract)}
    
    @is_agent_set
    @normalize_chain_params
    def get_token_price(self, asset_symbol: str, asset_chain: str) -> dict[float, str]:
        """
        Retrieves the price in USD of a specified asset.
        
        Args:
            asset_symbol (str): The symbol of the asset (e.g., NEAR, ETH).
            asset_chain (str): The blockchain where the asset is stored.
        
        Returns:
            dict: {"usd_price", float, "price_updated_at", str } The price of the specified asset.
        """
        usd_price, price_updated_at = self.agent.get_token_price(asset_symbol=asset_symbol, asset_chain=asset_chain)
        return {"usd_price", usd_price, "price_updated_at", price_updated_at}
    
    @is_agent_set
    @normalize_chain_params
    @normalize_amount_params
    def get_best_quote(self, asset_in_symbol: str, asset_in_chain: str, asset_out_symbol: str, asset_out_chain: str, amount_in: float) -> dict[str, float, str]:
        """
        Retrieves the best swap quote for an asset pair.
        
        Args:
            asset_in_symbol (str): The symbol of the asset to swap in (e.g., NEAR, ETH).
            asset_in_chain (str): The blockchain where the source asset is stored.
            asset_out_symbol (str): The symbol of the asset to swap out (e.g., NEAR, ETH).
            asset_in_chain (str): The blockchain where the destination asset is stored.
            amount_in (float): the destination asset amount of the quote.
        
        Returns:
            dict: {"quote_hash", str, "amount_out", float, "expiration_time": str } The quote_has, the amount out and the expiration time.
        """
        quote_hash, amount_out, expiration_time, _ = self.agent.get_best_quote(asset_in_symbol, asset_in_chain, asset_out_symbol, asset_out_chain, amount_in)
        return {"quote_hash": quote_hash, "amount_out": amount_out, "expiration_time": expiration_time}
    
    @is_agent_set
    def get_chains(self) -> dict[list[str]]:
        """
        Retrieves the list of supported blockchain networks.
        
        Returns:
            dict: {"chains": list[str]} A list of supported chains.
        """
        return {"chains": self.agent.get_chains()}

    @is_agent_set
    @normalize_chain_params
    def get_tokens_by_chain(self, chain: str) -> dict[list[str]]:
        """
        Retrieves the tokens available on a given blockchain.
        
        Args:
            chain (str): The blockchain network.
        
        Returns:
            dict: {"tokens": list[str]} A list of tokens available on the specified chain.
        """
        return {"tokens": self.agent.get_tokens_by_chain(chain)}
    
    @is_agent_set
    def get_chains_by_token(self, symbol: str) -> dict[list[str]]:
        """
        Retrieves the chains where a specified token is available.
        
        Args:
            symbol (str): The token symbol.
        
        Returns:
            dict: {"chains": list[str]} A list of chains supporting the specified token.
        """
        return {"chains": self.agent.get_chains_by_token(symbol)}
    
    @is_agent_set
    @normalize_chain_params
    @normalize_amount_params
    def deposit(self, asset_symbol: str, asset_chain: str, amount: float) -> dict[str, str]:
        """
        Deposits a specified amount of an asset into the agent's wallet.
        
        Args:
            asset_symbol (str): The asset to deposit.
            asset_chain (str): The blockchain network of the asset.
            amount (float): The amount to deposit.
        
        Returns:
            dict: {"chain": str, "tx_hash": str} The transaction hash and chain details.
        """
        tx_hash = self.agent.deposit(asset_symbol, asset_chain, amount)
        return {"chain": asset_chain, "tx_hash": tx_hash}
    
    @is_agent_set
    @normalize_chain_params
    @normalize_amount_params
    def swap(self, asset_in_symbol: str, asset_in_chain: str, asset_out_symbol: str, asset_out_chain: str, amount_in: float) -> dict[str, str, str, float]:
        """
        Swaps one asset for another across supported blockchains.
        
        Args:
            asset_in_symbol (str): The input asset symbol.
            asset_in_chain (str): The input asset chain.
            asset_out_symbol (str): The output asset symbol.
            asset_out_chain (str): The output asset chain.
            amount_in (float): The amount of input asset.
        
        Returns:
            dict: {"status": str, "intent_hash": str, "tx_hash": str, "amount_out": float} Swap details.
        """
        status, intent_hash, tx_hash, amount_out = self.agent.swap(asset_in_symbol, asset_in_chain, asset_out_symbol, asset_out_chain, amount_in)
        return {"status": status, "intent_hash": intent_hash, "tx_hash": tx_hash, "amount_out": amount_out}

    @is_agent_set
    @normalize_chain_params
    @normalize_amount_params
    def withdraw(self, asset_symbol: str, asset_chain: str, amount: float, native_dest_address=None) -> dict[str, str, str, str]:
        """
        Withdraws an asset to an external address.
        
        Args:
            asset_symbol (str): The asset to withdraw.
            asset_chain (str): The blockchain network of the asset.
            amount (float): The amount to withdraw.
            native_dest_address (str, optional): The destination address.
        
        Returns:
            dict: {"status": str, "intent_hash": str, "tx_hash": str, "chain": str} Withdrawal details.
        """
        status, intent_hash, tx_hash, chain = self.agent.withdraw(asset_symbol, asset_chain, amount, native_dest_address)
        return {"status": status, "intent_hash": intent_hash, "tx_hash": tx_hash, "chain": chain}

    @is_agent_set
    @normalize_chain_params
    @normalize_amount_params
    def send(self, asset_symbol: str, asset_chain: str, to_address: str, amount: float) -> str:
        """
        Send an asset.
        
        Args:
            asset_symbol (str): The asset to withdraw.
            asset_chain (str): The blockchain network of the asset.
            to_address (str): The address recipient
            amount (float): The amount to withdraw.
        
        Returns:
            dict: {"tx_hash": str, "chain": str} Transaction hash.
        """
        tx_hash = self.agent.send(asset_symbol, asset_chain, to_address, amount)
        return {"tx_hash": tx_hash, "chain": asset_chain}
