import time
import requests
import streamlit as st
import ccxt
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator


st.set_page_config(page_title="Crypto Scanner Pro", layout="wide")

st.markdown(
    "<h2 style='text-align: center; color: #10b981;'>"
    "💻 CRYPTO DUAL-SIGNAL SCANNER PRO"
    "</h2>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align: center; color: #9ca3af;'>"
    "Multi-Exchange Futures Scanner"
    "</p>",
    unsafe_allow_html=True,
)
st.markdown("---")


page = st.sidebar.radio("📌 เมนู", ["Market Scanner", "⚙ Debug API"])


def create_exchange(exchange_name: str):
    if exchange_name == "OKX":
        return ccxt.okx({"enableRateLimit": True})
    if exchange_name == "Binance":
        return ccxt.binance({
            "enableRateLimit": True,
            "options": {"defaultType": "future"},
        })
    raise ValueError("ยังรองรับเฉพาะ OKX และ Binance")


def get_symbols(exchange, exchange_name: str):
    exchange.load_markets()

    if exchange_name == "OKX":
        return [
            s for s, m in exchange.markets.items()
            if m.get("swap") and m.get("quote") == "USDT" and m.get("active")
        ][:25]

    if exchange_name == "Binance":
        return [
            s for s, m in exchange.markets.items()
            if m.get("swap") and m.get("quote") == "USDT" and m.get("active")
        ][:25]

    return []


if page == "⚙ Debug API":
    st.title("⚙ API Connectivity Test")

    urls = {
        "Binance Futures": "https://fapi.binance.com/fapi/v1/exchangeInfo",
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
    st.sidebar.markdown("### ⚙️ ตั้งค่าระบบสแกน")

    exchange_name = st.sidebar.selectbox(
        "เลือก Exchange",
        ["OKX", "Binance"],
        index=0,
    )

    tf_choice = st.sidebar.selectbox(
        "เลือก Timeframe",
        ["3m", "5m", "15m", "1h", "4h", "1d"],
        index=2,
    )

    st.sidebar.markdown("### 🔍 Indicator")

    scan_rsi = st.sidebar.checkbox("RSI", value=True)
    with st.sidebar.expander("📊 RSI Settings", expanded=False):
        rsi_low = st.number_input("RSI ซื้อเมื่อ <=", 1.0, 50.0, 35.0)
        rsi_high = st.number_input("RSI ขายเมื่อ >=", 50.0, 99.0, 65.0)
        rsi_len = st.number_input("RSI Length", 2, 50, 14)

    scan_ema = st.sidebar.checkbox("EMA Cross", value=True)
    with st.sidebar.expander("📈 EMA Settings", expanded=False):
        ema_len = st.number_input("EMA Length", 2, 200, 50)

    scan_smc = st.sidebar.checkbox("SMC / Breakout", value=True)
    with st.sidebar.expander("🧱 Breakout Settings", expanded=False):
        smc_len = st.number_input("Breakout ย้อนหลัง", 5, 100, 20)

    scan_btn = st.sidebar.button("🚀 Scan Market", type="primary", use_container_width=True)

    st.title("Market Scanner")
    st.caption(f"Exchange: {exchange_name} | Timeframe: {tf_choice}")

    if exchange_name == "Binance":
        st.warning("Binance อาจใช้งานไม่ได้บน Streamlit Cloud เพราะโดน 451 ให้ใช้ OKX ก่อน")

    if scan_btn:
        if not (scan_rsi or scan_ema or scan_smc):
            st.warning("กรุณาเลือก Indicator อย่างน้อย 1 ตัว")
        else:
            with st.spinner(f"กำลังสแกน {exchange_name} TF: {tf_choice}"):
                try:
                    exchange = create_exchange(exchange_name)
                    symbols_to_scan = get_symbols(exchange, exchange_name)

                    matched_list = []

                    progress = st.progress(0)
                    total = len(symbols_to_scan)

                    for i, symbol in enumerate(symbols_to_scan):
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

                            if not bars or len(bars) < 50:
                                continue

                            df = pd.DataFrame(
                                bars,
                                columns=["timestamp", "open", "high", "low", "close", "volume"],
                            )

                            for col in ["open", "high", "low", "close", "volume"]:
                                df[col] = pd.to_numeric(df[col], errors="coerce")

                            symbol_clean = symbol
                            last_price = df["close"].iloc[-1]
                            prev_price = df["close"].iloc[-2]

                            if scan_rsi:
                                rsi_init = RSIIndicator(close=df["close"], window=int(rsi_len))
                                df["RSI"] = rsi_init.rsi()
                                last_rsi = df["RSI"].iloc[-1]

                                if last_rsi <= rsi_low:
                                    matched_list.append({
                                        "Exchange": exchange_name,
                                        "คู่เหรียญ": symbol_clean,
                                        "ราคาปัจจุบัน": f"{last_price:,.6f}",
                                        "Indicator": f"RSI ({rsi_len})",
                                        "เงื่อนไข": f"Oversold RSI {last_rsi:.2f}",
                                        "สัญญาณ": "🟢 BUY / LONG",
                                    })
                                    continue

                                if last_rsi >= rsi_high:
                                    matched_list.append({
                                        "Exchange": exchange_name,
                                        "คู่เหรียญ": symbol_clean,
                                        "ราคาปัจจุบัน": f"{last_price:,.6f}",
                                        "Indicator": f"RSI ({rsi_len})",
                                        "เงื่อนไข": f"Overbought RSI {last_rsi:.2f}",
                                        "สัญญาณ": "🔴 SELL / SHORT",
                                    })
                                    continue

                            if scan_ema:
                                ema_init = EMAIndicator(close=df["close"], window=int(ema_len))
                                df["EMA"] = ema_init.ema_indicator()

                                last_ema = df["EMA"].iloc[-1]
                                prev_ema = df["EMA"].iloc[-2]

                                if prev_price < prev_ema and last_price > last_ema:
                                    matched_list.append({
                                        "Exchange": exchange_name,
                                        "คู่เหรียญ": symbol_clean,
                                        "ราคาปัจจุบัน": f"{last_price:,.6f}",
                                        "Indicator": f"EMA ({ema_len})",
                                        "เงื่อนไข": "ราคาตัดขึ้นเหนือ EMA",
                                        "สัญญาณ": "🟢 BUY / LONG",
                                    })
                                    continue

                                if prev_price > prev_ema and last_price < last_ema:
                                    matched_list.append({
                                        "Exchange": exchange_name,
                                        "คู่เหรียญ": symbol_clean,
                                        "ราคาปัจจุบัน": f"{last_price:,.6f}",
                                        "Indicator": f"EMA ({ema_len})",
                                        "เงื่อนไข": "ราคาตัดลงใต้ EMA",
                                        "สัญญาณ": "🔴 SELL / SHORT",
                                    })
                                    continue

                            if scan_smc:
                                highest_prev = (
                                    df["high"].shift(1).rolling(window=int(smc_len)).max().iloc[-1]
                                )
                                lowest_prev = (
                                    df["low"].shift(1).rolling(window=int(smc_len)).min().iloc[-1]
                                )

                                if last_price > highest_prev:
                                    matched_list.append({
                                        "Exchange": exchange_name,
                                        "คู่เหรียญ": symbol_clean,
                                        "ราคาปัจจุบัน": f"{last_price:,.6f}",
                                        "Indicator": "SMC / Breakout",
                                        "เงื่อนไข": f"ทะลุ High {smc_len} แท่ง",
                                        "สัญญาณ": "🟢 BUY / LONG",
                                    })
                                    continue

                                if last_price < lowest_prev:
                                    matched_list.append({
                                        "Exchange": exchange_name,
                                        "คู่เหรียญ": symbol_clean,
                                        "ราคาปัจจุบัน": f"{last_price:,.6f}",
                                        "Indicator": "SMC / Breakout",
                                        "เงื่อนไข": f"หลุด Low {smc_len} แท่ง",
                                        "สัญญาณ": "🔴 SELL / SHORT",
                                    })
                                    continue

                        except Exception:
                            continue
                        finally:
                            progress.progress((i + 1) / total if total else 1.0)

                    if not matched_list:
                        st.info(f"สแกนเสร็จ TF {tf_choice} แต่ไม่พบสัญญาณ")
                    else:
                        st.success(f"พบสัญญาณ {len(matched_list)} รายการ")
                        st.dataframe(pd.DataFrame(matched_list), use_container_width=True, hide_index=True)

                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")