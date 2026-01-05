import streamlit as st
import requests

CMC_API_KEY = st.secrets.get("CMC_API_KEY", "6149fceb68f646848f2a0fe0299aba1a")

st.title("🧪 RHEA TEST")
prompt = st.chat_input("swap 1 usdc for near")

if prompt and "swap" in prompt.lower():
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    resp = requests.get(url, params={"symbol": "NEAR", "convert": "USD"},
                       headers={"X-CMC_PRO_API_KEY": CMC_API_KEY})
    price = resp.json()["data"]["NEAR"]["quote"]["USD"]["price"]
    
    st.markdown(f"""
# ✅ SWAP OK
**1 USDC → {1/price:.6f} NEAR**
**Precio: ${price:.2f}**

<a href="https://app.rhea.finance/" target="_blank">
    <button style="background:#3b82f6;color:white;padding:20px 40px;border:none;border-radius:50px;font-size:20px;">
        🚀 RHEA FINANCE
    </button>
</a>
    """, unsafe_allow_html=True)
