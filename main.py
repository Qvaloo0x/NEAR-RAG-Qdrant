import streamlit as st
import os
from dotenv import load_dotenv
import requests
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# Carga EXPLÍCITA del .env
load_dotenv(dotenv_path='.env')

# Lee DIRECTO del archivo (arreglado el None.strip() error)
def get_env(key, default=''):
    value = os.getenv(key)
    if not value:
        try:
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith(key + '='):
                        value = line.split('=', 1)[1].strip()
                        break
        except:
            pass
    return value if value else default

QDRANT_URL = get_env('QDRANT_URL', '')
QDRANT_API_KEY = get_env('QDRANT_API_KEY', '')
CMC_API_KEY = get_env('CMC_API_KEY', '')
DEEPSEEK_API_KEY = get_env('DEEPSEEK_API_KEY', '')

# Sidebar API status
st.sidebar.title("🔧 API Status")
st.sidebar.success("✅ Interface OK")
st.sidebar.info(f"CMC Key: {'✅ OK' if CMC_API_KEY else '❌ MISSING'} ({len(CMC_API_KEY)} chars)")
st.sidebar.info(f"Qdrant: {'✅ OK' if QDRANT_URL else '❌ MISSING'}")

# Initialize clients with fallbacks
@st.cache_resource
def init_clients():
    try:
        qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        st.sidebar.success("✅ Qdrant OK")
    except:
        qdrant_client = None
        st.sidebar.error("❌ Qdrant FAIL")
    
    try:
        model = SentenceTransformer('all-MiniLM-L6-v2')
        st.sidebar.success("✅ Embeddings OK")
    except:
        model = None
        st.sidebar.error("❌ Embeddings FAIL")
    
    return qdrant_client, model

qdrant_client, model = init_clients()

def get_near_price_usd():
    """Get NEAR/USD price with CMC fallback to 4.20"""
    if not CMC_API_KEY:
        st.sidebar.error("❌ CMC: No key")
        return 4.20
    
    try:
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY, "Accept": "application/json"}
        params = {"symbol": "NEAR", "convert": "USD"}
        
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        if resp.status_code == 200:
            price = float(resp.json()["data"]["NEAR"]["quote"]["USD"]["price"])
            st.sidebar.success(f"✅ CMC: ${price:.2f}")
            return price
        else:
            st.sidebar.error(f"❌ CMC: {resp.status_code}")
    except:
        st.sidebar.error("❌ CMC: Error")
    
    return 4.20  # Safe fallback

def search_docs(query):
    """Search docs or fallback"""
    if not qdrant_client or not model:
        return ["**Fallback:** No Qdrant connection. Try: `swap 1 usdc for near`"]
    
    try:
        query_vector = model.encode(query).tolist()
        result = qdrant_client.query(
            collection_name="near_docs",
            query_vector=query_vector,
            limit=2
        )
        return [p.payload.get('document', 'Doc without text') for p in result.points]
    except:
        return ["**Fallback:** Search error. Use swap commands."]

def generate_response(query, context):
    """DeepSeek with fallback"""
    if not DEEPSEEK_API_KEY:
        st.sidebar.error("❌ DeepSeek: No key")
        return "💡 **Try:** `swap 1 usdc for near` (uses CoinMarketCap)"
    
    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": f"Question: {query}\n\nContext: {context}\n\nAnswer briefly in English."}],
            "max_tokens": 300
        }
        
        resp = requests.post(url, headers=headers, json=data, timeout=15)
        if resp.status_code == 200:
            st.sidebar.success("✅ DeepSeek OK")
            return resp.json()["choices"][0]["message"]["content"]
        else:
            st.sidebar.error(f"❌ DeepSeek: {resp.status_code}")
    except:
        st.sidebar.error("❌ DeepSeek: Error")
    
    return "🤖 **Fallback mode:** Type `swap 1 usdc for near` to test CoinMarketCap."

def parse_swap(query):
    """Parse swap commands"""
    if "swap" in query.lower() and "for near" in query.lower():
        try:
            amount = float(query.lower().split()[1])
            price = get_near_price_usd()
            near_amount = amount / price
            return f"✅ **SWAP:** {amount} USDC → **{near_amount:.6f} NEAR**\n💰 Price: ${price:.4f}"
        except:
            return "❌ Format: `swap 1 usdc for near`"
    return None

# Main UI
st.title("🤖 NEAR RAG Assistant")
st.markdown("**Try:** `swap 1 usdc for near` or ask about NEAR Protocol")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Your message..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # SWAP priority
    swap_result = parse_swap(prompt)
    if swap_result:
        with st.chat_message("assistant"):
            st.markdown(swap_result)
        st.session_state.messages.append({"role": "assistant", "content": swap_result})
    else:
        # RAG flow
        with st.chat_message("assistant"):
            with st.spinner("Searching NEAR docs..."):
                docs = search_docs(prompt)
                response = generate_response(prompt, "\n".join(docs))
                st.markdown(response)
                
                with st.expander("📚 Docs used"):
                    for i, doc in enumerate(docs[:2], 1):
                        st.write(f"**{i}.** {doc[:150]}...")
        
        st.session_state.messages.append({"role": "assistant", "content": response})
