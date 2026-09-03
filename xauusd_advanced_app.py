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
    page_title="XAUUSD Dynamic Scalper",
    page_icon="⚡",
    layout="centered"
)

st.markdown("### ⚡ XAUUSD Dynamic Scalper")
st.caption("Mode Analisis Super Peka & Dinamis (Anti-Monoton)")

# ==========================================
# 2. PILIHAN TIMEFRAME (M1 / M5)
# ==========================================
pilihan_tf = st.selectbox("Pilih Timeframe Analisis:", ["1m", "5m"], index=1)
periode_data = "1d" if pilihan_tf == "1m" else "5d"

# ==========================================
# 3. FUNGSI INDIKATOR & DINAMIKA HARGA
# ==========================================
def hitung_indikator_dinamis(df):
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

    # TAMBAHAN: Menghitung selisih perubahan harga kilat (Velocity)
    df['Price_Change'] = df['Close'].diff()

    return df

# ==========================================
# 4. PENGAMBILAN DATA TANPA CACHE KAKU
# ==========================================
@st.cache_data(ttl=5) # Cache dipercepat jadi 5 detik agar sangat responsif
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
# 5. PROSES DATA & LOADING
# ==========================================
with st.spinner(f"🔄 Membaca pergerakan live {pilihan_tf}..."):
    df_live = get_dynamic_data(pilihan_tf, periode_data)

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
    perubahan_harga = float(data_terbaru['Price_Change'].iloc[0])
    waktu_data = data_terbaru.index[0].strftime("%H:%M:%S")

    # ==========================================
    # 6. LOGIKA PREDIKSI SUPER DINAMIS & PEKA
    # ==========================================
    # Menggabungkan tren dasar dengan kecepatan perubahan harga detik ini
    skor_dinamis = 50.0 # Titik tengah netral
    
    # Faktor Tren EMA
    if harga_sekarang > ema_sekarang:
        skor_dinamis += 15.0
    else:
        skor_dinamis -= 15.0
        
    # Faktor Kecepatan Perubahan Harga (Price Velocity)
    if perubahan_harga > 0:
        skor_dinamis += (perubahan_harga * 10)
    elif perubahan_harga < 0:
        skor_dinamis += (perubahan_harga * 10) # Mengurangi skor jika minus
        
    # Faktor RSI (Sensitivitas momentum)
    if rsi_sekarang > 50:
        skor_dinamis += (rsi_sekarang - 50) * 0.4
    else:
        skor_dinamis -= (50 - rsi_sekarang) * 0.4

    # Membatasi persentase agar berada di rentang wajar (10% - 95%)
    skor_dinamis = max(10.0, min(95.0, skor_dinamis))
    prob_naik = skor_dinamis / 100.0
    prob_turun = 1.0 - prob_naik

    # Penentuan Status Sinyal Berdasarkan Angka Dinamis
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
    # 7. PANEL METRIK DASHBOARD
    # ==========================================
    st.text(f"⏱️ Update ({pilihan_tf}): {waktu_data}")
    
    c1, c2 = st.columns(2)
    c1.metric("📌 Entry (XAUUSD)", f"${harga_sekarang:.2f}", delta=f"{perubahan_harga:.2f}")
    c2.metric("📊 RSI (14)", f"{rsi_sekarang:.1f}")
    
    c3, c4 = st.columns(2)
    c3.metric("📈 ATR", f"{atr_sekarang:.2f}")
    c4.metric("🎯 EMA 50", f"${ema_sekarang:.2f}")
    
    st.divider()

    # ==========================================
    # 8. KEPUTUSAN DINAMIS DI LAYAR
    # ==========================================
    if status_sinyal == "BUY":
        st.success(f"🟢 **SINYAL DINAMIS : BUY**\n\nKekuatan Momentum: **{persen_tampil:.1f}%**\nHarga Acuan: **${harga_sekarang:.2f}**")
    elif status_sinyal == "SELL":
        st.error(f"🔴 **SINYAL DINAMIS : SELL**\n\nKekuatan Momentum: **{persen_tampil:.1f}%**\nHarga Acuan: **${harga_sekarang:.2f}**")
    else:
        st.warning(f"⚪ **STATUS : WAIT / KONSOLIDASI**\n\nPasar sedang bergerak tipis. Naik: {prob_naik*100:.1f}% | Turun: {prob_turun*100:.1f}%")

    # BAR LOADING & COUNTDOWN TEPAT DI BAWAH REKOMENDASI (DIUBAH JADI 5 DETIK)
    st.markdown("---")
    info_refresh = st.empty()
    bar_loading = st.progress(0)

    for i in range(5):
        sisa_waktu = 5 - i
        info_refresh.caption(f"⏳ Refresh dinamis dalam {sisa_waktu} detik...")
        bar_loading.progress((i + 1) * 20)
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
