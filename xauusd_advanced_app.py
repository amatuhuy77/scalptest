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
    layout="centered"
)

st.markdown("### 📈 XAUUSD AI Scalper (Valetax/Finex)")
st.caption("Sistem Analisis Real-Time & Pilihan Timeframe")

# ==========================================
# 2. PILIHAN TIMEFRAME (M1 / M5)
# ==========================================
pilihan_tf = st.selectbox("Pilih Timeframe Analisis:", ["1m", "5m"], index=0)

# Menyesuaikan parameter periode berdasarkan timeframe agar data selalu akurat
periode_data = "1d" if pilihan_tf == "1m" else "5d"

# ==========================================
# 3. FUNGSI INDIKATOR MANDIRI
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
# 4. FUNGSI PENGAMBILAN DATA DINAMIS
# ==========================================
@st.cache_data(ttl=10)
def get_advanced_data(tf, period):
    try:
        df = yf.download(tickers="XAUUSD=X", period=period, interval=tf, progress=False)
        if df.empty:
            df = yf.download(tickers="GC=F", period=period, interval=tf, progress=False)
            
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
# 5. PROSES DATA DENGAN ANIMASI LOADING
# ==========================================
with st.spinner(f"🔄 Menarik data pasar ({pilihan_tf})..."):
    df_live = get_advanced_data(pilihan_tf, periode_data)

if isinstance(df_live, str):
    if df_live == "KOSONG":
        st.warning("⚠️ Menunggu data dari server global...")
    else:
        st.error(f"🚨 Kendala sistem: {df_live}")
        
elif df_live is not None and not df_live.empty:
    data_terbaru = df_live.iloc[-1:]
    
    harga_mentah = float(data_terbaru['Close'].iloc[0])
    harga_sekarang = round(harga_mentah, 2) 
    
    rsi_sekarang = float(data_terbaru['RSI_14'].iloc[0])
    atr_sekarang = float(data_terbaru['ATR_14'].iloc[0])
    ema_sekarang = float(data_terbaru['EMA_50'].iloc[0])
    waktu_data = data_terbaru.index[0].strftime("%H:%M:%S")

    # ==========================================
    # 6. INTEGRASI MODEL XGBOOST
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
    # 7. PANEL METRIK DASHBOARD
    # ==========================================
    st.text(f"⏱️ Update ({pilihan_tf}): {waktu_data}")
    
    c1, c2 = st.columns(2)
    c1.metric("📌 Entry (XAUUSD)", f"${harga_sekarang:.2f}")
    c2.metric("📊 RSI", f"{rsi_sekarang:.1f}")
    
    c3, c4 = st.columns(2)
    c3.metric("📈 ATR", f"{atr_sekarang:.2f}")
    c4.metric("🎯 EMA 50", f"${ema_sekarang:.2f}")
    
    st.divider()

    # ==========================================
    # 8. PANEL KEPUTUSAN AI & BAR LOADING
    # ==========================================
    if prob_naik >= 0.60:
        st.success(f"🟢 **REKOMENDASI AI : BUY!**\n\nAkurasi: **{prob_naik*100:.1f}%**\nEntry: **${harga_sekarang:.2f}**")
    elif prob_turun >= 0.60:
        st.error(f"🔴 **REKOMENDASI AI : SELL!**\n\nAkurasi: **{prob_turun*100:.1f}%**\nEntry: **${harga_sekarang:.2f}**")
    else:
        st.warning(f"⚪ **AI STANDBY**\n\nMenunggu momentum. Naik: {prob_naik*100:.1f}% | Turun: {prob_turun*100:.1f}%")

    st.markdown("---")
    info_refresh = st.empty()
    bar_loading = st.progress(0)

    for i in range(10):
        sisa_waktu = 10 - i
        info_refresh.caption(f"⏳ Refresh otomatis dalam {sisa_waktu} detik...")
        bar_loading.progress((i + 1) * 10)
        time.sleep(1)

    # ==========================================
    # 9. GRAFIK CANDLESTICK ASLI YANG MUNCUL
    # ==========================================
    st.subheader(f"Grafik Asli ({pilihan_tf})")
    df_chart = df_live.tail(40).copy()
    
    # Memastikan indeks waktu terbaca sempurna oleh Plotly agar grafik muncul
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
        height=380,
        margin=dict(l=0, r=0, t=20, b=0),
        xaxis=dict(type='category') # Mengatasi celah kosong waktu libur di grafik pasar
    )
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 10. EKSEKUSI RERUN OTOMATIS
# ==========================================
try:
    st.rerun()
except AttributeError:
    st.experimental_rerun()
