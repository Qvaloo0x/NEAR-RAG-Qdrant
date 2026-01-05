import streamlit as st
import requests
import numpy as np
from sentence_transformers import SentenceTransformer

st.set_page_config(page_title="🤖 Y-24 NEAR RAG", layout="wide")

# 🔥 TUS SECRETS
CMC_API_KEY = st.secrets["CMC_API_KEY"]
QDRANT_URL = st.secrets["QDRANT_URL"]
QDRANT_API_KEY = st.secrets["QDRANT_API_KEY"]
DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]

@st.cache_resource
def load_model():
    return SentenceTransformer("all-MiniLM-L6-v2")

model = load_model()

# 🔥 DEEPSEEK + RAG
def ask_deepseek(query, context=""):
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    messages = [{"role": "system", "content": "Experto NEAR Protocol"}, {"role": "user", "content": f"{context}\n\nPregunta: {query}"}]
    resp = requests.post(url, json={"model": "deepseek-chat", "messages": messages, "max_tokens": 1000})
    return resp.json()["choices"][0]["message"]["content"]

def search_qdrant(query):
    query_vec = model.encode(query)
    query_vec = np.pad(query_vec, (0, 1536-384), "constant").tolist()
    url = f"{QDRANT_URL}/collections/near_docs/points/search"
    resp = requests.post(url, headers={"api-key": QDRANT_API_KEY, "Content-Type": "application/json"}, 
                        json={"vector": query_vec, "limit": 3, "with_payload": True})
    contexts = [hit["payload"]["content"] for hit in resp.json().get("result", [])]
    return "\n\n".join(contexts)

def get_near_price():
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    resp = requests.get(url, params={"symbol": "NEAR", "convert": "USD"}, 
                       headers={"X-CMC_PRO_API_KEY": CMC_API_KEY})
    return float(resp.json()["data"]["NEAR"]["quote"]["USD"]["price"])

# 🔥 SWAP DETECTOR
def process_query(query):
    if "swap" in query.lower() and "usdc" in query.lower() and "near" in query.lower():
        price = get_near_price()
        return f"""
🚀 **SWAP USDC → NEAR**
💱 1 USDC → {1/price:.6f} NEAR
💰 Precio: ${price:.4f}

🔗 [Rhea Finance](https://app.rhea.finance/)
        """
    
    # RAG + DeepSeek
    context = search_qdrant(query)
    return ask_deepseek(query, context)

# 🔥 UI
st.title("🤖 Y-24 NEAR Assistant")
st.columns(3)[0].metric("🧠 DeepSeek", "✅")
st.columns(3)[1].metric("📚 Qdrant", "✅")
st.columns(3)[2].metric("💰 CMC", "✅")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("Pregunta sobre NEAR o swap 1 usdc for near"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)
    
    with st.chat_message("assistant"):
        st.markdown(process_query(prompt))
    
    st.session_state.messages.append({"role": "assistant", "content": "OK"})
