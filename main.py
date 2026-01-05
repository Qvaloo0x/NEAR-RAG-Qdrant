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

st.title("🤖 Y-24 NEAR Swap Bot")
st.markdown("*Say: `swap 1 usdc for near`*")

with st.sidebar:
    st.metric("CMC Key", f"{len(CMC_API_KEY)} chars")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Try: swap 1 usdc for near"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        parsed = parse_swap_text(prompt)
        if parsed:
            amount, from_token, to_token = parsed
            price = get_near_price()
            
            if to_token == "NEAR":
                near_out = amount / price
                st.markdown(f"✅ **SWAP**: {amount} {from_token} → {near_out:.6f} NEAR 💰 Price: ${price:.4f}")
                st.markdown("**🔗 [Rhea Finance](https://app.rhea.finance/)**")
            else:
                st.info("Only USDC→NEAR")
        else:
            st.info("💡 Try: `swap 1 usdc for near`")
    
    st.session_state.messages.append({"role": "assistant", "content": "OK"})
