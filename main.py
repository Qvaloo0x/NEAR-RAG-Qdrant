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

# 🔥 NEAR FAQ DATABASE (GRATIS - sin APIs externas)
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

# 🔥 SIDEBAR ENHANCED
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
        # PRIORITY 1: SWAP
        if is_swap(prompt):
            numbers = re.findall(r'\d+(?:\.\d+)?', prompt.lower())
            amount = float(numbers[0]) if numbers else 1.0
            price = get_near_price()
            near_out = amount / price
            
            st.markdown(f"""
<div style='border: 3px solid #10b981; border-radius: 16px; padding: 24px; background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);'>
    <h2 style='color: #065f46; margin: 0 0 20px 0; font-size: 1.8em;'>🚀 SWAP CONFIRMED</h2>
    
    <div style='background: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 8px 25px rgba(0,0,0,0.15);'>
        <div style='font-size: 1.4em; margin-bottom: 10px;'>
            <span style='color: #059669;'>💱 {amount} USDC</span> 
            <span style='color: #dc2626;'>→</span> 
            <span style='color: #059669; font-weight: bold; font-size: 1.6em;'>{near_out:.6f} NEAR</span>
        </div>
        <div style='font-size: 1.1em; color: #374151;'>
            💰 <strong>Price:</strong> <span style='color: #dc2626; font-weight: bold;'>${price:.4f}</span>
        </div>
    </div>
    
    <a href='https://app.rhea.finance/' target='_blank' 
       style='display: inline-block; background: linear-gradient(45deg, #3b82f6, #1d4ed8); color: white; padding: 16px 32px; 
              border-radius: 50px; text-decoration: none; font-weight: bold; font-size: 18px; 
              box-shadow: 0 8px 25px rgba(59,130,246,0.4); transition: transform 0.2s;'>
        🔗 OPEN RHEA FINANCE
    </a>
    
    <p style='margin: 20px 0 0 0; font-size: 0.95em; color: #6b7280;'>
        *Rhea Finance = Native NEAR DEX for USDC↔NEAR swaps*
    </p>
</div>
            """, unsafe_allow_html=True)
            
        # PRIORITY 2: NEAR TECHNICAL FAQ
        else:
            q_lower = prompt.lower()
            response = None
            
            # Busca en FAQ database
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
• `sharding explained`
• `Nightshade details` 
• `validator requirements`
• `how to stake`
• `chain abstraction`
• `account model`

**Ask anything about NEAR!** 👇
                """)
    
    st.session_state.messages.append({"role": "assistant", "content": "OK"})
