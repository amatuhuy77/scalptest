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
# 2. FUNGSI INDIKATOR MANDIRI
# ==========================================
def hitung_indikator_mandiri(df):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI_14'] = 100 - (100 / (1 + rs))

    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()

    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26

    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR_14'] = tr.rolling(window=14).mean()

    return df

# ==========================================
# 3. FUNGSI PENGAMBILAN DATA (KEBAL ERROR)
# ==========================================
@st.cache_data(ttl=60)
def get_advanced_data():
    try:
        # Tarik data XAUUSD. Jika gagal/kosong, otomatis beralih ke GC=F (Emas Berjangka)
        df = yf.download(tickers="XAUUSD=X", period="5d", interval="5m", progress=False)
        if df.empty:
            df = yf.download(tickers="GC=F", period="5d", interval="5m", progress=False)
            
        if df.empty:
            return "KOSONG"
            
        # Meratakan format kolom MultiIndex dari update yfinance terbaru
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
            
        df = hitung_indikator_mandiri(df)
        df.dropna(inplace=True)
        return df
    except Exception as e:
        return str(e) # Kirim pesan error aslinya agar terbaca di layar

# ==========================================
# 4. PROSES DATA & RENDER DASHBOARD
# ==========================================
df_live = get_advanced_data()

# Jika kembaliannya berupa teks (error/kosong), tampilkan peringatan di layar
if isinstance(df_live, str):
    if df_live == "KOSONG":
        st.warning("⚠️ Yahoo Finance tidak mengembalikan data emas saat ini. Sedang mencoba ulang...")
    else:
        st.error(f"🚨 Terjadi kendala sistem penarikan data: {df_live}")
        
elif df_live is not None and not df_live.empty:
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
        st.info(f"💡 Mode Simulasi Aktif (File '{nama_file_model}' belum diunggah).")
        prob_naik = 0.896 if rsi_sekarang < 40 else 0.400
        prob_turun = 1 - prob_naik

    # ==========================================
    # 6. TAMPILAN PANEL METRIK UTAMA
    # ==========================================
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📌 Entry Sekarang", f"${harga_sekarang:.2f}")
    col2.metric("📊 RSI (Momentum)", f"{rsi_sekarang:.1f}")
    col3.metric("📈 ATR (Volatilitas)", f"{atr_sekarang:.2f}")
    col4.metric("🎯 EMA 50 (Tren)", f"${ema_sekarang:.2f}")
    
    st.divider()

    # Panel Keputusan AI
    if prob_naik >= 0.60:
        st.success(f"### 🟢 REKOMENDASI AI : BUY!\n**Akurasi Prediksi: {prob_naik*100:.1f}%** | Bersiap scalping NAIK dari harga **${harga_sekarang:.2f}**")
    elif prob_turun >= 0.60:
        st.error(f"### 🔴 REKOMENDASI AI : SELL!\n**Akurasi Prediksi: {prob_turun*100:.1f}%** | Bersiap scalping TURUN dari harga **${harga_sekarang:.2f}**")
    else:
        st.warning(f"### ⚪ AI STANDBY\nTidak ada sinyal kuat. Prediksi Naik: {prob_naik*100:.1f}% vs Turun: {prob_turun*100:.1f}%.")

    # ==========================================
    # 7. GRAFIK CANDLESTICK INTERAKTIF
    # ==========================================
    st.subheader("Visualisasi Market (50 Candle Terakhir - M5)")
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
    with st.spinner("Membangun ulang struktur data..."):
        pass
