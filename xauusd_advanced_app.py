import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
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

st.title("📈 XAUUSD Advanced AI Scalper")
st.markdown("Sistem Analisis Real-Time berbasis XGBoost & Indikator Teknikal")

# ==========================================
# 2. FUNGSI PENGAMBILAN & PENGOLAHAN DATA
# ==========================================
@st.cache_data(ttl=60) # Data otomatis refresh setiap 60 detik
def get_advanced_data():
    try:
        # Menarik data Emas M5 (Timeframe 5 Menit) dari server global
        df = yf.download(tickers="XAUUSD=X", period="5d", interval="5m", progress=False)
        
        if df.empty:
            return None
            
        # Perbaiki format kolom jika menggunakan yfinance versi terbaru
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
            
        # FEATURE ENGINEERING (Mempertajam Panca Indera AI)
        df['RSI_14'] = df.ta.rsi(length=14)
        df['ATR_14'] = df.ta.atr(length=14)
        df['EMA_50'] = df.ta.ema(length=50)
        
        # MACD menghasilkan 3 kolom, kita ambil garis utamanya saja
        macd = df.ta.macd(fast=12, slow=26, signal=9)
        df['MACD'] = macd['MACD_12_26_9']
        
        # Bersihkan data awal yang kosong akibat perhitungan indikator
        df.dropna(inplace=True)
        return df
    except Exception as e:
        st.error(f"Gagal mengambil data dari server: {e}")
        return None

# ==========================================
# 3. PROSES DATA REAL-TIME
# ==========================================
df_live = get_advanced_data()

if df_live is not None and not df_live.empty:
    # Ambil baris paling akhir (Harga detik ini)
    data_terbaru = df_live.iloc[-1:]
    
    harga_sekarang = float(data_terbaru['Close'].iloc[0])
    rsi_sekarang = float(data_terbaru['RSI_14'].iloc[0])
    atr_sekarang = float(data_terbaru['ATR_14'].iloc[0])
    ema_sekarang = float(data_terbaru['EMA_50'].iloc[0])

    # ==========================================
    # 4. INTEGRASI MODEL XGBOOST
    # ==========================================
    nama_file_model = "model_xgboost_terbaik.pkl" # Pastikan nama file ini ada di GitHub Anda
    prob_naik, prob_turun = 0.0, 0.0
    
    if os.path.exists(nama_file_model):
        try:
            model = joblib.load(nama_file_model)
            # Pastikan urutan fitur sama persis dengan saat model dilatih!
            fitur_x = data_terbaru[['RSI_14', 'ATR_14', 'EMA_50', 'MACD', 'Close']]
            probabilitas = model.predict_proba(fitur_x)[0]
            prob_turun = probabilitas[0]
            prob_naik = probabilitas[1]
            st.toast("✅ Model XGBoost berhasil dimuat!", icon="🧠")
        except Exception as e:
            st.error(f"Terjadi kesalahan saat membaca model: {e}")
    else:
        st.warning(f"⚠️ File '{nama_file_model}' tidak ditemukan di repositori. Menampilkan mode simulasi.")
        # Mode simulasi (Hapus jika model sudah diunggah)
        prob_naik = 0.896 if rsi_sekarang < 40 else 0.400
        prob_turun = 1 - prob_naik

    # ==========================================
    # 5. ANTARMUKA WEB (DASHBOARD)
    # ==========================================
    # Baris Metrik Utama
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📌 Entry Sekarang", f"${harga_sekarang:.2f}")
    col2.metric("📊 RSI (Momentum)", f"{rsi_sekarang:.1f}")
    col3.metric("📈 ATR (Volatilitas)", f"{atr_sekarang:.2f}")
    col4.metric("🎯 EMA 50 (Tren)", f"${ema_sekarang:.2f}")
    
    st.divider()

    # Panel Keputusan AI
    if prob_naik >= 0.60:
        st.success(f"### 🟢 REKOMENDASI AI : BUY!\n**Akurasi Prediksi: {prob_naik*100:.1f}%** | Bersiap untuk scalping naik dari harga **${harga_sekarang:.2f}**")
    elif prob_turun >= 0.60:
        st.error(f"### 🔴 REKOMENDASI AI : SELL!\n**Akurasi Prediksi: {prob_turun*100:.1f}%** | Bersiap untuk scalping turun dari harga **${harga_sekarang:.2f}**")
    else:
        st.info(f"### ⚪ AI STANDBY\nTidak ada sinyal kuat. Prediksi Naik: {prob_naik*100:.1f}% vs Turun: {prob_turun*100:.1f}%.")

    # ==========================================
    # 6. GRAFIK CANDLESTICK INTERAKTIF (PLOTLY)
    # ==========================================
    st.subheader("Visualisasi Market (5 Menit Terakhir)")
    
    # Menampilkan 50 candle terakhir agar grafik bersih
    df_chart = df_live.tail(50).copy()
    
    fig = go.Figure(data=[go.Candlestick(
        x=df_chart.index,
        open=df_chart['Open'],
        high=df_chart['High'],
        low=df_chart['Low'],
        close=df_chart['Close'],
        name="XAUUSD"
    )])
    
    # Menambahkan garis EMA 50 ke dalam grafik
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
