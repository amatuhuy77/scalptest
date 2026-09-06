import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time

# ==========================================
# 1. KONFIGURASI HALAMAN 
# ==========================================
st.set_page_config(
    page_title="XAUUSD Dynamic Scalper",
    page_icon="⚡",
    layout="centered"
)

st.markdown("### ⚡ XAUUSD Dynamic Scalper")
st.caption("Mode Analisis Murni (Aman dari Blokir Server)")

# ==========================================
# 2. PILIHAN TIMEFRAME (PERBAIKAN SENIN PAGI)
# ==========================================
pilihan_tf = st.selectbox("Pilih Timeframe Analisis:", ["1m", "5m"], index=0)

# KUNCI PERBAIKAN: Selalu gunakan 5d (5 hari) agar M1 tidak kosong setelah libur akhir pekan
periode_data = "5d" 

# ==========================================
# 3. FUNGSI INDIKATOR DINAMIS
# ==========================================
def hitung_indikator_dinamis(df):
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
    df['Price_Change'] = df['Close'].diff()

    return df

# ==========================================
# 4. PENGAMBILAN DATA (CACHE AMAN 30 DETIK)
# ==========================================
@st.cache_data(ttl=30) 
def get_dynamic_data(tf, period):
    try:
        df = yf.download(tickers="XAUUSD=X", period=period, interval=tf, progress=False)
        if df.empty:
            df = yf.download(tickers="GC=F", period=period, interval=tf, progress=False)
            
        if df.empty:
            return "KOSONG"
            
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
            
        df = hitung_indikator_dinamis(df)
        df.dropna(inplace=True)
        return df
    except Exception as e:
        return str(e)

# ==========================================
# 5. PROSES DATA
# ==========================================
with st.spinner(f"🔄 Menarik aliran data pasar {pilihan_tf}..."):
    df_live = get_dynamic_data(pilihan_tf, periode_data)

if isinstance(df_live, str):
    if df_live == "KOSONG":
        st.warning("⚠️ Menunggu respons pasar atau blokir server (Rate Limit) terbuka. Tunggu sekitar 1 menit...")
    else:
        st.error(f"🚨 Kendala sistem: {df_live}")
        
elif df_live is not None and not df_live.empty:
    data_terbaru = df_live.iloc[-1:]
    
    harga_sekarang = round(float(data_terbaru['Close'].iloc[0]), 2)
    rsi_sekarang = float(data_terbaru['RSI_14'].iloc[0])
    atr_sekarang = float(data_terbaru['ATR_14'].iloc[0])
    ema_sekarang = float(data_terbaru['EMA_50'].iloc[0])
    perubahan_harga = float(data_terbaru['Price_Change'].iloc[0])
    waktu_data = data_terbaru.index[0].strftime("%H:%M:%S")

    # ==========================================
    # 6. LOGIKA PREDIKSI DINAMIS
    # ==========================================
    skor_dinamis = 50.0 
    
    if harga_sekarang > ema_sekarang:
        skor_dinamis += 15.0
    else:
        skor_dinamis -= 15.0
        
    if perubahan_harga > 0:
        skor_dinamis += (perubahan_harga * 10)
    elif perubahan_harga < 0:
        skor_dinamis += (perubahan_harga * 10) 
        
    if rsi_sekarang > 50:
        skor_dinamis += (rsi_sekarang - 50) * 0.4
    else:
        skor_dinamis -= (50 - rsi_sekarang) * 0.4

    skor_dinamis = max(10.0, min(95.0, skor_dinamis))
    prob_naik = skor_dinamis / 100.0
    prob_turun = 1.0 - prob_naik

    if prob_naik >= 0.58:
        status_sinyal = "BUY"
        persen_tampil = prob_naik * 100
    elif prob_turun >= 0.58:
        status_sinyal = "SELL"
        persen_tampil = prob_turun * 100
    else:
        status_sinyal = "WAIT"
        persen_tampil = 50.0

    # ==========================================
    # 7. PANEL METRIK 
    # ==========================================
    st.text(f"⏱️ Update Terakhir: {waktu_data} | Mode Anti-Banned")
    
    c1, c2 = st.columns(2)
    c1.metric("📌 Entry (XAUUSD)", f"${harga_sekarang:.2f}", delta=f"{perubahan_harga:.2f}")
    c2.metric("📊 RSI (14)", f"{rsi_sekarang:.1f}")
    
    c3, c4 = st.columns(2)
    c3.metric("📈 ATR", f"{atr_sekarang:.2f}")
    c4.metric("🎯 EMA 50", f"${ema_sekarang:.2f}")
    
    st.divider()

    # ==========================================
    # 8. KEPUTUSAN 
    # ==========================================
    if status_sinyal == "BUY":
        st.success(f"🟢 **SINYAL DINAMIS : BUY**\n\nKekuatan Momentum: **{persen_tampil:.1f}%**\nHarga Acuan: **${harga_sekarang:.2f}**")
    elif status_sinyal == "SELL":
        st.error(f"🔴 **SINYAL DINAMIS : SELL**\n\nKekuatan Momentum: **{persen_tampil:.1f}%**\nHarga Acuan: **${harga_sekarang:.2f}**")
    else:
        st.warning(f"⚪ **STATUS : WAIT / KONSOLIDASI**\n\nPasar sedang tipis. Naik: {prob_naik*100:.1f}% | Turun: {prob_turun*100:.1f}%")

    # BAR LOADING 30 DETIK
    st.markdown("---")
    info_refresh = st.empty()
    bar_loading = st.progress(0)

    for i in range(30):
        sisa_waktu = 30 - i
        info_refresh.caption(f"⏳ Refresh siklus aman dalam {sisa_waktu} detik...")
        bar_loading.progress(int((i + 1) * 3.33))
        time.sleep(1)
        
    bar_loading.progress(100)

    # ==========================================
    # 9. GRAFIK CANDLESTICK
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
