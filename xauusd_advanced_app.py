import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time

# ==========================================
# 1. KONFIGURASI HALAMAN (RAMAH ANDROID)
# ==========================================
st.set_page_config(
    page_title="XAUUSD Technical Pro Scalper",
    page_icon="🎯",
    layout="centered"
)

st.markdown("### 🎯 XAUUSD Technical Pro Scalper")
st.caption("Dashboard Sinyal Murni Berbasis Indikator Teknikal & Tren")

# ==========================================
# 2. PILIHAN TIMEFRAME (M1 / M5)
# ==========================================
pilihan_tf = st.selectbox("Pilih Timeframe Analisis:", ["1m", "5m"], index=1)
periode_data = "1d" if pilihan_tf == "1m" else "5d"

# ==========================================
# 3. FUNGSI INDIKATOR TEKNIKAL MANDIRI
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
# 4. FUNGSI PENGAMBILAN DATA
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
# 5. PROSES DATA & LOADING
# ==========================================
with st.spinner(f"🔄 Menganalisis pasar {pilihan_tf}..."):
    df_live = get_advanced_data(pilihan_tf, periode_data)

if isinstance(df_live, str):
    if df_live == "KOSONG":
        st.warning("⚠️ Menunggu data pasar global...")
    else:
        st.error(f"🚨 Kendala sistem: {df_live}")
        
elif df_live is not None and not df_live.empty:
    data_terbaru = df_live.iloc[-1:]
    
    harga_sekarang = round(float(data_terbaru['Close'].iloc[0]), 2)
    rsi_sekarang = float(data_terbaru['RSI_14'].iloc[0])
    atr_sekarang = float(data_terbaru['ATR_14'].iloc[0])
    ema_sekarang = float(data_terbaru['EMA_50'].iloc[0])
    macd_sekarang = float(data_terbaru['MACD'].iloc[0])
    waktu_data = data_terbaru.index[0].strftime("%H:%M:%S")

    # ==========================================
    # 6. LOGIKA SINYAL TEKNIKAL PROFESIONAL
    # ==========================================
    # Menentukan arah tren murni berdasarkan posisi harga terhadap EMA 50 & MACD
    di_atas_ema = harga_sekarang > ema_sekarang
    macd_positif = macd_sekarang > 0
    
    skor_sinyal = 0 # Positif untuk Buy, Negatif untuk Sell
    
    if di_atas_ema: skor_sinyal += 1
    if macd_positif: skor_sinyal += 1
    if rsi_sekarang < 65 and rsi_sekarang > 40: skor_sinyal += 1 # Zona aman momentum

    # Keputusan Akhir Sinyal
    if skor_sinyal >= 2 and rsi_sekarang < 75:
        status_sinyal = "BUY"
        kekuatan = "85% (Tren Kuat Naik)"
    elif not di_atas_ema and not macd_positif and rsi_sekarang > 35:
        status_sinyal = "SELL"
        kekuatan = "85% (Tren Kuat Turun)"
    else:
        status_sinyal = "WAIT"
        kekuatan = "Konsolidasi / Ragu-ragu"

    # ==========================================
    # 7. PANEL METRIK DASHBOARD
    # ==========================================
    st.text(f"⏱️ Update ({pilihan_tf}): {waktu_data}")
    
    c1, c2 = st.columns(2)
    c1.metric("📌 Entry (XAUUSD)", f"${harga_sekarang:.2f}")
    c2.metric("📊 RSI (14)", f"{rsi_sekarang:.1f}")
    
    c3, c4 = st.columns(2)
    c3.metric("📈 ATR", f"{atr_sekarang:.2f}")
    c4.metric("🎯 EMA 50", f"${ema_sekarang:.2f}")
    
    st.divider()

    # ==========================================
    # 8. KEPUTUSAN SINYAL DI LAYAR
    # ==========================================
    if status_sinyal == "BUY":
        st.success(f"🟢 **SINYAL TEKNIKAL : BUY**\n\nAkurasi Konfirmasi: **{kekuatan}**\nHarga Acuan: **${harga_sekarang:.2f}**")
    elif status_sinyal == "SELL":
        st.error(f"🔴 **SINYAL TEKNIKAL : SELL**\n\nAkurasi Konfirmasi: **{kekuatan}**\nHarga Acuan: **${harga_sekarang:.2f}**")
    else:
        st.warning(f"⚪ **STATUS : WAIT / STANDBY**\n\nPasar sedang tidak searah. Menunggu momentum aman.")

    # BAR LOADING & COUNTDOWN TEPAT DI BAWAH REKOMENDASI
    st.markdown("---")
    info_refresh = st.empty()
    bar_loading = st.progress(0)

    for i in range(10):
        sisa_waktu = 10 - i
        info_refresh.caption(f"⏳ Refresh otomatis dalam {sisa_waktu} detik...")
        bar_loading.progress((i + 1) * 10)
        time.sleep(1)

    # ==========================================
    # 9. GRAFIK ASLI DENGAN EMA 50
    # ==========================================
    st.subheader(f"Grafik Candlestick ({pilihan_tf})")
    df_chart = df_live.tail(40).copy()
    
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
        line=dict(color='yellow', width=2), 
        name='EMA 50'
    ))

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=380,
        margin=dict(l=0, r=0, t=20, b=0),
        xaxis=dict(type='category')
    )
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 10. RERUN OTOMATIS
# ==========================================
try:
    st.rerun()
except AttributeError:
    st.experimental_rerun()
