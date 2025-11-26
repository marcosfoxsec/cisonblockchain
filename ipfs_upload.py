# ipfs_upload.py
import os
import json
import requests
from typing import Tuple

WEB3_STORAGE_TOKEN = os.getenv("WEB3_STORAGE_TOKEN")

def upload_json_to_ipfs(obj: dict) -> Tuple[str, str]:
    """
    Envia um JSON para o Web3.Storage.
    Retorna (cid, ipfs_url).
    Lança ValueError se token ausente.
    """
    if not WEB3_STORAGE_TOKEN:
        raise ValueError("WEB3_STORAGE_TOKEN não definido no .env")

    # converte para bytes (arquivo .json na requisição)
    data = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    files = {
        "file": ("relatorio.json", data, "application/json")
    }
    headers = {"Authorization": f"Bearer {WEB3_STORAGE_TOKEN}"}
    resp = requests.post("https://api.web3.storage/upload", files=files, headers=headers, timeout=60)
    resp.raise_for_status()
    j = resp.json()
    cid = j.get("cid")
    if not cid:
        raise RuntimeError(f"Resposta inesperada da Web3.Storage: {j}")
    return cid, f"ipfs://{cid}"
