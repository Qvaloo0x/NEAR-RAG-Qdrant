import streamlit as st
import requests
import re
import numpy as np
import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

st.set_page_config(page_title="🤖 Y-24 NEAR RAG Assistant", layout="wide")
load_dotenv()

# 🔥 SECRETS - Tus datos
CMC_API_KEY = st.secrets.get("CMC_API_KEY", "6149fceb68f646848f2a0fe0299aba1a")
QDRANT_URL = st.secrets.get("QDRANT_URL")
QDRANT_API_KEY = st.secrets.get("QDRANT_API_KEY")
DEEPSEEK_API_KEY = st.secrets.get("DEEPSEEK_API_KEY")

@st.cache_resource
def load_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

model = load_model()

# 🔥 PRECIO CON CACHE (2 minutos)
@st.cache_data(ttl=120)
def get_near_price():
    """CMC + cache inteligente → 0 rate limits"""
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
    """Simple y robusto"""
    text = text.lower().strip()
    if not all(word in text for word in ["swap", "usdc", "near"]):
        return None
        
    numbers = re.findall(r'\d+(?:\.\d+)?', text)
    amount = float(numbers[0]) if numbers else 1.0
    
    return amount, "USDC", "NEAR"

def handle_swap(query):
    """FIXED - No crashea con preguntas normales"""
    q_lower = query.lower()
    
    # Check rápido ANTES de regex
    if not all(word in q_lower for word in ["swap", "usdc", "near"]):
        return False
    
    try:
        parsed = parse_swap_text(query)
        if parsed:
            amount, from_token, to_token = parsed
            price = get_near_price()
            near_out = amount / price
            st.markdown(f"""
<div style='border: 2px solid #10b981; border-radius: 12px; padding: 20px; background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);'>
    <h2 style='color: #065f46; margin: 0 0 15px 0;'>🚀 SWAP CONFIRMED</h2>
    
    <div style='background: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
        <strong>💱 {amount} {from_token} → <span style='color: #059669; font-size: 1.4em;'>{near_out:.6f} NEAR</span></strong><br>
        <strong>💰 Price:</strong> <span style='color: #dc2626; font-weight: bold;'>${price:.4f}</span>
    </div>
    
    <a href='https://app.rhea.finance/' target='_blank' 
       style='display: inline-block; background: linear-gradient(45deg, #3b82f6, #1d4ed8); color: white; padding: 12px 24px; 
              border-radius: 50px; text-decoration: none; font-weight: bold; font-size: 16px; 
              box-shadow: 0 4px 15px rgba(59,130,246,0.4);'>
        🔗 OPEN RHEA FINANCE
    </a>
    
    <p style='margin: 15px 0 0 0; font-size: 0.9em; color: #6b7280;'>
        *Rhea = Native NEAR DEX for USDC↔NEAR*
    </p>
</div>
            """, unsafe_allow_html=True)
            return True
    except:
        return False

# 🔥 QDRANT RAG
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

# 🔥 DEEPSEEK RAG
def ask_deepseek(query, context=None):
    if not DEEPSEEK_API_KEY:
        return "DeepSeek not configured"
    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
        system_prompt = "NEAR Protocol expert. Technical, precise, concise answers. Use bullet points."
        messages = [{"role": "system", "content": system_prompt}]
        if context:
            messages.append({"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION: {query}"})
        else:
            messages.append({"role": "user", "content": query})
        resp = requests.post(url, headers=headers, json={
            "model": "deepseek-chat", "messages": messages, "max_tokens": 1200, "temperature": 0.1
        }, timeout=30)
        return resp.json()["choices"][0]["message"]["content"]
    except:
        return "DeepSeek unavailable - try swap command"

# 🔥 UI PRINCIPAL
st.title("🤖 Y-24 NEAR RAG Assistant")
st.markdown("**Rhea Swaps | DeepSeek AI | Qdrant Docs | NEAR Technical**")

# Status metrics
col1, col2, col3, col4 = st.columns(4)
with col1: 
    st.metric("CMC", f"{len(CMC_API_KEY)} chars ✓")
with col2: 
    st.metric("Qdrant", "✅" if QDRANT_URL else "❌")
with col3: 
    st.metric("DeepSeek", "✅" if DEEPSEEK_API_KEY else "❌")
with col4: 
    price = get_near_price()
    st.metric("NEAR", f"${price:.4f}")

# Sidebar
with st.sidebar:
    st.header("🔧 Status")
    st.info(f"**Qdrant:** {'🟢 Connected' if QDRANT_URL else '🔴 Missing'}")
    st.info("💬 **Commands:**\n• `swap 10 usdc for near`\n• `explain Nightshade`\n• `sharding details`")

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 🔥 MAIN LOGIC
if prompt := st.chat_input("Ask about NEAR Protocol or `swap 1 usdc for near`"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # PRIORITY 1: SWAP
        if handle_swap(prompt):
            pass
        # PRIORITY 2: RAG + DeepSeek
        else:
            with st.spinner("🤖 AI Researching NEAR docs..."):
                context = search_qdrant(prompt)
                if context:
                    st.success("📚 **Qdrant context found**")
                    response = ask_deepseek(prompt, context)
                else:
                    st.warning("📚 **No Qdrant context** - Direct AI")
                    response = ask_deepseek(prompt)
                
                st.markdown(response)
    
    st.session_state.messages.append({"role": "assistant", "content": "processed"})
