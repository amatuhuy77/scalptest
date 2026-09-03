import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import joblib
import os

# ==========================================
# 1. KONFIGURASI HALAMAN WEB
# ==========================================
st.set_page_config(
    page_title="XAUUSD AI Scalper - Atma Fathul Hadi",
    page_icon="📈",
    layout="wide"
)

st.title("📈 XAUUSD Advanced AI Scalper (Independent Version)")
st.markdown("Sistem Analisis Real-Time berbasis XGBoost & Indikator Teknikal Internal")

# ==========================================
# 2. FUNGSI INDIKATOR MANDIRI (ANTI-ERROR)
# ==========================================
def hitung_indikator_mandiri(df):
    # Hitung RSI 14
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI_14'] = 100 - (100 / (1 + rs))

    # Hitung EMA 50
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()

    # Hitung MACD
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26

    # Hitung ATR 14
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR_14'] = tr.rolling(window=14).mean()

    return df

# ==========================================
# 3. FUNGSI PENGAMBILAN DATA
# ==========================================
@st.cache_data(ttl=60)
def get_advanced_data():
    try:
        df = yf.download(tickers="XAUUSD=X", period="5d", interval="5m", progress=False)
        
        if df.empty:
            return None
            
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
            
        # Panggil fungsi indikator manual
        df = hitung_indikator_mandiri(df)
        df.dropna(inplace=True)
        
        return df
    except Exception as e:
        st.error(f"Gagal mengambil data dari server: {e}")
        return None

# ==========================================
# 4. PROSES DATA REAL-TIME
# ==========================================
df_live = get_advanced_data()

if df_live is not None and not df_live.empty:
    data_terbaru = df_live.iloc[-1:]
    
    harga_sekarang = float(data_terbaru['Close'].iloc[0])
    rsi_sekarang = float(data_terbaru['RSI_14'].iloc[0])
    atr_sekarang = float(data_terbaru['ATR_14'].iloc[0])
    ema_sekarang = float(data_terbaru['EMA_50'].iloc[0])

    # ==========================================
    # 5. INTEGRASI MODEL XGBOOST
    # ==========================================
    nama_file_model = "model_xgboost_terbaik.pkl"
    prob_naik, prob_turun = 0.0, 0.0
    
    if os.path.exists(nama_file_model):
        try:
            model = joblib.load(nama_file_model)
            fitur_x = data_terbaru[['RSI_14', 'ATR_14', 'EMA_50', 'MACD', 'Close']]
            probabilitas = model.predict_proba(fitur_x)[0]
            prob_turun = probabilitas[0]
            prob_naik = probabilitas[1]
            st.toast("✅ Model XGBoost berhasil dimuat!", icon="🧠")
        except Exception as e:
            st.error(f"Terjadi kesalahan saat membaca model: {e}")
    else:
        st.warning(f"⚠️ File '{nama_file_model}' tidak ditemukan. Menampilkan mode simulasi.")
        prob_naik = 0.896 if rsi_sekarang < 40 else 0.400
        prob_turun = 1 - prob_naik

    # ==========================================
    # 6. ANTARMUKA WEB (DASHBOARD)
    # ==========================================
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📌 Entry Sekarang", f"${harga_sekarang:.2f}")
    col2.metric("📊 RSI (Momentum)", f"{rsi_sekarang:.1f}")
    col3.metric("📈 ATR (Volatilitas)", f"{atr_sekarang:.2f}")
    col4.metric("🎯 EMA 50 (Tren)", f"${ema_sekarang:.2f}")
    
    st.divider()

    if prob_naik >= 0.60:
        st.success(f"### 🟢 REKOMENDASI AI : BUY!\n**Akurasi Prediksi: {prob_naik*100:.1f}%** | Bersiap untuk scalping naik dari harga **${harga_sekarang:.2f}**")
    elif prob_turun >= 0.60:
        st.error(f"### 🔴 REKOMENDASI AI : SELL!\n**Akurasi Prediksi: {prob_turun*100:.1f}%** | Bersiap untuk scalping turun dari harga **${harga_sekarang:.2f}**")
    else:
        st.info(f"### ⚪ AI STANDBY\nTidak ada sinyal kuat. Prediksi Naik: {prob_naik*100:.1f}% vs Turun: {prob_turun*100:.1f}%.")

    # ==========================================
    # 7. GRAFIK CANDLESTICK INTERAKTIF
    # ==========================================
    st.subheader("Visualisasi Market (5 Menit Terakhir)")
    df_chart = df_live.tail(50).copy()
    
    fig = go.Figure(data=[go.Candlestick(
        x=df_chart.index,
        open=df_chart['Open'],
        high=df_chart['High'],
        low=df_chart['Low'],
        close=df_chart['Close'],
        name="XAUUSD"
    )])
    
    fig.add_trace(go.Scatter(
        x=df_chart.index, 
        y=df_chart['EMA_50'], 
        line=dict(color='blue', width=1.5), 
        name='EMA 50'
    ))

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=500,
        margin=dict(l=0, r=0, t=30, b=0)
    )
    st.plotly_chart(fig, use_container_width=True)

else:
    st.spinner("Mengunduh data pasar real-time...")
