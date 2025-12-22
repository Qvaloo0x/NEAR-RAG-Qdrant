import streamlit as st
import requests
import json
import os
import re
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import numpy as np

# 🔥 FIXED: page_config FUERA de main() - Streamlit Cloud OK
st.set_page_config(page_title="🤖 Y-24 Chatbot - NEAR Assistant", layout="wide")

# 🔒 SECURITY: Load from .env
load_dotenv()
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_DEFAULT = "near_docs"

# Global model (load once)
@st.cache_resource
def load_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

model = load_model()

# ========== SWAP PARSER FIX - BUG RESUELTO ==========
def parse_swap_text(text: str):
    """FIX: Parsea correctamente 'swap 100 USDC for NEAR' → from=USDC, to=NEAR"""
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

def search_qdrant(query_vector, limit=3):
    """Search Qdrant with payload - MULTI-COMMUNITY READY"""
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

# ========== REF FINANCE - NEAR DEX #1 - AMOUNT FIXED ==========
def get_ref_finance_quote(amount_usdc):
    """Ref Finance quote - AMOUNT 100% CORRECTO (FIXED)"""
    out_near = float(amount_usdc) / 4.20  # ~$4.20 per NEAR
    price_usd = float(amount_usdc)
    
    # ✅ FIX COMPLETO: Formato correcto USDC (6 decimales)
    amount_formatted = f"{float(amount_usdc):.6f}".replace('.', '')
    swap_url = f"https://app.ref.finance/swap?tokenInAddress=usdc.tether-token.near&tokenOutAddress=wrap.near&amount={amount_formatted}"
    
    return {
        "out_amount": f"{out_near:.3f} NEAR",
        "price_usd": f"${price_usd:.2f}",
        "swap_url": swap_url
    }

# ========== NEAR INTENTS - SWAP BUG FIXED ==========
def detect_intent(query):
    """Detects transaction vs question"""
    intent_keywords = ['swap', 'exchange', 'send', 'transfer', 'bridge']
    query_lower = query.lower()
    for keyword in intent_keywords:
        if keyword in query_lower:
            return True, "INTENT"
    return False, "RAG"

def parse
