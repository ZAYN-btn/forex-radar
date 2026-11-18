
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone

from forex_engine import MARKETS, analyze_market

st.set_page_config(
    page_title="FOREX RADAR PRO",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: Inter, sans-serif;
}

.stApp {
    background: #080b12;
    color: #e8edf7;
}

.block-container {
    max-width: 1450px;
    padding-top: 1.5rem;
}

header[data-testid="stHeader"] {
    background: transparent;
}

div[data-testid="stMetric"] {
    background: #111827;
    border: 1px solid #202b3d;
    padding: 18px;
    border-radius: 14px;
}

div[data-testid="stMetricLabel"] {
    color: #8b9bb4;
}

div[data-testid="stMetricValue"] {
    color: #f1f5ff;
}

.market-card {
    background: linear-gradient(145deg, #131c2b, #0e1521);
    border: 1px solid #26344a;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 14px;
}

.muted {
    color: #8494ad;
    font-size: 13px;
}

.price {
    font-size: 27px;
    font-weight: 800;
    color: #f1f5ff;
}

.long {
    color: #19d69b;
    font-weight: 800;
}

.short {
    color: #ff6377;
    font-weight: 800;
}

.wait {
    color: #f5bd4f;
    font-weight: 800;
}

.section-title {
    font-size: 19px;
    font-weight: 800;
    margin-top: 25px;
    margin-bottom: 12px;
}

hr {
    border-color: #26344a;
}

.stButton button {
    background: #14b88a;
    color: #06130f;
    border: none;
    border-radius: 10px;
    font-weight: 800;
    min-height: 42px;
}

.stButton button:hover {
    background: #20d9a5;
    color: #06130f;
}

[data-testid="stDataFrame"] {
    border: 1px solid #26344a;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)

# HEADER
st.markdown("""
<div style="display:flex;justify-content:space-between;align-items:center;
background:#111827;border:1px solid #26344a;border-radius:16px;
padding:20px;margin-bottom:20px;">
<div>
<div style="font-size:12px;color:#19d69b;font-weight:800;letter-spacing:3px;">
MARKET INTELLIGENCE
</div>
<div style="font-size:29px;font-weight:800;color:white;">
📡 FOREX RADAR <span style="color:#19d69b;">PRO</span>
</div>
<div style="color:#8494ad;font-size:12px;">
TEKNİK ANALİZ • RİSK TAKİBİ • PİYASA GÖZLEMİ
</div>
</div>
<div style="text-align:right;color:#19d69b;font-weight:700;">
● ANALİZ MODU
<div style="color:#8494ad;font-size:11px;font-weight:400;">
OTOMATİK EMİR KAPALI
</div>
</div>
</div>
""", unsafe_allow_html=True)

# SIDEBAR
st.sidebar.title("⚙️ RADAR AYARLARI")

balance = st.sidebar.number_input(
    "Demo bakiye ($)",
    min_value=100,
    value=10000,
    step=500
)

risk_percent = st.sidebar.number_input(
    "İşlem başına risk (%)",
    min_value=0.1,
    max_value=2.0,
    value=0.5,
    step=0.1
)

risk_amount = balance * risk_percent / 100

st.sidebar.metric("Planlanan risk", f"${risk_amount:.2f}")
st.sidebar.caption("Lot hesabı aracı kurum sözleşme bilgisi olmadan kesinleştirilemez.")

if st.sidebar.button("🔄 Analizi yenile", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# TOP METRICS
st.markdown('<div class="section-title">PİYASA ÖZETİ</div>',
            unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
c1.metric("Demo bakiye", f"${balance:,.0f}")
c2.metric("İşlem riski", f"{risk_percent:.1f}%")
c3.metric("Risk bütçesi", f"${risk_amount:.2f}")

st.caption(
    "Son panel açılışı: " +
    datetime.now().strftime("%d.%m.%Y %H:%M:%S")
)

# ANALYSIS
st.markdown('<div class="section-title">PİYASA TARAMASI</div>',
            unsafe_allow_html=True)

@st.cache_data(ttl=60)
def load_results():
    return [
        analyze_market(name, symbol)
        for name, symbol in MARKETS.items()
    ]

results = load_results()

for item in results:
    name = item["market"]

    if item["status"] != "OK":
        st.markdown(f"""
        <div class="market-card">
        <b>{name}</b>
        <div class="wait">WAIT — VERİ HATASI</div>
        <div class="muted">{item.get("error", "Veri alınamadı")}</div>
        </div>
        """, unsafe_allow_html=True)
        continue

    direction = item["direction"]

    if direction == "LONG":
        signal_class = "long"
    elif direction == "SHORT":
        signal_class = "short"
    else:
        signal_class = "wait"

    st.markdown(f"""
    <div class="market-card">
    <div style="display:flex;justify-content:space-between;align-items:center;">
    <div>
    <div style="font-size:20px;font-weight:800;">{name}</div>
    <div class="muted">Yahoo Finance • Teknik analiz</div>
    </div>
    <div class="{signal_class}" style="font-size:19px;">{direction}</div>
    </div>
    <hr>
    <div class="price">{item["price"]:.5f}</div>
    <div class="muted">Sinyal uyum puanı: {item["score"]}/100</div>
    </div>
    """, unsafe_allow_html=True)

    a, b, c, d = st.columns(4)
    a.metric("RSI", f'{item["rsi"]:.2f}')
    b.metric("5 dakika", item["trend5"])
    c.metric("15 dakika", item["trend15"])
    d.metric("1 saat", item["trend1"])

    levels = []

    if item.get("support") is not None:
        levels.append({
            "Seviye": "Destek",
            "Fiyat": item["support"]
        })

    if item.get("resistance") is not None:
        levels.append({
            "Seviye": "Direnç",
            "Fiyat": item["resistance"]
        })

    if direction != "WAIT":
        levels.extend([
            {"Seviye": "Giriş referansı", "Fiyat": item["price"]},
            {"Seviye": "Stop Loss", "Fiyat": item["stop_loss"]},
            {"Seviye": "TP1", "Fiyat": item["tp1"]},
            {"Seviye": "TP2", "Fiyat": item["tp2"]}
        ])

    if levels:
        st.dataframe(
            pd.DataFrame(levels),
            use_container_width=True,
            hide_index=True
        )

    st.divider()

# FOOTER
st.markdown("""
<div style="text-align:center;padding:25px;color:#718198;
font-size:12px;">
FOREX RADAR PRO • ANALİZ VE KARAR DESTEK PANELİ<br><br>
Bu sistem emir göndermez. Sinyal puanı kazanma olasılığı değildir.
Veriler gecikmeli veya hatalı olabilir. Ekonomik haber filtresi henüz
aktif değildir. İşlem kararları ve risk yönetimi kullanıcıya aittir.
</div>
""", unsafe_allow_html=True)
