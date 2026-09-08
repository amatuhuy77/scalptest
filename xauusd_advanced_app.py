import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time
import io

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ==========================================
# 1. KONFIGURASI HALAMAN STREAMLIT
# ==========================================
st.set_page_config(
    page_title="XAUUSD Scalper Pro",
    page_icon="⚡",
    layout="wide"
)

# ==========================================
# 2. FUNGSI GENERATOR PDF GUIDEBOOK IN-MEMORY
# ==========================================
def buat_pdf_guidebook():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=18, leading=22, textColor=colors.HexColor('#1E293B'), spaceAfter=4)
    subtitle_style = ParagraphStyle('DocSubtitle', parent=styles['Normal'], fontSize=10, leading=13, textColor=colors.HexColor('#64748B'), spaceAfter=12)
    h1_style = ParagraphStyle('SectionH1', parent=styles['Heading2'], fontSize=12, leading=15, textColor=colors.HexColor('#0F172A'), spaceBefore=10, spaceAfter=4)
    body_style = ParagraphStyle('BodyTextCustom', parent=styles['Normal'], fontSize=9, leading=13, textColor=colors.HexColor('#334155'), spaceAfter=5)

    story = []
    story.append(Paragraph("BUKU PANDUAN PENGGUNA (USER GUIDEBOOK)", title_style))
    story.append(Paragraph("XAUUSD Scalper Pro — Modal Kecil Edition (v2.4)", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CBD5E1'), spaceAfter=10))

    story.append(Paragraph("1. PENDAHULUAN & KONSEP UTAMA", h1_style))
    story.append(Paragraph("XAUUSD Scalper Pro dirancang khusus untuk perdagangan emas pada akun bermodal terbatas ($5 - $100). Sistem ini menggabungkan penentuan tren berbasis konfluensi indikator dengan Filter Area Pullback untuk memastikan eksekusi dilakukan pada rasio Risk/Reward terbaik.", body_style))

    story.append(Paragraph("2. ARSITEKTUR INDIKATOR TEKNIKAL", h1_style))
    story.append(Paragraph("• <b>EMA 50 & EMA 200:</b> Menentukan tren utama dan batas Support/Resistance Dinamis.<br/>• <b>RSI 14:</b> Filter kejenuhan pasar (Zona Bullish: 50–68, Bearish: 32–50).<br/>• <b>MACD (12, 26, 9):</b> Konfirmasi persilangan momentum intraday.<br/>• <b>ATR 14:</b> Mengukur volatilitas harga dalam nominal Dolar ($).<br/>• <b>AI Multi-Timeframe Engine:</b> Memindai tren bersamaan di M1, M5, dan M15.", body_style))

    story.append(Paragraph("3. TABEL SKORING KONFLUENSI SINYAL", h1_style))
    table_data = [
        ['Parameter Evaluasi', 'Kondisi Bullish', 'Kondisi Bearish', 'Bobot'],
        ['Tren EMA 50 & 200', 'Harga > EMA50 > EMA200', 'Harga < EMA50 < EMA200', '+30%'],
        ['MACD Crossover', 'MACD > Signal Line', 'MACD < Signal Line', '+25%'],
        ['Filter RSI', '50 < RSI < 68', '32 < RSI <= 50', '+25%'],
        ['Momentum Lilin', 'Close > Open', 'Close < Open', '+20%'],
        ['AI Macro Bias', 'Macro Trend Bullish', 'Macro Trend Bearish', '+10%']
    ]
    t = Table(table_data, colWidths=[130, 150, 150, 60])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')])
    ]))
    story.append(t)
    story.append(Spacer(1, 8))

    story.append(Paragraph("4. RUMUS MANAJEMEN RISIKO", h1_style))
    story.append(Paragraph("• <b>Maksimal Rugi ($):</b> Modal ($) x Batas Risiko (%)<br/>• <b>Jarak Stop Loss:</b> 1.5 x ATR 14 ($ Nominal)<br/>• <b>Lot Standard:</b> Max Risk ($) / (Jarak SL $ x 100)<br/>• <b>Lot Cent:</b> Max Risk ($) / (Jarak SL $ x 1)", body_style))

    doc.build(story)
    buffer.seek(0)
    return buffer

# ==========================================
# 3. SIDEBAR: MANAJEMEN RISIKO & PARAMETER
# ==========================================
st.sidebar.header("🛡️ Manajemen Risiko & Sinyal")

tipe_akun = st.sidebar.selectbox("Tipe Akun Broker:", ["Standard / Raw Spread", "Cent Account"])
modal_akun = st.sidebar.number_input("Modal Akun ($):", min_value=5.0, value=50.0, step=5.0)
risiko_persen = st.sidebar.slider("Batas Risiko per Trade (%):", min_value=0.5, max_value=3.0, value=1.0, step=0.5)

min_konfluensi = st.sidebar.slider("Min. Konfluensi Sinyal (%):", min_value=50, max_value=90, value=70, step=5)
toleransi_pullback_atr = st.sidebar.slider("Toleransi Area Pullback (x ATR):", min_value=0.3, max_value=1.5, value=0.8, step=0.1)

max_risk_usd = modal_akun * (risiko_persen / 100.0)
st.sidebar.markdown("---")
st.sidebar.metric("💥 Maksimal Rugi / Trade", f"${max_risk_usd:.2f}")
st.sidebar.markdown("---")
pilihan_tf = st.sidebar.selectbox("Timeframe Utama:", ["1m", "5m", "15m"], index=1)
periode_data = "5d"

st.sidebar.markdown("---")
st.sidebar.subheader("📄 Dokumentasi System")
pdf_bytes = buat_pdf_guidebook()
st.sidebar.download_button(
    label="📥 Download PDF Guidebook", data=pdf_bytes, file_name="XAUUSD_Scalper_Pro_Guidebook.pdf", mime="application/pdf", use_container_width=True
)

# ==========================================
# 4. FUNGSI INDIKATOR TEKNIKAL & AI ENGINE
# ==========================================
def hitung_indikator(df):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df['RSI_14'] = 100 - (100 / (1 + rs))

    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()

    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR_14'] = tr.rolling(window=14).mean()
    return df

@st.cache_data(ttl=10, show_spinner=False)
def fetch_single_tf(tf, period="5d"):
    try:
        df = yf.download(tickers="GC=F", period=period, interval=tf, progress=False)
        if df.empty:
            df = yf.download(tickers="XAUUSD=X", period=period, interval=tf, progress=False)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = hitung_indikator(df)
        df.dropna(inplace=True)
        return df
    except Exception:
        return None

@st.cache_data(ttl=10, show_spinner=False)
def hitung_ai_multi(timeframes=("1m", "5m", "15m")):
    hasil = {}
    skor_total, count = 0, 0
    for tf in timeframes:
        df = fetch_single_tf(tf)
        if df is not None and not df.empty:
            last = df.iloc[-1]
            close, ema50, ema200, rsi = float(last['Close']), float(last['EMA_50']), float(last['EMA_200']), float(last['RSI_14'])
            if close > ema50 > ema200 and rsi > 50:
                bias, skor = "BULLISH", 100
            elif close < ema50 < ema200 and rsi < 50:
                bias, skor = "BEARISH", -100
            else:
                bias, skor = "NEUTRAL", 0
            hasil[tf] = {"bias": bias, "close": close, "rsi": rsi}
            skor_total += skor
            count += 1
    bias_global = "NEUTRAL"
    if count > 0:
        rata_skor = skor_total / count
        if rata_skor >= 50: bias_global = "BULLISH"
        elif rata_skor <= -50: bias_global = "BEARISH"
    return hasil, bias_global

# ==========================================
# 5. TAMPILAN UTAMA TAB STREAMLIT
# ==========================================
st.title("⚡ XAUUSD Scalper Pro (Modal Kecil Edition)")
tab_dashboard, tab_panduan = st.tabs(["📊 Live Scalper Dashboard", "📖 Buku Panduan & Pengertian"])

with tab_dashboard:
    with st.spinner("🔄 Sedang memperbarui data pasar & mengecek area Pullback..."):
        df_live = fetch_single_tf(pilihan_tf, periode_data)
        ai_data, bias_macro = hitung_ai_multi(timeframes=("1m", "5m", "15m"))

    if df_live is None or df_live.empty:
        st.error("🚨 Data pasar belum merespons. Menunggu sinkronisasi...")
    else:
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
        momentum_usd = harga_sekarang - harga_buka

        skor_bullish, skor_bearish = 0, 0
        if harga_sekarang > ema50_sekarang and ema50_sekarang > ema200_sekarang: skor_bullish += 30
        elif harga_sekarang < ema50_sekarang and ema50_sekarang < ema200_sekarang: skor_bearish += 30

        if momentum_usd > 0: skor_bullish += 20
        elif momentum_usd < 0: skor_bearish += 20

        if macd_sekarang > macd_sig_sekarang: skor_bullish += 25
        else: skor_bearish += 25

        if 50 < rsi_sekarang < 68: skor_bullish += 25
        elif 32 < rsi_sekarang <= 50: skor_bearish += 25

        if bias_macro == "BULLISH": skor_bullish = min(100, skor_bullish + 10)
        elif bias_macro == "BEARISH": skor_bearish = min(100, skor_bearish + 10)

        jarak_ke_ema50 = abs(harga_sekarang - ema50_sekarang)
        batas_jarak_ideal = atr_sekarang * toleransi_pullback_atr
        is_in_pullback_zone = jarak_ke_ema50 <= batas_jarak_ideal

        if skor_bullish >= min_konfluensi:
            bias_tren = "BUY"
            kekuatan = skor_bullish
            sl = harga_sekarang - (atr_sekarang * 1.5)
            tp = harga_sekarang + (atr_sekarang * 2.25)
        elif skor_bearish >= min_konfluensi:
            bias_tren = "SELL"
            kekuatan = skor_bearish
            sl = harga_sekarang + (atr_sekarang * 1.5)
            tp = harga_sekarang - (atr_sekarang * 2.25)
        else:
            bias_tren = "WAIT"
            kekuatan = max(skor_bullish, skor_bearish)
            sl, tp = 0.0, 0.0

        # PEMISAHAN STATUS AGAR WARNANYA BERBEDA
        if bias_tren == "BUY":
            if is_in_pullback_zone:
                status_sinyal = "READY BUY"
                catatan_pullback = f"✅ Harga di area Pullback ideal (Jarak ke EMA 50: `${jarak_ke_ema50:.2f}` <= `${batas_jarak_ideal:.2f}`). Momen Entry Presisi!"
            else:
                status_sinyal = "WAIT PULLBACK (BUY)"
                catatan_pullback = f"⏳ Tren kuat BUY, namun harga sudah *overextended* (terlalu jauh dari EMA 50). Tunggu harga memantul mendekati area `${ema50_sekarang:.2f}`."
        elif bias_tren == "SELL":
            if is_in_pullback_zone:
                status_sinyal = "READY SELL"
                catatan_pullback = f"✅ Harga di area Pullback ideal (Jarak ke EMA 50: `${jarak_ke_ema50:.2f}` <= `${batas_jarak_ideal:.2f}`). Momen Entry Presisi!"
            else:
                status_sinyal = "WAIT PULLBACK (SELL)"
                catatan_pullback = f"⏳ Tren kuat SELL, namun harga sudah *overextended* (terlalu jauh dari EMA 50). Tunggu harga memantul mendekati area `${ema50_sekarang:.2f}`."
        else:
            status_sinyal = "WAIT TREN"
            catatan_pullback = "⚪ Konfluensi tren belum terpenuhi. Sabar menunggu persilangan atau breakout."

        jarak_sl_usd = abs(harga_sekarang - sl) if sl > 0 else (atr_sekarang * 1.5)
        jarak_sl_pips = jarak_sl_usd * 10
        
        if tipe_akun == "Standard / Raw Spread":
            lot_ideal = max_risk_usd / (jarak_sl_usd * 100) if jarak_sl_usd > 0 else 0.01
            lot_rekomendasi = max(0.01, round(lot_ideal, 2))
            unit_lot = "Lot Standard"
        else:
            lot_ideal = max_risk_usd / (jarak_sl_usd * 1) if jarak_sl_usd > 0 else 0.1
            lot_rekomendasi = max(0.1, round(lot_ideal, 1))
            unit_lot = "Lot Cent"

        st.caption(f"⏱️ **Update Terakhir:** `{waktu_data}` | **AI Macro Trend:** `{bias_macro}` | **Status Pullback:** {'`DEKAT EMA 50`' if is_in_pullback_zone else '`OVEREXTENDED`'}")
        
        col_tf1, col_tf2, col_tf3 = st.columns(3)
        for idx, (tf_key, tf_val) in enumerate(ai_data.items()):
            col = [col_tf1, col_tf2, col_tf3][idx]
            col.caption(f"TF {tf_key}: **{tf_val['bias']}** (RSI: {tf_val['rsi']:.1f})")

        st.divider()

        c1, c2, c3, c4 = st.columns(4)
        format_delta = f"+${momentum_usd:.2f}" if momentum_usd >= 0 else f"-${abs(momentum_usd):.2f}"
        
        c1.metric("📌 Entry Price", f"${harga_sekarang:.2f}", delta=format_delta)
        c2.metric("🎯 EMA 50 (Dynamic SR)", f"${ema50_sekarang:.2f}")
        c3.metric("📊 Jarak Ke EMA 50", f"${jarak_ke_ema50:.2f}")
        c4.metric("📈 Max Jarak Ideal", f"${batas_jarak_ideal:.2f}")

        st.divider()

        col_sig, col_plan = st.columns([1.2, 1])

        # RENDER BLOK WARNA SESUAI STATUS SINYAL
        with col_sig:
            if status_sinyal == "READY BUY":
                st.success(f"🟢 **SIGNAL: {status_sinyal}**\n\nKekuatan Konfluensi: **{kekuatan}%**\n\n{catatan_pullback}")
            elif status_sinyal == "READY SELL":
                st.error(f"🔴 **SIGNAL: {status_sinyal}**\n\nKekuatan Konfluensi: **{kekuatan}%**\n\n{catatan_pullback}")
            elif status_sinyal == "WAIT PULLBACK (BUY)":
                st.warning(f"🟡 **STATUS: {status_sinyal}**\n\nKekuatan Konfluensi: **{kekuatan}%**\n\n{catatan_pullback}")
            elif status_sinyal == "WAIT PULLBACK (SELL)":
                st.warning(f"🟠 **STATUS: {status_sinyal}**\n\nKekuatan Konfluensi: **{kekuatan}%**\n\n{catatan_pullback}")
            else:
                st.info(f"⚪ **STATUS: {status_sinyal}**\n\nKonfluensi tertinggi: **{kekuatan}%** (Target: {min_konfluensi}%).\n\n{catatan_pullback}")

        with col_plan:
            if bias_tren in ["BUY", "SELL"]:
                st.markdown(f"""
                **📋 TRADING PLAN & RISIKO:**
                * 🛡️ **Stop Loss (SL):** `${sl:.2f}` (Jarak: `${jarak_sl_usd:.2f}` / ~{jarak_sl_pips:.1f} Pips)
                * 🎯 **Take Profit (TP):** `${tp:.2f}`
                * ⚖️ **Rasio Risk/Reward:** `1 : 1.5`
                * 💼 **Gunakan Size:** **`{lot_rekomendasi}` {unit_lot}**
                """)
            else:
                st.info("💡 **Tips Modal Kecil:** Tunggu harga bergerak mendekati EMA 50 untuk mendapatkan Stop Loss yang lebih kecil dan rasio Risk/Reward lebih ideal.")

        st.subheader(f"Grafik Candlestick & Area Pullback ({pilihan_tf})")
        df_chart = df_live.tail(45).copy()
        fig = go.Figure(data=[go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], name="XAUUSD")])
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['EMA_50'], line=dict(color='yellow', width=1.5), name='EMA 50 (Dynamic SR)'))
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['EMA_200'], line=dict(color='cyan', width=1.5), name='EMA 200 (Trend)'))
        fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=400, margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(type='category'))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        progress_slot = st.empty()
        for sisa in range(15, 0, -1):
            persen = int(((15 - sisa) / 15) * 100)
            with progress_slot.container():
                st.caption(f"🔄 **Status Sistem:** Monitoring Pullback & Live Data | *Auto-refresh* dalam **{sisa} detik**...")
                st.progress(persen)
            time.sleep(1)
        st.rerun()

with tab_panduan:
    st.header("📖 Buku Panduan & Pengertian Sistem")
    st.caption("Panduan komprehensif indikator, logika skoring, dan manajemen risiko akun modal kecil.")
    st.markdown("""
    ### 1. PENGERTIAN INDIKATOR TEKNIKAL
    * **EMA 50 & EMA 200 (Exponential Moving Average):**
      * **EMA 200:** Indikator penentu tren utama (makro). Jika harga di atas EMA 200, pasar dalam fase *bullish*.
      * **EMA 50:** Berfungsi sebagai *Support/Resistance* dinamis. Tempat terbaik mencari pantulan harga (*pullback*).
    * **RSI 14 (Relative Strength Index):** Mengukur kecepatan dan perubahan pergerakan harga. Rentang 50–68 digunakan untuk konfirmasi *BUY*, dan 32–50 untuk *SELL*.
    * **MACD (Moving Average Convergence Divergence):** Mengukur momentum persilangan pergerakan harga intraday.
    * **ATR 14 (Average True Range):** Mengukur nilai volatilitas aktual pasar dalam Dolar ($). Digunakan untuk menghitung jarak Stop Loss dan Take Profit yang dinamis mengikuti kondisi pasar.
    ---
    ### 2. LOGIKA SKORING & FILTER PULLBACK
    Sistem mengevaluasi kondisi pasar dengan mengakumulasi skor persentase (%):
    """)
    st.table(pd.DataFrame({
        "Parameter Evaluasi": ["Tren EMA 50 & 200", "MACD Crossover", "Filter RSI", "Momentum Lilin", "AI Macro Bias"],
        "Kondisi Bullish": ["Harga > EMA 50 > EMA 200", "MACD > Signal Line", "50 < RSI < 68", "Close > Open", "Macro Trend Bullish"],
        "Kondisi Bearish": ["Harga < EMA 50 < EMA 200", "MACD < Signal Line", "32 < RSI <= 50", "Close < Open", "Macro Trend Bearish"],
        "Bobot Skor": ["+30%", "+25%", "+25%", "+20%", "+10%"]
    }))
    st.markdown("""
    **Penjelasan Status Sinyal:**
    * **READY BUY / SELL:** Konfluensi $\ge$ Min. Konfluensi DAN harga berada di dekat EMA 50 (area pemantulan ideal).
    * **WAIT PULLBACK:** Konfluensi tren terkuat terpenuhi, namun harga sudah terlanjur melompat jauh dari EMA 50 (*overextended*). Dilarang mengejar harga.
    * **WAIT TREN:** Skor konfluensi belum mencapai ambang batas minimal.
    ---
    ### 3. FORMULA MANAJEMEN RISIKO & LOT AUTOMATION
    Sistem menghitung ukuran lot berdasarkan Dolar ($) yang siap dirisikokan, bukan pips statis:
    $$\text{Max Risk USD} = \text{Modal Akun} \times \left(\frac{\text{Batas Risiko \%}}{100}\right)$$
    * **Akun Standard / Raw Spread:** $\text{Lot Standard} = \frac{\text{Max Risk USD}}{\text{Jarak SL USD} \times 100}$
    * **Akun Cent:** $\text{Lot Cent} = \frac{\text{Max Risk USD}}{\text{Jarak SL USD} \times 1}$
    ---
    ### 4. STRATEGI EXECUTION & ATURAN DISIPLIN
    1. **Disiplin Lot:** Gunakan selalu lot rekomendasi dari sistem. Jangan menambah lot saat mengalami *loss*.
    2. **Patuhi Status WAIT PULLBACK:** Mengejar harga yang sudah melompat jauh adalah penyebab utama *Stop Loss* tersentuh akibat koreksi alami pasar.
    3. **Hindari High-Impact News:** Fluktuasi saat rilis berita besar dapat melebar skenario *spread* broker.
    """)
