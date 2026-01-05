import os
import re
import json
import requests
import numpy as np
import streamlit as st
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

# 🔥 Page config
st.set_page_config(page_title="🤖 Y-24 Chatbot - NEAR Assistant", layout="wide")

# 🔒 ENV
load_dotenv()
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_DEFAULT = "near_docs"

CMC_API_KEY = os.getenv("CMC_API_KEY")  # o deja tu key fija si quieres

# ================== CMC PRICE ==================
def get_near_price_usd() -> float:
    """
    Get NEAR/USD price from CoinMarketCap.
    Falls back to 4.20 if anything fails.
    """
    if not CMC_API_KEY:
        return 4.20

    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    headers = {
        "X-CMC_PRO_API_KEY": CMC_API_KEY,
        "Accept": "application/json",
    }
    params = {"symbol": "NEAR", "convert": "USD"}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return float(data["data"]["NEAR"]["quote"]["USD"]["price"])
    except Exception:
        pass

    return 4.20

# 🔁 Global model (loaded once)
@st.cache_resource
def load_model():
    return SentenceTransformer("all-MiniLM-L6-v2")

model = load_model()

# ========== SWAP PARSER ==========
def parse_swap_text(text: str):
    """
    Parse swap phrases like:
    - swap 1 usdc for near
    - swap 50 usdc to near
    Returns amount, from_token, to_token.
    """
    text = text.lower().strip()
    pattern = r"swap\s+(\d+(?:\.\d+)?)\s+(\w+)\s+(?:for|to)\s+(\w+)"
    match = re.search(pattern, text)
    if not match:
        return None

    amount, from_token, to_token = match.groups()
    return {
        "amount": float(amount),
        "from_token": from_token.upper(),
        "to_token": to_token.upper(),
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
    body = {"vector": query_vector, "limit": limit, "with_payload": True}

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
        "constant",
    ).tolist()

    hits = search_qdrant(query_vector, limit=3)

    contexts = []
    for point in hits:
        payload = point.get("payload", {})
        contexts.append(payload.get("content", f"Chunk ID: {point.get('id')}"))

    return "\n\n---\n\n".join(contexts) if contexts else "No docs found"

# ========== RHEA / REF LINK ==========
def get_rhea_link():
    """
    Returns a generic USDC <-> NEAR pool link.
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
    Uses real NEAR price from CoinMarketCap.
    """
    parsed = parse_swap_text(query)
    if not parsed:
        return None

    price = get_near_price_usd()
    if parsed["to_token"] == "NEAR":
        out_amount = parsed["amount"] / price
    else:
        out_amount = parsed["amount"] * price

    rhea_url = get_rhea_link()

    return f"""
🚀 **NEAR INTENT DETECTED**

**💱 SWAP {parsed['amount']} {parsed['from_token']} → {parsed['to_token']} (estimation)**  
• **Estimated output**: ~{out_amount:.4f} {parsed['to_token']}  
• **Note**: This is an estimate. You will set the exact USDC amount directly on Rhea.  
• **Price used**: ~${price:.4f} per NEAR

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
        return "❌ Intent not recognized. Example: `swap 1 usdc for near`"

    context = rag_near_fixed(query)
    return f"📚 **RAG MODE**\n\nSearching NEAR docs for: '{query}'\n\n{context[:500]}..."

# ========== STREAMLIT UI ==========
def main():
    st.title("🤖 Y-24 Chatbot - NEAR Protocol Assistant")
    st.markdown("**Y-24 Labs: NEAR intents + RAG + Rhea/Ref DEX**")

    # Sidebar config (multi-community Qdrant)
    st.sidebar.header("🔧 Config")
    st.sidebar.markdown("### 🤖 **Y-24 Chatbot**")
    st.sidebar.markdown("*Gnomai 
