import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
import streamlit.components.v1 as components
from datetime import datetime
import pytz

# Konfigurasi Halaman Khusus Mobile & Desktop
st.set_page_config(page_title="XAU/USD M1 Scalper Pro", layout="wide", initial_sidebar_state="collapsed")

# Suntikan CSS agar tampilan lebar penuh dan pas di Android
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

# 1. Panel Sesi Pasar WITA (Kalimantan)
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

# 2. Mesin AI Khusus M1 (Sangat Sensitif & Cepat)
@st.cache_data(ttl=2) # Cache dipercepat 2 detik
def hitung_ai_m1():
    # Menarik data M1 (1 hari terakhir saja agar data paling fresh dan responsif)
    gold = yf.download("XAUUSD=X", period="1d", interval="1m", progress=False)
    
    if gold.empty:
        gold = yf.download("GC=F", period="1d", interval="1m", progress=False)
    if gold.empty:
        raise ValueError("Data M1 sedang sinkronisasi.")

    df = pd.DataFrame(index=gold.index)
    df['Close'] = gold['Close']
    df['Open'] = gold['Open']
    df['High'] = gold['High']
    df['Low'] = gold['Low']
    df.dropna(inplace=True)
    
    # Feature Engineering khusus M1 (Sensitif terhadap perubahan cepat)
    df['Return'] = df['Close'].pct_change()
    df['Body'] = df['Close'] - df['Open']
    
    # Periode diperpendek (SMA 10) untuk scalping cepat
    df['SMA_10'] = df['Close'].rolling(window=10).mean()
    df['Std_Dev'] = df['Close'].rolling(window=10).std()
    df['BB_Width'] = (df['SMA_10'] + (df['Std_Dev'] * 2)) - (df['SMA_10'] - (df['Std_Dev'] * 2))
    
    df['TR'] = np.maximum(df['High'] - df['Low'], 
                          np.maximum(abs(df['High'] - df['Close'].shift(1)), 
                                     abs(df['Low'] - df['Close'].shift(1))))
    df['ATR'] = df['TR'].rolling(window=10).mean()
    
    # Target 1 candle ke depan
    df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
    df.dropna(inplace=True)
    
    if len(df) < 15: raise ValueError("Menunggu data M1 terkumpul.")
    
    features = ['Return', 'Body', 'BB_Width', 'ATR']
    # Model XGBoost disetel dengan kedalaman lebih dangkal agar bereaksi instan
    model = XGBClassifier(n_estimators=50, learning_rate=0.15, max_depth=3, random_state=42)
    model.fit(df[features][:-1], df['Target'][:-1])
    
    latest_data = df[features].tail(1)
    proba = model.predict_proba(latest_data)[0]
    
    return df['Close'].iloc[-1], df['ATR'].iloc[-1], proba[1]*100, proba[0]*100

# 3. Panel AI Live M1 (Auto-Update setiap 5 Detik)
st.subheader("🤖 Sinyal Scalping M1 (Auto-Update 5 Detik)")

@st.fragment(run_every="5s")
def ai_scalper_dashboard():
    try:
        c_price, c_atr, p_naik, p_turun = hitung_ai_m1()
        
        # Untuk scalping M1, jarak TP/SL dibuat lebih padat (1:1 atau 1:1.2 dari ATR)
        jarak_tp = c_atr * 1.2
        jarak_sl = c_atr * 0.9
        
        batas_naik = c_price + jarak_tp
        batas_turun = c_price - jarak_tp
        
        # Ambang batas diturunkan sedikit ke 58% agar scalper tidak ketinggalan momentum
        if p_naik >= 58.0:
            st.success(f"🟢 **BUY SCALP** | Prob: **{p_naik:.1f}%** | Entry: **${c_price:.2f}**\n\n📈 **TP Cepat:** ${batas_naik:.2f} *(+${jarak_tp:.2f})* \n\n🛡️ **SL Ketat:** ${c_price - jarak_sl:.2f} *(-${jarak_sl:.2f})*")
        elif p_turun >= 58.0:
            st.error(f"🔴 **SELL SCALP** | Prob: **{p_turun:.1f}%** | Entry: **${c_price:.2f}**\n\n📉 **TP Cepat:** ${batas_turun:.2f} *(-${jarak_tp:.2f})* \n\n🛡️ **SL Ketat:** ${c_price + jarak_sl:.2f} *(+${jarak_sl:.2f})*")
        else:
            st.warning(f"⚪ **HOLD / WAIT** | Naik {p_naik:.1f}% vs Turun {p_turun:.1f}%.\n\nPasar M1 sedang konsolidasi ketat. Tunggu arah pecah.")
            
    except Exception as e:
        st.warning(f"Menyiapkan data M1 kilat... (Refresh dalam 5s)")

ai_scalper_dashboard()

st.markdown("---")

# 4. Grafik True Live M1 (OANDA)
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

# Grafik dikunci 580px agar sangat pas di layar HP saat mode M1
components.html(tradingview_html, height=580)