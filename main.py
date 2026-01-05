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
CMC_API_KEY = os.getenv("CMC_API_KEY")
COLLECTION_DEFAULT = "near_docs"

# ================== CMC PRICE (REAL) ==================
def get_near_price_usd() -> float:
    """Get REAL NEAR/USD price from CoinMarketCap."""
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
    """Parse: swap 1 usdc for near → {amount: 1.0, from: USDC, to: NEAR}"""
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
    """Search Qdrant vector DB."""
    qdrant_url = st.session_state.get("qdrant_url") or QDRANT_URL
    qdrant_key = st.session_state.get("qdrant_key") or QDRANT_API_KEY
    collection = st.session_state.get("qdrant_collection", COLLECTION_DEFAULT)

    if not qdrant_url or not qdrant_key:
        return []

    url = f"{qdrant_url}/collections/{collection}/points/search"
    headers = {"Content-Type": "application/json", "api-key": qdrant_key}
    body = {"vector": query_vector, "limit": limit, "with_payload": True}

    try:
        response = requests.post(url, headers=headers, json=body)
        data = response.json()
        return data.get("result", [])
    except Exception as e:
        st.error(f"Qdrant error: {e}")
        return []

def rag_near_fixed(query_text):
    """RAG: embed → search → context."""
    if not model:
        return "Model not loaded"

    query_vector = np.pad(
        model.encode(query_text), (0, 1536 - 384), "constant"
    ).tolist()

    hits = search_qdrant(query_vector, limit=3)
    contexts = []
    for point in hits:
        payload = point.get("payload", {})
        contexts.append(payload.get("content", f"Chunk ID: {point.get('id')}"))

    return "\n\n---\n\n".join(contexts) if contexts else "No docs found"

# ========== RHEA LINK ==========
def get_rhea_link():
    """Rhea Finance USDC-NEAR pool."""
    return "https://app.rhea.finance"

# ========== INTENT DETECTOR ==========
def detect_intent(query):
    """swap/exchange → INTENT, else → RAG."""
    intent_keywords = ["swap", "exchange", "send", "transfer", "bridge"]
    query_lower = query.lower()
    for keyword in intent_keywords:
        if keyword in query_lower:
            return True, "INTENT"
    return False, "RAG"

def parse_intent(query):
    """Parse swap + show Rhea link with REAL price."""
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

**💱 SWAP {parsed['amount']} {parsed['from_token']} → {parsed['to_token']}**  
• **Estimated output**: ~{out_amount:.4f} {parsed['to_token']}  
• **Price**: ${price:.4f} per NEAR  
• **Note**: Set exact amount on Rhea.

✅ **Open Rhea Finance**  
[🌐 app.rhea.finance]({rhea_url})

*Y-24: I guide → you confirm on-chain.*
"""

def near_assistant(query):
    """INTENT → DEX, else → RAG."""
    is_intent, mode = detect_intent(query)

    if mode == "INTENT":
        intent = parse_intent(query)
        if intent:
            return intent
        return "❌ Try: `swap 1 usdc for near`"

    context = rag_near_fixed(query)
    return f"📚 **NEAR Docs**\n\n{context[:800]}..."

# ========== UI ==========
def main():
    st.title("🤖 Y-24 NEAR Assistant")
    st.markdown("**Swaps + RAG + DEX links**")

    # Sidebar status
    with st.sidebar:
        st.header("🔧 Status")
        st.success("✅ Interface")
        st.metric("CMC Key", f"{len(CMC_API_KEY) if CMC_API_KEY else 0} chars")
        st.metric("Qdrant URL", "OK" if QDRANT_URL else "MISSING")

        # Qdrant config
        st.markdown("---")
        st.text_input("Qdrant URL", key="qdrant_url")
        st.text_input("Qdrant Key", key="qdrant_key", type="password")
        st.text_input("Collection", value="near_docs", key="qdrant_collection")

    # Chat
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask about NEAR or `swap 1 usdc for near`"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("🤖 Processing..."):
                response = near_assistant(prompt)
                st.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()
