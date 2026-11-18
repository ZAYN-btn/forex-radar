
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(
    page_title="FOREX RADAR",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =====================================================
# AYARLAR
# =====================================================

MARKETS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "USD/CHF": "CHF=X",
    "USD/CAD": "CAD=X",
    "AUD/USD": "AUDUSD=X",
    "NZD/USD": "NZDUSD=X",
    "EUR/GBP": "EURGBP=X",
    "EUR/JPY": "EURJPY=X",
    "EUR/CHF": "EURCHF=X",
    "GBP/JPY": "GBPJPY=X",
    "GBP/CHF": "GBPCHF=X",
    "AUD/JPY": "AUDJPY=X",
    "EUR/AUD": "EURAUD=X",
    "GBP/AUD": "GBPAUD=X",
    "AUD/NZD": "AUDNZD=X",
    "CAD/JPY": "CADJPY=X",
    "XAU/USD": "XAUUSD=X",
    "XAG/USD": "XAGUSD=X"
}

# =====================================================
# BEYAZ ARAYÜZ
# =====================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background: #FFFFFF !important;
    color: #171717 !important;
    font-family: 'Inter', sans-serif;
}

[data-testid="stHeader"] {
    background: #FFFFFF !important;
}

[data-testid="stSidebar"] {
    background: #FFFFFF !important;
}

.block-container {
    max-width: 1450px;
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}

h1, h2, h3, p, label {
    color: #171717;
}

.brand {
    font-size: 23px;
    font-weight: 800;
    letter-spacing: 2px;
    color: #171717;
}

.brand span {
    color: #888888;
}

.topline {
    border-bottom: 1px solid #EAEAEA;
    margin-top: 15px;
    margin-bottom: 22px;
}

.section-label {
    color: #777777;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
    margin: 25px 0 13px 0;
}

.metric-card {
    background: #FFFFFF;
    border: 1px solid #E9E9E9;
    border-radius: 9px;
    padding: 17px 19px;
    min-height: 90px;
}

.metric-title {
    font-size: 10px;
    color: #777777;
    letter-spacing: 1.5px;
    font-weight: 700;
}

.metric-number {
    font-size: 27px;
    font-weight: 800;
    margin-top: 8px;
}

.green { color: #16834A !important; }
.red { color: #D13C3C !important; }
.yellow { color: #9A751B !important; }
.muted { color: #777777 !important; }

.main-card {
    background: #FFFFFF;
    border: 1px solid #E8E8E8;
    border-radius: 12px;
    padding: 22px;
    margin-top: 10px;
}

.card-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
}

.pair-name {
    font-size: 28px;
    font-weight: 800;
    letter-spacing: -1px;
}

.price {
    color: #777777;
    font-size: 14px;
    margin-top: 5px;
}

.signal {
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 1px;
    padding: 9px 15px;
    border-radius: 5px;
}

.signal-long {
    background: #F0F8F2;
    color: #16834A;
    border: 1px solid #D5EBDD;
}

.signal-short {
    background: #FCF1F1;
    color: #D13C3C;
    border: 1px solid #F2DADA;
}

.signal-wait {
    background: #F4F4F4;
    color: #777777;
    border: 1px solid #E6E6E6;
}

.score {
    font-size: 30px;
    font-weight: 800;
    margin-top: 8px;
}

.data-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    margin-top: 20px;
}

.data-box {
    background: #F7F8FA;
    border: 1px solid #ECEEF0;
    padding: 14px;
    border-radius: 7px;
}

.data-title {
    font-size: 10px;
    color: #777777;
    letter-spacing: 1px;
    margin-bottom: 9px;
}

.data-value {
    font-size: 16px;
    font-weight: 700;
    color: #171717;
}

.market-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #FFFFFF;
    border: 1px solid #EAEAEA;
    border-radius: 7px;
    padding: 14px 16px;
    margin-bottom: 8px;
}

.market-name {
    font-size: 13px;
    font-weight: 700;
    color: #171717;
}

.market-price {
    font-size: 12px;
    color: #777777;
    margin-top: 5px;
}

.market-signal {
    font-size: 11px;
    font-weight: 800;
}

.info-card {
    background: #FFFFFF;
    border: 1px solid #EAEAEA;
    border-radius: 9px;
    padding: 20px;
    margin-bottom: 12px;
}

div[data-testid="stSelectbox"] label {
    color: #555555 !important;
}

div[data-testid="stSelectbox"] > div > div {
    background: #FFFFFF !important;
    border-color: #E5E5E5 !important;
}

div[data-testid="stButton"] button {
    background: #FFFFFF;
    color: #171717;
    border: 1px solid #E5E5E5;
    border-radius: 7px;
    font-weight: 600;
}

div[data-testid="stButton"] button:hover {
    border-color: #16834A;
    color: #16834A;
}

hr {
    border-color: #EAEAEA !important;
}

@media(max-width: 700px) {
    .block-container {
        padding-left: 12px;
        padding-right: 12px;
    }

    .pair-name {
        font-size: 23px;
    }

    .data-grid {
        grid-template-columns: repeat(2, 1fr);
    }

    .metric-number {
        font-size: 23px;
    }
}
</style>
""", unsafe_allow_html=True)


# =====================================================
# HESAPLAMA FONKSİYONLARI
# =====================================================

def price_format(value):
    if pd.isna(value):
        return "—"

    if abs(value) >= 100:
        return f"{value:,.3f}"

    return f"{value:.5f}"


def signal_class(signal):
    if signal == "LONG":
        return "signal-long"
    elif signal == "SHORT":
        return "signal-short"

    return "signal-wait"


def signal_color(signal):
    if signal == "LONG":
        return "green"
    elif signal == "SHORT":
        return "red"

    return "muted"


def calculate_indicators(df):

    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    ema20 = close.ewm(
        span=20,
        adjust=False
    ).mean()

    ema50 = close.ewm(
        span=50,
        adjust=False
    ).mean()

    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1/14,
        adjust=False,
        min_periods=14
    ).mean()

    avg_loss = loss.ewm(
        alpha=1/14,
        adjust=False,
        min_periods=14
    ).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    rsi = 100 - (100 / (1 + rs))

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)

    atr = tr.ewm(
        alpha=1/14,
        adjust=False,
        min_periods=14
    ).mean()

    return ema20, ema50, rsi, atr


# =====================================================
# PARİTE ANALİZİ
# =====================================================

def analyze_market(name, symbol):

    try:

        df = yf.Ticker(symbol).history(
            period="5d",
            interval="15m",
            auto_adjust=True
        )

        if df is None or len(df) < 60:
            return name, {
                "available": False,
                "symbol": symbol
            }

        df = df.dropna()

        if len(df) < 30:
            return name, {
                "available": False,
                "symbol": symbol
            }

        ema20, ema50, rsi, atr = calculate_indicators(df)

        price = float(df["Close"].iloc[-1])
        e20 = float(ema20.iloc[-1])
        e50 = float(ema50.iloc[-1])
        current_rsi = float(rsi.iloc[-1])
        current_atr = float(atr.iloc[-1])

        if not all(np.isfinite(x) for x in [
            price, e20, e50, current_rsi, current_atr
        ]) or current_atr <= 0:

            return name, {
                "available": False,
                "symbol": symbol
            }

        # Puanlama

        score = 50

        if e20 > e50:
            score += 20
        else:
            score -= 20

        if price > e20:
            score += 15
        else:
            score -= 15

        if current_rsi > 50:
            score += 15
        else:
            score -= 15

        score = max(0, min(100, score))

        if score >= 65:
            signal = "LONG"

        elif score <= 35:
            signal = "SHORT"

        else:
            signal = "WAIT"

        # ATR STOP VE HEDEFLER

        entry = price

        if signal == "LONG":

            stop = entry - (current_atr * 1.5)

            risk_distance = entry - stop

            tp1 = entry + risk_distance
            tp2 = entry + (risk_distance * 2)
            tp3 = entry + (risk_distance * 3)

        elif signal == "SHORT":

            stop = entry + (current_atr * 1.5)

            risk_distance = stop - entry

            tp1 = entry - risk_distance
            tp2 = entry - (risk_distance * 2)
            tp3 = entry - (risk_distance * 3)

        else:

            stop = None
            tp1 = None
            tp2 = None
            tp3 = None

        return name, {
            "available": True,
            "symbol": symbol,
            "df": df,
            "price": price,
            "ema20": e20,
            "ema50": e50,
            "rsi": current_rsi,
            "atr": current_atr,
            "score": score,
            "signal": signal,
            "entry": entry,
            "stop": stop,
            "tp1": tp1,
            "tp2": tp2,
            "tp3": tp3,
            "updated": datetime.now()
        }

    except Exception:

        return name, {
            "available": False,
            "symbol": symbol
        }


@st.cache_data(ttl=180, show_spinner=False)
def get_market_data():

    results = {}

    with ThreadPoolExecutor(max_workers=6) as executor:

        futures = {
            executor.submit(
                analyze_market,
                name,
                symbol
            ): name

            for name, symbol in MARKETS.items()
        }

        for future in as_completed(futures):

            name, result = future.result()

            results[name] = result

    return results


# =====================================================
# ÜST BÖLÜM
# =====================================================

st.markdown("""
<div class="brand">FOREX <span>RADAR</span></div>
<div class="topline"></div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([5, 1])

with col1:
    st.caption("MARKET ANALYSIS TERMINAL")

with col2:
    if st.button("↻ Yenile", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


with st.spinner("Piyasalar analiz ediliyor..."):
    data = get_market_data()


# =====================================================
# SİNYAL SAYILARI
# =====================================================

valid_data = {
    name: item
    for name, item in data.items()
    if item.get("available")
}

long_count = sum(
    item["signal"] == "LONG"
    for item in valid_data.values()
)

short_count = sum(
    item["signal"] == "SHORT"
    for item in valid_data.values()
)

wait_count = sum(
    item["signal"] == "WAIT"
    for item in valid_data.values()
)

st.markdown(
    '<div class="section-label">PİYASA ÖZETİ</div>',
    unsafe_allow_html=True
)

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">LONG</div>
        <div class="metric-number green">{long_count:02d}</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">SHORT</div>
        <div class="metric-number red">{short_count:02d}</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">BEKLE</div>
        <div class="metric-number muted">{wait_count:02d}</div>
    </div>
    """, unsafe_allow_html=True)


# =====================================================
# TÜM PARİTELER
# =====================================================

st.markdown(
    '<div class="section-label">TÜM PARİTELER</div>',
    unsafe_allow_html=True
)

rows = []

for name in MARKETS:

    item = data.get(name, {})

    if item.get("available"):

        rows.append({
            "PARİTE": name,
            "FİYAT": price_format(item["price"]),
            "SİNYAL": item["signal"],
            "SKOR": f"{item['score']}/100",
            "RSI": round(item["rsi"], 1),
            "STOP LOSS": (
                price_format(item["stop"])
                if item["stop"] is not None else "—"
            ),
            "TP1": (
                price_format(item["tp1"])
                if item["tp1"] is not None else "—"
            ),
            "TP2": (
                price_format(item["tp2"])
                if item["tp2"] is not None else "—"
            ),
            "TP3": (
                price_format(item["tp3"])
                if item["tp3"] is not None else "—"
            )
        })

    else:

        rows.append({
            "PARİTE": name,
            "FİYAT": "—",
            "SİNYAL": "VERİ YOK",
            "SKOR": "—",
            "RSI": "—",
            "STOP LOSS": "—",
            "TP1": "—",
            "TP2": "—",
            "TP3": "—"
        })


market_df = pd.DataFrame(rows)

st.dataframe(
    market_df,
    use_container_width=True,
    hide_index=True,
    height=650
)

st.caption(
    f"{len(valid_data)} / {len(MARKETS)} paritenin verisi başarıyla alındı."
)


# =====================================================
# GRAFİK SEÇİMİ
# =====================================================

st.markdown(
    '<div class="section-label">SEÇİLİ PARİTE</div>',
    unsafe_allow_html=True
)

selected = st.selectbox(
    "Grafiğini ve işlem seviyelerini görüntüle",
    list(MARKETS.keys()),
    index=0
)

item = data.get(selected, {})


if item.get("available"):

    signal = item["signal"]

    st.markdown(f"""
    <div class="main-card">

        <div class="card-top">

            <div>
                <div class="pair-name">{selected}</div>
                <div class="price">
                    {price_format(item['price'])}
                </div>
            </div>

            <div class="signal {signal_class(signal)}">
                {signal}
            </div>

        </div>

        <div style="margin-top:22px">

            <div class="metric-title">
                ANALİZ SKORU
            </div>

            <div class="score">
                {item['score']}
                <span style="font-size:14px;color:#777">
                    / 100
                </span>
            </div>

            <div style="
                height:5px;
                background:#EEEEEE;
                border-radius:5px;
                margin-top:10px;
            ">
                <div style="
                    height:5px;
                    width:{item['score']}%;
                    background:#16834A;
                    border-radius:5px;
                "></div>
            </div>

        </div>

    </div>
    """, unsafe_allow_html=True)

    # GRAFİK

    df = item["df"]

    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="Fiyat",
        increasing_line_color="#16834A",
        decreasing_line_color="#D13C3C"
    ))

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["Close"].ewm(span=20).mean(),
        name="EMA 20",
        line=dict(color="#3286D8", width=1.5)
    ))

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["Close"].ewm(span=50).mean(),
        name="EMA 50",
        line=dict(color="#D99A35", width=1.5)
    ))

    # İşlem seviyeleri

    if signal in ["LONG", "SHORT"]:

        levels = [
            ("ENTRY", item["entry"], "#3286D8"),
            ("STOP LOSS", item["stop"], "#D13C3C"),
            ("TP1", item["tp1"], "#16834A"),
            ("TP2", item["tp2"], "#16834A"),
            ("TP3", item["tp3"], "#16834A")
        ]

        for label, value, color in levels:

            fig.add_hline(
                y=value,
                line_dash="dot",
                line_color=color,
                annotation_text=label,
                annotation_position="right"
            )

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(
            family="Inter",
            color="#333333"
        ),
        height=430,
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=55, t=20, b=10),
        legend=dict(
            orientation="h",
            y=1.08,
            x=0
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor="#EEEEEE"
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#EEEEEE"
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displayModeBar": False,
            "responsive": True
        }
    )

    # İŞLEM SEVİYELERİ

    st.markdown(
        '<div class="section-label">İŞLEM SEVİYELERİ</div>',
        unsafe_allow_html=True
    )

    if signal in ["LONG", "SHORT"]:

        levels = [
            ("GİRİŞ", item["entry"], "muted"),
            ("STOP LOSS", item["stop"], "red"),
            ("TAKE PROFIT 1", item["tp1"], "green"),
            ("TAKE PROFIT 2", item["tp2"], "green"),
            ("TAKE PROFIT 3", item["tp3"], "green")
        ]

        cols = st.columns(3)

        for index, (label, value, color) in enumerate(levels):

            with cols[index % 3]:

                st.markdown(f"""
                <div class="data-box">
                    <div class="data-title">{label}</div>
                    <div class="data-value {color}">
                        {price_format(value)}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown(
            '<div class="section-label">TEKNİK GÖSTERGELER</div>',
            unsafe_allow_html=True
        )

        a, b, c = st.columns(3)

        a.metric("RSI", f"{item['rsi']:.1f}")
        b.metric("EMA 20", price_format(item["ema20"]))
        c.metric("EMA 50", price_format(item["ema50"]))

        st.caption(
            "Stop mesafesi 1.5 ATR olarak hesaplanmıştır. "
            "TP1 = 1R, TP2 = 2R, TP3 = 3R."
        )

    else:

        st.info(
            "Şu anda işlem yönü için yeterli sinyal koşulu oluşmadı. "
            "Bu nedenle aktif giriş, stop ve hedef seviyesi üretilmedi."
        )

        a, b, c = st.columns(3)

        a.metric("RSI", f"{item['rsi']:.1f}")
        b.metric("EMA 20", price_format(item["ema20"]))
        c.metric("EMA 50", price_format(item["ema50"]))

else:

    st.warning(
        f"{selected} için şu anda veri alınamıyor. "
        "Başka bir parite seçebilir veya daha sonra tekrar deneyebilirsin."
    )


# =====================================================
# HABERLER
# =====================================================

with st.expander("PİYASA HABERLERİ"):

    try:

        response = requests.get(
            "https://nfs.faireconomy.media/ff_calendar_thisweek.xml",
            timeout=12,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        response.raise_for_status()

        root = ET.fromstring(response.content)

        events = root.findall(".//event")

        for event in events[:30]:

            title = event.findtext(
                "title",
                "Başlıksız haber"
            )

            country = event.findtext("country", "")
            date = event.findtext("date", "")
            time = event.findtext("time", "")
            impact = event.findtext("impact", "Bilinmiyor")

            forecast = event.findtext("forecast", "-")
            previous = event.findtext("previous", "-")

            st.markdown(f"""
            <div class="info-card">
                <b>{title}</b>
                <div class="market-price">
                    {country} · {date} {time}
                </div>
                <div class="market-price">
                    Önem: {impact} · Tahmin: {forecast}
                    · Önceki: {previous}
                </div>
            </div>
            """, unsafe_allow_html=True)

    except Exception:

        st.warning("Haber akışı şu anda alınamıyor.")


# =====================================================
# ALT BİLGİ
# =====================================================

st.markdown('<div class="topline"></div>', unsafe_allow_html=True)

st.markdown("""
<div style="
    text-align:center;
    color:#888888;
    font-size:10px;
    letter-spacing:1px;
">
    FOREX RADAR · MARKET ANALYSIS TERMINAL
    <br><br>
    Teknik analiz bilgilendirme amaçlıdır.
    İşlem garantisi veya yatırım tavsiyesi değildir.
</div>
""", unsafe_allow_html=True)

st.caption(
    "Son veri kontrolü: " + datetime.now().strftime("%d.%m.%Y %H:%M:%S")
)
