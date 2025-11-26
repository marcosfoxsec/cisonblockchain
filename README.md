# 🛡️ CIS Controls (IG1 / IG2 / IG3) • Blockchain Proof (Sepolia + IPFS)

Este projeto implementa uma **Prova de Conformidade e Maturidade Cibernética baseada nos CIS Controls v8**, permitindo registrar **hashes de relatórios** e **artefatos de evidência** na **blockchain Sepolia (Ethereum Testnet)** e armazenar o relatório completo em **IPFS via Pinata**.

O sistema utiliza Python + Streamlit como front-end interativo, Web3.py para integração com smart contracts e análise de maturidade baseada em CMMI.

---

## 📁 Estrutura de Pastas

```bash
cis_ig1_blockchain/
│
├── app.py                    # Interface principal em Streamlit
├── chain.py                  # Funções de integração com o contrato Ethereum (Sepolia)
├── cis_v8_safeguards.json    # Banco de perguntas e controles CIS Controls (v8)
├── .env                      # Variáveis de ambiente (chaves e endpoints)
├── requirements.txt          # Dependências Python
│
├── ProofOfReport.sol         # Smart Contract (Solidity)
├── deploy.py                 # Script de implantação do contr
└── README.md                 # Este documento
```

---

## 🧰 Tecnologias Utilizadas

| Categoria | Tecnologia | Função |
|------------|-------------|--------|
| **Interface** | [Streamlit](https://streamlit.io/) | Criação da interface web interativa |
| **Blockchain** | [Web3.py](https://web3py.readthedocs.io/) | Comunicação com o contrato inteligente na rede Ethereum |
| **Smart Contract** | Solidity + Sepolia Testnet | Registro imutável dos hashes de relatório |
| **Armazenamento Descentralizado** | [Pinata API (IPFS)](https://pinata.cloud/) | Upload dos relatórios JSON completos |
| **Análise de Maturidade** | Modelo [CMMI](https://cmmiinstitute.com/) | Conversão das respostas CIS em níveis de maturidade (1 a 5) |
| **Ambiente** | Python 3.13 + dotenv | Gestão das variáveis e credenciais |
| **Visualização** | Matplotlib + NumPy | Gráfico radar (CMMI por controle) |

---

## 🔑 Configuração e Chaves de API (.env)

Crie um arquivo `.env` na raiz do projeto com o seguinte conteúdo:

```bash
# === Configuração do ambiente CIS IG1 Blockchain ===

# RPC Sepolia via Alchemy (testnet segura)
RPC_URL=https://eth-sepolia.g.alchemy.com/v2/<sua_api_key_aqui>

# ✅ Chave privada da sua carteira MetaMask (Sepolia)
PRIVATE_KEY=0x<sua_chave_privada_aqui>

# Endereço do contrato (atualizado após deploy)
CONTRACT_ADDRESS=0x<b20387f4d76e0448cbd04b0c01bd336175da609

# Base do Etherscan (explorador da rede)
ETHERSCAN_BASE=https://sepolia.etherscan.io

# Endereço público da conta (para exibição)
ACCOUNT_PUBLIC=0x1ad3e50f0c4073244cb324f89b7b43f6bdb8d1f

# === Upload IPFS via Pinata ===
PINATA_JWT=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ...<chave_gerada_no_painel_Pinata>
PINATA_ENDPOINT=https://api.pinata.cloud/pinning/pinJSONToIPFS
```

---

## ⚙️ Fluxo de Funcionamento

### 1. Geração do Relatório CIS
O usuário preenche o **questionário CIS Controls v8** (IG1, IG2, IG3).  
O sistema calcula automaticamente a maturidade por controle, gera um **hash SHA-256** do relatório e exibe o **nível CMMI médio**.

### 2. Upload no IPFS
O relatório completo (JSON) é enviado ao **IPFS via Pinata**, que retorna um **CID (Content Identifier)**.  
Esse CID é uma referência única e descentralizada ao arquivo armazenado.

### 3. Registro na Blockchain (Sepolia)
O hash do relatório e o CID (opcional) são enviados ao **Smart Contract implantado em Sepolia**:
- `registerReport()` → registra apenas o hash  
- `registerReportWithCID()` → registra hash + CID (recomendado)  
- Se o hash já existir, o contrato retorna:  
  ⚠️ “Hash já registrado — nenhuma nova transação foi enviada.”

### 4. Verificação
Na aba “Verificar”, o usuário insere um hash (0x + 64 hex) e o sistema consulta:
- `owner` (carteira que registrou)
- `timestamp` (data do registro)
- `CID` (caso disponível, com link direto ao IPFS)

---

## 🧮 Saída e Relatórios

- **Arquivo JSON gerado automaticamente**, com:
  - Respostas CIS Controls IG1–IG3
  - Percentual por controle
  - Nível CMMI (1 a 5)
  - Hash (SHA-256)
- **Gráfico radar (spider chart)** mostrando a maturidade por controle.
- **Registro público e verificável** no Etherscan (rede Sepolia).

---

## 🚀 Como Executar Localmente

```bash
# 1️⃣ Clone o repositório
git clone https://github.com/<seu_usuario>/cis_ig1_blockchain.git
cd cis_ig1_blockchain

# 2️⃣ Instale dependências
pip install -r requirements.txt

# 3️⃣ Configure o .env conforme instruções acima

# 4️⃣ Execute o app
streamlit run app.py
```

Acesse em [http://localhost:8501](http://localhost:8501)

---

## 👨‍💻 Desenvolvido por
**Marcos Paulo Castro Pereira**  
PoC acadêmica e corporativa: *Automação de Provas de Conformidade em Blockchain para Avaliação de Maturidade Cibernética (CIS + CMMI)*  

> Ferramentas: Python • Streamlit • Web3.py • Solidity • Pinata • Sepolia Testnet  
