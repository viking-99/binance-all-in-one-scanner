import time
import requests
import streamlit as st
import ccxt
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator


st.set_page_config(page_title="Crypto Scanner Pro", layout="wide")

st.markdown(
    "<h2 style='text-align: center; color: #10b981; font-family: Arial;'>"
    "💻 CRYPTO DUAL-SIGNAL SCANNER PRO"
    "</h2>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align: center; color: #9ca3af;'>"
    "Binance Futures GUI Multi-Scanner Pro"
    "</p>",
    unsafe_allow_html=True,
)
st.markdown("---")


page = st.sidebar.radio(
    "📌 เมนู",
    [
        "Market Scanner",
        "⚙ Debug API",
    ],
)


if page == "⚙ Debug API":
    st.title("⚙ API Connectivity Test")

    urls = {
        "Binance Futures": "https://fapi.binance.com/fapi/v1/exchangeInfo",
        "Bybit Linear": "https://api.bybit.com/v5/market/instruments-info?category=linear",
        "OKX Swap": "https://www.okx.com/api/v5/public/instruments?instType=SWAP",
        "Bitget Futures": "https://api.bitget.com/api/v2/mix/market/contracts?productType=USDT-FUTURES",
    }

    for name, url in urls.items():
        st.subheader(name)
        st.code(url)

        try:
            r = requests.get(url, timeout=10)
            st.write("Status code:", r.status_code)

            if r.status_code == 200:
                st.success("✅ ใช้งานได้")
            elif r.status_code == 451:
                st.error("❌ โดนบล็อก Region / Legal restriction")
            elif r.status_code == 403:
                st.error("❌ Forbidden / IP ถูกบล็อก")
            else:
                st.warning("⚠️ ตอบกลับ แต่ไม่ใช่ 200")

            st.code(r.text[:1000])

        except Exception as e:
            st.error("เชื่อมต่อไม่ได้")
            st.code(str(e))


else:
    st.sidebar.markdown(
        "<h3 style='color: #10b981;'>⚙️ ตั้งค่าระบบสแกน</h3>",
        unsafe_allow_html=True,
    )

    tf_choice = st.sidebar.selectbox(
        "เลือกช่วงเวลาแท่งเทียน (Timeframe):",
        ["3m", "5m", "15m", "1h", "4h", "1d"],
        index=3,
    )

    st.sidebar.markdown("### 🔍 ตั้งค่าตัวกรองและพารามิเตอร์ระบบ")

    scan_rsi = st.sidebar.checkbox("ใช้งาน RSI", value=True)
    with st.sidebar.expander("📊 ปรับค่าพารามิเตอร์ RSI", expanded=scan_rsi):
        rsi_low = st.number_input("RSI ซื้อเมื่อ <=", 1.0, 50.0, 35.0)
        rsi_high = st.number_input("RSI ขายเมื่อ >=", 50.0, 99.0, 65.0)
        rsi_len = st.number_input("ความยาว RSI", 2, 50, 14)

    scan_ema = st.sidebar.checkbox("ใช้งาน EMA Cross", value=True)
    with st.sidebar.expander("📈 ปรับค่าพารามิเตอร์ EMA", expanded=scan_ema):
        ema_len = st.number_input("EMA Length", 2, 200, 50)

    scan_smc = st.sidebar.checkbox("ใช้งาน SMC / Breakout", value=True)
    with st.sidebar.expander("🧱 ปรับค่าพารามิเตอร์ SMC", expanded=scan_smc):
        smc_len = st.number_input("Breakout ย้อนหลัง", 5, 100, 20)

    scan_btn = st.sidebar.button(
        "🚀 เริ่มสแกนสัญญาณ",
        type="primary",
        use_container_width=True,
    )

    exchange = ccxt.binance({
        "enableRateLimit": True,
        "options": {
            "defaultType": "future",
            "adjustForTimeDifference": True,
        },
    })

    if scan_btn:
        if not (scan_rsi or scan_ema or scan_smc):
            st.warning("กรุณาเลือก Indicator อย่างน้อย 1 ตัว")
        else:
            with st.spinner(f"กำลังสแกนตลาด Futures TF: {tf_choice}"):
                try:
                    exchange.load_markets()

                    symbols_to_scan = [
                        s for s in exchange.symbols
                        if "/USDT" in s and ":USDT" in s
                    ]

                    symbols_to_scan = symbols_to_scan[:25]

                    matched_list = []

                    for symbol in symbols_to_scan:
                        try:
                            time.sleep(0.1)

                            max_limit = max(
                                150,
                                int(rsi_len) + 50,
                                int(ema_len) + 50,
                                int(smc_len) + 50,
                            )

                            bars = exchange.fetch_ohlcv(
                                symbol,
                                timeframe=tf_choice,
                                limit=max_limit,
                            )

                            if len(bars) < max_limit - 30:
                                continue

                            df = pd.DataFrame(
                                bars,
                                columns=[
                                    "timestamp",
                                    "open",
                                    "high",
                                    "low",
                                    "close",
                                    "volume",
                                ],
                            )

                            symbol_clean = symbol.replace("/USDT:USDT", "")
                            last_price = df["close"].iloc[-1]
                            prev_price = df["close"].iloc[-2]

                            if scan_rsi:
                                rsi_init = RSIIndicator(
                                    close=df["close"],
                                    window=int(rsi_len),
                                )
                                df["RSI"] = rsi_init.rsi()
                                last_rsi = df["RSI"].iloc[-1]

                                if last_rsi <= rsi_low:
                                    matched_list.append({
                                        "คู่เหรียญ": symbol_clean,
                                        "ราคาปัจจุบัน": f"${last_price:,.4f}",
                                        "Indicator": f"RSI ({rsi_len})",
                                        "เงื่อนไข": f"Oversold RSI {last_rsi:.2f}",
                                        "สัญญาณ": "🟢 BUY / LONG",
                                    })
                                    continue

                                if last_rsi >= rsi_high:
                                    matched_list.append({
                                        "คู่เหรียญ": symbol_clean,
                                        "ราคาปัจจุบัน": f"${last_price:,.4f}",
                                        "Indicator": f"RSI ({rsi_len})",
                                        "เงื่อนไข": f"Overbought RSI {last_rsi:.2f}",
                                        "สัญญาณ": "🔴 SELL / SHORT",
                                    })
                                    continue

                            if scan_ema:
                                ema_init = EMAIndicator(
                                    close=df["close"],
                                    window=int(ema_len),
                                )
                                df["EMA"] = ema_init.ema_indicator()

                                last_ema = df["EMA"].iloc[-1]
                                prev_ema = df["EMA"].iloc[-2]

                                if prev_price < prev_ema and last_price > last_ema:
                                    matched_list.append({
                                        "คู่เหรียญ": symbol_clean,
                                        "ราคาปัจจุบัน": f"${last_price:,.4f}",
                                        "Indicator": f"EMA ({ema_len})",
                                        "เงื่อนไข": "ราคาตัดขึ้นเหนือ EMA",
                                        "สัญญาณ": "🟢 BUY / LONG",
                                    })
                                    continue

                                if prev_price > prev_ema and last_price < last_ema:
                                    matched_list.append({
                                        "คู่เหรียญ": symbol_clean,
                                        "ราคาปัจจุบัน": f"${last_price:,.4f}",
                                        "Indicator": f"EMA ({ema_len})",
                                        "เงื่อนไข": "ราคาตัดลงใต้ EMA",
                                        "สัญญาณ": "🔴 SELL / SHORT",
                                    })
                                    continue

                            if scan_smc:
                                highest_prev = (
                                    df["high"]
                                    .shift(1)
                                    .rolling(window=int(smc_len))
                                    .max()
                                    .iloc[-1]
                                )

                                lowest_prev = (
                                    df["low"]
                                    .shift(1)
                                    .rolling(window=int(smc_len))
                                    .min()
                                    .iloc[-1]
                                )

                                if last_price > highest_prev:
                                    matched_list.append({
                                        "คู่เหรียญ": symbol_clean,
                                        "ราคาปัจจุบัน": f"${last_price:,.4f}",
                                        "Indicator": "SMC / Breakout",
                                        "เงื่อนไข": f"ทะลุ High {smc_len} แท่ง",
                                        "สัญญาณ": "🟢 BUY / LONG",
                                    })
                                    continue

                                if last_price < lowest_prev:
                                    matched_list.append({
                                        "คู่เหรียญ": symbol_clean,
                                        "ราคาปัจจุบัน": f"${last_price:,.4f}",
                                        "Indicator": "SMC / Breakout",
                                        "เงื่อนไข": f"หลุด Low {smc_len} แท่ง",
                                        "สัญญาณ": "🔴 SELL / SHORT",
                                    })
                                    continue

                        except Exception:
                            continue

                    if not matched_list:
                        st.info(f"สแกนเสร็จ TF {tf_choice} แต่ไม่พบสัญญาณ")
                    else:
                        st.success(f"พบสัญญาณ {len(matched_list)} รายการ")
                        st.dataframe(
                            pd.DataFrame(matched_list),
                            use_container_width=True,
                            hide_index=True,
                        )

                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")