import streamlit as st
import requests
import numpy as np
import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

st.set_page_config(page_title="🤖 Y-24 NEAR RAG Assistant", layout="wide")
load_dotenv()

# 🔥 SECRETS - TUS DATOS
CMC_API_KEY = st.secrets.get("CMC_API_KEY", "6149fceb68f646848f2a0fe0299aba1a")
QDRANT_URL = st.secrets.get("QDRANT_URL")
QDRANT_API_KEY = st.secrets.get("QDRANT_API_KEY")
DEEPSEEK_API_KEY = st.secrets.get("DEEPSEEK_API_KEY")
NEAR_AI_API_KEY = st.secrets.get("NEAR_AI_API_KEY")

@st.cache_resource
def load_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

model = load_model()

# 🔥 CMC PRICE (ya funciona)
def get_near_price():
    try:
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        resp = requests.get(url, params={"symbol": "NEAR", "convert": "USD"},
                          headers={"X-CMC_PRO_API_KEY": CMC_API_KEY}, timeout=10)
        return float(resp.json()["data"]["NEAR"]["quote"]["USD"]["price"])
    except:
        return 1.75

# 🔥 SWAP (ya funciona)
def parse_swap_text(text):
    text = text.lower().strip()
    pattern = r"swap\s+(\d+(?:\.\d+)?)\s+(\w+)\s+(?:for|to)\s+(\w+)"
    match = re.search(pattern, text)
    if match:
        amount, from_token, to_token = match.groups()
        return float(amount), from_token.upper(), to_token.upper()
    return None

def handle_swap(query):
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
    return False

# 🔥 QDRANT RAG - TUS DOCUMENTOS NEAR
def search_qdrant(query):
    if not QDRANT_URL or not QDRANT_API_KEY:
        return None
        
    try:
        query_vec = model.encode(query)
        query_vec = np.pad(query_vec, (0, 1536-len(query_vec)), 'constant').tolist()
        
        url = f"{QDRANT_URL}/collections/near_docs/points/search"
        headers = {"api-key": QDRANT_API_KEY, "Content-Type": "application/json"}
        
        resp = requests.post(url, headers=headers, json={
            "vector": query_vec, 
            "limit": 3, 
            "with_payload": True
        }, timeout=15)
        
        if resp.status_code == 200:
            hits = resp.json().get("result", [])
            contexts = [hit.get("payload", {}).get("content", "")[:1000] for hit in hits]
            return "\n\n---\n\n".join(contexts)
    except:
        pass
    return None

# 🔥 DEEPSEEK RAG - Contexto Qdrant
def ask_deepseek(query, context=None):
    if not DEEPSEEK_API_KEY:
        return "DeepSeek API key missing"
        
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    system_prompt = """You are a NEAR Protocol expert. Answer accurately using ONLY the provided context.
Be concise, technical, and professional. Use bullet points when appropriate."""
    
    messages = [{"role": "system", "content": system_prompt}]
    
    if context:
        messages.append({"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION: {query}"})
    else:
        messages.append({"role": "user", "content": query})
    
    try:
        resp = requests.post(url, headers=headers, json={
            "model": "deepseek-chat",
            "messages": messages,
            "max_tokens": 1200,
            "temperature": 0.1
        }, timeout=30)
        
        return resp.json()["choices"][0]["message"]["content"]
    except:
        return "DeepSeek unavailable"

# 🔥 UI PRINCIPAL
st.title("🤖 Y-24 NEAR RAG Assistant")
st.markdown("**Rhea Swaps | DeepSeek RAG | Qdrant Docs | NEAR Technical**")

# 🔥 STATUS ENHANCED
col1, col2, col3, col4 = st.columns(4)
with col1: st.metric("CMC", f"{len(CMC_API_KEY)} chars ✓")
with col2: st.metric("Qdrant", "✅" if QDRANT_URL else "❌")
with col3: st.metric("DeepSeek", "✅" if DEEPSEEK_API_KEY else "❌")
with col4: st.metric("NEAR", f"${get_near_price():.4f}")

# Sidebar
with st.sidebar:
    st.header("🔧 Status")
    st.info(f"**Qdrant:** {'🟢 OK' if QDRANT_URL else '🔴 Missing'}")
    st.info("💬 **Try:**\n• `swap 10 usdc for near`\n• `explain Nightshade`\n• `how does sharding work`")

# Chat
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 🔥 MAIN LOGIC
if prompt := st.chat_input("Ask about NEAR or `swap 1 usdc for near`"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # 1. SWAP FIRST (priority)
        if handle_swap(prompt):
            pass
            
        # 2. RAG + DeepSeek
        else:
            with st.spinner("🔍 Searching NEAR docs..."):
                context = search_qdrant(prompt)
                if context:
                    st.info("📚 **Using Qdrant context**")
                    response = ask_deepseek(prompt, context)
                else:
                    st.warning("📚 **No Qdrant context**")
                    response = ask_deepseek(prompt)
                
                st.markdown(response)
    
    st.session_state.messages.append({"role": "assistant", "content": "processed"})
