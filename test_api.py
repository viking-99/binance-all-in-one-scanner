 import streamlit as st
import requests

st.title("API Connectivity Test")

urls = {
    "Binance Futures": "https://fapi.binance.com/fapi/v1/exchangeInfo",
    "Bybit Linear": "https://api.bybit.com/v5/market/instruments-info?category=linear",
    "OKX Swap": "https://www.okx.com/api/v5/public/instruments?instType=SWAP",
}

for name, url in urls.items():
    st.subheader(name)
    st.code(url)

    try:
        r = requests.get(url, timeout=10)

        st.write("Status code:", r.status_code)

        if r.status_code == 200:
            st.success("ใช้งานได้")
        elif r.status_code == 451:
            st.error("โดนบล็อก Region / Legal restriction")
        elif r.status_code == 403:
            st.error("โดนบล็อก Forbidden")
        else:
            st.warning("ตอบกลับ แต่ไม่ใช่ 200")

        st.code(r.text[:1000])

    except Exception as e:
        st.error("เชื่อมต่อไม่ได้")
        st.code(str(e))