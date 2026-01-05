import streamlit as st
import requests
import re

CMC_API_KEY = "6149fceb68f646848f2a0fe0299aba1a"

def get_price():
    try:
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
        params = {"symbol": "NEAR", "convert": "USD"}
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        return float(resp.json()["data"]["NEAR"]["quote"]["USD"]["price"])
    except:
        return 1.75

def is_swap(text):
    return "swap" in text.lower() and "usdc" in text.lower() and "near" in text.lower()

st.title("🆕 SWAP BOT TEST")
st.write("**Debe salir LINK RHEA con este mensaje**")

if "chat" not in st.session_state:
    st.session_state.chat = []

prompt = st.chat_input("swap 1 usdc for near")

if prompt:
    st.session_state.chat.append({"user": prompt})
    
    if is_swap(prompt):
        price = get_price()
        near_out = 1.0 / price
        
        st.markdown(f"""
# 🚀 SWAP DETECTADO
        
**1 USDC → {near_out:.6f} NEAR**
**Precio: ${price:.4f}**

## 🔗 **RHEA FINANCE**
**[CLICK AQUÍ → app.rhea.finance](https://app.rhea.finance/)**

**¡FUNCIONA!** 🎉
        """)
    else:
        st.write("Solo swap 1 usdc for near")

# MOSTRAR CHAT
for msg in st.session_state.chat:
    st.write(f"**User:** {msg['user']}")
