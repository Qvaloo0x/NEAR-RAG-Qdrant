import streamlit as st
import os
from dotenv import load_dotenv
import requests

# Load env (optional) + hardcoded CMC key for now
load_dotenv()
CMC_API_KEY = os.getenv("CMC_API_KEY") or "6149fceb68f646848f2a0fe0299aba1a"

def get_near_price_usd():
    """Get NEAR/USD price from CoinMarketCap."""
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

    # Fallback demo price
    return 4.20

def parse_swap(query: str) -> str | None:
    """Parse commands like: swap 1 usdc for near."""
    q = query.lower()
    if "swap" in q and "for near" in q and "usdc" in q:
        try:
            # very simple parse: "swap 1 usdc for near"
            parts = q.split()
            # parts = ["swap", "1", "usdc", "for", "near"]
            amount = float(parts[1])
            price = get_near_price_usd()
            near_out = amount / price

            # Build rich response including DEX link
            return (
                "🚀 NEAR INTENT DETECTED\n"
                f"💱 SWAP {amount} USDC → NEAR (estimation)\n"
                f"• Estimated output: ~{near_out:.4f} NEAR\n"
                f"• Note: This is an estimate. You will set the exact USDC amount directly on Rhea.\n\n"
                "✅ Open Rhea (USDC ⇄ NEAR pool)\n"
                "[🌐 Rhea Finance](https://app.rhea.finance/)\n\n"
                "Y-24 stays humble: I guide you, you confirm the exact amount on-chain."
            )
        except Exception:
            return "❌ Format error. Try: `swap 1 usdc for near`."
    return None

# ---------- Streamlit UI ----------

st.title("🤖 NEAR Swap Helper")
st.markdown("Try: `swap 1 usdc for near`")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Show history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Your message..."):
    # user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # try swap intent
    swap_reply = parse_swap(prompt)
    if swap_reply:
        with st.chat_message("assistant"):
            st.markdown(swap_reply)
        st.session_state.messages.append({"role": "assistant", "content": swap_reply})
    else:
        # fallback response
        reply = "💡 Try: `swap 1 usdc for near` to get an estimated output and Rhea link."
        with st.chat_message("assistant"):
            st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})
