import streamlit as st
import os
from dotenv import load_dotenv
import requests
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# Carga EXPLÍCITA del .env PRIMERO
load_dotenv(dotenv_path='.env')

# Función get_env MEJORADA (sin errores None)
def get_env(key, default=''):
    # Intenta os.getenv primero
    value = os.getenv(key)
    if value:
        return value.strip()
    
    # Fallback: lee directo del .env
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{key}="):
                    value = line.split('=', 1)[1]
                    return value.strip()
    except:
        pass
    
    return default

# Cargar TODAS las keys ANTES de cualquier Streamlit
QDRANT_URL = get_env('QDRANT_URL')
QDRANT_API_KEY = get_env('QDRANT_API_KEY') 
CMC_API_KEY = get_env('CMC_API_KEY')
DEEPSEEK_API_KEY = get_env('DEEPSEEK_API_KEY')

print(f"DEBUG CMC_KEY length: {len(CMC_API_KEY) if CMC_API_KEY else 0}")  # Para terminal

# Initialize clients
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
    if not CMC_API_KEY or len(CMC_API_KEY) < 20:
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

# UI PRINCIPAL
st.title("🤖 NEAR RAG Assistant")
st.markdown("**Try:** `swap 1 usdc for near`")

# Sidebar con status REAL (después de cargar keys)
with st.sidebar:
    st.title("🔧 API Status")
    st.success("✅ Interface OK")
    
    st.info(f"CMC Key: {'✅ OK ({len(CMC_API_KEY)} chars)' if CMC_API_KEY and len(CMC_API_KEY)>20 else '❌ MISSING'}")
    st.info(f"Qdrant URL: {'✅ OK' if QDRANT_URL else '❌ MISSING'}")
    st.info(f"Qdrant Client: {'✅ OK' if qdrant_client else '❌ FAIL'}")
    st.info(f"DeepSeek: {'✅ OK' if DEEPSEEK_API_KEY else '❌ MISSING'}")
    st.info(f"Embeddings: {'✅ OK' if model else '❌ FAIL'}")

# Chat
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Your message..."):
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
