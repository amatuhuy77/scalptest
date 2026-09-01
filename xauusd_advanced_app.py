import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
import streamlit.components.v1 as components
from datetime import datetime
import pytz

st.set_page_config(page_title="XAU/USD M1 Scalper Pro", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .block-container {
        padding-top: 0.8rem !important;
        padding-bottom: 0.8rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 100% !important;
    }
    @media (max-width: 768px) {
        h1 { font-size: 1.5rem !important; }
        h3 { font-size: 1.1rem !important; }
    }
    </style>
""", unsafe_allow_html=True)

st.title("XAU/USD - M1 SCALPER AI (Valetax Cent) ⚡")

def get_market_session_wita():
    wita = pytz.timezone('Asia/Makassar')
    now_wita = datetime.now(wita)
    jam = now_wita.hour
    waktu_str = f"{jam:02d}:{now_wita.minute:02d} WITA"
    
    if 6 <= jam < 14: return waktu_str, "Sesi Asia 🌏", "Scalping Hati-hati (Range Sempit)"
    elif 14 <= jam < 20: return waktu_str, "Sesi London 🌍", "Momentum Bagus untuk Breakout"
    else: return waktu_str, "Sesi New York 🌎", "Sangat Liar (Wajib Cepat Eksekusi)"

waktu, sesi, karakter = get_market_session_wita()
st.info(f"🕒 **{waktu}** | **{sesi}**\n\n💡 {karakter}")

# Fungsi AI dengan penanganan error transparan & aman untuk Cloud
@st.cache_data(ttl=5)
def hitung_ai_m1():
    # Menggunakan period '5d' agar aman dari pembatasan 7 hari Yahoo Finance untuk data 1m
    gold = yf.download("XAUUSD=X", period="5d", interval="1m", progress=False)
    
    if gold.empty:
        gold = yf.download("GC=F", period="5d", interval="1m", progress=False)
    if gold.empty:
        raise ValueError("Yahoo Finance membatasi data M1 dari Cloud. Silakan tunggu 1 menit.")

    df = pd.DataFrame(index=gold.index)
    df['Close'] = gold['Close']
    df['Open'] = gold['Open']
    df['High'] = gold['High']
    df['Low'] = gold['Low']
    df.dropna(inplace=True)
    
    df['Return'] = df['Close'].pct_change()
    df['Body'] = df['Close'] - df['Open']
    
    df['SMA_10'] = df['Close'].rolling(window=10).mean()
    df['Std_Dev'] = df['Close'].rolling(window=10).std()
    df['BB_Width'] = (df['SMA_10'] + (df['Std_Dev'] * 2)) - (df['SMA_10'] - (df['Std_Dev'] * 2))
    
    df['TR'] = np.maximum(df['High'] - df['Low'], 
                          np.maximum(abs(df['High'] - df['Close'].shift(1)), 
                                     abs(df['Low'] - df['Close'].shift(1))))
    df['ATR'] = df['TR'].rolling(window=10).mean()
    
    df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
    df.dropna(inplace=True)
    
    if len(df) < 15: 
        raise ValueError(f"Data M1 terkumpul hanya {len(df)} baris. Belum cukup untuk AI.")
    
    features = ['Return', 'Body', 'BB_Width', 'ATR']
    model = XGBClassifier(n_estimators=50, learning_rate=0.15, max_depth=3, random_state=42)
    model.fit(df[features][:-1], df['Target'][:-1])
    
    latest_data = df[features].tail(1)
    proba = model.predict_proba(latest_data)[0]
    
    return df['Close'].iloc[-1], df['ATR'].iloc[-1], proba[1]*100, proba[0]*100

st.subheader("🤖 Sinyal Scalping M1 (Auto-Update 5 Detik)")

@st.fragment(run_every="5s")
def ai_scalper_dashboard():
    try:
        c_price, c_atr, p_naik, p_turun = hitung_ai_m1()
        
        jarak_tp = c_atr * 1.2
        jarak_sl = c_atr * 0.9
        
        batas_naik = c_price + jarak_tp
        batas_turun = c_price - jarak_tp
        
        if p_naik >= 58.0:
            st.success(f"🟢 **BUY SCALP** | Prob: **{p_naik:.1f}%** | Entry: **${c_price:.2f}**\n\n📈 **TP Cepat:** ${batas_naik:.2f} *(+${jarak_tp:.2f})* \n\n🛡️ **SL Ketat:** ${c_price - jarak_sl:.2f} *(-${jarak_sl:.2f})*")
        elif p_turun >= 58.0:
            st.error(f"🔴 **SELL SCALP** | Prob: **{p_turun:.1f}%** | Entry: **${c_price:.2f}**\n\n📉 **TP Cepat:** ${batas_turun:.2f} *(-${jarak_tp:.2f})* \n\n🛡️ **SL Ketat:** ${c_price + jarak_sl:.2f} *(+${jarak_sl:.2f})*")
        else:
            st.warning(f"⚪ **HOLD / WAIT** | Naik {p_naik:.1f}% vs Turun {p_turun:.1f}%.\n\nPasar M1 sedang konsolidasi ketat. Tunggu arah pecah.")
            
    except Exception as e:
        # Menampilkan pesan error asli agar kita tahu jika ada kendala jaringan API
        st.error(f"Gagal memproses AI M1: {e}")

ai_scalper_dashboard()

st.markdown("---")

st.subheader("📊 Grafik M1 Live (Fokus Scalping)")

tradingview_html = """
<!-- TradingView Widget BEGIN -->
<div class="tradingview-widget-container" style="height:100%;width:100%">
  <div id="tradingview_xauusd" style="height:100%;width:100%"></div>
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
  "backgroundColor": "rgba(0, 0, 0, 1)",
  "gridColor": "rgba(66, 66, 66, 1)",
  "hide_top_toolbar": false,
  "hide_legend": false,
  "save_image": false,
  "container_id": "tradingview_xauusd",
  "toolbar_bg": "#f1f3f6"
}
  );
  </script>
</div>
<!-- TradingView Widget END -->
"""

components.html(tradingview_html, height=580)
