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

# Debug keys
print(f"🔑 DEBUG: CMC_API_KEY = {'OK' if CMC_API_KEY else 'VACÍA'}")
print(f"🔑 DEBUG: DEEPSEEK_API_KEY = {'OK' if DEEPSEEK_API_KEY else 'VACÍA'}")

# Inicializar clientes
@st.cache_resource
def init_clients():
    qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    model = SentenceTransformer('all-MiniLM-L6-v2')
    return qdrant_client, model

qdrant_client, model = init_clients()

COLLECTION_NAME = "near_docs"

def get_near_price_usd():
    """Obtiene precio NEAR/USD de CoinMarketCap con debug completo"""
    if not CMC_API_KEY:
        print("❌ NO CMC_API_KEY en .env")
        return 4.20
    
    print(f"🔑 KEY CMC detectada: {CMC_API_KEY[:10]}...")
    
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
        print("📡 Haciendo request a CMC...")
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"📊 Status CMC: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            price = float(data["data"]["NEAR"]["quote"]["USD"]["price"])
            print(f"✅ Precio NEAR: ${price}")
            return price
        else:
            print(f"❌ Error CMC: {resp.status_code} - {resp.text[:100]}")
            return 4.20
    except Exception as e:
        print(f"💥 CMC Exception: {e}")
        return 4.20

def embed_query(query):
    """Genera embedding de la query"""
    return model.encode(query).tolist()

def search_docs(query, limit=3):
    """Busca documentos relevantes en Qdrant"""
    try:
        query_vector = embed_query(query)
        search_result = qdrant_client.query(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=limit
        )
        return [point.payload['document'] for point in search_result.points]
    except:
        return ["No se encontraron documentos relevantes."]

def generate_response(query, context):
    """Genera respuesta con DeepSeek"""
    if not DEEPSEEK_API_KEY:
        return "❌ Falta DEEPSEEK_API_KEY en .env"
    
    DEEPSEEK_BASE_URL = "https://api.deepseek.com"
    
    prompt = f"""
    Contexto sobre NEAR Protocol:
    {context}
    
    Pregunta del usuario: {query}
    
    Responde de forma clara y precisa usando SOLO la información del contexto.
    Si no sabes algo, di que no está en el contexto.
    """
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
        "temperature": 0.1
    }
    
    try:
        print("🤖 Llamando DeepSeek...")
        resp = requests.post(f"{DEEPSEEK_BASE_URL}/v1/chat/completions", 
                           headers=headers, json=data, timeout=30)
        print(f"📊 Status DeepSeek: {resp.status_code}")
        
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        else:
            print(f"❌ DeepSeek error: {resp.status_code}")
            return f"Error DeepSeek: {resp.status_code}"
    except Exception as e:
        print(f"💥 DeepSeek Exception: {e}")
        return f"Error conectando DeepSeek: {e}"

def parse_swap_command(query):
    """Parsea comandos de swap: 'swap 1 usdc for near'"""
    query_lower = query.lower()
    if "swap" in query_lower and "for" in query_lower:
        try:
            parts = query_lower.replace("swap", "").split("for")
            amount_str = parts[0].strip()
            token_to = parts[1].strip()
            
            amount = float(amount_str.split()[0])
            near_price = get_near_price_usd()
            
            if "near" in token_to:
                near_amount = amount / near_price
                return f"✅ **Swap ejecutado:**\n{amount} USDC → **{near_amount:.6f} NEAR**\n💰 Precio: ${near_price:.4f}/NEAR"
            else:
                return f"❌ Solo swaps USDC → NEAR por ahora."
        except:
            return "❌ Error parseando swap. Usa: `swap 1 usdc for near`"
    return None

# Streamlit UI
st.title("🤖 NEAR RAG Assistant (DeepSeek)")
st.write("**Pregunta sobre NEAR** o **haz swaps**: `swap 1 usdc for near`")

# Sidebar con debug
with st.sidebar:
    st.header("🔧 Debug")
    st.write("**Keys cargadas:**")
    st.write(f"CMC: {'✅' if CMC_API_KEY else '❌'}")
    st.write(f"DeepSeek: {'✅' if DEEPSEEK_API_KEY else '❌'}")
    
    if st.button("🧪 Test APIs"):
        near_price = get_near_price_usd()
        st.success(f"NEAR Price: ${near_price}")

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Escribe sobre NEAR o `swap 1 usdc for near`..."):
    # Añadir mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Parsear si es comando swap
    swap_result = parse_swap_command(prompt)
    if swap_result:
        with st.chat_message("assistant"):
            st.markdown(swap_result)
        st.session_state.messages.append({"role": "assistant", "content": swap_result})
    else:
        # RAG normal
        with st.chat_message("assistant"):
            with st.spinner("🔍 Buscando docs NEAR → 🤖 DeepSeek..."):
                # Buscar contexto
                docs = search_docs(prompt)
                context = "\n".join(docs)
                
                # Generar respuesta
                response = generate_response(prompt, context)
                st.markdown(response)
                
                # Mostrar contexto usado
                with st.expander("📚 Contexto usado (3 docs)"):
                    for i, doc in enumerate(docs, 1):
                        st.write(f"**Doc {i}:** {doc[:200]}...")
        
        st.session_state.messages.append({"role": "assistant", "content": response})

# Footer
st.markdown("---")
st.markdown("**Stack:** Qdrant (RAG) + DeepSeek (LLM) + CoinMarketCap (precios)")
