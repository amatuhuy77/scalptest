import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
import streamlit.components.v1 as components
from datetime import datetime
import pytz

st.set_page_config(page_title="XAU/USD M1 & M5 Scalper Pro", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .block-container {
        padding-top: 0.6rem !important;
        padding-bottom: 0.6rem !important;
        padding-left: 0.4rem !important;
        padding-right: 0.4rem !important;
        max-width: 100% !important;
    }
    @media (max-width: 768px) {
        h1 { font-size: 1.4rem !important; }
        h3 { font-size: 1rem !important; }
    }
    </style>
""", unsafe_allow_html=True)

st.title("XAU/USD - DUAL SCALPER AI (M1 & M5) ⚡")

def get_market_session_wita():
    wita = pytz.timezone('Asia/Makassar')
    now_wita = datetime.now(wita)
    jam = now_wita.hour
    waktu_str = f"{jam:02d}:{now_wita.minute:02d} WITA"
    
    if 6 <= jam < 14: return waktu_str, "Sesi Asia 🌏", "Range Sempit (Fokus M1/M5 Aman)"
    elif 14 <= jam < 20: return waktu_str, "Sesi London 🌍", "Breakout Kuat (Hati-hati Lonjakan)"
    else: return waktu_str, "Sesi New York 🌎", "Sangat Volatil (Gunakan SL Ketat)"

waktu, sesi, karakter = get_market_session_wita()
st.info(f"🕒 **{waktu}** | **{sesi}**\n\n💡 {karakter}")

# Fungsi AI Dinamis untuk M1 atau M5
@st.cache_data(ttl=5)
def hitung_ai_multi(interval):
    tf_map = {"M1": "1m", "M5": "5m"}
    period_map = {"M1": "5d", "M5": "1mo"}
    
    gold = yf.download("XAUUSD=X", period=period_map[interval], interval=tf_map[interval], progress=False)
    
    if gold.empty:
        gold = yf.download("GC=F", period=period_map[interval], interval=tf_map[interval], progress=False)
    if gold.empty:
        raise ValueError(f"Yahoo Finance membatasi data {interval}. Coba beberapa saat lagi.")

    df = pd.DataFrame(index=gold.index)
    df['Close'] = gold['Close']
    df['Open'] = gold['Open']
    df['High'] = gold['High']
    df['Low'] = gold['Low']
    df.dropna(inplace=True)
    
    df['Return'] = df['Close'].pct_change()
    df['Body'] = df['Close'] - df['Open']
    
    window_size = 10 if interval == "M1" else 14
    
    df['SMA'] = df['Close'].rolling(window=window_size).mean()
    df['Std_Dev'] = df['Close'].rolling(window=window_size).std()
    df['BB_Width'] = (df['SMA'] + (df['Std_Dev'] * 2)) - (df['SMA'] - (df['Std_Dev'] * 2))
    
    df['TR'] = np.maximum(df['High'] - df['Low'], 
                          np.maximum(abs(df['High'] - df['Close'].shift(1)), 
                                     abs(df['Low'] - df['Close'].shift(1))))
    df['ATR'] = df['TR'].rolling(window=window_size).mean()
    
    df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
    df.dropna(inplace=True)
    
    if len(df) < 15: 
        raise ValueError(f"Data {interval} terkumpul hanya {len(df)} baris. Belum cukup.")
    
    features = ['Return', 'Body', 'BB_Width', 'ATR']
    model = XGBClassifier(n_estimators=60, learning_rate=0.12, max_depth=3, random_state=42)
    model.fit(df[features][:-1], df['Target'][:-1])
    
    latest_data = df[features].tail(1)
    proba = model.predict_proba(latest_data)[0]
    
    return df['Close'].iloc[-1], df['ATR'].iloc[-1], proba[1]*100, proba[0]*100

st.subheader("🤖 Pilih Timeframe Analisis AI")

if 'tf_aktif' not in st.session_state:
    st.session_state.tf_aktif = "M1"

pilih_col1, pilih_col2 = st.columns(2)
with pilih_col1:
    if st.button("⚡ Mode M1 (Cepat)", use_container_width=True):
        st.session_state.tf_aktif = "M1"
with pilih_col2:
    if st.button("🛡️ Mode M5 (Tren)", use_container_width=True):
        st.session_state.tf_aktif = "M5"

st.markdown(f"**AI Aktif:** Timeframe **{st.session_state.tf_aktif}** (Auto-Update 5 Detik)")

@st.fragment(run_every="5s")
def ai_dual_dashboard():
    try:
        tf = st.session_state.tf_aktif
        c_price, c_atr, p_naik, p_turun = hitung_ai_multi(tf)
        
        pengali_tp = 1.2 if tf == "M1" else 1.8
        pengali_sl = 0.9 if tf == "M1" else 1.2
        
        jarak_tp = c_atr * pengali_tp
        jarak_sl = c_atr * pengali_sl
        
        batas_naik = c_price + jarak_tp
        batas_turun = c_price - jarak_tp
        
        if p_naik >= 58.0:
            st.success(f"🟢 **BUY SCALP ({tf})** | Prob: **{p_naik:.1f}%** | Entry: **${c_price:.2f}**\n\n📈 **TP:** ${batas_naik:.2f} *(+${jarak_tp:.2f})* \n\n🛡️ **SL:** ${c_price - jarak_sl:.2f} *(-${jarak_sl:.2f})*")
        elif p_turun >= 58.0:
            st.error(f"🔴 **SELL SCALP ({tf})** | Prob: **{p_turun:.1f}%** | Entry: **${c_price:.2f}**\n\n📉 **TP:** ${batas_turun:.2f} *(-${jarak_tp:.2f})* \n\n🛡️ **SL:** ${c_price + jarak_sl:.2f} *(+${jarak_sl:.2f})*")
        else:
            st.warning(f"⚪ **WAIT ({tf})** | Naik {p_naik:.1f}% vs Turun {p_turun:.1f}%.\n\nPasar konsolidasi di {tf}. Tunggu arah dominan.")
            
    except Exception as e:
        st.error(f"Gagal memproses AI {st.session_state.tf_aktif}: {e}")

ai_dual_dashboard()

st.markdown("---")

st.subheader("📊 Grafik Live (OANDA)")

# ==========================================
# PENGATURAN UKURAN GRAFIK (PANJANG & LEBAR)
# ==========================================
TINGGI_GRAFIK = 500  # Ubah angka ini jika ingin lebih panjang atau pendek ke bawah
LEBAR_GRAFIK = "100%" # Ubah ukuran lebar jika diinginkan

tradingview_html = """
<!-- TradingView Widget BEGIN -->
<div class="tradingview-widget-container" style="height:100%; width:100%;">
  <div id="tradingview_xauusd" style="height:100%; width:100%;"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
  <script type="text/javascript">
  new TradingView.widget(
  {
  "autosize": true,
  "symbol": "OANDA:XAUUSD",
  "interval": "1",
  "timezone": "Asia/Makassar",
  "theme": "dark",
  "style": "1",
  "locale": "id",
  "enable_publishing": false,
  "backgroundColor": "#0e1117",
  "gridColor": "#222629",
  "hide_top_toolbar": false,
  "hide_legend": false,
  "save_image": false,
  "container_id": "tradingview_xauusd",
  "toolbar_bg": "#0e1117"
}
  );
  </script>
</div>
<!-- TradingView Widget END -->
"""

components.html(tradingview_html, height=TINGGI_GRAFIK)
