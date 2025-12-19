import streamlit as st
import requests
import json
import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import numpy as np

# 🔥 FIXED: page_config FUERA de main() - Streamlit Cloud OK
st.set_page_config(page_title="🤖 Y-24 Chatbot - NEAR Assistant", layout="wide")

# 🔒 SECURITY: Load from .env
load_dotenv()
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION = "near_docs"

# Global model (load once)
@st.cache_resource
def load_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

model = load_model()

def search_qdrant(query_vector, limit=3):
    """Search Qdrant with payload"""

    # 1) Leer primero de la config del sidebar; si no, del .env
    qdrant_url = st.session_state.get("qdrant_url") or QDRANT_URL
    qdrant_key = st.session_state.get("qdrant_key") or QDRANT_API_KEY

    # 2) Si no hay URL o KEY, no se puede buscar
    if not qdrant_url or not qdrant_key:
        return []

    # 3) Endpoint correcto de search con payload
    url = f"{qdrant_url}/collections/{COLLECTION}/points/search"
    headers = {
        "Content-Type": "application/json",
        "api-key": qdrant_key,
    }
    body = {
        "vector": query_vector,
        "limit": limit,
        "with_payload": True
    }

    try:
        response = requests.post(url, headers=headers, json=body)
        data = response.json()
        # 4) Devolvemos directamente la lista de hits
        return data.get("result", [])
    except Exception as e:
        print("Qdrant error:", e)
        return []

def rag_near_fixed(query_text):
    """RAG pipeline"""
    if not model:
        return "Model not loaded"
    
    # El modelo all-MiniLM-L6-v2 devuelve 384 dims → se rellena hasta 1536
    query_vector = np.pad(
        model.encode(query_text),
        (0, 1536 - 384),
        'constant'
    ).tolist()

    # Ahora search_qdrant devuelve una lista de hits, no un dict
    hits = search_qdrant(query_vector, limit=3)

    contexts = []
    for point in hits:
        payload = point.get("payload", {})
        # En tu Qdrant el campo de texto es "content"
        contexts.append(payload.get("content", f"Chunk ID: {point.get('id')}"))

    return "\n\n---\n\n".join(contexts) if contexts else "No docs found"

# ========== NEAR INTENTS ==========
def detect_intent(query):
    """Detects transaction vs question"""
    intent_keywords = ['swap', 'exchange', 'send', 'transfer', 'bridge']
    query_lower = query.lower()
    for keyword in intent_keywords:
        if keyword in query_lower:
            return True, "INTENT"
    return False, "RAG"

def parse_intent(query):
    """Parse swap intent"""
    if "swap" in query.lower():
        parts = query.lower().split()
        amount = parts[1] if len(parts) > 1 else "100"
        return {
            "type": "swap",
            "from": "USDC",
            "to": "NEAR",
            "amount": amount
        }
    return None

def near_assistant(query):
    """Unified RAG + Intents"""
    is_intent, mode = detect_intent(query)
    
    if mode == "INTENT":
        intent = parse_intent(query)
        if intent:
            return f"""
🚀 **NEAR INTENT DETECTED**

**{intent['type'].upper():}**
• From: {intent['from']}
• To: {intent['to']}  
• Amount: {intent['amount']}

✅ Ready for NEAR Intents solvers
⏳ Searching best cross-chain price...
💰 **(Demo - production connects real API)**"""
        return "❌ Intent not recognized"
    
    # RAG fallback
    context = rag_near_fixed(query)
    return f"📚 **RAG MODE**\n\nSearching NEAR docs for: '{query}'\n\n{context[:500]}..."

# ========== STREAMLIT UI ==========
def main():
    st.title("🤖 Y-24 Chatbot - NEAR Protocol Assistant")
    st.markdown("**Y-24 Labs: NEAR intents + RAG assistant**")
    
    # Sidebar config
    st.sidebar.header("🔧 Config")
    st.sidebar.markdown("### 🤖 **Y-24 Chatbot**")
    st.sidebar.markdown("*Gnomai Labs - NEAR RAG Assistant*")
    
    # Guardar en session_state para que search_qdrant pueda leerlo
    qdrant_url = st.sidebar.text_input("Qdrant URL", type="password")
    qdrant_key = st.sidebar.text_input("Qdrant Key", type="password")
    if st.sidebar.button("Save Config"):
        st.session_state["qdrant_url"] = qdrant_url
        st.session_state["qdrant_key"] = qdrant_key
        st.sidebar.success("Config saved!")
    
    # Chat interface
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    if prompt := st.chat_input("Ask about NEAR or try: 'Swap 100 USDC to NEAR'"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                response = near_assistant(prompt)
                st.markdown(f"**🤖 Y-24:**\n\n{response}")
        
        st.session_state.messages.append({"role": "assistant", "content": f"**🤖 Y-24:**\n\n{response}"})

if __name__ == "__main__":
    main()
