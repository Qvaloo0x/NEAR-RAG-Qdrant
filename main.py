import streamlit as st
import os
from dotenv import load_dotenv
import requests
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# CARGAR .env MUY SIMPLE
load_dotenv()

# LEER DIRECTO (tu .env YA FUNCIONA)
CMC_API_KEY = os.getenv('CMC_API_KEY')
QDRANT_URL = os.getenv('QDRANT_URL') 
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

print(f"DEBUG TERMINAL: CMC_KEY='{CMC_API_KEY}'")  # Mira la terminal

@st.cache_resource
def init_clients():
    qdrant_client = None
    model = None
    
    if QDRANT_URL and QDRANT_API_KEY:
        try:
            qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        except:
            pass
    
    try:
        model = SentenceTransformer('all-MiniLM-L6-v2')
    except:
        pass
    
    return qdrant_client, model

qdrant_client, model = init_clients()

def get_near_price_usd():
    if not CMC_API_KEY:
        return 4.20
    
    try:
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY, "Accept": "application/json"}
        params = {"symbol": "NEAR", "convert": "USD"}
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        if resp.status_code == 200:
            return float(resp.json()["data"]["NEAR"]["quote"]["USD"]["price"])
    except:
        pass
    return 4.20

def parse_swap(query):
    if "swap" in query.lower() and "for near" in query.lower():
        try:
            amount = float(query.lower().split()[1])
            price = get_near_price_usd()
            near_amount = amount / price
            return f"✅ **SWAP:** {amount} USDC → **{near_amount:.6f} NEAR**\n💰 Price: ${price:.4f}"
        except:
            return "❌ Format: `swap 1 usdc for near`"
    return None

# UI
st.title("🤖 NEAR RAG Assistant")
st.markdown("**Try:** `swap 1 usdc for near`")

# Sidebar SIMPLE
with st.sidebar:
    st.title("🔧 Status")
    st.success("✅ Interface")
    st.metric("CMC Key", f"{len(CMC_API_KEY) if CMC_API_KEY else 0} chars")
    st.metric("Qdrant URL", "OK" if QDRANT_URL else "MISSING")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Message..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    swap_result = parse_swap(prompt)
    if swap_result:
        with st.chat_message("assistant"):
            st.markdown(swap_result)
        st.session_state.messages.append({"role": "assistant", "content": swap_result})
    else:
        with st.chat_message("assistant"):
            st.info("💡 Try `swap 1 usdc for near`")
        st.session_state.messages.append({"role": "assistant", "content": "💡 Try `swap 1 usdc for near`"})
