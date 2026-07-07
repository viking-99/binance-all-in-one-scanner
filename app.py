import streamlit as st
import ccxt
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

# ตั้งค่าหน้าตาของเว็บและสไตล์การแสดงผล
st.set_page_config(page_title="All-in-One Crypto Scanner", layout="wide")
st.markdown("<h2 style='text-align: center; color: #F3BA2F;'>📊 All-in-One Quant Scanner</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #848E9C;'>ระบบสแกนรวมทุก Indicator บน Binance Futures ในลิงก์เดียว</p>", unsafe_allow_html=True)
st.markdown("---")

# --- ส่วนควบคุมพารามิเตอร์ (Sidebar) ---
st.sidebar.header("⚙️ ตั้งค่าพารามิเตอร์หลัก")
tf_choice = st.sidebar.selectbox("1. เลือก Timeframe", ['3m', '5m', '15m', '30m', '1h', '4h'], index=4)

# เมนูเลือกเงื่อนไข Indicator ที่ต้องการสแกน
st.sidebar.markdown("### 🔍 เลือกเงื่อนไขการสแกน")
scan_mode = st.sidebar.radio(
    "รูปแบบการกรองข้อมูล",
    ["แสดงทุกเหรียญที่ติดสัญญาณใดสัญญาณหนึ่ง", "แสดงเฉพาะเหรียญที่ติดทุกสัญญาณพร้อมกัน (Combo)"]
)

# กล่องติ๊กเลือกเปิด-ปิด Indicator แต่ละตัว
use_smc = st.sidebar.checkbox("ใช้งาน SMC (Bullish FVG)", value=True)
use_breakout = st.sidebar.checkbox("ใช้งาน Price Breakout", value=True)
use_rsi = st.sidebar.checkbox("ใช้งาน RSI (Oversold/Overbought)", value=True)

# ปรับค่าพารามิเตอร์แบบละเอียด
with st.sidebar.expander("🛠️ ปรับค่าพารามิเตอร์ Indicator"):
    lookback = st.number_input("ระยะ Breakout (แท่งย้อนหลัง)", min_value=5, max_value=100, value=20)
    rsi_per = st.number_input("RSI Period", min_value=2, max_value=50, value=14)
    rsi_low = st.number_input("RSI Oversold (แนวรับ)", min_value=10, max_value=40, value=30)
    rsi_high = st.number_input("RSI Overbought (แนวต้าน)", min_value=60, max_value=90, value=70)
    min_volume = st.number_input("ขั้นต่ำ Volume 24ชม. (USDT)", min_value=0, value=1000000, step=500000)

scan_btn = st.sidebar.button("🚀 เริ่มสแกนเนอร์ระบบรวม", type="primary", use_container_width=True)

# เชื่อมต่อ Binance Futures Public API
exchange = ccxt.binance({'options': {'defaultType': 'future'}})

def calculate_and_scan(symbol):
    try:
        # ดึงข้อมูลแท่งเทียนย้อนหลัง 100 แท่ง
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_choice, limit=100)
        if not ohlcv or len(ohlcv) < max(int(lookback), int(rsi_per)) + 2:
            return None
            
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # คำนวณมูลค่าซื้อขายแท่งล่าสุดเพื่อกรองเหรียญไม่มีสภาพคล่อง
        last_volume_usdt = df['volume'].iloc[-1] * df['close'].iloc[-1]
        if last_volume_usdt < min_volume:
            return None

        # 1. คำนวณ RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=int(rsi_per)).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=int(rsi_per)).mean()
        rs = gain / (loss + 1e-10)
        df['rsi'] = 100 - (100 / (1 + rs))

        # 2. คำนวณ Breakout (ราคาทะลุ High สูงสุดย้อนหลัง ไม่รวมแท่งปัจจุบัน)
        df['highest_high'] = df['high'].shift(1).rolling(window=int(lookback)).max()
        df['lowest_low'] = df['low'].shift(1).rolling(window=int(lookback)).min()
        
        # 3. คำนวณ SMC (Bullish FVG และ Bearish FVG)
        df['fvg_bullish'] = df['low'] > df['high'].shift(2)
        df['fvg_bearish'] = df['high'] < df['low'].shift(2)

        last_row = df.iloc[-1]
        
        # ตรวจสอบสถานะแต่ละ Indicator
        is_breakout_up = last_row['close'] > last_row['highest_high']
        is_breakout_down = last_row['close'] < last_row['lowest_low']
        is_fvg_bull = last_row['fvg_bullish']
        is_fvg_bear = last_row['fvg_bearish']
        is_rsi_os = last_row['rsi'] < rsi_low
        is_rsi_ob = last_row['rsi'] > rsi_high

        # รวบรวมสัญญาณที่เกิดขึ้นจริง
        signals = []
        if use_breakout and is_breakout_up: signals.append("🟩 Breakout UP")
        if use_breakout and is_breakout_down: signals.append("🟥 Breakout DOWN")
        if use_smc and is_fvg_bull: signals.append("🟩 Bullish FVG (SMC)")
        if use_smc and is_fvg_bear: signals.append("🟥 Bearish FVG (SMC)")
        if use_rsi and is_rsi_os: signals.append("🟩 RSI Oversold")
        if use_rsi and is_rsi_ob: signals.append("🟥 RSI Overbought")

        # ตรวจสอบเงื่อนไขตามโหมดที่ผู้ใช้เลือก
        if scan_mode == "แสดงเฉพาะเหรียญที่ติดทุกสัญญาณพร้อมกัน (Combo)":
            # นับจำนวน Indicator ที่ผู้ใช้เปิดใช้งานจริง
            active_count = sum([use_smc, use_breakout, use_rsi])
            # ตรวจสอบว่าสัญญาณขึ้นครบตามจำนวนที่เปิดไหม
            if len(signals) >= active_count and len(signals) > 0:
                return {"Symbol": symbol.replace(':USDT', ''), "Price": float(last_row['close']), "RSI": round(float(last_row['rsi']), 2), "Signal": " & ".join(signals)}
        else:
            # โหมดทั่วไป: เจอสัญญาณไหนอันเดียวก็เอาแสดงผลเลย
            if signals:
                return {"Symbol": symbol.replace(':USDT', ''), "Price": float(last_row['close']), "RSI": round(float(last_row['rsi']), 2), "Signal": " | ".join(signals)}
                
    except:
        pass
    return None

# --- ส่วนประมวลผลหน้าเว็บหลัก ---
if scan_btn:
    # ตรวจสอบก่อนว่าเลือกเปิดใช้สักตัวไหม
    if not (use_smc or use_breakout or use_rsi):
        st.warning("⚠️ โปรดเลือกเปิดใช้งาน Indicator อย่างน้อย 1 ตัวที่แถบด้านข้างก่อนกดสแกนครับ")
    else:
        with st.spinner(f"🔄 ระบบกำลังสแกนเหรียญที่ตรงเงื่อนไขใน Timeframe: {tf_choice} ..."):
            try:
                exchange.load_markets()
                symbols = [s for s in exchange.symbols if s.endswith(':USDT')]
                
                matched_list = []
                # ดึงราคาแบบขนานเพื่อความเร็วสูงสุด
                with ThreadPoolExecutor(max_workers=20) as executor:
                    results = executor.map(calculate_and_scan, symbols)
                    for r in results:
                        if r: matched_list.append(r)
                
                if matched_list:
                    st.success(f"🔥 สแกนเสร็จสิ้น! พบเหรียญที่เข้าเงื่อนไข {len(matched_list)} คู่เหรียญ")
                    df_res = pd.DataFrame(matched_list)
                    st.dataframe(df_res, use_container_width=True, hide_index=True)
                else:
                    st.info("ไม่พบเหรียญที่ตรงตามเงื่อนไขที่เลือกในแท่งเทียนปัจจุบัน ลองเปลี่ยนโหมดหรือปรับค่าพารามิเตอร์ให้กว้างขึ้น")
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อระบบ: {e}")
