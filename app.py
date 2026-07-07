import streamlit as st
import ccxt
import pandas as pd
import ta
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator

# ตั้งค่าธีมหน้าเว็บให้แสดงผลแบบกว้างและรองรับ Dark Mode มือถือ
st.set_page_config(page_title="Binance Futures GUI Multi-Scanner Pro", layout="wide")

# ออกแบบหัวข้อแอปตามสไตล์ GUI ของคุณ
st.markdown("<h2 style='text-align: center; color: #10b981; font-family: Arial;'>💻 CRYPTO DUAL-SIGNAL SCANNER PRO</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #9ca3af;'>Binance Futures GUI Multi-Scanner Pro (เวอร์ชันพกพาบนมือถือ)</p>", unsafe_allow_html=True)
st.markdown("---")

# --- PANEL 1 & 2: SETUP PARAMETERS (Sidebar) ---
st.sidebar.markdown("<h3 style='color: #10b981;'>⚙️ ตั้งค่าระบบสแกน</h3>", unsafe_allow_html=True)

# ติ๊กเลือกช่วงเวลาแท่งเทียน (Timeframe)
tf_choice = st.sidebar.selectbox(
    "เลือกช่วงเวลาแท่งเทียน (Timeframe):", 
    ["3m", "5m", "15m", "1h", "4h", "1d"], 
    index=3  # เลือก 1h เป็นค่าเริ่มต้นตามโค้ดของคุณ
)

st.sidebar.markdown("### 🔍 ตั้งค่าตัวกรองและพารามิเตอร์ระบบ")

# ตัวกรอง RSI
scan_rsi = st.sidebar.checkbox("ใช้งาน RSI (Oversold/Overbought)", value=True)
with st.sidebar.expander("📊 ปรับค่าพารามิเตอร์ RSI", expanded=scan_rsi):
    rsi_low = st.number_input("RSI ซื้อเมื่อ <= (Oversold)", min_value=1.0, max_value=50.0, value=35.0)
    rsi_high = st.number_input("RSI ขายเมื่อ >= (Overbought)", min_value=50.0, max_value=99.0, value=65.0)
    rsi_len = st.number_input("ความยาว RSI (Length)", min_value=2, max_value=50, value=14)

# ตัวกรอง EMA
scan_ema = st.sidebar.checkbox("ใช้งาน EMA Cross (ราคาตัดเส้น)", value=True)
with st.sidebar.expander("📈 ปรับค่าพารามิเตอร์ EMA", expanded=scan_ema):
    ema_len = st.number_input("EMA ตัดขึ้น/ลง เส้นความยาว:", min_value=2, max_value=200, value=50)

# ตัวกรอง SMC
scan_smc = st.sidebar.checkbox("ใช้งาน SMC / Breakout", value=True)
with st.sidebar.expander("🧱 ปรับค่าพารามิเตอร์ SMC", expanded=scan_smc):
    smc_len = st.number_input("SMC ทะลุ High/Low ย้อนหลัง:", min_value=5, max_value=100, value=20)

# ปุ่มสั่งสแกนดีไซน์สีเขียวสะดุดตา
scan_btn = st.sidebar.button("🔄 เริ่มสแกนสัญญาณ ซื้อ & ขาย ตลาด Futures", type="primary", use_container_width=True)

# เชื่อมต่อ Binance Futures ด้วยรูปแบบพาสแกนผ่านชัวร์ๆ 
exchange = ccxt.binance({'options': {'defaultType': 'future'}})

# --- ส่วนประมวลผลการสแกนราคาสด ---
if scan_btn:
    if not (scan_rsi or scan_ema or scan_smc):
        st.warning("⚠️ กรุณาเลือกเงื่อนไข Indicator อย่างน้อย 1 ตัวก่อนเริ่มสแกนครับ")
    else:
        # กล่องจำลองสเตตัสโหลดแบบเดียวกับโปรแกรมเดิมของคุณ
        with st.spinner(f"⌛ กำลังสแกนตลาดฟิวเจอร์สทั้งหมด (TF: {tf_choice})..."):
            try:
                exchange.load_markets()
                
                # ถอดรูปรหัสคู่เหรียญแบบดั้งเดิมที่ Binance ปล่อยผ่าน
                symbols_to_scan = [s for s in exchange.symbols if '/USDT' in s and ':' not in s]
                
                # แนะนำกรองสแกนช่วง 40 คู่เหรียญแรก เพื่อป้องกันระบบหน่วงบนเว็บบราวเซอร์มือถือ
                symbols_to_scan = symbols_to_scan[:40] 
                
                matched_list = []
                detected_count = 0
                
                for symbol in symbols_to_scan:
                    try:
                        max_limit = max(150, int(rsi_len) + 50, int(ema_len) + 50, int(smc_len) + 50)
                        bars = exchange.fetch_ohlcv(symbol, timeframe=tf_choice, limit=max_limit)
                        
                        if len(bars) < max_limit - 30: 
                            continue
                            
                        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                        symbol_clean = symbol.replace('/USDT', '')
                        last_price = df['close'].iloc[-1]
                        prev_price = df['close'].iloc[-2]

                        # --- 1. ตรวจสอบเงื่อนไข RSI ---
                        if scan_rsi:
                            rsi_init = RSIIndicator(close=df['close'], window=int(rsi_len))
                            df['RSI'] = rsi_init.rsi()
                            last_rsi = df['RSI'].iloc[-1]
                            
                            if last_rsi <= rsi_low:
                                matched_list.append({
                                    "คู่เหรียญ": symbol_clean, "ราคาปัจจุบัน": f"${last_price:,}",
                                    "ประเภทอินดิเคเตอร์": f"RSI ({rsi_len})", "เงื่อนไขเทคนิคอลที่เกิดขึ้น": f"Oversold (RSI: {last_rsi:.2f})", "คำแนะนำสัญญาณ": "🟢 BUY / LONG"
                                })
                                detected_count += 1
                                continue 
                            elif last_rsi >= rsi_high:
                                matched_list.append({
                                    "คู่เหรียญ": symbol_clean, "ราคาปัจจุบัน": f"${last_price:,}",
                                    "ประเภทอินดิเคเตอร์": f"RSI ({rsi_len})", "เงื่อนไขเทคนิคอลที่เกิดขึ้น": f"Overbought (RSI: {last_rsi:.2f})", "คำแนะนำสัญญาณ": "🔴 SELL / SHORT"
                                })
                                detected_count += 1
                                continue

                        # --- 2. ตรวจสอบเงื่อนไข EMA ---
                        if scan_ema:
                            ema_init = EMAIndicator(close=df['close'], window=int(ema_len))
                            df['EMA'] = ema_init.ema_indicator()
                            last_ema = df['EMA'].iloc[-1]
                            prev_ema = df['EMA'].iloc[-2]
                            
                            if prev_price < prev_ema and last_price > last_ema:
                                matched_list.append({
                                    "คู่เหรียญ": symbol_clean, "ราคาปัจจุบัน": f"${last_price:,}",
                                    "ประเภทอินดิเคเตอร์": f"EMA ({ema_len})", "เงื่อนไขเทคนิคอลที่เกิดขึ้น": f"ราคาตัดทะลุขึ้น ยืนเหนือเส้น EMA {ema_len}", "คำแนะนำสัญญาณ": "🟢 BUY / LONG"
                                })
                                detected_count += 1
                                continue
                            elif prev_price > prev_ema and last_price < last_ema:
                                matched_list.append({
                                    "คู่เหรียญ": symbol_clean, "ราคาปัจจุบัน": f"${last_price:,}",
                                    "ประเภทอินดิเคเตอร์": f"EMA ({ema_len})", "เงื่อนไขเทคนิคอลที่เกิดขึ้น": f"ราคาตัดดิ่งหลุด ใต้เส้น EMA {ema_len}", "คำแนะนำสัญญาณ": "🔴 SELL / SHORT"
                                })
                                detected_count += 1
                                continue

                        # --- 3. ตรวจสอบเงื่อนไข SMC / Breakout ---
                        if scan_smc:
                            highest_prev = df['high'].shift(1).rolling(window=int(smc_len)).max().iloc[-1]
                            if last_price > highest_prev:
                                matched_list.append({
                                    "คู่เหรียญ": symbol_clean, "ราคาปัจจุบัน": f"${last_price:,}",
                                    "ประเภทอินดิเคเตอร์": "SMC / Break", "เงื่อนไขเทคนิคอลที่เกิดขึ้น": f"ทะลุ High รอบ {smc_len} แท่ง (${highest_prev:,})", "คำแนะนำสัญญาณ": "🟢 BUY / LONG"
                                })
                                detected_count += 1
                                continue
                                
                            lowest_prev = df['low'].shift(1).rolling(window=int(smc_len)).min().iloc[-1]
                            if last_price < lowest_prev:
                                matched_list.append({
                                    "คู่เหรียญ": symbol_clean, "ราคาปัจจุบัน": f"${last_price:,}",
                                    "ประเภทอินดิเคเตอร์": "SMC / Break", "เงื่อนไขเทคนิคอลที่เกิดขึ้น": f"ดิ่งหลุด Low รอบ {smc_len} แท่ง (${lowest_prev:,})", "คำแนะนำสัญญาณ": "🔴 SELL / SHORT"
                                })
                                detected_count += 1
                                continue
                    except:
                        continue
                
                # --- แสดงผลลัพธ์ผ่านหน้าจอหลัก (ตารางแบบ Treeview ดั้งเดิม) ---
                if detected_count == 0:
                    st.info(f"ℹ️ สแกนเสร็จสิ้นใน TF {tf_choice} แต่ไม่พบเหรียญที่ตรงเงื่อนไขในรอบนี้ครับ")
                else:
                    st.success(f"🎉 สแกนเสร็จสิ้นใน TF {tf_choice}! พบเหรียญเข้าเงื่อนไขทั้งหมด {detected_count} รายการ")
                    df_res = pd.DataFrame(matched_list)
                    
                    # พ่นตารางรูปแบบ Interactive ปรับแต่งตามขนาดจอมือถืออัตโนมัติ
                    st.dataframe(df_res, use_container_width=True, hide_index=True)
                    
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดรุนแรงในระบบคำนวณ: {str(e)}")
