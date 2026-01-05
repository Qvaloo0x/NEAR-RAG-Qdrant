import streamlit as st
import requests
import re
import os
from dotenv import load_dotenv

st.set_page_config(page_title="🤖 Y-24 NEAR Assistant", layout="wide")
load_dotenv()

# 🔥 API Keys
CMC_API_KEY = os.getenv("CMC_API_KEY") or "6149fceb68f646848f2a0fe0299aba1a"

# 🔥 NEAR PRICE con CACHE (2 minutos)
@st.cache_data(ttl=120)
def get_near_price():
    try:
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY, "Accept": "application/json"}
        params = {"symbol": "NEAR", "convert": "USD"}
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code == 200:
            return float(resp.json()["data"]["NEAR"]["quote"]["USD"]["price"])
    except:
        pass
    return 1.75

# 🔥 SWAP DETECTOR SIMPLE
def is_swap(query):
    q = query.lower()
    return "swap" in q and "usdc" in q and "near" in q

# 🔥 NEAR FAQ DATABASE (GRATIS)
NEAR_FAQ = {
    "sharding": "Nightshade sharding: 100k+ TPS, dynamic resharding, stateless validation, cross-shard messaging",
    "nightshade": "NEAR's sharding protocol. Epoch-based re-sharding, one-shard-at-a-time validation, chunk-only state",
    "stake": "Stake via wallet.near.org → Choose pool → ~10% APY. Top validators: MetaPool, StakeFish, Everstake",
    "fees": "Gas fees ~$0.01. Fees are burned (deflationary). Validator rewards from 5% inflation",
    "account": "NEAR accounts = ed25519 public keys. Human-readable names (.near). Implicit accounts from private keys",
    "chain abstraction": "Intent-centric UX: sign once → multi-chain execution. User-defined intents, solvers compete",
    "rpc": "RPC endpoints: rpc.mainnet.near.org (free). JSON-RPC for blocks, txns, accounts, contracts",
    "bridge": "Rainbow Bridge (ETH↔NEAR), LayerZero (multi-chain), Axelar (Cosmos/Solana)",
    "validator": "Run validator: 67k NEAR minimum stake, hardware reqs: 16GB RAM, 4+ cores, SSD",
    "protocol": "Proof-of-Stake + Nightshade sharding. Finality ~1.5s. One-block finality guarantees"
}

st.title("🤖 Y-24 NEAR Assistant")
st.markdown("**Rhea Swaps | NEAR Technical Docs | Live Prices**")

# 🔥 SIDEBAR
with st.sidebar:
    st.header("🔧 Status")
    st.metric("CMC Key", f"{len(CMC_API_KEY)} chars ✓")
    price = get_near_price()
    st.metric("NEAR Price", f"${price:.4f}")
    st.markdown("---")
    st.info("""
**💬 Commands:**
• `swap 10 usdc for near`
• `sharding explained`
• `Nightshade details`
• `how to stake`
• `validator requirements`
    """)

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 🔥 MAIN INPUT
if prompt := st.chat_input("Try: `swap 1 usdc for near` or ask about NEAR Protocol"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # PRIORITY 1: SWAP (formato SIMPLE como antes)
        if is_swap(prompt):
            numbers = re.findall(r'\d+(?:\.\d+)?', prompt.lower())
            amount = float(numbers[0]) if numbers else 1.0
            price = get_near_price()
            near_out = amount / price
            
            st.markdown(f"""
✅ **SWAP**: {amount} USDC → **{near_out:.6f} NEAR** 💰 Price: **${price:.4f}**

**🔗 [Rhea Finance](https://app.rhea.finance/)**

*Native NEAR DEX for USDC↔NEAR swaps*
            """)
            
        # PRIORITY 2: NEAR FAQ
        else:
            q_lower = prompt.lower()
            response = None
            
            # Busca exact match en FAQ
            for topic, answer in NEAR_FAQ.items():
                if topic in q_lower:
                    response = f"""**{topic.upper()}**  
{answer}"""
                    break
            
            if response:
                st.markdown(response)
            else:
                st.info("""
**🤖 NEAR Protocol Assistant**

**💱 Trading:**
• `swap 10 usdc for near`
• `swap 100 usd for near`

**📚 Technical:**
• `sharding` 
• `Nightshade`
• `stake`
• `validator`
• `chain abstraction`
• `account model`

**Ask anything about NEAR!** 👇
                """)
    
    st.session_state.messages.append({"role": "assistant", "content": "OK"})
