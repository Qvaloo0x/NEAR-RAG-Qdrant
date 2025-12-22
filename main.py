import streamlit as st
import requests
import json
import os
import re
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import numpy as np

# 🔥 Page config
st.set_page_config(page_title="🤖 Y-24 Chatbot - NEAR Assistant", layout="wide")

# 🔒 ENV
load_dotenv()
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_DEFAULT = "near_docs"

# 🔁 Global model (loaded once)
@st.cache_resource
def load_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

model = load_model()

# ========== SWAP PARSER ==========
def parse_swap_text(text: str):
    """
    Parse swap phrases like:
    - swap 100 usdc for near
    - swap 50 usdc to near
    Returns amount, from_token, to_token.
    """
    text = text.lower().strip()
    pattern = r'swap\s+(\d+(?:\.\d+)?)\s+(\w+)\s+(?:for|to)\s+(\w+)'
    match = re.search(pattern, text)
    if not match:
        return None
    
    amount, from_token, to_token = match.groups()
    return {
        "amount": float(amount),
        "from_token": from_token.upper(),
        "to_token": to_token.upper()
    }

# ========== QDRANT RAG ==========
def search_qdrant(query_vector, limit=3):
    """
    Generic Qdrant search with payload.
    Uses session_state overrides if provided in the sidebar.
    """
    qdrant_url = st.session_state.get("qdrant_url") or QDRANT_URL
    qdrant_key = st.session_state.get("qdrant_key") or QDRANT_API_KEY
    collection = st.session_state.get("qdrant_collection", COLLECTION_DEFAULT)

    if not qdrant_url or not qdrant_key:
        return []

    url = f"{qdrant_url}/collections/{collection}/points/search"
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
        st.error(f"Qdrant error: {e}")
        return []

def rag_near_fixed(query_text):
    """
    Basic RAG pipeline:
    - embed query
    - search Qdrant
    - join top-k contexts
    """
    if not model:
        return "Model not loaded"
    
    query_vector = np.pad(
        model.encode(query_text),
        (0, 1536 - 384),
        "constant"
    ).tolist()

    hits = search_qdrant(query_vector, limit=3)

    contexts = []
    for point in hits:
        payload = point.get("payload", {})
        contexts.append(payload.get("content", f"Chunk ID: {point.get('id')}"))

    return "\n\n---\n\n".join(contexts) if contexts else "No docs found"

# ========== RHEA / REF LINK (NO AMOUNT GUARANTEE) ==========
def get_rhea_link():
    """
    Returns a generic USDC <-> NEAR pool link.
    For now we do NOT guarantee that the amount is pre-filled.
    User will set the exact amount on Rhea.
    """
    return "https://app.rhea.finance"

# ========== NEAR INTENTS ==========
def detect_intent(query):
    """
    Very simple intent detector:
    if it contains swap/exchange/send/transfer/bridge -> INTENT
    otherwise -> RAG
    """
    intent_keywords = ["swap", "exchange", "send", "transfer", "bridge"]
    query_lower = query.lower()
    for keyword in intent_keywords:
        if keyword in query_lower:
            return True, "INTENT"
    return False, "RAG"

def parse_intent(query):
    """
    Use the swap parser to understand amount/from/to.
    The link only opens the USDC <-> NEAR pool;
    the user will type the final amount on Rhea.
    """
    parsed = parse_swap_text(query)
    if not parsed:
        return None

    # Very rough demo estimate (do NOT treat as real price)
    est_rate = 4.20  # NEAR ≈ 4.20 USD (demo only)
    if parsed["to_token"] == "NEAR":
        out_amount = parsed["amount"] / est_rate
    else:
        out_amount = parsed["amount"] * est_rate

    rhea_url = get_rhea_link()

    return f"""
🚀 **NEAR INTENT DETECTED**

**💱 SWAP {parsed['amount']} {parsed['from_token']} → {parsed['to_token']} (estimation)**  
• **Estimated output**: ~{out_amount:.4f} {parsed['to_token']}  
• **Note**: This is an estimate. You will set the exact USDC amount directly on Rhea.

✅ **Open Rhea (USDC ⇄ NEAR pool)**  
[🌐 Rhea Finance]({rhea_url})

*Y-24 stays humble: I guide you, you confirm the exact amount on-chain.*
"""

def near_assistant(query):
    """
    Unified entrypoint:
    - If intent: try swap parser and show DEX guidance.
    - Else: fall back to NEAR RAG answer.
    """
    is_intent, mode = detect_intent(query)
    
    if mode == "INTENT":
        intent = parse_intent(query)
        if intent:
            return intent
        return "❌ Intent not recognized. Example: `swap 100 usdc for near`"
    
    context = rag_near_fixed(query)
    return f"📚 **RAG MODE**\n\nSearching NEAR docs for: '{query}'\n\n{context[:500]}..."

# ========== STREAMLIT UI ==========
def main():
    st.title("🤖 Y-24 Chatbot - NEAR Protocol Assistant")
    st.markdown(
        "**Y-24 Labs: NEAR intents + RAG + Rhea/Ref DEX** "
    
    )

    # Sidebar config (multi-community Qdrant)
    st.sidebar.header("🔧 Config")
    st.sidebar.markdown("### 🤖 **Y-24 Chatbot**")
    st.sidebar.markdown("*Gnomai Labs - NEAR RAG + DEX Assistant*")

    col1, col2 = st.sidebar.columns(2)
    with col1:
        qdrant_url = st.text_input(
            "Qdrant URL", type="password",
            value=st.session_state.get("qdrant_url", "")
        )
    with col2:
        qdrant_key = st.text_input(
            "Qdrant Key", type="password",
            value=st.session_state.get("qdrant_key", "")
        )

    collection_input = st.sidebar.text_input(
        "Collection",
        value=st.session_state.get("qdrant_collection", "near_docs")
    )

    if st.sidebar.button("💾 Save Config"):
        st.session_state["qdrant_url"] = qdrant_url
        st.session_state["qdrant_key"] = qdrant_key
        st.session_state["qdrant_collection"] = collection_input
        st.sidebar.success("✅ Config saved!")

    # SWAP TESTER (parser debug)
    st.sidebar.markdown("---")
    st.sidebar.markdown("🧪 **SWAP TESTER**")
    test_swap = st.sidebar.text_input("Test swap:", "swap 100 usdc for near")
    if test_swap:
        parsed = parse_swap_text(test_swap)
        if parsed:
            st.sidebar.success(
                f"✅ Parsed: {parsed['amount']} {parsed['from_token']} → {parsed['to_token']}"
            )
        else:
            st.sidebar.error("❌ Invalid format")

    # Chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    placeholder = (
        "Ask about NEAR or try: 'swap usdc to near' "
        "(I'll open the pool, you set the amount on Rhea)."
    )
    if prompt := st.chat_input(placeholder):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("🤖 Y-24 processing..."):
                response = near_assistant(prompt)
                st.markdown(response)
                st.session_state.messages.append(
                    {"role": "assistant", "content": response}
                )

if __name__ == "__main__":
    main()
