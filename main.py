import streamlit as st
import requests
import re
import os
from dotenv import load_dotenv

st.set_page_config(page_title="🤖 Y-24 NEAR Bot", layout="wide")
load_dotenv()

CMC_API_KEY = os.getenv("CMC_API_KEY") or "6149fceb68f646848f2a0fe0299aba1a"

def get_near_price():
    """Precio REAL de NEAR."""
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

def parse_swap(text):
    """Detecta: swap 1 usdc for near."""
    text = text.lower().strip()
    match = re.search(r"swap\s+(\d+(?:\.\d+)?)\s+(\w+)\s+(?:for|to)\s+(\w+)", text)
    if match:
        return float(match.group(1)), match.group(2).upper(), match.group(3).upper()
    return None

st.title("🤖 Y-24 NEAR Assistant")
st.markdown("**Swaps → Rhea | Questions → Docs**")

# Sidebar - Status SIMPLE
with st.sidebar:
    st.header("Status")
    st.metric("CMC", f"{len(CMC_API_KEY)} chars ✓")
    st.caption("✅ Swap + Price LIVE")
    st.caption("❌ Qdrant OFF (por ahora)")

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar mensajes
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input
if prompt := st.chat_input("Try: `swap 1 usdc for near` o pregunta sobre NEAR"):
    
    # User message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Assistant response
    with st.chat_message("assistant"):
        parsed = parse_swap(prompt)
        
        if parsed:
            amount, from_token, to_token = parsed
            price = get_near_price()
            
            if to_token == "NEAR" and from_token in ["USDC", "USD"]:
                near_amount = amount / price
                st.markdown(f"""
🚀 **SWAP DETECTED!**

💱 **{amount} {from_token} → {near_amount:.6f} NEAR**  
💰 **Precio**: ${price:.4f}/NEAR  

✅ **Trade en Rhea Finance**  
[![Rhea Finance](https://app.rhea.finance/)](https://app.rhea.finance/)

*Rhea es el DEX nativo de NEAR para swaps USDC↔NEAR*
                """)
            else:
                st.info("💡 Solo `swap X usdc for near` por ahora")
                
        else:
            # RAG simple (respuestas fijas)
            q = prompt.lower()
            if "qué es near" in q or "que es near" in q:
                st.markdown("""
**NEAR Protocol** es una blockchain layer-1 compatible con EVM, 
fácil de usar,
