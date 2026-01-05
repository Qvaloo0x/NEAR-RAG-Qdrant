import os
import requests
import streamlit as st
from dotenv import load_dotenv

# -------------------------------------------------
# Load environment variables
# -------------------------------------------------
load_dotenv()
CMC_API_KEY = os.getenv("CMC_API_KEY") or "6149fceb68f646848f2a0fe0299aba1a"

# -------------------------------------------------
# CoinMarketCap price fetch
# -------------------------------------------------
def get_near_price_usd() -> float:
    """
    Get NEAR/USD price from CoinMarketCap.
    Falls back to 4.20 if anything fails.
    """
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

# -------------------------------------------------
# Intent parsing (swap)
# -------------------------------------------------
def parse_swap_intent(text: str) -> str | None:
    """
    Parse commands like: "swap 1 usdc for near".
    Returns a rich markdown response including the DEX link,
    or None if no swap intent is found.
    """
    q = text.lower().strip()
    if "swap" not in q or "for near" not in q or "usdc" not in q:
        return None

    try:
        # Very naive parse: "swap 1 usdc for near"
        parts = q.split()
        # e.g. ["swap", "1", "usdc", "for", "near"]
        amount = float(parts[1])
    except Exception:
        return "❌ Format error. Try: `swap 1 usdc for near`."

    price = get_near_price_usd()
    near_out = amount / price

    response = (
        "🚀 NEAR INTENT DETECTED\n"
        f"💱 SWAP {amount} USDC → NEAR (estimation)\n"
        f"• Estimated output: ~{near_out:.4f} NEAR\n"
        "• Note: This is an estimate. You will set the exact USDC amount directly on Rhea.\n\n"
        "✅ Open Rhea (USDC ⇄ NEAR pool)\n"
        "[🌐 Rhea Finance](https://app.rhea.finance/)\n\n"
        "Y-24 stays humble: I guide you, you confirm the exact amount on-chain."
    )
    return response

# -------------------------------------------------
# Streamlit UI
# -------------------------------------------------
st.title("🤖 NEAR Swap Helper")
st.markdown("Type: `swap 1 usdc for near`")

if "messages" not in st.session_state:
    st.session_state.messages = []

# show history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# input
if prompt := st.chat_input("Your message..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    swap_reply = parse_swap_intent(prompt)
    if swap_reply:
        with st.chat_message("assistant"):
            st.markdown(swap_reply)
        st.session_state.messages.append({"role": "assistant", "content": swap_reply})
    else:
        fallback = "💡 Try: `swap 1 usdc for near` to get an estimated output and Rhea link."
        with st.chat_message("assistant"):
            st.markdown(fallback)
        st.session_state.messages.append({"role": "assistant", "content": fallback})
