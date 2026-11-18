
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

st.set_page_config(
    page_title="FOREX RADAR",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------- TASARIM --------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background: #08090b !important;
    color: #f5f5f5 !important;
    font-family: 'Inter', sans-serif;
}

[data-testid="stHeader"] {
    background: #08090b;
}

[data-testid="stSidebar"] {
    background: #08090b;
}

.block-container {
    max-width: 1450px;
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}

h1, h2, h3, p, label {
    color: #f5f5f5;
}

.brand {
    font-size: 23px;
    font-weight: 800;
    letter-spacing: 2px;
    color: white;
}

.brand span {
    color: #888;
}

.topline {
    border-bottom: 1px solid #24262a;
    margin-top: 15px;
    margin-bottom: 22px;
}

.nav {
    display: flex;
    gap: 30px;
    flex-wrap: wrap;
    align-items: center;
    margin-bottom: 5px;
}

.nav a {
    color: #85878d !important;
    text-decoration: none !important;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 12px 0;
}

.nav a.active {
    color: white !important;
    border-bottom: 2px solid white;
}

.section-label {
    color: #85878d;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
    margin: 22px 0 13px 0;
}

.metric-card {
    background: #111316;
    border: 1px solid #25272c;
    border-radius: 9px;
    padding: 17px 19px;
    min-height: 90px;
}

.metric-title {
    font-size: 10px;
    color: #85878d;
    letter-spacing: 1.5px;
    font-weight: 700;
}

.metric-number {
    font-size: 27px;
    font-weight: 800;
    margin-top: 8px;
}

.green { color: #20d69a !important; }
.red { color: #ff5364 !important; }
.yellow { color: #f5c84c !important; }
.muted { color: #85878d !important; }

.main-card {
    background: #111316;
    border: 1px solid #292c32;
    border-radius: 12px;
    padding: 25px;
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
    color: #a8abb2;
    font-size: 14px;
    margin-top: 5px;
}

.signal {
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 1px;
    padding: 10px 17px;
    border-radius: 5px;
}

.signal-long {
    background: rgba(32,214,154,.12);
    color: #20d69a;
    border: 1px solid rgba(32,214,154,.35);
}

.signal-short {
    background: rgba(255,83,100,.12);
    color: #ff5364;
    border: 1px solid rgba(255,83,100,.35);
}

.signal-wait {
    background: rgba(245,200,76,.12);
    color: #f5c84c;
    border: 1px solid rgba(245,200,76,.35);
}

.score {
    font-size: 30px;
    font-weight: 800;
    margin-top: 8px;
}

.data-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-top: 28px;
}

.data-box {
    background: #191b20;
    border: 1px solid #282b31;
    padding: 15px;
    border-radius: 7px;
}

.data-title {
    font-size: 10px;
    color: #85878d;
    letter-spacing: 1px;
    margin-bottom: 9px;
}

.data-value {
    font-size: 17px;
    font-weight: 700;
    color: white;
}

.market-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #111316;
    border: 1px solid #25272c;
    border-radius: 7px;
    padding: 15px 17px;
    margin-bottom: 9px;
    gap: 10px;
}

.market-name {
    font-size: 13px;
    font-weight: 700;
}

.market-price {
    font-size: 12px;
    color: #92959c;
    margin-top: 5px;
}

.market-signal {
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1px;
}

.info-card {
    background: #111316;
    border: 1px solid #25272c;
    border-radius: 9px;
    padding: 20px;
    margin-bottom: 12px;
}

.info-title {
    font-size: 11px;
    color: #85878d;
    letter-spacing: 1px;
    margin-bottom: 10px;
}

.info-value {
    font-size: 22px;
    font-weight: 800;
}

hr {
    border-color: #25272c !important;
}

@media(max-width: 700px) {
    .block-container {
        padding-left: 12px;
        padding-right: 12px;
    }
    .nav {
        gap: 15px;
    }
    .nav a {
        font-size: 9px;
    }
    .pair-name {
        font-size: 23px;
    }
    .data-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}
</style>
""", unsafe_allow_html=True)


# -------------------- MENÜ --------------------

if "page" not in st.session_state:
    st.session_state.page = "overview"

page = st.query_params.get("page", st.session_state.page)
valid_pages = ["overview", "chart", "news", "history", "risk"]

if page not in valid_pages:
    page = "overview"

st.session_state.page = page

st.markdown("""
<div class="brand">FOREX <span>RADAR</span></div>
<div class="topline"></div>
""", unsafe_allow_html=True)

menu = [
    ("GENEL BAKIŞ", "overview"),
    ("GRAFİK", "chart"),
    ("HABERLER", "news"),
    ("SİNYAL GEÇMİŞİ", "history"),
    ("RİSK", "risk")
]

nav_html = '<div class="nav">'
for label, key in menu:
    active = "active" if page == key else ""
    nav_html += f'<a class="{active}" href="?page={key}">{label}</a>'
nav_html += "</div>"

st.markdown(nav_html, unsafe_allow_html=True)
st.markdown('<div class="topline"></div>', unsafe_allow_html=True)


# -------------------- PİYASA VERİLERİ --------------------

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

@st.cache_data(ttl=180, show_spinner=False)
def get_market_data():
    results = {}

    for name, symbol in MARKETS.items():
        try:
            df = yf.Ticker(symbol).history(
                period="5d",
                interval="15m",
                auto_adjust=True
            )

            if df is None or len(df) < 30:
                continue

            df = df.dropna()

            close = df["Close"]
            high = df["High"]
            low = df["Low"]

            ema20 = close.ewm(span=20).mean()
            ema50 = close.ewm(span=50).mean()

            delta = close.diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)

            avg_gain = gain.rolling(14).mean()
            avg_loss = loss.rolling(14).mean()

            rs = avg_gain / avg_loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))

            tr = pd.concat([
                high - low,
                (high - close.shift()).abs(),
                (low - close.shift()).abs()
            ], axis=1).max(axis=1)

            atr = tr.rolling(14).mean()

            latest_price = float(close.iloc[-1])
            latest_ema20 = float(ema20.iloc[-1])
            latest_ema50 = float(ema50.iloc[-1])
            latest_rsi = float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else 50
            latest_atr = float(atr.iloc[-1]) if pd.notna(atr.iloc[-1]) else 0

            score = 50

            if latest_ema20 > latest_ema50:
                score += 20
            else:
                score -= 20

            if latest_price > latest_ema20:
                score += 15
            else:
                score -= 15

            if latest_rsi > 50:
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

            results[name] = {
                "symbol": symbol,
                "df": df,
                "price": latest_price,
                "ema20": latest_ema20,
                "ema50": latest_ema50,
                "rsi": latest_rsi,
                "atr": latest_atr,
                "score": score,
                "signal": signal
            }

        except Exception:
            continue

    return results


with st.spinner("Piyasa verileri analiz ediliyor..."):
    data = get_market_data()


def price_format(value):
    if value >= 100:
        return f"{value:,.3f}"
    return f"{value:.5f}"


def signal_class(signal):
    if signal == "LONG":
        return "signal-long"
    if signal == "SHORT":
        return "signal-short"
    return "signal-wait"


def signal_color(signal):
    if signal == "LONG":
        return "green"
    if signal == "SHORT":
        return "red"
    return "yellow"


# -------------------- GENEL BAKIŞ --------------------

if page == "overview":

    st.markdown(
        '<div class="section-label">PİYASA ÖZETİ</div>',
        unsafe_allow_html=True
    )

    long_count = sum(1 for x in data.values() if x["signal"] == "LONG")
    short_count = sum(1 for x in data.values() if x["signal"] == "SHORT")
    wait_count = sum(1 for x in data.values() if x["signal"] == "WAIT")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">LONG SİNYAL</div>
            <div class="metric-number green">{long_count:02d}</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">SHORT SİNYAL</div>
            <div class="metric-number red">{short_count:02d}</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">BEKLEME</div>
            <div class="metric-number yellow">{wait_count:02d}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(
        '<div class="section-label">ANA İŞLEM ANALİZİ</div>',
        unsafe_allow_html=True
    )

    if "EUR/USD" in data:
        main = data["EUR/USD"]
        signal = main["signal"]
        atr = main["atr"]
        price = main["price"]

        if signal == "LONG":
            entry = price
            stop = price - atr * 1.5
            target1 = price + atr * 1.5
            target2 = price + atr * 3
        elif signal == "SHORT":
            entry = price
            stop = price + atr * 1.5
            target1 = price - atr * 1.5
            target2 = price - atr * 3
        else:
            entry = price
            stop = price - atr * 1.5
            target1 = price + atr * 1.5
            target2 = price + atr * 3

        st.markdown(f"""
        <div class="main-card">
            <div class="card-top">
                <div>
                    <div class="pair-name">EUR/USD</div>
                    <div class="price">{price_format(price)}</div>
                </div>
                <div class="signal {signal_class(signal)}">{signal}</div>
            </div>
            <div style="margin-top:25px">
                <div class="metric-title">ANALİZ GÜVEN SKORU</div>
                <div class="score">{main['score']}<span style="font-size:15px;color:#85878d"> / 100</span></div>
                <div style="height:5px;background:#292c32;border-radius:5px;margin-top:12px">
                    <div style="height:5px;width:{main['score']}%;background:#20d69a;border-radius:5px"></div>
                </div>
            </div>
            <div class="data-grid">
                <div class="data-box">
                    <div class="data-title">GİRİŞ</div>
                    <div class="data-value">{price_format(entry)}</div>
                </div>
                <div class="data-box">
                    <div class="data-title">STOP LOSS</div>
                    <div class="data-value red">{price_format(stop)}</div>
                </div>
                <div class="data-box">
                    <div class="data-title">HEDEF 1</div>
                    <div class="data-value green">{price_format(target1)}</div>
                </div>
                <div class="data-box">
                    <div class="data-title">HEDEF 2</div>
                    <div class="data-value green">{price_format(target2)}</div>
                </div>
            </div>
            <div style="margin-top:20px;color:#85878d;font-size:11px">
                RSI: {main['rsi']:.1f} &nbsp; | &nbsp;
                EMA 20: {price_format(main['ema20'])} &nbsp; | &nbsp;
                EMA 50: {price_format(main['ema50'])}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("EUR/USD verisi şu anda alınamadı.")

    st.markdown(
        '<div class="section-label">DİĞER PARİTELER</div>',
        unsafe_allow_html=True
    )

    for name, item in data.items():
        if name == "EUR/USD":
            continue

        st.markdown(f"""
        <div class="market-row">
            <div>
                <div class="market-name">{name}</div>
                <div class="market-price">{price_format(item['price'])}</div>
            </div>
            <div class="market-signal {signal_color(item['signal'])}">
                {item['signal']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.caption("Veriler yaklaşık 3 dakikada bir yenilenir. Sinyaller teknik göstergelere dayalıdır.")


# -------------------- GRAFİK --------------------

elif page == "chart":

    st.markdown(
        '<div class="section-label">FİYAT GRAFİKLERİ</div>',
        unsafe_allow_html=True
    )

    selected = st.selectbox("PARİTE SEÇ", list(MARKETS.keys()))

    if selected in data:
        item = data[selected]
        df = item["df"]

        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Fiyat"
        ))

        fig.add_trace(go.Scatter(
            x=df.index,
            y=df["Close"].ewm(span=20).mean(),
            name="EMA 20",
            line=dict(color="#20d69a", width=1)
        ))

        fig.add_trace(go.Scatter(
            x=df.index,
            y=df["Close"].ewm(span=50).mean(),
            name="EMA 50",
            line=dict(color="#f5c84c", width=1)
        ))

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#08090b",
            plot_bgcolor="#08090b",
            font=dict(color="white"),
            height=550,
            xaxis_rangeslider_visible=False,
            margin=dict(l=10, r=10, t=30, b=10),
            legend=dict(orientation="h")
        )

        st.plotly_chart(fig, use_container_width=True)

        a, b, c = st.columns(3)
        a.metric("RSI", f"{item['rsi']:.1f}")
        b.metric("EMA 20", price_format(item["ema20"]))
        c.metric("EMA 50", price_format(item["ema50"]))

    else:
        st.warning("Bu paritenin grafiği için veri alınamadı.")


# -------------------- HABERLER --------------------

elif page == "news":

    st.markdown(
        '<div class="section-label">PİYASA HABERLERİ</div>',
        unsafe_allow_html=True
    )

    st.caption("Forex Factory haber akışı. Haber saatleri ve önem dereceleri kaynağa bağlıdır.")

    try:
        response = requests.get(
            "https://nfs.faireconomy.media/ff_calendar_thisweek.xml",
            timeout=12,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        response.raise_for_status()

        root = ET.fromstring(response.content)
        events = root.findall(".//event")

        if not events:
            st.info("Şu anda haber bulunamadı.")

        for event in events[:35]:
            title = event.findtext("title", "Başlıksız haber")
            country = event.findtext("country", "")
            date = event.findtext("date", "")
            time = event.findtext("time", "")
            impact = event.findtext("impact", "Bilinmiyor")
            forecast = event.findtext("forecast", "-")
            previous = event.findtext("previous", "-")

            color = "yellow"
            if impact.lower() == "high":
                color = "red"
            elif impact.lower() == "low":
                color = "muted"

            st.markdown(f"""
            <div class="info-card">
                <div class="card-top">
                    <div style="font-weight:700">{title}</div>
                    <div class="{color}" style="font-size:11px;font-weight:800">{impact.upper()}</div>
                </div>
                <div style="font-size:12px;color:#85878d;margin-top:10px">
                    {country} &nbsp; | &nbsp; {date} {time}
                </div>
                <div style="font-size:12px;margin-top:10px">
                    Tahmin: {forecast} &nbsp; | &nbsp; Önceki: {previous}
                </div>
            </div>
            """, unsafe_allow_html=True)

    except Exception:
        st.error("Haber akışı şu anda alınamıyor. Daha sonra tekrar deneyin.")


# -------------------- SİNYAL GEÇMİŞİ --------------------

elif page == "history":

    st.markdown(
        '<div class="section-label">SİNYAL GEÇMİŞİ</div>',
        unsafe_allow_html=True
    )

    if "signal_history" not in st.session_state:
        st.session_state.signal_history = []

    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    for name, item in data.items():
        signature = f"{name}-{item['signal']}"

        if signature not in [
            x["signature"] for x in st.session_state.signal_history
        ]:
            st.session_state.signal_history.insert(0, {
                "signature": signature,
                "pair": name,
                "signal": item["signal"],
                "price": item["price"],
                "score": item["score"],
                "time": now
            })

    if st.session_state.signal_history:
        for item in st.session_state.signal_history[:100]:
            st.markdown(f"""
            <div class="market-row">
                <div>
                    <div class="market-name">{item['pair']}</div>
                    <div class="market-price">{item['time']} · {price_format(item['price'])}</div>
                </div>
                <div style="text-align:right">
                    <div class="market-signal {signal_color(item['signal'])}">{item['signal']}</div>
                    <div class="market-price">Skor: {item['score']}/100</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Henüz sinyal geçmişi bulunmuyor.")

    st.caption("Bu liste oturum bazlıdır. Uygulama yeniden başlatıldığında geçmiş sıfırlanabilir.")


# -------------------- RİSK --------------------

elif page == "risk":

    st.markdown(
        '<div class="section-label">RİSK YÖNETİMİ</div>',
        unsafe_allow_html=True
    )

    selected = st.selectbox("PARİTE SEÇ", list(MARKETS.keys()))

    if selected in data:
        item = data[selected]
        price = item["price"]
        atr = item["atr"]

        st.markdown(f"""
        <div class="info-card">
            <div class="info-title">SEÇİLİ PARİTE</div>
            <div class="info-value">{selected}</div>
            <div class="market-price">{price_format(price)}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### Pozisyon hesaplama")

        balance = st.number_input(
            "Hesap büyüklüğü (USD)",
            min_value=1.0,
            value=1000.0,
            step=100.0
        )

        risk_percent = st.slider(
            "İşlem başına risk (%)",
            min_value=0.1,
            max_value=2.0,
            value=0.5,
            step=0.1
        )

        stop_multiplier = st.slider(
            "ATR stop katsayısı",
            min_value=0.5,
            max_value=3.0,
            value=1.5,
            step=0.1
        )

        risk_amount = balance * risk_percent / 100
        stop_distance = atr * stop_multiplier

        st.markdown(f"""
        <div class="data-grid">
            <div class="data-box">
                <div class="data-title">RİSK TUTARI</div>
                <div class="data-value red">${risk_amount:.2f}</div>
            </div>
            <div class="data-box">
                <div class="data-title">STOP MESAFESİ</div>
                <div class="data-value">{stop_distance:.5f}</div>
            </div>
            <div class="data-box">
                <div class="data-title">ATR</div>
                <div class="data-value">{atr:.5f}</div>
            </div>
            <div class="data-box">
                <div class="data-title">RİSK ORANI</div>
                <div class="data-value yellow">%{risk_percent:.1f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.warning(
            "Bu hesaplama yalnızca yaklaşık risk planlaması içindir. "
            "Forex lot büyüklüğü, pip değeri, kaldıraç ve hesap para birimi "
            "ayrıca dikkate alınmalıdır."
        )

    else:
        st.warning("Parite verisi alınamadı.")


# -------------------- ALT BİLGİ --------------------

st.markdown('<div class="topline"></div>', unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center;color:#666970;font-size:10px;letter-spacing:1px">
FOREX RADAR · MARKET ANALYSIS TERMINAL
<br><br>
Bu uygulama yatırım tavsiyesi veya otomatik işlem sistemi değildir.
</div>
""", unsafe_allow_html=True)
