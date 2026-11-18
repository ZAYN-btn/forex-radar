
import streamlit as st
import pandas as pd
from datetime import datetime
from forex_engine import MARKETS, analyze_market

st.set_page_config(
    page_title="Forex Radar",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
.stApp {
    background: #101722;
    color: #F1F5F9;
}
.block-container {
    max-width: 1250px;
    padding-top: 2rem;
}
header[data-testid="stHeader"] {
    background: transparent;
}
h1, h2, h3, p, label, span {
    color: #F1F5F9;
}
.market-card {
    background: #1B2736;
    border: 1px solid #34445A;
    border-radius: 14px;
    padding: 18px;
    margin-bottom: 12px;
}
.muted {
    color: #B6C4D6 !important;
    font-size: 13px;
}
.price {
    font-size: 28px;
    font-weight: 800;
    color: #FFFFFF;
}
.long {
    color: #36E0A1 !important;
    font-weight: 800;
}
.short {
    color: #FF7888 !important;
    font-weight: 800;
}
.wait {
    color: #FFD166 !important;
    font-weight: 800;
}
div[data-testid="stMetric"] {
    background: #1B2736;
    border: 1px solid #34445A;
    border-radius: 12px;
    padding: 14px;
}
div[data-testid="stMetricLabel"] {
    color: #C3D0E0 !important;
}
div[data-testid="stMetricValue"] {
    color: #FFFFFF !important;
}
.stButton button {
    background: #36D9A0;
    color: #10231D;
    border: none;
    border-radius: 9px;
    font-weight: 700;
}
.stButton button:hover {
    background: #65E9BA;
    color: #10231D;
}
hr {
    border-color: #34445A;
}
[data-testid="stDataFrame"] {
    border: 1px solid #34445A;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="background:#1B2736;padding:22px;border:1px solid #34445A;
border-radius:15px;margin-bottom:22px;">
<div style="color:#36E0A1;font-size:12px;font-weight:800;letter-spacing:2px;">
MARKET ANALYSIS
</div>
<div style="font-size:29px;font-weight:800;color:white;">
📡 FOREX RADAR PRO
</div>
<div style="color:#B6C4D6;font-size:13px;">
Sade • Modern • Çoklu zaman dilimi analizi
</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.title("Ayarlar")

balance = st.sidebar.number_input(
    "Demo bakiye ($)", min_value=100, value=10000, step=500
)

risk_percent = st.sidebar.number_input(
    "İşlem riski (%)",
    min_value=0.1, max_value=2.0, value=0.5, step=0.1
)

risk_amount = balance * risk_percent / 100

st.sidebar.metric("Risk bütçesi", f"${risk_amount:.2f}")

if st.sidebar.button("Analizi yenile", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.title("Piyasa özeti")

a, b, c = st.columns(3)
a.metric("Demo bakiye", f"${balance:,.0f}")
b.metric("İşlem riski", f"{risk_percent:.1f}%")
c.metric("Risk bütçesi", f"${risk_amount:.2f}")

st.caption("Son panel açılışı: " + datetime.now().strftime("%d.%m.%Y %H:%M"))

@st.cache_data(ttl=60)
def load_results():
    return [analyze_market(name, symbol) for name, symbol in MARKETS.items()]

st.markdown("## Piyasa analizi")

results = load_results()

for item in results:
    name = item["market"]

    if item["status"] != "OK":
        st.markdown(f"""
        <div class="market-card">
        <b>{name}</b>
        <div class="wait">WAIT — VERİ ALINAMADI</div>
        <div class="muted">{item.get("error", "Bilinmeyen hata")}</div>
        </div>
        """, unsafe_allow_html=True)
        continue

    direction = item["direction"]
    signal_class = {
        "LONG": "long",
        "SHORT": "short",
        "WAIT": "wait"
    }.get(direction, "wait")

    st.markdown(f"""
    <div class="market-card">
    <div style="display:flex;justify-content:space-between;align-items:center;">
        <div style="font-size:21px;font-weight:800;color:white;">{name}</div>
        <div class="{signal_class}" style="font-size:19px;">{direction}</div>
    </div>
    <div class="price">{item["price"]:.5f}</div>
    <div class="muted">Sinyal uyum puanı: {item["score"]}/100</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**Zaman dilimleri**")

    t1, t2, t3 = st.columns(3)
    t1.metric("5 DAKİKA", item["trend5"])
    t2.metric("15 DAKİKA", item["trend15"])
    t3.metric("1 SAAT", item["trend1"])

    r1, r2 = st.columns(2)
    r1.metric("RSI", f'{item["rsi"]:.2f}')
    r2.metric("Fiyat", f'{item["price"]:.5f}')

    levels = []

    if item.get("support") is not None:
        levels.append({"Seviye": "Destek", "Fiyat": item["support"]})

    if item.get("resistance") is not None:
        levels.append({"Seviye": "Direnç", "Fiyat": item["resistance"]})

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

st.caption(
    "Forex Radar yalnızca analiz sunar. Otomatik emir göndermez. "
    "Sinyal puanı kazanma olasılığı değildir. Haber filtresi henüz aktif değildir."
)
