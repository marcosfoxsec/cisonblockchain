# test_env.py
import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env", override=True)  # carrega .env explicitamente

rpc = os.getenv("RPC_URL")
assert rpc, "RPC_URL não definido no .env"
w3 = Web3(Web3.HTTPProvider(rpc))
print("Conectado:", w3.is_connected())
if w3.is_connected():
    print("Chain ID:", w3.eth.chain_id)
    print("Account (opcional):", os.getenv("ACCOUNT_PUBLIC"))
