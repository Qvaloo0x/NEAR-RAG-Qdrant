import streamlit as st
import requests
import numpy as np
import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

st.set_page_config(page_title="🤖 Y-24 NEAR RAG Assistant", layout="wide")
load_dotenv()

# 🔥 SECRETS
CMC_API_KEY = st.secrets.get("CMC_API_KEY", "6149fceb68f646848f2a0fe0299aba1a")
QDRANT_URL = st.secrets.get("QDRANT_URL")
QDRANT_API_KEY = st.secrets.get("QDRANT_API_KEY")
DEEPSEEK_API_KEY = st.secrets.get("DEEPSEEK_API_KEY")

@st.cache_resource
def load_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

model = load_model()

def get_near_price():
    try:
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        resp = requests.get(url, params={"symbol": "NEAR", "convert": "USD"},
                          headers={"X-CMC_PRO_API_KEY": CMC_API_KEY}, timeout=10)
        return float(resp.json()["data"]["NEAR"]["quote"]["USD"]["price"])
    except:
        return 1.75

def parse_swap_text(text):
    """FIXED - Simple y robusto"""
    text = text.lower().strip()
    if "swap" not in text or "usdc" not in text or "near" not in text:
        return None
        
    numbers = re.findall(r'\d+(?:\.\d+)?', text)
    amount = float(numbers[0]) if numbers else 1.0
    
    return amount, "USDC", "NEAR"

def handle_swap(query):
    """FIXED - Error handling"""
    try:
        parsed = parse_swap_text(query)
        if parsed:
            amount, from_token, to_token = parsed
            if from_token in ["USDC", "USD"] and to_token == "NEAR":
                price = get_near_price()
                near_out = amount / price
                st.markdown(f"""
✅ **SWAP**: {amount} {from_token} → **{near_out:.6f} NEAR** 💰 Price: **${price:.4f}**

**🔗 [Rhea Finance](https://app.rhea.finance/)**

*Native NEAR DEX for USDC↔NEAR swaps*
                """)
                return True
    except Exception as e:
        st.error(f"Swap error: {e}")
    return False

# 🔥 QDRANT + DEEPSEEK (resto igual...)
def search_qdrant(query):
    if not QDRANT_URL or not QDRANT_API_KEY:
        return None
    try:
        query_vec = model.encode(query)
        query_vec = np.pad(query_vec, (0, 1536-len(query_vec)), 'constant').tolist()
        url = f"{QDRANT_URL}/collections/near_docs/points/search"
        headers = {"api-key": QDRANT_API_KEY, "Content-Type": "application/json"}
        resp = requests.post(url, headers=headers, json={
            "vector": query_vec, "limit": 3, "with_payload": True
        }, timeout=15)
        if resp.status_code == 200:
            hits = resp.json().get("result", [])
            contexts = [hit.get("payload", {}).get("content", "")[:1000] for hit in hits]
            return "\n\n---\n\n".join(contexts)
    except:
        pass
    return None

def ask_deepseek(query, context=None):
    if not DEEPSEEK_API_KEY:
        return "DeepSeek not configured"
    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
        messages = [{"role": "system", "content": "NEAR Protocol expert. Concise technical answers."}]
        if context:
            messages.append({"role": "user", "content": f"CONTEXT:\n{context}\n\nQ: {query}"})
        else:
            messages.append({"role": "user", "content": query})
        resp = requests.post(url, headers=headers, json={
            "model": "deepseek-chat", "messages": messages, "max_tokens": 1000
        }, timeout=30)
        return resp.json()["choices"][0]["message"]["content"]
    except:
        return "DeepSeek error"

# 🔥 UI (igual)
st.title("🤖 Y-24 NEAR RAG Assistant")
col1, col2, col3 = st.columns(3)
with col1: st.metric("CMC", "✓")
with col2: st.metric("Qdrant", "✅" if QDRANT_URL else "❌")
with col3: st.metric("DeepSeek", "✅" if DEEPSEEK_API_KEY else "❌")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("Ask about NEAR or swap"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)
    
    with st.chat_message("assistant"):
        if handle_swap(prompt):
            pass
        else:
            with st.spinner("Searching..."):
                context = search_qdrant(prompt)
                response = ask_deepseek(prompt, context) if context else ask_deepseek(prompt)
                st.markdown(response)
    
    st.session_state.messages.append({"role": "assistant", "content": "OK"})
