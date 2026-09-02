import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
import streamlit.components.v1 as components
from datetime import datetime
import pytz
import requests

# Konfigurasi Halaman Khusus Mobile
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

# =========================================================================
# FUNGSI AI DENGAN JALUR BELAKANG (BINANCE PAXG - KEMBARAN EMAS ANTI BLOKIR)
# =========================================================================
@st.cache_data(ttl=60)
def hitung_ai_multi(interval):
    tf_map = {"M1": "1m", "M5": "5m"}
    df = pd.DataFrame()
    
    # 1. Coba jalur normal Yahoo Finance
    try:
        gold = yf.download("XAUUSD=X", period="1d", interval=tf_map[interval], progress=False)
        if not gold.empty and len(gold) > 15:
            df = pd.DataFrame(index=gold.index)
            df['Close'] = gold['Close']
            df['Open'] = gold['Open']
            df['High'] = gold['High']
            df['Low'] = gold['Low']
    except:
        pass
        
    # 2. Jika Yahoo ngambek/blokir, AI otomatis pindah ke jalur belakang (Binance API)
    if df.empty or len(df) < 15:
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol=PAXGUSDT&interval={tf_map[interval]}&limit=500"
            res = requests.get(url).json()
            if isinstance(res, list) and len(res) > 0:
                df = pd.DataFrame(res, columns=['time','Open','High','Low','Close','vol','ct','qav','nt','tbbav','tbqav','ignore'])
                df['Open'] = df['Open'].astype(float)
                df['High'] = df['High'].astype(float)
                df['Low'] = df['Low'].astype(float)
                df['Close'] = df['Close'].astype(float)
            else:
                raise ValueError("Gagal mengambil data kembaran emas.")
        except Exception as e:
            raise ValueError(f"Semua jalur data terputus. Mohon refresh web. Error: {e}")

    df.dropna(inplace=True)
    
    # Kalkulasi Indikator
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
        raise ValueError(f"Data belum terkumpul sempurna.")
    
    # Proses Machine Learning
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

st.markdown(f"**AI Aktif:** Timeframe **{st.session_state.tf_aktif}** (Auto-Update tiap pergantian candle)")

@st.fragment(run_every="60s")
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

TINGGI_GRAFIK = 500  

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
