# app.py
# -*- coding: utf-8 -*-
"""
CIS Controls (v8) + IG1/IG2/IG3 questionnaire -> Hash + IPFS (Pinata) -> On-chain registry (Sepolia)
- Lê todas as salvaguardas de um arquivo local opcional: cis_v8_safeguards.json
"""

import os
import io
import json
import hashlib
import unicodedata
import re
import datetime as dt
from collections import defaultdict

import requests
import streamlit as st
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import numpy as np
from web3 import Web3
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader

# -----------------------------------------------------------------------------
# Blockchain helpers (seu chain.py)
# -----------------------------------------------------------------------------
from chain import (
    register_hash,
    verify_hash,
    etherscan_tx_url,
    register_hash_with_cid,
    get_cid,
)

# -----------------------------------------------------------------------------
# ENV & Provedores
# -----------------------------------------------------------------------------
load_dotenv(dotenv_path=".env", override=True)

# Pinata (recomendado)
PINATA_JWT = (os.getenv("PINATA_JWT") or "").strip()
PINATA_ENDPOINT = (os.getenv("PINATA_ENDPOINT") or "https://api.pinata.cloud/pinning/pinJSONToIPFS").strip()

# (Opcional) NFT.Storage clássico (JWT) e Web3.Storage – mantidos como fallback
NFT_STORAGE_TOKEN = (os.getenv("NFT_STORAGE_TOKEN") or "").strip()
NFT_STORAGE_API   = (os.getenv("NFT_STORAGE_API") or "https://api.nft.storage/upload").strip()
WEB3_STORAGE_TOKEN = (os.getenv("WEB3_STORAGE_TOKEN") or "").strip()

# -----------------------------------------------------------------------------
# Utilidades
# -----------------------------------------------------------------------------
def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9_-]+", "-", text).strip("-")
    return text or "empresa"

def sha256_hex(data: bytes) -> str:
    return "0x" + hashlib.sha256(data).hexdigest()

def keccak256_hex(data: bytes) -> str:
    """Keccak-256 (Ethereum) usando Web3.py. Retorna com prefixo 0x."""
    return Web3.keccak(data).hex()

def normalize_hash(h: str) -> str | None:
    if not h:
        return None
    h = unicodedata.normalize("NFKC", h).strip()
    h = h.replace(" ", "").replace("\n", "").replace("\r", "").strip("'\"")
    if h.startswith(("0x", "0X")):
        h = h[2:]
    if re.fullmatch(r"[0-9a-fA-F]{64}", h):
        return "0x" + h.lower()
    return None

# -----------------------------------------------------------------------------
# Carregamento das perguntas CIS (com fallback)
# -----------------------------------------------------------------------------
FALLBACK = [
    {"control": 1, "id": "1.1", "ig": "IG1", "title": "Inventário de ativos de hardware mantido", "control_name": "1 — Inventory and Control of Enterprise Assets"},
    {"control": 1, "id": "1.2", "ig": "IG2", "title": "Rastrear ativos temporários ou remotos", "control_name": "1 — Inventory and Control of Enterprise Assets"},
    {"control": 1, "id": "1.3", "ig": "IG3", "title": "Automatizar descoberta de ativos", "control_name": "1 — Inventory and Control of Enterprise Assets"},
    {"control": 2, "id": "2.1", "ig": "IG1", "title": "Inventário de software autorizado", "control_name": "2 — Inventory and Control of Software Assets"},
    {"control": 2, "id": "2.2", "ig": "IG2", "title": "Bloquear instalações não autorizadas", "control_name": "2 — Inventory and Control of Software Assets"},
    {"control": 3, "id": "3.1", "ig": "IG1", "title": "Proteção de dados em repouso (criptografia básica)", "control_name": "3 — Data Protection"},
    {"control": 3, "id": "3.5", "ig": "IG2", "title": "Classificação de dados sensíveis", "control_name": "3 — Data Protection"},
    {"control": 3, "id": "3.7", "ig": "IG3", "title": "DLP aplicado a SaaS", "control_name": "3 — Data Protection"},
    {"control": 4, "id": "4.1", "ig": "IG1", "title": "Defesa contra malware em endpoints", "control_name": "4 — Secure Configuration of Enterprise Assets and Software"},
    {"control": 4, "id": "4.6", "ig": "IG2", "title": "Hardening padronizado (CIS Benchmarks)", "control_name": "4 — Secure Configuration of Enterprise Assets and Software"},
    {"control": 5, "id": "5.1", "ig": "IG1", "title": "Políticas de acesso e identidade básicas", "control_name": "5 — Account Management"},
    {"control": 5, "id": "5.6", "ig": "IG2", "title": "Revisões periódicas de acessos", "control_name": "5 — Account Management"},
    {"control": 5, "id": "5.9", "ig": "IG3", "title": "Automatizar recertificação de acessos", "control_name": "5 — Account Management"},
    {"control": 16, "id": "16.1", "ig": "IG1", "title": "Treinamento de conscientização (básico)", "control_name": "16 — Security Awareness and Skills Training"},
    {"control": 16, "id": "16.3", "ig": "IG2", "title": "Simulações de phishing", "control_name": "16 — Security Awareness and Skills Training"},
    {"control": 16, "id": "16.7", "ig": "IG3", "title": "Programa de skills por função", "control_name": "16 — Security Awareness and Skills Training"},
    {"control": 17, "id": "17.1", "ig": "IG1", "title": "Resposta a incidentes: plano básico", "control_name": "17 — Incident Response Management"},
    {"control": 17, "id": "17.5", "ig": "IG2", "title": "Tabletop exercises recorrentes", "control_name": "17 — Incident Response Management"},
    {"control": 17, "id": "17.7", "ig": "IG3", "title": "Integração de forense e e-discovery", "control_name": "17 — Incident Response Management"},
    {"control": 18, "id": "18.1", "ig": "IG2", "title": "Pentest externo anual", "control_name": "18 — Penetration Testing"},
    {"control": 18, "id": "18.2", "ig": "IG3", "title": "Red Team orientado a objetivos", "control_name": "18 — Penetration Testing"},
]

def load_cis_safeguards() -> list[dict]:
    json_path = "cis_v8_safeguards.json"
    if os.path.isfile(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert isinstance(data, list) and len(data) > 0
            for item in data:
                assert {"control", "id", "ig", "title", "control_name"} <= set(item.keys())
            return data
        except Exception as e:
            st.warning(f"Falha ao ler '{json_path}': {e}. Usando fallback reduzido.")
    return FALLBACK

# -----------------------------------------------------------------------------
# Cálculo de maturidade (CMMI 1–5) por controle
# -----------------------------------------------------------------------------
CHOICES = ["Implementado", "Parcial", "Não implementado", "Não se aplica"]

def score_answer(a: str) -> float:
    if a == "Implementado":
        return 1.0
    if a == "Parcial":
        return 0.5
    if a == "Não se aplica":
        return 1.0  # N/A não penaliza
    return 0.0

def cmmi_level_from_igs(p_ig1: float, p_ig2: float, p_ig3: float) -> int:
    if p_ig1 < 0.2 and p_ig2 < 0.2:
        return 1
    if p_ig1 >= 0.80 and p_ig2 < 0.40:
        return 2
    if p_ig1 >= 0.80 and p_ig2 >= 0.50 and p_ig3 < 0.40:
        return 3
    if p_ig1 >= 0.80 and p_ig2 >= 0.70 and p_ig3 >= 0.40:
        return 5 if (p_ig1 >= 0.90 and p_ig2 >= 0.85 and p_ig3 >= 0.70) else 4
    return 2 if p_ig1 >= 0.5 else 1

def compute_maturity(respostas_by_id: dict, safeguards: list[dict]):
    by_control = defaultdict(lambda: {"name": "", "IG1": [], "IG2": [], "IG3": []})
    for s in safeguards:
        by_control[s["control"]]["name"] = s["control_name"]
        by_control[s["control"]][s["ig"]].append(s["id"])

    maturity = {}
    all_levels = []
    for ctrl, bucket in by_control.items():
        ig_perc = {}
        for ig in ["IG1", "IG2", "IG3"]:
            ids = bucket[ig]
            if not ids:
                ig_perc[ig] = 0.0
                continue
            scores = []
            for sid in ids:
                ans = respostas_by_id.get(sid, "Não implementado")
                scores.append(score_answer(ans))
            ig_perc[ig] = sum(scores) / len(scores)

        cmmi = cmmi_level_from_igs(ig_perc["IG1"], ig_perc["IG2"], ig_perc["IG3"])
        maturity[ctrl] = {
            "name": bucket["name"],
            "ig1": ig_perc["IG1"],
            "ig2": ig_perc["IG2"],
            "ig3": ig_perc["IG3"],
            "cmmi": cmmi,
        }
        all_levels.append(cmmi)

    cmmi_avg = sum(all_levels) / len(all_levels) if all_levels else 0.0
    return maturity, cmmi_avg

# -----------------------------------------------------------------------------
# IPFS Upload (Pinata + fallbacks)
# -----------------------------------------------------------------------------
def ipfs_upload_json_pinata(obj: dict) -> tuple[str, str, str]:
    if not PINATA_JWT:
        raise RuntimeError("PINATA_JWT não definido no .env")
    company = (obj.get("company") or "empresa").strip()
    name = f"cis_ig1_ig2_ig3_{slugify(company)}_{dt.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}"
    payload = {"pinataContent": obj, "pinataMetadata": {"name": name}}
    headers = {"Authorization": f"Bearer {PINATA_JWT}", "Content-Type": "application/json"}
    r = requests.post(PINATA_ENDPOINT, headers=headers, json=payload, timeout=60)
    if not r.ok:
        raise RuntimeError(f"{PINATA_ENDPOINT} -> {r.status_code}: {r.text}")
    data = r.json()
    cid = data.get("IpfsHash")
    if not cid:
        raise RuntimeError(f"Pinata respondeu sem CID: {data}")
    return cid, f"ipfs://{cid}", "pinata"

def _post_multipart(url: str, token: str, filename: str, data_bytes: bytes) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": (filename, data_bytes, "application/json")}
    resp = requests.post(url, headers=headers, files=files, timeout=60)
    if not resp.ok:
        raise RuntimeError(f"{url} -> {resp.status_code}: {resp.text}")
    return resp.json()

def ipfs_upload_json_auto(obj: dict) -> tuple[str, str, str]:
    if PINATA_JWT:
        return ipfs_upload_json_pinata(obj)
    if NFT_STORAGE_TOKEN and NFT_STORAGE_TOKEN.startswith("eyJ"):
        b = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        j = _post_multipart(NFT_STORAGE_API, NFT_STORAGE_TOKEN, "relatorio.json", b)
        cid = (j.get("value") or {}).get("cid") if j.get("ok") else None
        if not cid:
            raise RuntimeError(f"NFT.Storage respondeu sem CID: {j}")
        return cid, f"ipfs://{cid}", "nft.storage"
    if WEB3_STORAGE_TOKEN:
        b = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        j = _post_multipart("https://api.web3.storage/upload", WEB3_STORAGE_TOKEN, "relatorio.json", b)
        cid = j.get("cid") or ((j.get("value") or {}).get("cid") if j.get("ok") else None)
        if not cid:
            raise RuntimeError(f"Web3.Storage respondeu sem CID: {j}")
        return cid, f"ipfs://{cid}", "web3.storage"
    raise RuntimeError("Nenhum provedor IPFS configurado. Defina PINATA_JWT (recomendado) "
                       "ou NFT_STORAGE_TOKEN (JWT clássico) ou WEB3_STORAGE_TOKEN.")

# -----------------------------------------------------------------------------
# Radar (gráfico aranha) + PDF
# -----------------------------------------------------------------------------
def plot_radar(maturity_per_control: dict[int, dict], figsize=(4, 4), return_png: bool = False):
    controls = sorted(maturity_per_control.keys())
    labels = [f"C{c}" for c in controls]
    values = [maturity_per_control[c]["cmmi"] for c in controls]

    N = len(values)
    if N == 0:
        st.info("Sem dados para o gráfico.")
        return None

    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    values_plot = values + values[:1]
    angles_plot = angles + angles[:1]

    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, polar=True)
    ax.plot(angles_plot, values_plot, linewidth=2)
    ax.fill(angles_plot, values_plot, alpha=0.15)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_ylim(0, 5)
    ax.set_xticks(angles)
    ax.set_xticklabels(labels)
    ax.set_title("Maturidade (CMMI) por Controle")
    st.pyplot(fig, clear_figure=True)

    if return_png:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=180, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf.read()
    return None

def build_pdf(report: dict, cmmi_avg: float, radar_png: bytes | None) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    top = H - 2 * cm

    c.setFont("Helvetica-Bold", 14)
    c.drawString(2*cm, top, "CIS Controls • Prova de Integridade")

    c.setFont("Helvetica", 10)
    c.drawString(2*cm, top-0.8*cm, f"Empresa: {report.get('company','-')}")
    c.drawString(2*cm, top-1.4*cm, f"Gerado em: {report.get('generated_at','-')}")
    c.drawString(2*cm, top-2.0*cm, f"CMMI médio: {cmmi_avg:.2f} / 5")

    if radar_png:
        img = ImageReader(io.BytesIO(radar_png))
        c.drawImage(img, 2*cm, H/2 - 2*cm, width=10*cm, height=10*cm, preserveAspectRatio=True, mask='auto')

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()

# -----------------------------------------------------------------------------
# Streamlit State
# -----------------------------------------------------------------------------
st.set_page_config(page_title="CIS Controls IG1/IG2/IG3 — Blockchain Proof", page_icon="🛡️", layout="wide")
if "answers" not in st.session_state:
    st.session_state.answers = {}
if "last_report" not in st.session_state:
    st.session_state.last_report = None
if "last_hash" not in st.session_state:
    st.session_state.last_hash = ""
if "last_cid" not in st.session_state:
    st.session_state.last_cid = ""
if "company" not in st.session_state:
    st.session_state.company = ""
if "form_key" not in st.session_state:
    st.session_state.form_key = "form_cis_full_main"

# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------
st.title("CIS Controls (IG1/IG2/IG3) • Prova em Blockchain")

left, right = st.columns([2, 1])
with left:
    st.caption("Preencha o questionário (carrega 100% se existir `cis_v8_safeguards.json`; caso contrário, usa fallback reduzido).")
with right:
    st.text_input("Nome da empresa", key="company", placeholder="Minha Empresa LTDA")

safeguards = load_cis_safeguards()

# Abas (inclui nova aba Arquivo/Texto → Hash)
tabs = st.tabs([
    "Questionário", "Arquivo/Texto → Hash", "Relatório & Ações", "Registrar", "Verificar"
])

# --- TAB: QUESTIONÁRIO --------------------------------------------------------
with tabs[0]:
    st.subheader("Questionário CIS v8")
    grouped = defaultdict(lambda: defaultdict(list))
    control_names = {}
    for s in safeguards:
        grouped[s["control"]][s["ig"]].append(s)
        control_names[s["control"]] = s["control_name"]

    with st.form(key=st.session_state.form_key):
        for control in sorted(grouped.keys()):
            st.markdown(f"### Controle {control} — {control_names[control]}")
            cols = st.columns(3)
            for idx, ig in enumerate(["IG1", "IG2", "IG3"]):
                with cols[idx]:
                    st.markdown(f"**{ig}**")
                    for item in sorted(grouped[control][ig], key=lambda x: x["id"]):
                        key = f"ans_{item['id']}"
                        default = st.session_state.answers.get(key, "Não implementado")
                        st.session_state.answers[key] = st.selectbox(
                            f"{item['id']} — {item['title']}",
                            CHOICES,
                            index=CHOICES.index(default),
                            key=key,
                        )
        submitted = st.form_submit_button("Gerar relatório")

    if submitted:
        company = (st.session_state.company or "").strip()
        if not company:
            st.error("Informe o nome da empresa.")
            st.stop()

        respostas_by_id = {k.replace("ans_", ""): v for k, v in st.session_state.answers.items()}
        maturity, cmmi_avg = compute_maturity(respostas_by_id, safeguards)

        now_iso = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
        report = {
            "schema": "cis-v8/ig1-ig2-ig3/v1",
            "company": company,
            "generated_at": now_iso,
            "safeguards": safeguards,
            "answers": respostas_by_id,
            "maturity": maturity,
            "cmmi_avg": cmmi_avg,
        }
        report_json = json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        h = sha256_hex(report_json.encode("utf-8"))

        st.session_state.last_report = report
        st.session_state.last_hash = h

        st.success(f"Hash do relatório (SHA-256): {h}")
        st.download_button(
            "Baixar relatório (JSON)",
            report_json,
            file_name=f"cis_controls_{slugify(company)}_{dt.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.json",
            mime="application/json",
        )

        st.markdown("#### Radar (CMMI por Controle)")
        radar_png = plot_radar(maturity, figsize=(4, 4), return_png=True)

        cmmi_level_empresa = int(round(cmmi_avg))
        st.markdown(
            f"**Nível de maturidade (CMMI) da empresa:** {cmmi_level_empresa} / 5  "
            f"<span style='color:#94a3b8'>(média: {cmmi_avg:.2f})</span>",
            unsafe_allow_html=True
        )

        try:
            pdf_bytes = build_pdf(report, cmmi_avg, radar_png)
            st.download_button(
                "📄 Baixar relatório (PDF)",
                data=pdf_bytes,
                file_name=f"cis_controls_{slugify(company)}_{dt.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.pdf",
                mime="application/pdf",
            )
        except Exception as e:
            st.warning(f"Não foi possível gerar o PDF: {e}")

# --- NOVA TAB: ARQUIVO/TEXTO → HASH ------------------------------------------
with tabs[1]:
    st.subheader("Arquivo/Texto → Hash")
    st.caption("Gere um hash a partir de um arquivo **ou** de um texto e use o mesmo fluxo de registro/verificação.")

    algo = st.radio("Algoritmo", ["SHA-256", "Keccak-256"], horizontal=True)
    up = st.file_uploader("Envie um arquivo (opcional)", type=None)
    text = st.text_area("Ou cole o conteúdo (opcional)", height=150, placeholder="Cole aqui o conteúdo do relatório/artefato…")

    colh1, colh2 = st.columns([1, 1])
    with colh1:
        if st.button("Gerar hash"):
            data: bytes | None = None
            if up is not None:
                data = up.read()
            elif text.strip():
                data = text.encode("utf-8")
            else:
                st.error("Forneça um arquivo **ou** um texto.")
                st.stop()

            try:
                h = sha256_hex(data) if algo == "SHA-256" else keccak256_hex(data)
                st.session_state.last_hash = h
                st.success(f"Hash gerado ({algo}): {h}")
                st.code(h, language="text")
            except Exception as e:
                st.exception(e)
    with colh2:
        st.write("Último hash calculado:")
        st.code(st.session_state.get("last_hash", ""), language="text")

    st.divider()
    st.markdown("**Ações rápidas**")
    colr1, colr2 = st.columns(2)
    with colr1:
        if st.button("Registrar agora (apenas hash)"):
            norm = normalize_hash(st.session_state.get("last_hash", ""))
            if not norm:
                st.error("Gere ou informe um hash válido (0x + 64 hex).")
            else:
                try:
                    tx, block = register_hash(norm)
                    st.success(f"Hash registrado no bloco {block}")
                    st.write("Tx:", etherscan_tx_url(tx))
                except Exception as e:
                    msg = str(e)
                    if ("Hash ja registrado" in msg) or ("execution reverted" in msg and "Hash" in msg and "registrado" in msg):
                        st.warning("⚠️ Este hash já foi registrado anteriormente. Nenhuma nova transação foi enviada.")
                    else:
                        st.exception(e)
    with colr2:
        if st.button("Verificar agora"):
            norm = normalize_hash(st.session_state.get("last_hash", ""))
            if not norm:
                st.error("Gere ou informe um hash válido (0x + 64 hex).")
            else:
                try:
                    ok, owner, ts = verify_hash(norm)
                    if ok:
                        dt_utc = dt.datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S UTC")
                        st.success(f"Encontrado — Owner={owner} • Timestamp={dt_utc}")
                        try:
                            cid = get_cid(norm)
                            if cid:
                                st.info(f"CID: {cid}\nhttps://ipfs.io/ipfs/{cid}")
                        except Exception:
                            pass
                    else:
                        st.warning("Não encontrado.")
                except Exception as e:
                    st.exception(e)

# --- TAB: RELATÓRIO & AÇÕES ---------------------------------------------------
with tabs[2]:
    st.subheader("Relatório & Ações")
    if not st.session_state.last_report:
        st.info("Gere um relatório na primeira aba.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📦 Enviar relatório ao IPFS (Pinata)"):
                try:
                    cid, ipfs_url, prov = ipfs_upload_json_auto(st.session_state.last_report)
                    st.session_state.last_cid = cid
                    st.success(f"CID: {cid} (via {prov})")
                    st.write(ipfs_url)
                except Exception as e:
                    st.error(str(e))
        with col2:
            if st.button("🧾 Registrar hash + CID (Blockchain)"):
                if not st.session_state.last_cid:
                    st.error("Envie ao IPFS primeiro para obter o CID.")
                else:
                    try:
                        tx, block = register_hash_with_cid(st.session_state.last_hash, st.session_state.last_cid)
                        st.success(f"Registrado no bloco {block}")
                        st.write("Tx:", etherscan_tx_url(tx))
                    except Exception as e:
                        msg = str(e)
                        if ("Hash ja registrado" in msg) or ("execution reverted" in msg and "Hash" in msg and "registrado" in msg):
                            st.warning("⚠️ Este hash já foi registrado anteriormente. Nenhuma nova transação foi enviada.")
                        else:
                            st.exception(e)
        with col3:
            st.write("Últimos valores:")
            st.code(json.dumps({
                "hash": st.session_state.last_hash,
                "cid": st.session_state.last_cid,
            }, indent=2, ensure_ascii=False))

# --- TAB: REGISTRAR (manual) --------------------------------------------------
with tabs[3]:
    st.subheader("Registrar (manual)")
    h_in = st.text_input("Hash (0x + 64 hex)", value=st.session_state.get("last_hash", ""))
    cid_in = st.text_input("CID (IPFS) — opcional", value=st.session_state.get("last_cid", ""))

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Registrar apenas o hash"):
            norm = normalize_hash(h_in)
            if not norm:
                st.error("Hash inválido.")
            else:
                try:
                    tx, block = register_hash(norm)
                    st.success(f"Hash registrado no bloco {block}")
                    st.write("Tx:", etherscan_tx_url(tx))
                except Exception as e:
                    msg = str(e)
                    if ("Hash ja registrado" in msg) or ("execution reverted" in msg and "Hash" in msg and "registrado" in msg):
                        st.warning("⚠️ Este hash já foi registrado anteriormente. Nenhuma nova transação foi enviada.")
                    else:
                        st.exception(e)
    with c2:
        if st.button("Registrar hash + CID"):
            norm = normalize_hash(h_in)
            if not norm:
                st.error("Hash inválido.")
            elif not cid_in.strip():
                st.error("Informe o CID para este modo.")
            else:
                try:
                    tx, block = register_hash_with_cid(norm, cid_in.strip())
                    st.success(f"Hash + CID registrados no bloco {block}")
                    st.write("Tx:", etherscan_tx_url(tx))
                except Exception as e:
                    msg = str(e)
                    if ("Hash ja registrado" in msg) or ("execution reverted" in msg and "Hash" in msg and "registrado" in msg):
                        st.warning("⚠️ Este hash já foi registrado anteriormente. Nenhuma nova transação foi enviada.")
                    else:
                        st.exception(e)

# --- TAB: VERIFICAR -----------------------------------------------------------
with tabs[4]:
    st.subheader("Verificar hash")
    h_lookup = st.text_input("Hash para verificar", value=st.session_state.get("last_hash", ""))
    if st.button("Verificar"):
        norm = normalize_hash(h_lookup)
        if not norm:
            st.error("Hash inválido.")
        else:
            try:
                ok, owner, ts = verify_hash(norm)
                if ok:
                    dt_utc = dt.datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S UTC")
                    st.success(f"Encontrado — Owner={owner} • Timestamp={dt_utc}")
                    try:
                        cid = get_cid(norm)
                        if cid:
                            st.info(f"CID: {cid}\nhttps://ipfs.io/ipfs/{cid}")
                    except Exception:
                        pass
                else:
                    st.warning("Não encontrado.")
            except Exception as e:
                st.exception(e)
