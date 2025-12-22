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
CMC_API_KEY = os.getenv("CMC_API_KEY")
COLLECTION_DEFAULT = "near_docs"

# 🔁 Global model (loaded once)
@st.cache_resource
def load_model():
    return SentenceTransformer("all-MiniLM-L6-v2")

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
    pattern = r"swap\s+(\d+(?:\.\d+)?)\s+(\w+)\s+(?:for|to)\s+(\w+)"
    match = re.search(pattern, text)
    if not match:
        return None
    
    amount, from_token, to_token = match.groups()
    return {
        "amount": float(amount),
        "from_token": from_token.upper(),
        "to_token": to_token.upper()
    }

# ========== COINMARKETCAP PRICE ==========
def get_near_price_usd():
    """
    Get NEAR price in USD using CoinMarketCap.
    Falls back to a static demo price if anything fails.
    """
    if not CMC_API_KEY:
        return 4.20  # demo fallback

    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    headers = {
        "X-CMC_PRO_API_KEY": CMC_API_KEY,
        "Accept": "application/json"
    }
    params = {
        "symbol": "NEAR",
        "convert": "USD"
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        data = resp.json()
        return float(data["data"]["NEAR"]["quote"]["USD"]["price"])
    except Exception:
        return 4.20  # safe fallback

def get_live_near_quote(amount_usdc: float) -> float:
    """
    Estimate how many NEAR you get for amount_usdc USDC
    using the live NEAR/USD price from CoinMarketCap.
    """
    near_price = get_near_price_usd()
    # Assuming USDC ~ 1 USD
    return amount_usdc / near_price

# ========== QDRANT RAG ==========
def search_qdrant(query_vector, limit=3):
    """
    Qdrant search with payload.
    Uses QDRANT_URL and QDRANT_API_KEY from environment.
    """
    if not QDRANT_URL or not QDRANT_API_KEY:
        return []

    url = f"{QDRANT_URL}/collections/{COLLECTION_DEFAULT}/points/search"
    headers = {
        "Content-Type": "application/json",
        "api-key": QDRANT_API_KEY,
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

    # Live estimation using CoinMarketCap (USDC -> NEAR)
    out_amount = get_live_near_quote(parsed["amount"])

    rhea_url = get_rhea_link()

    return f"""
🚀 **NEAR INTENT DETECTED**

**💱 SWAP {parsed['amount']} {parsed['from_token']} → {parsed['to_token']} (live estimation)**  
• **Estimated output**: ~{out_amount:.6f} {parsed['to_token']}  
• **Note**: This estimation uses current NEAR/USDC price (CoinMarketCap).  
  You will set the exact USDC amount directly on Rhea.

✅ **Open Rhea (USDC ⇄ NEAR pool)**  
[🌐 Rhea Finance]({rhea_url})

*Y-24 uses live price data for a more realistic quote.*
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
    st.markdown(
        "**Y-24 Labs: NEAR intents + RAG + Rhea/Ref DEX** "
        "(live NEAR/USDC estimation, no pre-filled amounts)."
    )

    # Sidebar info only (no API/URL inputs)
    st.sidebar.header("ℹ️ About Y-24")
    st.sidebar.markdown(
        "- NEAR RAG over Qdrant\n"
        "- Simple intents for USDC → NEAR swaps\n"
        "- Prices via CoinMarketCap (estimation, not execution)"
    )

    # SWAP TESTER (parser debug) – optional but useful
    st.sidebar.markdown("---")
    st.sidebar.markdown("🧪 **SWAP PARSER TEST**")
    test_swap = st.sidebar.text_input("Test swap:", "swap 1 usdc for near")
    if test_swap:
        parsed = parse_swap_text(test_swap)
        if parsed:
            st.sidebar.success(
                f"Parsed: {parsed['amount']} {parsed['from_token']} → {parsed['to_token']}"
            )
        else:
            st.sidebar.error("Invalid format")

    # Chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    placeholder = (
        "Ask about NEAR or try: 'swap 1 usdc for near' "
        "(I'll estimate using live NEAR/USDC price)."
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
