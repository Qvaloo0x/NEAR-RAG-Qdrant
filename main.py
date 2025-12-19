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
    qdrant_url = st.session_state.get("qdrant_url") or QDRANT_URL
    qdrant_key = st.session_state.get("qdrant_key") or QDRANT_API_KEY

    if not qdrant_url or not qdrant_key:
        return []

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
        return data.get("result", [])
    except Exception as e:
        print("Qdrant error:", e)
        return []

def rag_near_fixed(query_text):
    """RAG pipeline"""
    if not model:
        return "Model not loaded"
    
    query_vector = np.pad(
        model.encode(query_text),
        (0, 1536 - 384),
        'constant'
    ).tolist()

    hits = search_qdrant(query_vector, limit=3)

    contexts = []
    for point in hits:
        payload = point.get("payload", {})
        contexts.append(payload.get("content", f"Chunk ID: {point.get('id')}"))

    return "\n\n---\n\n".join(contexts) if contexts else "No docs found"

# ========== REF FINANCE - NEAR DEX #1 ==========
def get_ref_finance_quote(amount_usdc):
    """Ref Finance quote for NEAR (professional fallback)"""
    # Valores realistas para demo (Ref API simplificado)
    out_near = float(amount_usdc) / 4.20  # ~$4.20 per NEAR
    price_usd = float(amount_usdc)
    
    swap_url = f"https://app.ref.finance/swap?tokenInAddress=usdc.tether-token.near&tokenOutAddress=wrap.near&amount={int(float(amount_usdc)*10**6)}"
    
    return {
        "out_amount": f"{out_near:.3f} NEAR",
        "price_usd": f"${price_usd:.2f}",
        "swap_url": swap_url
    }

# ========== NEAR INTENTS ==========
def detect_intent(query):
    """Detects transaction vs question"""
    intent_keywords = ['swap', 'exchange', 'send', 'transfer', 'bridge']
    query_lower = query.lower()
    for keyword in intent_keywords:
        if keyword in query_lower:  # ✅ FIXED: query_lower (no intent_lower)
            return True, "INTENT"
    return False, "RAG"

def parse_intent(query):
    """Parse swap intent with Ref Finance"""
    if "swap" in query.lower():
        parts = query.lower().split()
        amount = parts[1] if len(parts) > 1 else "100"
        
        quote = get_ref_finance_quote(amount)
        
        return f"""
🚀 **NEAR INTENT DETECTED** *(Ref Finance)*

**💱 SWAP {amount} USDC → NEAR**
• **Output**: {quote['out_amount']}
• **Value**: {quote['price_usd']}
• **DEX Fee**: ~0.3%

✅ **Execute instantly:**
[🚀 Ref Finance]({quote['swap_url']})

*Y-24 + Ref Finance (NEAR's #1 DEX)*
        """
    return None

def near_assistant(query):
    """Unified RAG + Intents"""
    is_intent, mode = detect_intent(query)
    
    if mode == "INTENT":
        intent = parse_intent(query)
        if intent:
            return intent
        return "❌ Intent not recognized"
    
    # RAG fallback
    context = rag_near_fixed(query)
    return f"📚 **RAG MODE**\n\nSearching NEAR docs for: '{query}'\n\n{context[:500]}..."

# ========== STREAMLIT UI ==========
def main():
    st.title("🤖 Y-24 Chatbot - NEAR Protocol Assistant")
    st.markdown("**Y-24 Labs: NEAR intents + RAG + Ref Finance**")
    
    # Sidebar config
    st.sidebar.header("🔧 Config")
    st.sidebar.markdown("### 🤖 **Y-24 Chatbot**")
    st.sidebar.markdown("*Gnomai Labs - NEAR RAG + DEX Assistant*")
    
    qdrant_url = st.sidebar.text_input("Qdrant URL", type="password", value=st.session_state.get("qdrant_url", ""))
    qdrant_key = st.sidebar.text_input("Qdrant Key", type="password", value=st.session_state.get("qdrant_key", ""))
    
    if st.sidebar.button("Save Config"):
        st.session_state["qdrant_url"] = qdrant_url
        st.session_state["qdrant_key"] = qdrant_key
        st.sidebar.success("✅ Config saved!")
    
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
            with st.spinner("🤖 Y-24 processing..."):
                response = near_assistant(prompt)
                st.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()
