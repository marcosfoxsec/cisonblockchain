import json
import os
from pathlib import Path

from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from solcx import compile_source, install_solc

# Carrega .env explicitamente (evita bug do find_dotenv em here-doc)
load_dotenv(dotenv_path=".env", override=True)

RPC_URL = os.getenv("RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
assert RPC_URL, "RPC_URL não definido no .env"
assert PRIVATE_KEY, "PRIVATE_KEY não definido no .env"

# Lê o contrato Solidity
SOURCE_PATH = Path("ProofOfReport.sol")
assert SOURCE_PATH.exists(), "Arquivo ProofOfReport.sol não encontrado"
source = SOURCE_PATH.read_text(encoding="utf-8")

# Compila com solc 0.8.20 (instala se necessário)
install_solc("0.8.20")
compiled = compile_source(
    source,
    output_values=["abi", "bin"],
    solc_version="0.8.20",
)
(_, contract_interface), = compiled.items()
ABI = contract_interface["abi"]
BYTECODE = contract_interface["bin"]

# Conecta na rede
w3 = Web3(Web3.HTTPProvider(RPC_URL))
assert w3.is_connected(), "Falha ao conectar no RPC_URL"

acct = Account.from_key(PRIVATE_KEY)
sender = acct.address
print("Using sender:", sender)

# Prepara a transação de deploy (EIP-1559)
Proof = w3.eth.contract(abi=ABI, bytecode=BYTECODE)
nonce = w3.eth.get_transaction_count(sender)

# Gas params (seguros para testnet; ajuste se necessário)
tx = Proof.constructor().build_transaction({
    "from": sender,
    "nonce": nonce,
    "chainId": w3.eth.chain_id,
    "maxFeePerGas": w3.to_wei("2", "gwei"),
    "maxPriorityFeePerGas": w3.to_wei("1", "gwei"),
})

# Assina e envia
signed = acct.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)  # <- web3.py v6
print("Deploy enviado:", tx_hash.hex())

# Aguarda recibo
receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
address = receipt.contractAddress
print("Contrato implantado em:", address)

# Salva ABI para o app
Path("abi.json").write_text(json.dumps(ABI, indent=2))
print("ABI salva em abi.json")

# Dica: já imprime instrução para atualizar o .env
print("\nAtualize seu .env com:")
print(f"CONTRACT_ADDRESS={address}")
