import subprocess
import json
import regex
import os
from time import sleep
import bip39

ZCASH_RPC_LIGHTNODE_URL = "https://zec.rocks:443"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ZEC_LITE_BIN = os.path.join(BASE_DIR, "zecwallet-light-cli", "target", "release", "zecwallet-cli")
ZEC_LITE_WALLET_DATADIR = os.path.join(BASE_DIR, "data")

def is_valid_address(address: str) -> bool:
    return bool(regex.fullmatch(r"^[a-zA-Z0-9]{34,}$", address))

class ZcashWallet:
    def __init__(self, mnemonics=None, birthday=None, server=ZCASH_RPC_LIGHTNODE_URL, data_dir=ZEC_LITE_WALLET_DATADIR):
        if not os.path.exists(ZEC_LITE_BIN):
            raise RuntimeError("zecwallet-cli missing, compile zecwallet-cli first")
        self.configs = f"--server \"{server}\" --data-dir {data_dir}"
        self.pattern = regex.compile(r'[\{|\[](?:[^{}]|(?R))*[\}|\]]')  
        if mnemonics:
            if not birthday:
                birthday = 1
            wallet_path = os.path.join(data_dir, "zecwallet-light-wallet.dat")
            if os.path.exists(wallet_path):
                os.remove(wallet_path)

            self._recover_wallet(mnemonics=mnemonics, birthday=birthday)

    def get_balance(self) -> float:
        balance = self._balance()
        ua = int(balance.get('uabalance'))
        tb = int(balance.get('tbalance'))
        zb = int(balance.get('zbalance'))
        total = ua + tb + zb
        return total / 10 ** 8
    
    def get_wallet_summary(self) -> dict:
        result = self._balance()
        return {
            "ua_addresses": {
                "address": result['ua_addresses'][0]['address'],
                "balance": result['ua_addresses'][0]['balance'] / 10 ** 8
                },
            "z_addresses": [
                {"address": x['address'], "balance": x['zbalance'] / 10 ** 8} for x in result['z_addresses']
            ],
            "t_addresses": [
                {"address": x['address'], "balance": x['balance'] / 10 ** 8} for x in result['t_addresses']
            ]
        }
    
    def get_address(self, shielded=True):
        return self._addresses().get('ua_addresses' if shielded else "t_addresses")[-1]  
    
    def send(self, to:str, value:float):
        if not is_valid_address(address=to):
            raise ValueError("invalid address")
        payload = f"send {to} {int(value * 10 ** 8)}"
        return self._run_command(payload).get('txid')
    
    def shield(self, to:str):
        if not is_valid_address(address=to):
            raise ValueError("invalid address")
        if to.startswith('t'):
            raise ValueError("invalid shield address")
        payload = f"shield {to}"
        return self._run_command(payload).get('txid')
    
    def default_fee(self) -> float:
        return self._run_command("defaultfee").get("defaultfee") / 10 ** 8
    
    def _is_valid_address(address: str) -> bool:
        return bool(regex.fullmatch(r"^[a-zA-Z0-9]+$", address))

    def _run_command(self, args: list):
        process = subprocess.run(f'{ZEC_LITE_BIN} {self.configs} {args}',
            check=True, stdout=subprocess.PIPE, universal_newlines=True, shell=True
        )
        output_json = self.pattern.findall(process.stdout)
        try:
            return [json.loads(output_json[i]) for i in range(len(output_json))] if len(output_json) > 1 else json.loads(output_json[0])
        except Exception:
            raise RuntimeError(f"Error parsing zecwallet-cli JSON output: {process.stdout}")

    def _recover_wallet(self, mnemonics, birthday):
        if not bip39.check_phrase(phrase=mnemonics):
            raise ValueError("invalid mnemonic phrase")
        return self._run_command(f"balance --seed \"{mnemonics}\" --birthday {birthday}")

    def _sync(self):
        return True if self._run_command("sync").get("result") == "success" else False

    def _info(self):
        return self._run_command("info")

    def _height(self):
        return self._run_command("height").get("height")

    def _addresses(self):
        return self._run_command("addresses")

    def _balance(self):
        return self._run_command("balance")

    def _is_tx_confirmed(self, tx_hash):
        try:
            self._sync()
            return not next(filter(lambda x: x.get('txid') == tx_hash, self._run_command("list"))).get("unconfirmed")
        except StopIteration:
            return False
    def wait_tx_confirmed(self, tx_hash) -> bool:
        while not self._is_tx_confirmed(tx_hash=tx_hash):
            print(f"waiting {tx_hash} to be confirmed...")
            sleep(2)
        return True