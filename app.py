
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import requests
from datetime import datetime
from xml.etree import ElementTree as ET
from streamlit_autorefresh import st_autorefresh
from forex_engine import MARKETS, analyze_market

st.set_page_config(
    page_title="FOREX RADAR",
    page_icon="📈",
    layout="wide"
)

# ---------------- CSS ----------------

st.markdown("""
<style>
.stApp {
    background: #090909;
    color: #f5f5f5;
}
.block-container {
    max-width: 1250px;
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}
h1, h2, h3, p, label, span {
    color: #f5f5f5;
}
.stCaption, [data-testid="stCaptionContainer"] {
    color: #999 !important;
}
div[data-testid="stMetric"] {
    background: #151515;
    border: 1px solid #333;
    padding: 15px;
    border-radius: 12px;
}
div[data-testid="stMetricLabel"] {
    color: #aaa !important;
}
div[data-testid="stMetricValue"] {
    color: white !important;
}
.stButton > button {
    background: #191919 !important;
    color: #ffffff !important;
    border: 1px solid #444 !important;
    border-radius: 10px !important;
    min-height: 46px;
    font-weight: 650 !important;
    width: 100%;
}
.stButton > button:hover {
    background: #303030 !important;
    border-color: #888 !important;
    color: white !important;
}
.stSelectbox div[data-baseweb="select"] > div {
    background: #191919 !important;
    color: white !important;
    border-color: #444 !important;
}
.stTabs [data-baseweb="tab"] {
    color: #bbb !important;
}
.stTabs [aria-selected="true"] {
    color: white !important;
}
.trade-card {
    background: #141414;
    border: 1px solid #383838;
    border-radius: 18px;
    padding: 23px;
    margin: 12px 0 20px 0;
}
.trade-name {
    color: #aaa;
    font-size: 15px;
}
.trade-direction {
    font-size: 42px;
    font-weight: 900;
    margin: 5px 0;
}
.trade-price {
    color: white;
    font-size: 32px;
    font-weight: 800;
    margin: 10px 0 22px 0;
}
.trade-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
}
.trade-item {
    background: #202020;
    border: 1px solid #333;
    border-radius: 10px;
    padding: 13px;
    min-width: 0;
}
.trade-label {
    color: #aaa;
    font-size: 11px;
}
.trade-value {
    color: white;
    font-size: 18px;
    font-weight: 750;
    margin-top: 5px;
    overflow-wrap: anywhere;
}
.section-heading {
    font-size: 21px;
    font-weight: 800;
    margin-top: 28px;
    margin-bottom: 12px;
}
.market-button {
    color: white;
}
hr {
    border-color: #333 !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------- AUTO REFRESH ----------------

st_autorefresh(interval=300000, key="auto_refresh")

# ---------------- SESSION HISTORY ----------------

if "signal_history" not in st.session_state:
    st.session_state.signal_history = []

if "last_saved_signals" not in st.session_state:
    st.session_state.last_saved_signals = {}

# ---------------- DATA ----------------

@st.cache_data(ttl=240, show_spinner=False)
def load_market_data():
    output = []

    for name, symbol in MARKETS.items():
        try:
            result = analyze_market(name, symbol)
            if not isinstance(result, dict):
                raise ValueError("Analiz sonucu geçersiz")
            output.append(result)

        except Exception as error:
            output.append({
                "market": name,
                "direction": "WAIT",
                "status": "ERROR",
                "error": str(error)
            })

    return output

with st.spinner("Piyasalar analiz ediliyor..."):
    results = load_market_data()

if not results:
    st.error("Piyasa verisi alınamadı.")
    st.stop()

valid_results = [
    x for x in results
    if x.get("status") == "OK"
]

# ---------------- HISTORY SAVE ----------------

for item in valid_results:
    name = item.get("market", "")
    direction = item.get("direction", "WAIT")
    price = item.get("price")

    signature = (direction, price)
    previous = st.session_state.last_saved_signals.get(name)

    if signature != previous:
        st.session_state.signal_history.insert(0, {
            "Tarih": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "Piyasa": name,
            "İşlem": direction,
            "Fiyat": price,
            "Puan": item.get("score", 0)
        })
        st.session_state.last_saved_signals[name] = signature

st.session_state.signal_history = (
    st.session_state.signal_history[:200]
)

# ---------------- HELPERS ----------------

def fmt(value):
    if value is None:
        return "—"
    try:
        if pd.isna(value):
            return "—"
        return f"{float(value):.5f}"
    except (TypeError, ValueError):
        return "—"

def get_result(name):
    for item in results:
        if item.get("market") == name:
            return item
    return None

# ---------------- HEADER ----------------

st.markdown("# FOREX RADAR")
st.caption("Forex analiz ve işlem sinyali paneli")

left, right = st.columns([3, 1])

with left:
    st.caption("Teknik analiz • Çoklu zaman dilimi • Risk takibi")

with right:
    st.caption("Son yenileme: " + datetime.now().strftime("%H:%M:%S"))

st.divider()

# ---------------- SELECTED MARKET ----------------

market_names = list(MARKETS.keys())

if "selected_market" not in st.session_state:
    st.session_state.selected_market = (
        "EUR/USD" if "EUR/USD" in market_names else market_names[0]
    )

selected = get_result(st.session_state.selected_market)

if selected is None:
    selected = results[0]
    st.session_state.selected_market = selected.get("market")

st.markdown(
    '<div class="section-heading">ANA İŞLEM ANALİZİ</div>',
    unsafe_allow_html=True
)

if selected.get("status") != "OK":
    st.error(
        "Bu paritenin fiyat verisi alınamadı. "
        + str(selected.get("error", "Veri sağlayıcı hatası"))
    )
    st.info("Başka bir parite seçerek analizini kontrol edebilirsin.")

else:
    direction = selected.get("direction", "WAIT")

    if direction == "LONG":
        color = "#22c77a"
        description = "ALIŞ YÖNLÜ SİNYAL"
    elif direction == "SHORT":
        color = "#ff5555"
        description = "SATIŞ YÖNLÜ SİNYAL"
    else:
        color = "#bbbbbb"
        description = "ŞU AN İŞLEM SİNYALİ YOK"

    st.markdown(f"""
    <div class="trade-card">
        <div class="trade-name">{selected.get("market", "")}</div>
        <div class="trade-direction" style="color:{color}">
            {direction}
        </div>
        <div style="color:#aaa;font-size:13px">{description}</div>
        <div class="trade-price">{fmt(selected.get("price"))}</div>
        <div class="trade-grid">
            <div class="trade-item">
                <div class="trade-label">GİRİŞ FİYATI</div>
                <div class="trade-value">{fmt(selected.get("price"))}</div>
            </div>
            <div class="trade-item">
                <div class="trade-label">SİNYAL PUANI</div>
                <div class="trade-value">{selected.get("score", 0)}/100</div>
            </div>
            <div class="trade-item">
                <div class="trade-label">STOP LOSS</div>
                <div class="trade-value">{fmt(selected.get("stop_loss"))}</div>
            </div>
            <div class="trade-item">
                <div class="trade-label">HEDEF 1</div>
                <div class="trade-value">{fmt(selected.get("tp1"))}</div>
            </div>
            <div class="trade-item">
                <div class="trade-label">HEDEF 2</div>
                <div class="trade-value">{fmt(selected.get("tp2"))}</div>
            </div>
            <div class="trade-item">
                <div class="trade-label">RSI</div>
                <div class="trade-value">{fmt(selected.get("rsi"))}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if direction == "WAIT":
        st.info("Şimdilik bekle. Sistem yeterli LONG veya SHORT koşulu bulamadı.")

    st.caption(
        "LONG = alış | SHORT = satış | WAIT = bekle. "
        "Sinyal puanı kazanma ihtimali değildir."
    )

# ---------------- SUMMARY ----------------

st.markdown(
    '<div class="section-heading">PİYASA ÖZETİ</div>',
    unsafe_allow_html=True
)

long_count = sum(
    x.get("direction") == "LONG" for x in valid_results
)
short_count = sum(
    x.get("direction") == "SHORT" for x in valid_results
)
wait_count = sum(
    x.get("direction") == "WAIT" for x in results
)

a, b, c = st.columns(3)

with a:
    st.metric("ALIŞ SİNYALİ", long_count)

with b:
    st.metric("SATIŞ SİNYALİ", short_count)

with c:
    st.metric("BEKLEMEDE", wait_count)

# ---------------- OTHER MARKETS ----------------

st.markdown(
    '<div class="section-heading">DİĞER PİYASALAR</div>',
    unsafe_allow_html=True
)
st.caption("Bir pariteye dokunarak ana analiz kartını değiştirebilirsin.")

other_results = [
    x for x in results
    if x.get("market") != st.session_state.selected_market
]

for i in range(0, len(other_results), 2):
    cols = st.columns(2)

    for j, item in enumerate(other_results[i:i+2]):
        with cols[j]:
            name = item.get("market", "")
            direction = item.get("direction", "WAIT")

            if direction == "LONG":
                mark = "🟢"
            elif direction == "SHORT":
                mark = "🔴"
            else:
                mark = "⚪"

            price_text = fmt(item.get("price"))
            score = item.get("score", 0)

            label = (
                f"{mark} {name}  |  {direction}\n"
                f"{price_text}  •  {score}/100"
            )

            if st.button(label, key="pair_" + name):
                st.session_state.selected_market = name
                st.rerun()

# ---------------- TABS ----------------

st.divider()

tab_chart, tab_calendar, tab_history, tab_risk = st.tabs([
    "GRAFİK",
    "EKONOMİK TAKVİM",
    "SİNYAL GEÇMİŞİ",
    "RİSK ANALİZİ"
])

# ---------------- CHART ----------------

with tab_chart:
    st.subheader("Fiyat grafiği")

    chart_market = st.selectbox(
        "Parite seç",
        market_names,
        index=market_names.index(st.session_state.selected_market)
    )

    try:
        chart_data = yf.Ticker(
            MARKETS[chart_market]
        ).history(period="5d", interval="15m")

        if chart_data.empty:
            st.warning("Grafik verisi bulunamadı.")
        else:
            chart_data["EMA20"] = (
                chart_data["Close"].ewm(span=20).mean()
            )
            chart_data["EMA50"] = (
                chart_data["Close"].ewm(span=50).mean()
            )

            fig = go.Figure()

            fig.add_trace(go.Candlestick(
                x=chart_data.index,
                open=chart_data["Open"],
                high=chart_data["High"],
                low=chart_data["Low"],
                close=chart_data["Close"],
                name="Fiyat"
            ))

            fig.add_trace(go.Scatter(
                x=chart_data.index,
                y=chart_data["EMA20"],
                name="EMA 20"
            ))

            fig.add_trace(go.Scatter(
                x=chart_data.index,
                y=chart_data["EMA50"],
                name="EMA 50"
            ))

            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#090909",
                plot_bgcolor="#090909",
                height=450,
                xaxis_rangeslider_visible=False
            )

            st.plotly_chart(fig, use_container_width=True)

    except Exception as error:
        st.warning("Grafik yüklenemedi: " + str(error))

# ---------------- ECONOMIC CALENDAR ----------------

with tab_calendar:
    st.subheader("Ekonomik takvim")
    st.caption("Takvim kaynağı: Forex Factory XML")

    try:
        response = requests.get(
            "https://nfs.faireconomy.media/ff_calendar_thisweek.xml",
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        response.raise_for_status()

        root = ET.fromstring(response.content)
        events = []

        for event in root.findall(".//event"):
            events.append({
                "Tarih": event.findtext("date", ""),
                "Saat": event.findtext("time", ""),
                "Ülke": event.findtext("country", ""),
                "Etkinlik": event.findtext("title", ""),
                "Önem": event.findtext("impact", ""),
                "Tahmin": event.findtext("forecast", ""),
                "Önceki": event.findtext("previous", "")
            })

        if events:
            st.dataframe(
                pd.DataFrame(events),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Takvimde etkinlik bulunamadı.")

    except Exception as error:
        st.warning("Ekonomik takvim yüklenemedi: " + str(error))

# ---------------- HISTORY ----------------

with tab_history:
    st.subheader("Sinyal geçmişi")

    history = st.session_state.signal_history

    if history:
        st.dataframe(
            pd.DataFrame(history),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Henüz sinyal kaydı oluşmadı.")

    st.caption(
        "Geçmiş yalnızca bu açık oturum boyunca saklanır. "
        "Gerçekleşmiş kâr/zarar performansı değildir."
    )

# ---------------- RISK ----------------

with tab_risk:
    st.subheader("Risk analizi")

    if selected.get("status") == "OK":
        atr = selected.get("atr")
        price = selected.get("price")

        st.write("**Piyasa:**", selected.get("market"))
        st.write("**İşlem yönü:**", selected.get("direction"))
        st.write("**Fiyat:**", fmt(price))
        st.write("**ATR:**", fmt(atr))

        try:
            if atr and price:
                percentage = float(atr) / float(price) * 100
                st.metric("ATR / Fiyat", f"%{percentage:.3f}")
        except (TypeError, ValueError, ZeroDivisionError):
            st.info("Oynaklık oranı hesaplanamadı.")

    else:
        st.warning("Risk analizi için geçerli piyasa verisi bulunamadı.")

    st.info(
        "ATR fiyat hareketliliğini ölçer. Yüksek ATR daha geniş fiyat "
        "hareketleri anlamına gelebilir."
    )

    st.warning(
        "Bu sistem otomatik emir açmaz. LONG ve SHORT sinyalleri "
        "garantili kazanç değildir."
    )

# ---------------- FOOTER ----------------

st.divider()
st.caption(
    "FOREX RADAR • Analiz amaçlıdır. "
    "Fiyat verileri Yahoo Finance üzerinden gelebilir ve gecikmeli olabilir."
)
