# ZizZA Blockchain Intents Server

Provides an interface for executing cryptocurrency operations through the API class, enabling the creation of intents and performing actions on the NEAR and Zcash blockchains. It supports setting up an agent, importing of creating wallets, checking balances, performing swaps, deposits, withdrawals, and sending assets.

## Backend for ZizZa
This repository serves as the backend for the [ZizZa](https://github.com/andreabellacicca/zizza) project.

## Live Deployment
This project is live and accessible at:
  - https://zizza.xyz

## How does it work?

The frontend communicates with this backend via REST APIs.

To run the server locally, follow the instructions in the Install section.

## Usage as a Package
You can also use this backend as a package in your Python project:

```python
from zizza.api import API

api = API()
```
This allows you to integrate the backend functionality directly into other Python applications.
See API Methods for more examples

## Install

```sh
git clone --recurse-submodules https://github.com/wh00hw/zizza-blockchain-intents-server
```

```sh
docker build -t zizza-backend .
```
or by creating a virtual environment

```sh
git clone --recurse-submodules https://github.com/wh00hw/zizza-blockchain-intents-server
```

```
cd zizza/zcash/zecwallet-light-cli
cargo build --release
```

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running the Server


```sh
docker run -p 8000:5001 zizza-backend
```
or manually if you created the virtual environment

```sh
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```
The server will be available at `http://localhost:8000`.

## Endpoints

### 1. Execute Operations

**Endpoint:**

```http
POST /execute
```

**Request Body:**

```json
[
  {
    "command": "set_agent",
    "params": {
      "near_account_id": "zizza.near",
      "near_ed25519_key": "ed25519:...",
      "zec_mnemonics": "never gonna give you up never gonna let you down never gonna run around and desert you never gonna make you cry never gonna",
      "zec_wallet_birthday": 123456
    }
  },
  {
    "command": "deposit",
    "params": {
      "asset_symbol": "wNEAR",
      "asset_chain": "near",
      "amount": 10.0
    }
  },
  {
    "command": "swap",
    "params": {
      "asset_in_symbol": "wNEAR",
      "asset_in_chain": "near",
      "asset_out_symbol": "ZEC",
      "asset_out_chain": "zec",
      "amount_in": 5.0
    }
  },
  {
    "command": "withdraw",
    "params": {
      "asset_symbol": "ZEC",
      "asset_chain": "zec",
      "amount": 0.5,
      "native_dest_address": "u1a3a7km3ujtzfwywmrv759etufkwyuqve264eqavvsgcx2m7wpfk6kpt5evhqp2nq0qjrddvmp0gpr923q42ddagl7xv77uzmeckark6q"
    }
  }
]
```

**Response:**

```json
{
  "task_id": "unique-task-id"
}
```

### 2. Check Task Status

**Endpoint:**

```http
GET /status/{task_id}
```

**Response:**

```json
{
  "status": "Processing 1/2",
  "results": [
    {
      "command": "set_agent",
      "params": { ... },
      "result": { ... }
    }
  ]
}
```

**Error Response:**

If an error occurs during execution, the response will include the error details:

```json
{
  "status": "Failed at 2/4",
  "results": [
    {
      "command": "set_agent",
      "params": { ... },
      "result": { ... }
    },
    {
      "command": "deposit",
      "params": { ... },
      "error": "Insufficient funds"
    }
  ]
}
```

## Features
- Supports asynchronous execution of multiple operations.
- Tracks operation progress using a `task_id`.
- Provides structured responses with execution results.
- If a non-transparent (non-T) address is provided as the native_dest_address during a ZEC withdrawal, auto-shielding will be applied.

## API Methods

Below are examples of all the methods implemented in the `API` class.

### 1. Set Agent

Initializes and sets the `Agent` instance with the provided credentials.

**Example Request:**
```python
api = API()
response = api.set_agent(
    near_account_id="zizza.near",
    near_ed25519_key="ed25519:...",
    zec_mnemonics="never gonna give you up never gonna let you down never gonna run around and desert you never gonna make you cry never gonna",
    zec_wallet_birthday=123456
)
```

**Example Response:**
```json
{
  "ZEC": {
    "ua_addresses": [{"address": "ua1...", "balance": 10.0}],
    "z_addresses": [{"address": "zs1...", "balance": 5.0}],
    "t_addresses": [{"address": "t1...", "balance": 2.0}]
  },
  "NEAR": {"address": "zizza.near", "balance": 15.0}
}
```

---

### 2. Get Wallet Summary

Retrieves addresses and balances of the wallet.

**Example Request:**
```python
response = api.get_wallet_summary()
```

**Example Response:**
```json
{
  "ZEC": {
    "ua_addresses": [{"address": "ua1...", "balance": 10.0}],
    "z_addresses": [{"address": "zs1...", "balance": 5.0}],
    "t_addresses": [{"address": "t1...", "balance": 2.0}]
  },
  "NEAR": {"address": "zizza.near", "balance": 15.0}
}
```

---


### 2. Get Balance

Retrieves the balance of a specified asset.

**Example Request:**
```python
response = api.get_balance(asset_symbol="NEAR", asset_chain="near", on_intent_contract=False)
```

**Example Response:**
```json
{"balance": 15.0}
```

---

### 3. Send Asset

Sends a specified amount of an asset to a recipient address.

**Example Request:**
```python
response = api.send(
    asset_symbol="wNEAR",
    asset_chain="near",
    to_address="zizza.near",
    amount=1.0
)
```

**Example Response:**
```json
{"tx_hash": "abc123...", "chain": "near"}
```

---

### 4. Get Token Price

Retrieves the current price of a specified asset in USD.

**Example Request:**
```python
response = api.get_token_price(
    asset_symbol="wNEAR",
    asset_chain="near"
)
```

**Example Response:**
```json
{"usd_price": 5.25, "price_updated_at": "2023-10-01T12:34:56Z"}
```

---

### 5. Get Best Quote

Retrieves the best swap quote for converting one asset into another.

**Example Request:**
```python
response = api.get_best_quote(
    asset_in_symbol="wNEAR",
    asset_in_chain="near",
    asset_out_symbol="ZEC",
    asset_out_chain="zec",
    amount_in=5.0
)
```

**Example Response:**
```json
{
  "quote_hash": "def456...",
  "amount_out": 0.25,
  "expiration_time": "2023-10-01T12:44:56Z"
}
```

---

### 6. Get Chains

Retrieves the list of supported blockchain networks.

**Example Request:**
```python
response = api.get_chains()
```

**Example Response:**
```json
{"chains": ["near", "zec"]}
```

---

### 7. Get Tokens By Chain

Retrieves the tokens available on a given blockchain.

**Example Request:**
```python
response = api.get_tokens_by_chain(chain="near")
```

**Example Response:**
```json
{"tokens": ["wNEAR", "USDT"]}
```

---

### 8. Get Chains By Token

Retrieves the chains where a specified token is available.

**Example Request:**
```python
response = api.get_chains_by_token(symbol="wNEAR")
```

**Example Response:**
```json
{"chains": ["near"]}
```

---

### 9. Deposit

Deposits a specified amount of an asset into the agent's wallet.

**Example Request:**
```python
response = api.deposit(asset_symbol="NEAR", asset_chain="near", amount=10.0)
```

**Example Response:**
```json
{"chain": "near", "tx_hash": "..."}
```

---

### 10. Swap

Swaps one asset for another across supported blockchains.

**Example Request:**
```python
response = api.swap(
    asset_in_symbol="wNEAR",
    asset_in_chain="near",
    asset_out_symbol="ZEC",
    asset_out_chain="zec",
    amount_in=5.0
)
```

**Example Response:**
```json
{
  "status": "SETTLED",
  "intent_hash": "...",
  "tx_hash": "...",
  "amount_out": 0.25
}
```

---

### 11. Withdraw

Withdraws an asset to an external address.

**Example Request:**
```python
response = api.withdraw(
    asset_symbol="ZEC",
    asset_chain="zec",
    amount=0.5,
    native_dest_address="u1a3a7km3ujtzfwywmrv759etufkwyuqve264eqavvsgcx2m7wpfk6kpt5evhqp2nq0qjrddvmp0gpr923q42ddagl7xv77uzmeckark6q"
)
```

**Example Response:**
```json
{
  "status": "TX_BROADCASTED",
  "intent_hash": "...",
  "tx_hash": "jkl012...",
  "chain": "zec"
}
```

## Submodules

This project uses the following repository as a submodule:

- [zecwallet-light-cli](https://github.com/james-katz/zecwallet-light-cli): A fully functional Zcash wallet that uses lightnode and implements NU6 network upgrade.
    - Path: `zizza/zcash/zecwallet-light-cli`

## License

This project is licensed under the **Apache License 2.0**.  

## Donations

If this project has been helpful to you and you'd like to support its development, donations are greatly appreciated! You can contribute using the following addresses:

- **Zcash**:  
  `u1a3a7km3ujtzfwywmrv759etufkwyuqve264eqavvsgcx2m7wpfk6kpt5evhqp2nq0qjrddvmp0gpr923q42ddagl7xv77uzmeckark6q`

- **NEAR**:  
  `wh00hw.near`

Thank you for your support!
