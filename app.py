
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# =====================================================
# FOREX RADAR - STRICT EDITION
# =====================================================

st.set_page_config(
    page_title="FOREX RADAR",
    page_icon="📈",
    layout="wide"
)

MAX_RISK = 1.0
MIN_SCORE = 80
ADX_MIN = 18

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
    "XAU/USD": "GC=F",
    "XAG/USD": "SI=F"
}

# =====================================================
# STYLE
# =====================================================

st.markdown("""
<style>

html, body, [data-testid="stAppViewContainer"] {
    background: #f5f7fa;
    color: #172033;
}

[data-testid="stHeader"] {
    background: #f5f7fa;
}

.block-container {
    padding-top: 1.5rem;
    max-width: 1450px;
}

h1, h2, h3, p, label {
    color: #172033 !important;
}

[data-testid="stMetric"] {
    background: white;
    border: 1px solid #e7ebf0;
    border-radius: 13px;
    padding: 17px;
    box-shadow: 0 2px 8px rgba(20,30,50,.035);
}

[data-testid="stDataFrame"] {
    background: white;
    border-radius: 12px;
}

div.stButton > button {
    border-radius: 9px;
    border: 1px solid #dce2e9;
    background: white;
    color: #172033;
    font-weight: 600;
}

div.stButton > button:hover {
    border-color: #16a36a;
    color: #16a36a;
}

hr {
    border-color: #e5e9ef;
}

</style>
""", unsafe_allow_html=True)


# =====================================================
# DATA DOWNLOAD
# =====================================================

@st.cache_data(ttl=60)
def download_data(ticker, interval):

    try:

        period = "5d" if interval == "15m" else "60d"

        df = yf.download(
            ticker,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
            threads=False
        )

        if df is None or df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):

            if "Close" in df.columns.get_level_values(0):
                df.columns = df.columns.get_level_values(0)

            elif "Close" in df.columns.get_level_values(1):
                df.columns = df.columns.get_level_values(1)

        required = ["Open", "High", "Low", "Close"]

        if not all(x in df.columns for x in required):
            return None

        df = df[required].copy()

        for col in required:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna()

        # Son, tamamlanmamış mum kullanılmaz.
        if len(df) > 1:
            df = df.iloc[:-1]

        return df if len(df) >= 55 else None

    except Exception:
        return None


# =====================================================
# INDICATORS
# =====================================================

def calculate_indicators(df):

    df = df.copy()

    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    df["EMA20"] = close.ewm(
        span=20,
        adjust=False
    ).mean()

    df["EMA50"] = close.ewm(
        span=50,
        adjust=False
    ).mean()

    # RSI - Wilder smoothing

    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1/14,
        min_periods=14,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1/14,
        min_periods=14,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    df["RSI"] = 100 - (100 / (1 + rs))

    df["RSI"] = df["RSI"].fillna(50)

    # ATR

    previous_close = close.shift(1)

    tr = pd.concat([
        high - low,
        (high - previous_close).abs(),
        (low - previous_close).abs()
    ], axis=1).max(axis=1)

    df["ATR"] = tr.ewm(
        alpha=1/14,
        min_periods=14,
        adjust=False
    ).mean()

    # ADX

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(
        np.where(
            (up_move > down_move) & (up_move > 0),
            up_move,
            0
        ),
        index=df.index
    )

    minus_dm = pd.Series(
        np.where(
            (down_move > up_move) & (down_move > 0),
            down_move,
            0
        ),
        index=df.index
    )

    atr_smooth = tr.ewm(
        alpha=1/14,
        min_periods=14,
        adjust=False
    ).mean()

    plus_di = 100 * (
        plus_dm.ewm(alpha=1/14, adjust=False).mean()
        / atr_smooth.replace(0, np.nan)
    )

    minus_di = 100 * (
        minus_dm.ewm(alpha=1/14, adjust=False).mean()
        / atr_smooth.replace(0, np.nan)
    )

    dx = 100 * (
        (plus_di - minus_di).abs()
        / (plus_di + minus_di).replace(0, np.nan)
    )

    df["ADX"] = dx.ewm(
        alpha=1/14,
        min_periods=14,
        adjust=False
    ).mean()

    return df.dropna()


# =====================================================
# HIGHER TIMEFRAME
# =====================================================

def create_4h_data(hourly):

    if hourly is None or hourly.empty:
        return None

    four_hour = hourly.resample(
        "4h",
        label="left",
        closed="left"
    ).agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last"
    })

    four_hour = four_hour.dropna()

    if len(four_hour) < 55:
        return None

    # Son tamamlanmamış 4 saatlik mum çıkarılır.
    four_hour = four_hour.iloc[:-1]

    return calculate_indicators(four_hour)


# =====================================================
# STRICT SIGNAL ENGINE
# =====================================================

def analyze_market(name, ticker):

    try:

        data_15m = download_data(ticker, "15m")
        data_1h = download_data(ticker, "1h")

        if data_15m is None or data_1h is None:
            raise ValueError("Yetersiz piyasa verisi")

        df15 = calculate_indicators(data_15m)
        df1h = calculate_indicators(data_1h)
        df4h = create_4h_data(data_1h)

        if df4h is None:
            raise ValueError("4 saatlik veri yetersiz")

        if min(len(df15), len(df1h), len(df4h)) < 2:
            raise ValueError("Gösterge verisi yetersiz")

        m15 = df15.iloc[-1]
        m1h = df1h.iloc[-1]
        m4h = df4h.iloc[-1]

        price = float(m15["Close"])
        ema20 = float(m15["EMA20"])
        ema50 = float(m15["EMA50"])

        rsi15 = float(m15["RSI"])
        rsi1h = float(m1h["RSI"])

        atr = float(m15["ATR"])
        adx = float(m15["ADX"])

        # ---------------------------------------------
        # LONG SCORE
        # ---------------------------------------------

        long_score = 0

        if m4h["EMA20"] > m4h["EMA50"]:
            long_score += 25

        if m1h["EMA20"] > m1h["EMA50"]:
            long_score += 25

        if ema20 > ema50:
            long_score += 20

        if price > ema20:
            long_score += 10

        if 50 < rsi15 < 68:
            long_score += 10

        if rsi1h > 50:
            long_score += 5

        if adx >= ADX_MIN:
            long_score += 5

        # ---------------------------------------------
        # SHORT SCORE
        # ---------------------------------------------

        short_score = 0

        if m4h["EMA20"] < m4h["EMA50"]:
            short_score += 25

        if m1h["EMA20"] < m1h["EMA50"]:
            short_score += 25

        if ema20 < ema50:
            short_score += 20

        if price < ema20:
            short_score += 10

        if 32 < rsi15 < 50:
            short_score += 10

        if rsi1h < 50:
            short_score += 5

        if adx >= ADX_MIN:
            short_score += 5

        # ---------------------------------------------
        # SIGNAL VALIDATION
        # ---------------------------------------------

        signal = "WAIT"

        if (
            long_score >= MIN_SCORE
            and m4h["EMA20"] > m4h["EMA50"]
            and m1h["EMA20"] > m1h["EMA50"]
            and ema20 > ema50
            and price > ema20
            and 50 < rsi15 < 68
            and rsi1h > 50
            and adx >= ADX_MIN
        ):

            signal = "LONG"

        elif (
            short_score >= MIN_SCORE
            and m4h["EMA20"] < m4h["EMA50"]
            and m1h["EMA20"] < m1h["EMA50"]
            and ema20 < ema50
            and price < ema20
            and 32 < rsi15 < 50
            and rsi1h < 50
            and adx >= ADX_MIN
        ):

            signal = "SHORT"

        if signal == "LONG":
            score = long_score

        elif signal == "SHORT":
            score = short_score

        else:
            score = max(long_score, short_score)

        return {
            "pair": name,
            "price": price,
            "signal": signal,
            "score": score,
            "long_score": long_score,
            "short_score": short_score,
            "rsi": rsi15,
            "rsi1h": rsi1h,
            "adx": adx,
            "ema": (
                "Yükseliş" if ema20 > ema50 else "Düşüş"
            ),
            "atr": atr,
            "df": df15,
            "df1h": df1h,
            "df4h": df4h,
            "error": None
        }

    except Exception as e:

        return {
            "pair": name,
            "price": None,
            "signal": "VERİ YOK",
            "score": 0,
            "long_score": 0,
            "short_score": 0,
            "rsi": None,
            "rsi1h": None,
            "adx": None,
            "ema": "—",
            "atr": None,
            "df": None,
            "df1h": None,
            "df4h": None,
            "error": str(e)
        }


# =====================================================
# TRADE LEVELS
# =====================================================

def calculate_levels(data):

    price = data["price"]
    atr = data["atr"]
    signal = data["signal"]

    if price is None or atr is None:
        return None

    if signal not in ["LONG", "SHORT"]:
        return None

    if not np.isfinite(atr) or atr <= 0:
        return None

    risk_distance = atr * 1.5

    if signal == "LONG":

        entry = price
        sl = entry - risk_distance

        tp1 = entry + risk_distance
        tp2 = entry + risk_distance * 2
        tp3 = entry + risk_distance * 3

    else:

        entry = price
        sl = entry + risk_distance

        tp1 = entry - risk_distance
        tp2 = entry - risk_distance * 2
        tp3 = entry - risk_distance * 3

    return {
        "entry": entry,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "risk_distance": risk_distance
    }


# =====================================================
# FORMAT
# =====================================================

def format_price(value):

    if value is None:
        return "—"

    if abs(value) >= 100:
        return f"{value:.3f}"

    return f"{value:.5f}"


# =====================================================
# HEADER
# =====================================================

st.title("FOREX RADAR")

st.caption("STRICT MULTI-TIMEFRAME MARKET ANALYSIS")

st.caption(
    "15M + 1H + 4H | EMA | RSI | ADX | ATR | RISK CONTROL"
)

st.warning(
    "Piyasa verileri Yahoo Finance üzerinden alınır ve gecikmeli "
    "olabilir. Bu sistem otomatik emir göndermez. "
    "Sinyaller kâr garantisi vermez."
)

st.write(
    "Son kontrol:",
    datetime.now().strftime("%d.%m.%Y %H:%M:%S")
)

if st.button("↻ PİYASAYI YENİLE"):

    st.cache_data.clear()
    st.rerun()

st.divider()


# =====================================================
# MARKET SCAN
# =====================================================

@st.cache_data(ttl=60)
def scan_all():

    results = []

    with ThreadPoolExecutor(max_workers=5) as executor:

        futures = [
            executor.submit(analyze_market, name, ticker)
            for name, ticker in MARKETS.items()
        ]

        for future in futures:

            try:
                results.append(future.result())

            except Exception:
                continue

    return results


with st.spinner("Piyasalar çoklu zaman diliminde analiz ediliyor..."):

    results = scan_all()


valid = [
    x for x in results
    if x["price"] is not None
]

long_count = sum(
    x["signal"] == "LONG" for x in valid
)

short_count = sum(
    x["signal"] == "SHORT" for x in valid
)

wait_count = sum(
    x["signal"] == "WAIT" for x in valid
)


# =====================================================
# SUMMARY
# =====================================================

st.subheader("Piyasa Özeti")

c1, c2, c3, c4 = st.columns(4)

c1.metric("LONG", long_count)
c2.metric("SHORT", short_count)
c3.metric("WAIT", wait_count)

c4.metric(
    "Taranan Piyasa",
    f"{len(valid)}/{len(MARKETS)}"
)

st.divider()


# =====================================================
# MARKET TABLE
# =====================================================

st.subheader("Tüm Piyasalar")

table_rows = []

for item in results:

    table_rows.append({

        "PARİTE": item["pair"],

        "FİYAT": format_price(item["price"]),

        "SİNYAL": item["signal"],

        "GÜÇ": f"%{item['score']}",

        "RSI 15M": (
            round(item["rsi"], 2)
            if item["rsi"] is not None else "—"
        ),

        "RSI 1H": (
            round(item["rsi1h"], 2)
            if item["rsi1h"] is not None else "—"
        ),

        "ADX": (
            round(item["adx"], 2)
            if item["adx"] is not None else "—"
        ),

        "EMA TRENDİ": item["ema"]
    })


table = pd.DataFrame(table_rows)


def color_signal(value):

    if value == "LONG":
        return (
            "background-color: #dcfce7;"
            "color: #15803d; font-weight: bold"
        )

    if value == "SHORT":
        return (
            "background-color: #fee2e2;"
            "color: #b91c1c; font-weight: bold"
        )

    if value == "WAIT":
        return (
            "background-color: #f1f5f9;"
            "color: #475569; font-weight: bold"
        )

    return ""


styled_table = table.style.map(
    color_signal,
    subset=["SİNYAL"]
)

st.dataframe(
    styled_table,
    use_container_width=True,
    hide_index=True,
    height=680
)

st.divider()


# =====================================================
# SELECTED MARKET
# =====================================================

st.subheader("Detaylı Piyasa Analizi")

available_pairs = [
    x["pair"] for x in valid
]

if available_pairs:

    selected_pair = st.selectbox(
        "Analiz edilecek parite",
        available_pairs
    )

    selected = next(
        x for x in valid
        if x["pair"] == selected_pair
    )

    st.markdown(f"### {selected_pair}")

    a, b, c, d = st.columns(4)

    a.metric(
        "Güncel Fiyat",
        format_price(selected["price"])
    )

    b.metric(
        "Sinyal",
        selected["signal"]
    )

    c.metric(
        "Sinyal Gücü",
        f"%{selected['score']}"
    )

    d.metric(
        "ADX",
        f"{selected['adx']:.2f}"
    )

    st.markdown("#### Zaman Dilimi Doğrulaması")

    t1, t2, t3 = st.columns(3)

    for col, label, frame in [
        (t1, "15 DAKİKA", selected["df"]),
        (t2, "1 SAAT", selected["df1h"]),
        (t3, "4 SAAT", selected["df4h"])
    ]:

        last = frame.iloc[-1]

        trend = (
            "YÜKSELİŞ"
            if last["EMA20"] > last["EMA50"]
            else "DÜŞÜŞ"
        )

        col.metric(
            label,
            trend,
            f"RSI {last['RSI']:.2f}"
        )

    # ---------------------------------------------
    # CHART
    # ---------------------------------------------

    df = selected["df"]

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
        y=df["EMA20"],
        name="EMA 20",
        line=dict(width=1.5)

    ))

    fig.add_trace(go.Scatter(

        x=df.index,
        y=df["EMA50"],
        name="EMA 50",
        line=dict(width=1.5)

    ))

    fig.update_layout(

        height=470,
        template="plotly_white",

        margin=dict(
            l=10,
            r=10,
            t=25,
            b=10
        ),

        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h")

    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # ---------------------------------------------
    # RSI
    # ---------------------------------------------

    st.markdown("#### RSI Göstergesi")

    st.progress(
        int(max(
            0,
            min(100, selected["rsi"])
        ))
    )

    st.caption(
        f"RSI 15M: {selected['rsi']:.2f} | "
        f"RSI 1H: {selected['rsi1h']:.2f}"
    )

    # ---------------------------------------------
    # ADX
    # ---------------------------------------------

    st.markdown("#### Trend Gücü")

    st.progress(
        int(max(
            0,
            min(100, selected["adx"])
        ))
    )

    st.caption(
        f"ADX: {selected['adx']:.2f} | "
        f"Minimum filtre: {ADX_MIN}"
    )

    # ---------------------------------------------
    # SCORE
    # ---------------------------------------------

    st.markdown("#### Sinyal Puanları")

    s1, s2 = st.columns(2)

    s1.metric(
        "LONG Puanı",
        f"%{selected['long_score']}"
    )

    s2.metric(
        "SHORT Puanı",
        f"%{selected['short_score']}"
    )

    # ---------------------------------------------
    # TRADE LEVELS
    # ---------------------------------------------

    st.markdown("#### İşlem Seviyeleri")

    levels = calculate_levels(selected)

    if levels:

        l1, l2, l3, l4, l5 = st.columns(5)

        l1.metric(
            "ENTRY",
            format_price(levels["entry"])
        )

        l2.metric(
            "STOP LOSS",
            format_price(levels["sl"])
        )

        l3.metric(
            "TAKE PROFIT 1",
            format_price(levels["tp1"])
        )

        l4.metric(
            "TAKE PROFIT 2",
            format_price(levels["tp2"])
        )

        l5.metric(
            "TAKE PROFIT 3",
            format_price(levels["tp3"])
        )

        st.caption(
            "SL = 1.5 ATR | TP1 = 1R | "
            "TP2 = 2R | TP3 = 3R"
        )

    else:

        st.info(
            "STRICT filtreleri karşılayan işlem bulunmadı. "
            "WAIT sinyali korunuyor."
        )

else:

    st.warning(
        "Şu anda analiz edilebilir piyasa verisi alınamadı."
    )

st.divider()


# =====================================================
# RISK CALCULATOR
# =====================================================

st.subheader("Risk Hesaplayıcı")

st.caption(
    "Maksimum işlem riski: %1. "
    "Bu sınırın üzerine çıkılamaz."
)

r1, r2, r3 = st.columns(3)

with r1:

    balance = st.number_input(
        "Hesap bakiyesi ($)",
        min_value=1.0,
        value=1000.0,
        step=100.0
    )

with r2:

    risk_percent = st.number_input(
        "Risk (%)",
        min_value=0.1,
        max_value=MAX_RISK,
        value=1.0,
        step=0.1
    )

with r3:

    stop_distance = st.number_input(
        "Stop mesafesi (pip)",
        min_value=0.1,
        value=30.0,
        step=1.0
    )


risk_amount = balance * risk_percent / 100

pip_value = risk_amount / stop_distance

c1, c2 = st.columns(2)

c1.metric(
    "Risk Tutarı",
    f"${risk_amount:.2f}"
)

c2.metric(
    "Pip Başına Risk Bütçesi",
    f"${pip_value:.2f}"
)

st.caption(
    "Bu hesaplayıcı teorik risk bütçesini gösterir. "
    "Gerçek lot büyüklüğü için broker sözleşme büyüklüğü, "
    "hesap para birimi, pip değeri ve işlem maliyetleri gerekir."
)

st.divider()


# =====================================================
# FOOTER
# =====================================================

st.caption(
    "FOREX RADAR | STRICT EDITION | "
    "Maksimum risk %1 | "
    "Otomatik emir göndermez | "
    "Yatırım tavsiyesi değildir."
)
