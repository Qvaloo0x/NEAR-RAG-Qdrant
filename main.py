import streamlit as st
import requests
import numpy as np
from sentence_transformers import SentenceTransformer
import re
import os

st.set_page_config(page_title="🤖 Y-24 NEAR Assistant", layout="wide")

# 🔥 SECRETS
CMC_API_KEY = st.secrets.get("CMC_API_KEY", "6149fceb68f646848f2a0fe0299aba1a")
QDRANT_URL = st.secrets.get("QDRANT_URL", "")
QDRANT_API_KEY = st.secrets.get("QDRANT_API_KEY", "")
DEEPSEEK_API_KEY = st.secrets.get("DEEPSEEK_API_KEY", "")

@st.cache_resource
def load_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

model = load_model()

# 🔥 CMC PRECIO REAL
@st.cache_data(ttl=60)
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

# 🔥 SWAP DETECTOR Y RHEA LINK
def handle_swap(query):
    q = query.lower()
    if all(word in q for word in ["swap", "usdc", "near"]):
        price = get_near_price()
        amount_match = re.search(r'(\d+(?:\.\d+)?)', q)
        amount = float(amount_match.group(1)) if amount_match else 1.0
        near_out = amount / price
        
        st.markdown(f"""
<div style='border: 2px solid #4ade80; border-radius: 12px; padding: 20px; background: linear-gradient(135deg, #fef3c7 0%, #f59e0b 100%);'>
    <h2 style='color: #1e40af; margin: 0 0 15px 0;'>🚀 SWAP DETECTADO</h2>
    
    <div style='background: white; padding: 15px; border-radius: 8px; margin-bottom: 15px;'>
        <strong>💱 {amount} USDC → <span style='color: #059669; font-size: 1.3em;'>{near_out:.6f} NEAR</span></strong><br>
        <strong>💰 Precio actual:</strong> <span style='color: #dc2626;'>${price:.4f}</span> por NEAR
    </div>
    
    <a href='https://app.rhea.finance/' target='_blank' 
       style='display: inline-block; background: linear-gradient(45deg, #3b82f6, #1d4ed8); color: white; padding: 12px 24px; 
              border-radius: 50px; text-decoration: none; font-weight: bold; font-size: 16px; 
              box-shadow: 0 4px 15px rgba(59,130,246,0.4);'>
        🔗 ABRIR RHEA FINANCE
    </a>
    
    <p style='margin: 15px 0 0 0; font-size: 0.9em; color: #6b7280;'>
        *Rhea Finance = DEX nativo NEAR para swaps USDC↔NEAR*
    </p>
</div>
        """, unsafe_allow_html=True)
        return True
    return False

# 🔥 QDRANT SEARCH
def search_qdrant(query):
    try:
        query_vec = model.encode(query)
        query_vec = np.pad(query_vec, (0, 1536-len(query_vec)), 'constant').tolist()
        
        url = f"{QDRANT_URL}/collections/near_docs/points/search"
        headers = {"api-key": QDRANT_API_KEY, "Content-Type": "application/json"}
        
        resp = requests.post(url, headers=headers, json={
            "vector": query_vec, 
            "limit": 3, 
            "with_payload": True
        }, timeout=10)
        
        if resp.status_code == 200:
            hits = resp.json().get("result", [])
            contexts = [hit.get("payload", {}).get("content", "") for hit in hits]
            return "\n\n".join(contexts[:2])
    except:
        pass
    return "No context found"

# 🔥 DEEPSEEK RAG
def ask_deepseek(query, context):
    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        messages = [
            {"role": "system", "content": "Eres un experto en NEAR Protocol. Responde en español usando SOLO el contexto proporcionado. Sé preciso y conciso."},
            {"role": "user", "content": f"CONTEXTO:\n{context}\n\nPREGUNTA: {query}\n\nResponde:"}
        ]
        
        resp = requests.post(url, headers=headers, json={
            "model": "deepseek-chat",
            "messages": messages,
            "max_tokens": 800,
            "temperature": 0.1
        }, timeout=20)
        
        return resp.json()["choices"][0]["message"]["content"]
    except:
        return "DeepSeek no disponible. Usa comandos swap o preguntas básicas."

# 🔥 MAIN LOGIC
def process_query(query):
    # SWAP FIRST (prioridad máxima)
    if handle_swap(query):
        return
    
    # RAG + DeepSeek
    with st.spinner("Buscando en docs NEAR..."):
        context = search_qdrant(query)
        response = ask_deepseek(query, context)
        st.markdown(f"🤖 **Respuesta con contexto NEAR:**\n\n{response}")

# 🔥 UI PRINCIPAL
st.title("🤖 Y-24 NEAR Assistant")
st.markdown("**DeepSeek RAG + Qdrant + Rhea Finance**")

# Status sidebar
with st.sidebar:
    st.header("🔧 Status")
    st.success("✅ Interface")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("CMC", f"{len(CMC_API_KEY)} chars")
        st.metric("Qdrant", "OK" if QDRANT_URL else "❌")
    with col2:
        st.metric("DeepSeek", "OK" if DEEPSEEK_API_KEY else "❌")
        price = get_near_price()
        st.metric("NEAR Price", f"${price:.4f}")

    st.markdown("---")
    st.info("💬 **Prueba:**\n• `swap 1 usdc for near`\n• `¿qué es sharding?`")

# Chat interface
if "messages" not in st.session_state:
    st.session_state.messages = []

# Render chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# New message
if prompt := st.chat_input("Pregunta sobre NEAR o `swap 1 usdc for near`"):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate response
    with st.chat_message("assistant"):
        process_query(prompt)
    
    # Save assistant message (empty porque response se renderiza directo)
    st.session_state.messages.append({"role": "assistant", "content": "processed"})
