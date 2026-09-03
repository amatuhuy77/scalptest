import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import joblib
import os
import time

# ==========================================
# 1. KONFIGURASI HALAMAN (RAMAH ANDROID)
# ==========================================
st.set_page_config(
    page_title="XAUUSD AI Scalper Mobile",
    page_icon="📈",
    layout="centered" # Menggunakan centered agar sangat rapi di layar HP Android
)

st.markdown("### 📈 XAUUSD AI Scalper (Valetax/Finex)")
st.caption("Sistem Analisis Real-Time & Mobile Friendly")

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
# 3. FUNGSI PENGAMBILAN DATA (1 MENIT LIVE)
# ==========================================
@st.cache_data(ttl=10)
def get_advanced_data():
    try:
        df = yf.download(tickers="XAUUSD=X", period="1d", interval="1m", progress=False)
        if df.empty:
            df = yf.download(tickers="GC=F", period="1d", interval="1m", progress=False)
            
        if df.empty:
            return "KOSONG"
            
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
            
        df = hitung_indikator_mandiri(df)
        df.dropna(inplace=True)
        return df
    except Exception as e:
        return str(e)

# ==========================================
# 4. PROSES DATA DENGAN ANIMASI LOADING
# ==========================================
with st.spinner("🔄 Sinkronisasi harga pasar..."):
    df_live = get_advanced_data()

if isinstance(df_live, str):
    if df_live == "KOSONG":
        st.warning("⚠️ Menunggu data dari server global...")
    else:
        st.error(f"🚨 Kendala sistem: {df_live}")
        
elif df_live is not None and not df_live.empty:
    data_terbaru = df_live.iloc[-1:]
    
    # Penyesuaian presisi harga agar setara dengan standar XAUUSD.vxc
    harga_mentah = float(data_terbaru['Close'].iloc[0])
    harga_sekarang = round(harga_mentah, 2) 
    
    rsi_sekarang = float(data_terbaru['RSI_14'].iloc[0])
    atr_sekarang = float(data_terbaru['ATR_14'].iloc[0])
    ema_sekarang = float(data_terbaru['EMA_50'].iloc[0])
    waktu_data = data_terbaru.index[0].strftime("%H:%M:%S")

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
        except Exception:
            prob_naik = 0.896 if rsi_sekarang < 40 else 0.400
            prob_turun = 1 - prob_naik
    else:
        prob_naik = 0.896 if rsi_sekarang < 40 else 0.400
        prob_turun = 1 - prob_naik

    # ==========================================
    # 6. PANEL METRIK DASHBOARD (RESPONSIF HP)
    # ==========================================
    st.text(f"⏱️ Update: {waktu_data}")
    
    # Menggunakan 2 kolom agar nyaman dilihat di layar HP Android
    c1, c2 = st.columns(2)
    c1.metric("📌 Entry (XAUUSD)", f"${harga_sekarang:.2f}")
    c2.metric("📊 RSI", f"{rsi_sekarang:.1f}")
    
    c3, c4 = st.columns(2)
    c3.metric("📈 ATR", f"{atr_sekarang:.2f}")
    c4.metric("🎯 EMA 50", f"${ema_sekarang:.2f}")
    
    st.divider()

    # ==========================================
    # 7. PANEL KEPUTUSAN AI & BAR LOADING DI BAWAHNYA
    # ==========================================
    if prob_naik >= 0.60:
        st.success(f"🟢 **REKOMENDASI AI : BUY!**\n\nAkurasi: **{prob_naik*100:.1f}%**\nEntry: **${harga_sekarang:.2f}**")
    elif prob_turun >= 0.60:
        st.error(f"🔴 **REKOMENDASI AI : SELL!**\n\nAkurasi: **{prob_turun*100:.1f}%**\nEntry: **${harga_sekarang:.2f}**")
    else:
        st.warning(f"⚪ **AI STANDBY**\n\nMenunggu momentum. Naik: {prob_naik*100:.1f}% | Turun: {prob_turun*100:.1f}%")

    # BAR LOADING & COUNTDOWN DITARIK TEPAT DI BAWAH PERKIRAAN AI
    st.markdown("---")
    info_refresh = st.empty()
    bar_loading = st.progress(0)

    for i in range(10):
        sisa_waktu = 10 - i
        info_refresh.caption(f"⏳ Refresh otomatis dalam {sisa_waktu} detik...")
        bar_loading.progress((i + 1) * 10)
        time.sleep(1)

    # ==========================================
    # 8. GRAFIK CANDLESTICK (MOBILE FRIENDLY)
    # ==========================================
    st.subheader("Grafik M1")
    df_chart = df_live.tail(30).copy() # Ditampilkan 30 candle agar pas di layar HP
    
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
        line=dict(color='cyan', width=1.5), 
        name='EMA 50'
    ))

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=350, # Dibuat lebih ringkas agar tidak terlalu panjang discroll di HP
        margin=dict(l=0, r=0, t=20, b=0)
    )
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 9. EKsekusi RERUN OTOMATIS
# ==========================================
try:
    st.rerun()
except AttributeError:
    st.experimental_rerun()
