import streamlit as st
import requests
import re
import os
from dotenv import load_dotenv

st.set_page_config(page_title="🤖 Y-24 NEAR Bot", layout="wide")
load_dotenv()

# 🔥 CMC DIRECTO (sin secrets)
CMC_API_KEY = os.getenv("CMC_API_KEY") or "6149fceb68f646848f2a0fe0299aba1a"

# 🔥 PRECIO CON CACHE SIMPLE
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

def is_swap(query):
    """SIMPLEST swap detector"""
    q = query.lower()
    return "swap" in q and "usdc" in q and "near" in q

st.title("🤖 Y-24 NEAR Assistant")
st.markdown("**Swaps → Rhea | Questions → Docs**")

# 🔥 SIDEBAR SIMPLE
with st.sidebar:
    st.metric("CMC Key", f"{len(CMC_API_KEY)} chars ✓")
    price = get_near_price()
    st.metric("NEAR Price", f"${price:.4f}")

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 🔥 INPUT
if prompt := st.chat_input("Try: `swap 1 usdc for near` or ask about NEAR"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # 1. SWAP FIRST
        if is_swap(prompt):
            price = get_near_price()
            numbers = re.findall(r'\d+(?:\.\d+)?', prompt.lower())
            amount = float(numbers[0]) if numbers else 1.0
            near_out = amount / price
            
            st.markdown(f"""
✅ **SWAP**: {amount} USDC → **{near_out:.6f} NEAR** 💰 Price: **${price:.4f}**

**🔗 [Rhea Finance](https://app.rhea.finance/)**

*Native NEAR DEX for USDC↔NEAR swaps*
            """)
            
        # 2. SIMPLE DOCS (sin Qdrant/DeepSeek por ahora)
        else:
            q = prompt.lower()
            if any(x in q for x in ["what is", "about", "near protocol"]):
                st.markdown("""
**🤖 NEAR Protocol** - Layer 1 Blockchain:

🔥 **Key Features:**
• **Nightshade Sharding** → 100k+ TPS
• **Fees** ~$0.01
• **EVM + WASM** compatible  
• **Account Abstraction** native
                """)
            elif "stake" in q:
                st.markdown("""
**💰 Staking NEAR:**
1. [wallet.near.org](https://wallet.near.org)
2. **Pool** → Stake → Choose validator  
3. **~10% APY**

**Top pools:** MetaPool, StakeFish
                """)
            else:
                st.info("""
**💡 Commands:**
• `swap 10 usdc for near`
• `swap 100 usd for near`  
• `what is NEAR`
• `how to stake`
                """)
    
    st.session_state.messages.append({"role": "assistant", "content": "OK"})
