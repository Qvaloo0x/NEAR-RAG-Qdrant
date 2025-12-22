import streamlit as st
import os
from dotenv import load_dotenv
import requests
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# Cargar variables de entorno
load_dotenv()
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
CMC_API_KEY = os.getenv("CMC_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Debug sidebar
st.sidebar.title("🔧 Status APIs")
st.sidebar.success("✅ Interfaz OK")

# Inicializar clientes con fallback
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
    """Precio NEAR con fallback a 4.20 si CMC falla"""
    if not CMC_API_KEY:
        st.sidebar.error("❌ CMC: Sin key")
        return 4.20
    
    try:
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY, "Accept": "application/json"}
        params = {"symbol": "NEAR", "convert": "USD"}
        
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        if resp.status_code == 200:
            price = float(resp.json()["data"]["NEAR"]["quote"]["USD"]["price"])
            st.sidebar.success(f"✅ CMC: ${price}")
            return price
        else:
            st.sidebar.error(f"❌ CMC: {resp.status_code}")
    except:
        st.sidebar.error("❌ CMC: Error")
    
    return 4.20  # Fallback seguro

def search_docs(query):
    """Busca docs o fallback"""
    if not qdrant_client or not model:
        return ["**Fallback:** No hay conexión a Qdrant. Prueba: `swap 1 usdc for near`"]
    
    try:
        query_vector = model.encode(query).tolist()
        result = qdrant_client.query(
            collection_name="near_docs",
            query_vector=query_vector,
            limit=2
        )
        return [p.payload.get('document', 'Doc sin texto') for p in result.points]
    except:
        return ["**Fallback:** Error buscando docs. Usa comandos swap."]

def generate_response(query, context):
    """DeepSeek con fallback"""
    if not DEEPSEEK_API_KEY:
        st.sidebar.error("❌ DeepSeek: Sin key")
        return "💡 **Prueba:** `swap 1 usdc for near` (usa CoinMarketCap)"
    
    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": f"Pregunta: {query}\n\nContexto: {context}\n\nResponde breve."}],
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
    
    return "🤖 **Modo fallback:** Escribe `swap 1 usdc for near` para probar CoinMarketCap."

def parse_swap(query):
    """Swap con precio real"""
    if "swap" in query.lower() and "for near" in query.lower():
        try:
            amount = float(query.lower().split()[1])
            price = get_near_price_usd()
            near_amount = amount / price
            return f"✅ **SWAP:** {amount} USDC → **{near_amount:.6f} NEAR**\n💰 Precio actual: ${price:.4f}"
        except:
            return "❌ Formato: `swap 1 usdc for near`"
    return None

# UI Principal
st.title("🤖 NEAR Assistant")
st.markdown("**Prueba:** `swap 1 usdc for near` o pregunta sobre NEAR")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Tu mensaje..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # SWAP primero (prioridad)
    swap_result = parse_swap(prompt)
    if swap_result:
        with st.chat_message("assistant"):
            st.markdown(swap_result)
        st.session_state.messages.append({"role": "assistant", "content": swap_result})
    else:
        # RAG normal
        with st.chat_message("assistant"):
            with st.spinner("Procesando..."):
                docs = search_docs(prompt)
                response = generate_response(prompt, "\n".join(docs))
                st.markdown(response)
                
                with st.expander("📚 Docs usados"):
                    for i, doc in enumerate(docs[:2], 1):
                        st.write(f"**{i}.** {doc[:150]}...")
        
        st.session_state.messages.append({"role": "assistant", "content": response})
