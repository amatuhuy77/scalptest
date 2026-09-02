import streamlit as st
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
import streamlit.components.v1 as components
from datetime import datetime
import pytz
import requests
import time  # <-- Modul baru untuk mereset loading bar

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
# MESIN PENGAMBIL DATA TANGGUH 
# (Cache diturunkan ke 30s agar selalu dapat data baru tiap refresh 60s)
# =========================================================================
@st.cache_data(ttl=30)
def hitung_ai_multi(interval):
    df = pd.DataFrame()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    
    # --- JALUR 1: DIRECT YAHOO API ---
    try:
        tf_yahoo = "1m" if interval == "M1" else "5m"
        url_yahoo = f"https://query1.finance.yahoo.com/v8/finance/chart/XAUUSD=X?range=5d&interval={tf_yahoo}"
        res_y = requests.get(url_yahoo, headers=headers, timeout=5).json()
        
        if 'chart' in res_y and res_y['chart']['result']:
            quote = res_y['chart']['result'][0]['indicators']['quote'][0]
            df = pd.DataFrame({
                'Open': quote['open'],
                'High': quote['high'],
                'Low': quote['low'],
                'Close': quote['close']
            })
            df.dropna(inplace=True)
    except Exception:
        pass 

    # --- JALUR 2: KRAKEN API ---
    if df.empty or len(df) < 15:
        try:
            tf_kraken = 1 if interval == "M1" else 5
            url_kraken = f"https://api.kraken.com/0/public/OHLC?pair=PAXGUSD&interval={tf_kraken}"
            res_k = requests.get(url_kraken, headers=headers, timeout=5).json()
            
            if not res_k['error']:
                pair_key = list(res_k['result'].keys())[0] 
                data_k = res_k['result'][pair_key]
                df = pd.DataFrame(data_k, columns=['time','Open','High','Low','Close','vwap','vol','count'])
                df['Open'] = df['Open'].astype(float)
                df['High'] = df['High'].astype(float)
                df['Low'] = df['Low'].astype(float)
                df['Close'] = df['Close'].astype(float)
                df.dropna(inplace=True)
            else:
                raise ValueError("Kraken menolak request.")
        except Exception as e:
            raise ValueError(f"Server diblokir total. Gagal terhubung ke Yahoo maupun Kraken. Error: {e}")

    if df.empty or len(df) < 15:
        raise ValueError(f"Berhasil terhubung, tapi data {interval} belum cukup terbentuk. Tunggu 1 menit.")
    
    # --- PROSES MACHINE LEARNING ---
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
        raise ValueError("Data indikator belum siap. Refresh web.")
    
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

# 4. Panel AI Live dengan Loading Bar Paksa Refresh
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
        
        # Kotak Sinyal
        if p_naik >= 58.0:
            st.success(f"🟢 **BUY SCALP ({tf})** | Prob: **{p_naik:.1f}%** | Entry: **${c_price:.2f}**\n\n📈 **TP:** ${batas_naik:.2f} *(+${jarak_tp:.2f})* \n\n🛡️ **SL:** ${c_price - jarak_sl:.2f} *(-${jarak_sl:.2f})*")
        elif p_turun >= 58.0:
            st.error(f"🔴 **SELL SCALP ({tf})** | Prob: **{p_turun:.1f}%** | Entry: **${c_price:.2f}**\n\n📉 **TP:** ${batas_turun:.2f} *(-${jarak_tp:.2f})* \n\n🛡️ **SL:** ${c_price + jarak_sl:.2f} *(+${jarak_sl:.2f})*")
        else:
            st.warning(f"⚪ **WAIT ({tf})** | Naik {p_naik:.1f}% vs Turun {p_turun:.1f}%.\n\nPasar konsolidasi di {tf}. Tunggu arah dominan.")
            
        # =========================================================
        # ANIMASI LOADING BAR ANTI-MACET (DENGAN TIMESTAMP UNIK)
        # =========================================================
        waktu_sekarang = datetime.now(pytz.timezone('Asia/Makassar')).strftime("%H:%M:%S")
        unik_id = int(time.time()) # Membuat ID unik setiap 60 detik agar CSS di-reset paksa
        
        st.markdown(f"""
            <div style="margin-top: 10px; font-size: 0.85rem; color: #a1a1a1; display: flex; justify-content: space-between;">
                <span>🔄 Terakhir update: <b>{waktu_sekarang} WITA</b></span>
                <span>⏳ Memuat candle baru...</span>
            </div>
            <div style="width: 100%; background-color: #2b2b2b; border-radius: 4px; margin-top: 5px; overflow: hidden;">
                <div style="height: 5px; background-color: #00d26a; animation: load60s_{unik_id} 60s linear forwards;"></div>
            </div>
            <style>
                @keyframes load60s_{unik_id} {{
                    0% {{ width: 0%; }}
                    100% {{ width: 100%; }}
                }}
            </style>
        """, unsafe_allow_html=True)
            
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
