# chain.py
import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Tuple

from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

# --- .env (carrega explicitamente) -------------------------------------------
load_dotenv(dotenv_path=".env", override=True)

RPC_URL = os.getenv("RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
RAW_CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
ETHERSCAN_BASE = os.getenv("ETHERSCAN_BASE", "https://sepolia.etherscan.io")

assert RPC_URL, "RPC_URL não definido no .env"
assert PRIVATE_KEY, "PRIVATE_KEY não definido no .env"
assert RAW_CONTRACT_ADDRESS, "CONTRACT_ADDRESS não definido (rode deploy.py e atualize o .env)"

# --- Sanitização de endereço --------------------------------------------------
HEX40_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")

def _clean_address(value: str) -> str:
    v = unicodedata.normalize("NFKC", value)
    v = v.strip().strip("'").strip('"')
    v = re.sub(r"\s+", "", v)
    if not HEX40_RE.fullmatch(v):
        raise ValueError(f"CONTRACT_ADDRESS malformado: {repr(v)} (esperado 0x + 40 hex)")
    return v

def _to_bytes32(hash_hex: str) -> bytes:
    if not isinstance(hash_hex, str):
        raise ValueError("hash deve ser string")
    clean = hash_hex.lower().strip()
    if clean.startswith("0x"):
        clean = clean[2:]
    if len(clean) != 64 or not re.fullmatch(r"[0-9a-f]{64}", clean):
        raise ValueError("hash deve ter 64 caracteres hexadecimais (0x + 64).")
    return bytes.fromhex(clean)

# --- Conexão e contrato -------------------------------------------------------
w3 = Web3(Web3.HTTPProvider(RPC_URL))
assert w3.is_connected(), "Falha ao conectar no RPC_URL"

CONTRACT_ADDRESS = _clean_address(RAW_CONTRACT_ADDRESS)
checksum_addr = Web3.to_checksum_address(CONTRACT_ADDRESS)

abi = json.loads(Path("abi.json").read_text(encoding="utf-8"))
contract = w3.eth.contract(address=checksum_addr, abi=abi)

# --- Escrita: registrar somente hash -----------------------------------------
def register_hash(hash_hex: str) -> Tuple[str, int]:
    acct = Account.from_key(PRIVATE_KEY)
    sender = acct.address
    nonce = w3.eth.get_transaction_count(sender)
    tx = contract.functions.registerReport(_to_bytes32(hash_hex)).build_transaction({
        "from": sender,
        "nonce": nonce,
        "chainId": w3.eth.chain_id,
        "maxFeePerGas": w3.to_wei("2", "gwei"),
        "maxPriorityFeePerGas": w3.to_wei("1", "gwei"),
    })
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)  # web3.py v6
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash.hex(), receipt.blockNumber

# --- Escrita: registrar hash + CID (contrato com suporte) --------------------
def register_hash_with_cid(hash_hex: str, cid: str) -> Tuple[str, int]:
    """
    Requer que o contrato tenha a função:
      registerReportWithCID(bytes32 hash, string cid)
    """
    acct = Account.from_key(PRIVATE_KEY)
    sender = acct.address
    nonce = w3.eth.get_transaction_count(sender)
    tx = contract.functions.registerReportWithCID(_to_bytes32(hash_hex), cid).build_transaction({
        "from": sender,
        "nonce": nonce,
        "chainId": w3.eth.chain_id,
        "maxFeePerGas": w3.to_wei("2", "gwei"),
        "maxPriorityFeePerGas": w3.to_wei("1", "gwei"),
    })
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash.hex(), receipt.blockNumber

# --- Leitura: verificar hash e obter CID -------------------------------------
def verify_hash(hash_hex: str):
    exists, owner, ts = contract.functions.verifyReport(_to_bytes32(hash_hex)).call()
    owner = Web3.to_checksum_address(owner) if owner and owner != "0x0000000000000000000000000000000000000000" else owner
    return exists, owner, int(ts)

def get_cid(hash_hex: str) -> str:
    """
    Requer que o contrato tenha a função:
      getCID(bytes32 hash) returns (string)
    """
    return contract.functions.getCID(_to_bytes32(hash_hex)).call()

def etherscan_tx_url(tx_hash_hex: str) -> str:
    return f"{ETHERSCAN_BASE}/tx/{tx_hash_hex}"
