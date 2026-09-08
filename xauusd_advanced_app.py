import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time

# ==========================================
# 1. KONFIGURASI HALAMAN STREAMLIT
# ==========================================
st.set_page_config(
    page_title="XAUUSD Scalper - Small Account Edition",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ XAUUSD Scalper Pro (Modal Kecil Edition)")
st.caption("Sistem Analisis Presisi Tinggi & Kalkulator Manajemen Risiko Real-Time")

# ==========================================
# 2. SIDEBAR: KALKULATOR RISIKO & DYNAMIC THRESHOLD
# ==========================================
st.sidebar.header("🛡️ Manajemen Risiko & Sinyal")

tipe_akun = st.sidebar.selectbox("Tipe Akun Broker:", ["Standard / Raw Spread", "Cent Account"])
modal_akun = st.sidebar.number_input("Modal Akun ($):", min_value=5.0, value=50.0, step=5.0)
risiko_persen = st.sidebar.slider("Batas Risiko per Trade (%):", min_value=0.5, max_value=3.0, value=1.0, step=0.5)

# Slider Fleksibel untuk Batas Konfluensi Sinyal (Default: 70%)
min_konfluensi = st.sidebar.slider("Min. Konfluensi Sinyal (%):", min_value=50, max_value=90, value=70, step=5)

# Perhitungan Toleransi Kerugian Maksimal ($)
max_risk_usd = modal_akun * (risiko_persen / 100.0)
st.sidebar.markdown("---")
st.sidebar.metric("💥 Maksimal Rugi / Trade", f"${max_risk_usd:.2f}")

st.sidebar.markdown("---")
pilihan_tf = st.sidebar.selectbox("Timeframe Analisis:", ["1m", "5m", "15m"], index=1)
periode_data = "5d"

# ==========================================
# 3. FUNGSI INDIKATOR TEKNIKAL
# ==========================================
def hitung_indikator(df):
    # RSI (14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df['RSI_14'] = 100 - (100 / (1 + rs))

    # Moving Averages (EMA 50 & EMA 200 Tren Filter)
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()

    # MACD (12, 26, 9)
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

    # ATR (14) Volatilitas
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR_14'] = tr.rolling(window=14).mean()
    
    df['Price_Change'] = df['Close'].diff()
    return df

# ==========================================
# 4. PENGAMBILAN DATA LIVE (AUTO REFRESH DATA SENSITIF)
# ==========================================
@st.cache_data(ttl=10, show_spinner=False)
def get_live_data(tf, period):
    try:
        df = yf.download(tickers="GC=F", period=period, interval=tf, progress=False)
        if df.empty:
            df = yf.download(tickers="XAUUSD=X", period=period, interval=tf, progress=False)
            
        if df.empty:
            return "KOSONG"
            
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = hitung_indikator(df)
        df.dropna(inplace=True)
        return df
    except Exception as e:
        return str(e)

# ==========================================
# 5. PROSES ANALISIS DATA
# ==========================================
with st.spinner(f"🔄 Menarik data segar pasar XAUUSD ({pilihan_tf})..."):
    df_live = get_live_data(pilihan_tf, periode_data)

if isinstance(df_live, str):
    if df_live == "KOSONG":
        st.warning("⚠️ Data pasar belum merespons. Menunggu sinkronisasi...")
    else:
        st.error(f"🚨 Kendala Sistem: {df_live}")

elif df_live is not None and not df_live.empty:
    data_terbaru = df_live.iloc[-1:]
    
    harga_sekarang = float(data_terbaru['Close'].iloc[0])
    harga_buka = float(data_terbaru['Open'].iloc[0])
    rsi_sekarang = float(data_terbaru['RSI_14'].iloc[0])
    atr_sekarang = float(data_terbaru['ATR_14'].iloc[0])
    ema50_sekarang = float(data_terbaru['EMA_50'].iloc[0])
    ema200_sekarang = float(data_terbaru['EMA_200'].iloc[0])
    macd_sekarang = float(data_terbaru['MACD'].iloc[0])
    macd_sig_sekarang = float(data_terbaru['MACD_Signal'].iloc[0])
    waktu_data = data_terbaru.index[0].strftime("%H:%M:%S")
    
    # Selisih harga dalam Dolar ($)
    momentum_usd = harga_sekarang - harga_buka

    # ==========================================
    # 6. LOGIKA KONFLUENSI SINYAL
    # ==========================================
    skor_bullish = 0
    skor_bearish = 0

    # 1. Tren Makro EMA 200 & EMA 50 (30 Poin)
    if harga_sekarang > ema50_sekarang and ema50_sekarang > ema200_sekarang:
        skor_bullish += 30
    elif harga_sekarang < ema50_sekarang and ema50_sekarang < ema200_sekarang:
        skor_bearish += 30

    # 2. Momentum Lilin Berjalan (20 Poin)
    if momentum_usd > 0:
        skor_bullish += 20
    elif momentum_usd < 0:
        skor_bearish += 20

    # 3. MACD Crossover (25 Poin)
    if macd_sekarang > macd_sig_sekarang:
        skor_bullish += 25
    else:
        skor_bearish += 25

    # 4. Filter RSI Aman (25 Poin)
    if 50 < rsi_sekarang < 68:
        skor_bullish += 25
    elif 32 < rsi_sekarang <= 50:
        skor_bearish += 25

    # PENENTUAN SINYAL BERDASARKAN SLIDER CONFLUENCE
    if skor_bullish >= min_konfluensi:
        status_sinyal = "BUY"
        kekuatan = skor_bullish
        sl = harga_sekarang - (atr_sekarang * 1.5)
        tp = harga_sekarang + (atr_sekarang * 2.25)
    elif skor_bearish >= min_konfluensi:
        status_sinyal = "SELL"
        kekuatan = skor_bearish
        sl = harga_sekarang + (atr_sekarang * 1.5)
        tp = harga_sekarang - (atr_sekarang * 2.25)
    else:
        status_sinyal = "WAIT"
        kekuatan = max(skor_bullish, skor_bearish)
        sl, tp = 0.0, 0.0

    # PERHITUNGAN PRESISI JARAK & NIKMAT LOT BERDASARKAN DOLAR ($)
    jarak_sl_usd = abs(harga_sekarang - sl) if sl > 0 else (atr_sekarang * 1.5)
    jarak_sl_pips = jarak_sl_usd * 10  # 1 USD pergerakan Emas = 10 Pips (100 Points)
    
    if tipe_akun == "Standard / Raw Spread":
        # 1 Lot Standard = $100 nilai risiko per $1.00 pergerakan harga
        lot_ideal = max_risk_usd / (jarak_sl_usd * 100) if jarak_sl_usd > 0 else 0.01
        lot_rekomendasi = max(0.01, round(lot_ideal, 2))
        unit_lot = "Lot Standard"
    else:
        # Akun Cent = $1.00 nilai risiko per $1.00 pergerakan harga
        lot_ideal = max_risk_usd / (jarak_sl_usd * 1) if jarak_sl_usd > 0 else 0.1
        lot_rekomendasi = max(0.1, round(lot_ideal, 1))
        unit_lot = "Lot Cent"

    st.sidebar.info(f"💡 **Ukuran Lot Aman:** `{lot_rekomendasi}` {unit_lot}")

    # ==========================================
    # 7. TAMPILAN DASHBOARD & METRIK ($)
    # ==========================================
    st.caption(f"⏱️ Update Terakhir: **{waktu_data}** | Timeframe: **{pilihan_tf}** | Target Konfluensi: **{min_konfluensi}%**")

    c1, c2, c3, c4 = st.columns(4)
    # Tampilan perubahan harga dalam format nominal $ Dolar
    format_delta = f"+${momentum_usd:.2f}" if momentum_usd >= 0 else f"-${abs(momentum_usd):.2f}"
    
    c1.metric("📌 Entry Price (XAUUSD)", f"${harga_sekarang:.2f}", delta=format_delta)
    c2.metric("📊 RSI (14)", f"{rsi_sekarang:.1f}")
    c3.metric("📈 Volatilitas ATR", f"${atr_sekarang:.2f}")
    c4.metric("🎯 EMA 200 (Macro)", f"${ema200_sekarang:.2f}")

    st.divider()

    # ==========================================
    # 8. PANEL KEPUTUSAN SINYAL
    # ==========================================
    col_sig, col_plan = st.columns([1.2, 1])

    with col_sig:
        if status_sinyal == "BUY":
            st.success(f"🟢 **SIGNAL: CONFLUENCE BUY**\n\nKekuatan Konfluensi: **{kekuatan}%** (Target: {min_konfluensi}%)\nHarga Entry Acuan: **${harga_sekarang:.2f}**")
        elif status_sinyal == "SELL":
            st.error(f"🔴 **SIGNAL: CONFLUENCE SELL**\n\nKekuatan Konfluensi: **{kekuatan}%** (Target: {min_konfluensi}%)\nHarga Entry Acuan: **${harga_sekarang:.2f}**")
        else:
            st.warning(f"⚪ **STATUS: WAIT / BELUM MEMENUHI TARGET**\n\nKonfluensi tertinggi saat ini: **{kekuatan}%** (Target minimal: **{min_konfluensi}%**). Sabar menunggu momen yang pas!")

    with col_plan:
        if status_sinyal in ["BUY", "SELL"]:
            st.markdown(f"""
            **📋 TRADING PLAN & RISIKO:**
            * 🛡️ **Stop Loss (SL):** `${sl:.2f}` (Jarak: `${jarak_sl_usd:.2f}` / ~{jarak_sl_pips:.1f} Pips)
            * 🎯 **Take Profit (TP):** `${tp:.2f}`
            * ⚖️ **Rasio Risk/Reward:** `1 : 1.5`
            * 💼 **Gunakan Size:** **`{lot_rekomendasi}` {unit_lot}**
            """)
        else:
            st.info("💡 **Tips Modal Kecil:** Jika pergerakan pasar lambat, kamu dapat menggeser Slider Konfluensi di Sidebar ke **60%-65%**.")

    # ==========================================
    # 9. GRAFIK CANDLESTICK
    # ==========================================
    st.subheader(f"Grafik Candlestick Real-Time ({pilihan_tf})")
    df_chart = df_live.tail(45).copy()

    fig = go.Figure(data=[go.Candlestick(
        x=df_chart.index,
        open=df_chart['Open'],
        high=df_chart['High'],
        low=df_chart['Low'],
        close=df_chart['Close'],
        name="XAUUSD"
    )])

    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['EMA_50'], line=dict(color='yellow', width=1.5), name='EMA 50'))
    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['EMA_200'], line=dict(color='cyan', width=1.5), name='EMA 200'))

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=400,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(type='category')
    )
    st.plotly_chart(fig, use_container_width=True)

    # ==========================================
    # 10. TIMER HITUNG MUNDUR & AUTOMATIC RERUN
    # ==========================================
    st.markdown("---")
    info_refresh = st.empty()
    bar_loading = st.progress(0)

    for i in range(15):
        sisa_waktu = 15 - i
        info_refresh.caption(f"⏳ Auto-refresh live data dalam {sisa_waktu} detik...")
        bar_loading.progress(int((i + 1) * (100 / 15)))
        time.sleep(1)

# Memicu Streamlit untuk merender ulang halaman otomatis
st.rerun()
