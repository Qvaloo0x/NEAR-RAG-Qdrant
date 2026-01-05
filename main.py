import streamlit as st
import requests
import re
import os
from dotenv import load_dotenv

st.set_page_config(page_title="🤖 Y-24 NEAR Bot", layout="wide")
load_dotenv()

CMC_API_KEY = os.getenv("CMC_API_KEY") or "6149fceb68f646848f2a0fe0299aba1a"

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

def parse_swap_text(text):
    text = text.lower().strip()
    pattern = r"swap\s+(\d+(?:\.\d+)?)\s+(\w+)\s+(?:for|to)\s+(\w+)"
    match = re.search(pattern, text)
    if match:
        amount, from_token, to_token = match.groups()
        return float(amount), from_token.upper(), to_token.upper()
    return None

st.title("🤖 Y-24 NEAR Assistant")
st.markdown("**Swaps → Rhea | Questions → NEAR Docs**")

# 🔥 ENHANCED SIDEBAR
with st.sidebar:
    st.header("🔧 Status")
    st.metric("CMC Key", f"{len(CMC_API_KEY)} chars")
    price = get_near_price()
    st.metric("NEAR Price", f"${price:.4f}")
    st.markdown("---")
    st.info("💬 **Try:**\n• `swap 10 usdc for near`\n• `what is NEAR`\n• `how to stake`")

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 🔥 MAIN INPUT
if prompt := st.chat_input("Try: `swap 1 usdc for near` or ask about NEAR"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        parsed = parse_swap_text(prompt)
        
        if parsed:
            amount, from_token, to_token = parsed
            price = get_near_price()
            
            # 🔥 ENHANCED SWAP - More commands
            if from_token in ["USDC", "USD"] and to_token == "NEAR":
                near_out = amount / price
                st.markdown(f"""
✅ **SWAP**: {amount} {from_token} → **{near_out:.6f} NEAR** 💰 Price: **${price:.4f}**

**🔗 [Rhea Finance](https://app.rhea.finance/)**

*Native NEAR DEX for USDC↔NEAR swaps*
                """)
            else:
                st.warning("💱 Only `USDC/USD → NEAR` for now")
                
        else:
            # 🔥 SIMPLE RAG - NEAR Questions
            q = prompt.lower()
            if any(x in q for x in ["what is", "que es", "near protocol"]):
                st.markdown("""
**🤖 NEAR Protocol** is a layer-1 blockchain featuring:

🔥 **Key features:**
• **Native sharding** (Nightshade) → 100k+ TPS
• **Fees** ~$0.01
• **EVM + WASM** compatible
• **Account abstraction** native
                """)
                
            elif any(x in q for x in ["stake", "staking"]):
                st.markdown("""
**💰 Staking NEAR:**
1. [wallet.near.org](https://wallet.near.org)
2. **Pool** → Stake → Choose validator
3. **~10% APY**

**Top pools:** MetaPool, StakeFish
                """)
                
            elif any(x in q for x in ["bridge", "puente"]):
                st.markdown("""
**🌉 Bridges to NEAR:**
• [Rainbow Bridge](https://rainbowbridge.app) ← ETH/USDC
• [LayerZero](https://layerzero.network) ← Multi-chain
• [Axelar](https://axelar.network) ← Cosmos/Solana
                """)
                
            else:
                st.info("""
**💡 Available commands:**
• `swap 10 usdc for near`
• `swap 100 usd for near`
• `what is NEAR`
• `how to stake`
• `bridge eth to near`
                """)
    
    st.session_state.messages.append({"role": "assistant", "content": "OK"})
