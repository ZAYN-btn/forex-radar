
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import requests
from datetime import datetime
from xml.etree import ElementTree as ET
from streamlit_autorefresh import st_autorefresh
from forex_engine import MARKETS, analyze_market

# =========================
# SAYFA AYARLARI
# =========================

st.set_page_config(
    page_title="FOREX RADAR",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
.stApp {
    background: #080808;
    color: #ffffff;
}
.block-container {
    max-width: 1400px;
    padding-top: 1.2rem;
    padding-bottom: 3rem;
}
html, body, [class*="css"] {
    color: #ffffff;
}
h1, h2, h3, h4, p, label {
    color: #ffffff !important;
}
[data-testid="stCaptionContainer"] {
    color: #999999 !important;
}
[data-testid="stMetric"] {
    background: #151515;
    border: 1px solid #303030;
    padding: 14px;
    border-radius: 12px;
}
[data-testid="stMetricLabel"] {
    color: #aaaaaa !important;
}
[data-testid="stMetricValue"] {
    color: #ffffff !important;
}
.stButton > button {
    background: #171717 !important;
    color: #ffffff !important;
    border: 1px solid #383838 !important;
    border-radius: 9px !important;
    min-height: 44px;
    width: 100%;
    font-weight: 650 !important;
}
.stButton > button:hover {
    background: #292929 !important;
    border-color: #888888 !important;
    color: #ffffff !important;
}
.stTabs [data-baseweb="tab-list"] {
    background: #111111;
    border: 1px solid #292929;
    border-radius: 10px;
    gap: 4px;
    padding: 5px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    color: #bbbbbb !important;
    border-radius: 7px;
    padding: 10px 15px;
}
.stTabs [aria-selected="true"] {
    background: #303030 !important;
    color: #ffffff !important;
}
.stTabs [data-baseweb="tab-highlight"] {
    background: #ffffff !important;
}
div[data-baseweb="select"] > div {
    background: #171717 !important;
    color: white !important;
    border-color: #444444 !important;
}
.stTextInput input {
    background: #171717 !important;
    color: white !important;
}
hr {
    border-color: #303030 !important;
}
[data-testid="stDataFrame"] {
    border: 1px solid #303030;
    border-radius: 10px;
}
.trade-card {
    background: #141414;
    border: 1px solid #383838;
    border-radius: 16px;
    padding: 22px;
    margin: 10px 0 18px 0;
}
.trade-direction {
    font-size: 42px;
    font-weight: 900;
    margin: 5px 0;
}
.trade-price {
    font-size: 32px;
    font-weight: 850;
    margin: 12px 0 20px 0;
    color: white;
}
.trade-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
}
.trade-item {
    background: #202020;
    border: 1px solid #333333;
    border-radius: 10px;
    padding: 13px;
    min-width: 0;
}
.trade-label {
    color: #999999;
    font-size: 11px;
}
.trade-value {
    color: #ffffff;
    font-size: 18px;
    font-weight: 750;
    margin-top: 5px;
    overflow-wrap: anywhere;
}
.section-heading {
    color: #ffffff;
    font-size: 20px;
    font-weight: 800;
    margin: 20px 0 12px 0;
}
.market-row {
    background: #151515;
    border: 1px solid #303030;
    border-radius: 10px;
    padding: 12px;
    margin-bottom: 8px;
}
.small-muted {
    color: #999999;
    font-size: 12px;
}
@media (max-width: 600px) {
    .block-container {
        padding-left: 0.8rem;
        padding-right: 0.8rem;
    }
    .trade-direction {
        font-size: 36px;
    }
    .trade-price {
        font-size: 27px;
    }
    .trade-value {
        font-size: 16px;
    }
}
</style>
""", unsafe_allow_html=True)

# =========================
# YENİLEME
# =========================

st_autorefresh(interval=300000, key="radar_refresh")

# =========================
# OTURUM VERİLERİ
# =========================

if "selected_market" not in st.session_state:
    st.session_state.selected_market = "EUR/USD"

if "signal_history" not in st.session_state:
    st.session_state.signal_history = []

if "last_signatures" not in st.session_state:
    st.session_state.last_signatures = {}

# =========================
# YARDIMCI FONKSİYONLAR
# =========================

def fmt(value):
    try:
        if value is None or pd.isna(value):
            return "—"
        return f"{float(value):.5f}"
    except (TypeError, ValueError):
        return "—"


def color_for(direction):
    if direction == "LONG":
        return "#35D394"
    if direction == "SHORT":
        return "#FF5C68"
    return "#E8C65A"


def get_market(name, data):
    for item in data:
        if item.get("market") == name:
            return item
    return None


# =========================
# PİYASA ANALİZİ
# =========================

@st.cache_data(ttl=240, show_spinner=False)
def load_results():
    output = []

    for name, symbol in MARKETS.items():
        try:
            result = analyze_market(name, symbol)

            if not isinstance(result, dict):
                raise ValueError("Geçersiz analiz sonucu")

            output.append(result)

        except Exception as error:
            output.append({
                "market": name,
                "direction": "WAIT",
                "status": "ERROR",
                "error": str(error)
            })

    return output


st.markdown("""
<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;">
    <div>
        <div style="font-size:12px;letter-spacing:3px;color:#999;">
            MARKET INTELLIGENCE
        </div>
        <div style="font-size:30px;font-weight:900;color:#ffffff;">
            📡 FOREX RADAR
        </div>
        <div style="font-size:11px;color:#999;">
            TEKNİK ANALİZ • HABERLER • RİSK TAKİBİ
        </div>
    </div>
    <div style="background:#171717;border:1px solid #333;border-radius:8px;padding:9px 13px;color:#ddd;font-size:12px;">
        ANALİZ PANELİ
    </div>
</div>
""", unsafe_allow_html=True)

st.write("")

with st.spinner("Piyasalar analiz ediliyor..."):
    results = load_results()

if not results:
    st.error("Piyasa analizi alınamadı.")
    st.stop()

valid = [
    x for x in results
    if x.get("status") == "OK"
]

# =========================
# SİNYAL GEÇMİŞİ
# =========================

for item in valid:
    name = item.get("market", "")
    signature = (
        item.get("direction"),
        item.get("price"),
        item.get("score")
    )

    if st.session_state.last_signatures.get(name) != signature:
        st.session_state.signal_history.insert(0, {
            "Tarih": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "Piyasa": name,
            "İşlem": item.get("direction"),
            "Fiyat": item.get("price"),
            "Puan": item.get("score", 0)
        })
        st.session_state.last_signatures[name] = signature

st.session_state.signal_history = (
    st.session_state.signal_history[:200]
)

# =========================
# ÜST MENÜ
# =========================

tab_overview, tab_chart, tab_news, tab_history, tab_risk = st.tabs([
    "GENEL BAKIŞ",
    "GRAFİK",
    "HABERLER",
    "SİNYAL GEÇMİŞİ",
    "RİSK"
])

# =========================
# GENEL BAKIŞ
# =========================

with tab_overview:

    st.markdown(
        '<div class="section-heading">PİYASA DURUMU</div>',
        unsafe_allow_html=True
    )

    long_count = sum(x.get("direction") == "LONG" for x in valid)
    short_count = sum(x.get("direction") == "SHORT" for x in valid)
    wait_count = sum(x.get("direction") == "WAIT" for x in results)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("LONG", long_count)

    with c2:
        st.metric("SHORT", short_count)

    with c3:
        st.metric("WAIT", wait_count)

    st.caption(
        "LONG: alış yönü  •  SHORT: satış yönü  •  WAIT: bekle"
    )

    st.markdown(
        '<div class="section-heading">ANA İŞLEM ANALİZİ</div>',
        unsafe_allow_html=True
    )

    market_names = list(MARKETS.keys())

    if st.session_state.selected_market not in market_names:
        st.session_state.selected_market = market_names[0]

    selected = get_market(st.session_state.selected_market, results)

    if selected is None:
        st.warning("Seçili piyasa bulunamadı.")
    elif selected.get("status") != "OK":
        st.error(
            "Bu piyasanın verisi alınamadı: "
            + str(selected.get("error", "Bilinmeyen hata"))
        )
    else:
        direction = selected.get("direction", "WAIT")
        color = color_for(direction)

        if direction == "LONG":
            description = "ALIŞ YÖNLÜ SİNYAL"
        elif direction == "SHORT":
            description = "SATIŞ YÖNLÜ SİNYAL"
        else:
            description = "ŞU AN İŞLEM SİNYALİ YOK"

        st.markdown(f"""
        <div class="trade-card">
            <div style="font-size:13px;color:#999;">
                SEÇİLİ PİYASA
            </div>
            <div style="font-size:22px;font-weight:800;color:white;">
                {selected.get("market", "")}
            </div>
            <div class="trade-direction" style="color:{color};">
                {direction}
            </div>
            <div style="font-size:12px;color:#999;">
                {description}
            </div>
            <div class="trade-price">
                {fmt(selected.get("price"))}
            </div>
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
            st.info("Şu an yeterli işlem koşulu yok. Beklemede kal.")

        st.caption(
            "Sinyal puanı başarı olasılığı değildir. "
            "Bu panel otomatik emir göndermez."
        )

    st.markdown(
        '<div class="section-heading">DİĞER PİYASALAR</div>',
        unsafe_allow_html=True
    )

    st.caption("Bir piyasayı seçerek ana işlem kartında görüntüleyebilirsin.")

    other = [
        x for x in results
        if x.get("market") != st.session_state.selected_market
    ]

    for i in range(0, len(other), 2):
        cols = st.columns(2)

        for j, item in enumerate(other[i:i+2]):
            with cols[j]:
                name = item.get("market", "")
                direction = item.get("direction", "WAIT")
                color = color_for(direction)

                if direction == "LONG":
                    icon = "🟢"
                elif direction == "SHORT":
                    icon = "🔴"
                else:
                    icon = "🟡"

                st.markdown(f"""
                <div class="market-row">
                    <div style="font-weight:800;color:#fff;">
                        {icon} {name}
                    </div>
                    <div style="color:{color};font-weight:800;margin-top:5px;">
                        {direction}
                    </div>
                    <div style="font-size:12px;color:#aaa;margin-top:4px;">
                        Fiyat: {fmt(item.get("price"))}
                        &nbsp; | &nbsp;
                        Puan: {item.get("score", 0)}/100
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if st.button("PİYASAYI GÖR", key="select_" + name):
                    st.session_state.selected_market = name
                    st.rerun()

# =========================
# GRAFİK
# =========================

with tab_chart:

    st.markdown(
        '<div class="section-heading">TEKNİK GRAFİK ANALİZİ</div>',
        unsafe_allow_html=True
    )

    market_names = list(MARKETS.keys())

    chart_market = st.selectbox(
        "Piyasa seç",
        market_names,
        index=market_names.index(st.session_state.selected_market),
        key="chart_pair"
    )

    timeframe = st.selectbox(
        "Zaman dilimi",
        ["5m", "15m", "30m", "1h", "1d"],
        index=1
    )

    period_map = {
        "5m": "5d",
        "15m": "5d",
        "30m": "1mo",
        "1h": "1mo",
        "1d": "6mo"
    }

    try:
        chart_data = yf.Ticker(
            MARKETS[chart_market]
        ).history(
            period=period_map[timeframe],
            interval=timeframe
        )

        if chart_data.empty:
            st.warning("Bu piyasa için grafik verisi bulunamadı.")
        else:
            chart_data["EMA20"] = (
                chart_data["Close"].ewm(span=20, adjust=False).mean()
            )
            chart_data["EMA50"] = (
                chart_data["Close"].ewm(span=50, adjust=False).mean()
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
                paper_bgcolor="#080808",
                plot_bgcolor="#111111",
                font_color="white",
                height=520,
                xaxis_rangeslider_visible=False,
                margin=dict(l=10, r=10, t=30, b=10)
            )

            st.plotly_chart(fig, use_container_width=True)

    except Exception as error:
        st.error("Grafik yüklenemedi: " + str(error))

# =========================
# HABERLER
# =========================

with tab_news:

    st.markdown(
        '<div class="section-heading">EKONOMİK TAKVİM VE HABERLER</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "Forex Factory XML takvimi. Kaynakta veri bulunmaması "
        "veya bağlantı hatası yaşanması mümkündür."
    )

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
                "Haber": event.findtext("title", ""),
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
        st.warning("Takvim alınamadı: " + str(error))

# =========================
# SİNYAL GEÇMİŞİ
# =========================

with tab_history:

    st.markdown(
        '<div class="section-heading">SİNYAL GEÇMİŞİ</div>',
        unsafe_allow_html=True
    )

    history = st.session_state.signal_history

    if history:
        st.dataframe(
            pd.DataFrame(history),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Henüz sinyal kaydı bulunmuyor.")

    st.caption(
        "Bu kayıtlar açık oturum boyunca saklanır. "
        "Gerçekleşmiş işlem sonucu veya kâr oranı değildir."
    )

# =========================
# RİSK
# =========================

with tab_risk:

    st.markdown(
        '<div class="section-heading">RİSK VE OYNAKLIK ANALİZİ</div>',
        unsafe_allow_html=True
    )

    risk_market = st.selectbox(
        "Risk analizi yapılacak piyasa",
        list(MARKETS.keys()),
        index=list(MARKETS.keys()).index(
            st.session_state.selected_market
        ),
        key="risk_pair"
    )

    risk_data = get_market(risk_market, results)

    if risk_data and risk_data.get("status") == "OK":

        st.write("**Piyasa:**", risk_market)
        st.write("**İşlem yönü:**", risk_data.get("direction"))
        st.write("**Güncel fiyat:**", fmt(risk_data.get("price")))
        st.write("**ATR:**", fmt(risk_data.get("atr")))
        st.write("**Destek:**", fmt(risk_data.get("support")))
        st.write("**Direnç:**", fmt(risk_data.get("resistance")))

        try:
            atr = float(risk_data.get("atr"))
            price = float(risk_data.get("price"))

            if atr > 0 and price > 0:
                st.metric(
                    "ATR / FİYAT",
                    f"%{(atr / price) * 100:.3f}"
                )
        except (TypeError, ValueError, ZeroDivisionError):
            st.info("Oynaklık oranı hesaplanamadı.")

    else:
        st.warning("Bu piyasa için risk verisi alınamadı.")

    st.info(
        "ATR fiyat hareketliliğini ölçer. Yüksek ATR daha geniş "
        "fiyat hareketleri anlamına gelebilir."
    )

    st.warning(
        "Bu sistem otomatik emir açmaz. Stop-loss ve hedef seviyeleri "
        "analiz referansıdır; garanti sonuç değildir."
    )

# =========================
# ALT BİLGİ
# =========================

st.divider()

st.caption(
    "FOREX RADAR | Analiz amaçlıdır. "
    "Veriler Yahoo Finance üzerinden gelebilir ve gecikmeli olabilir. "
    "Sinyaller yatırım tavsiyesi veya garanti kazanç değildir."
)
