
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

st.set_page_config(
    page_title="FOREX RADAR",
    page_icon="📈",
    layout="wide"
)

# ---------------- CONFIG ----------------

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

# ---------------- STYLE ----------------

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

# ---------------- DATA ----------------

@st.cache_data(ttl=60)
def get_market_data(ticker):
    try:
        df = yf.download(
            ticker,
            period="5d",
            interval="15m",
            progress=False,
            auto_adjust=True,
            threads=False
        )

        if df is None or df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        required = ["Open", "High", "Low", "Close"]
        if not all(col in df.columns for col in required):
            return None

        df = df[required].dropna()

        if len(df) < 55:
            return None

        df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
        df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()

        delta = df["Close"].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        df["RSI"] = 100 - (100 / (1 + rs))
        df["RSI"] = df["RSI"].fillna(50)

        previous_close = df["Close"].shift(1)
        tr = pd.concat([
            df["High"] - df["Low"],
            (df["High"] - previous_close).abs(),
            (df["Low"] - previous_close).abs()
        ], axis=1).max(axis=1)

        df["ATR"] = tr.rolling(14).mean()

        return df.dropna()

    except Exception:
        return None


def analyze_market(name, ticker):
    df = get_market_data(ticker)

    if df is None or df.empty:
        return {
            "pair": name,
            "price": None,
            "signal": "VERİ YOK",
            "score": 0,
            "rsi": None,
            "ema": "—",
            "atr": None,
            "df": None
        }

    last = df.iloc[-1]
    price = float(last["Close"])
    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])
    rsi = float(last["RSI"])
    atr = float(last["ATR"])

    score = 50

    if ema20 > ema50:
        score += 20
    else:
        score -= 20

    if price > ema20:
        score += 15
    else:
        score -= 15

    if rsi > 55:
        score += 15
    elif rsi < 45:
        score -= 15

    score = max(0, min(100, score))

    if score >= 65:
        signal = "LONG"
    elif score <= 35:
        signal = "SHORT"
    else:
        signal = "WAIT"

    return {
        "pair": name,
        "price": price,
        "signal": signal,
        "score": score,
        "rsi": rsi,
        "ema": "Yükseliş" if ema20 > ema50 else "Düşüş",
        "atr": atr,
        "df": df
    }


def calculate_levels(data):
    price = data["price"]
    atr = data["atr"]
    signal = data["signal"]

    if price is None or atr is None or signal == "WAIT":
        return None

    if signal == "LONG":
        entry = price
        sl = entry - (atr * 1.5)
        tp1 = entry + (atr * 1.0)
        tp2 = entry + (atr * 2.0)
        tp3 = entry + (atr * 3.0)
    else:
        entry = price
        sl = entry + (atr * 1.5)
        tp1 = entry - (atr * 1.0)
        tp2 = entry - (atr * 2.0)
        tp3 = entry - (atr * 3.0)

    return {
        "entry": entry,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3
    }


# ---------------- HEADER ----------------

st.title("FOREX RADAR")
st.caption("FOREX MARKET ANALYSIS TERMINAL")
st.caption("Piyasa verileri gecikmeli olabilir. Sinyaller otomatik teknik analiz çıktısıdır.")

now = datetime.now().strftime("%d.%m.%Y  %H:%M:%S")
st.write(f"Son kontrol: {now}")

if st.button("↻ PİYASAYI YENİLE"):
    st.cache_data.clear()
    st.rerun()

st.divider()

# ---------------- SCAN ----------------

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
                pass
    return results


with st.spinner("Piyasalar taranıyor..."):
    results = scan_all()

valid = [x for x in results if x["price"] is not None]

long_count = sum(x["signal"] == "LONG" for x in valid)
short_count = sum(x["signal"] == "SHORT" for x in valid)
wait_count = sum(x["signal"] == "WAIT" for x in valid)

# ---------------- SUMMARY ----------------

st.subheader("Piyasa Özeti")

c1, c2, c3, c4 = st.columns(4)

c1.metric("LONG", long_count)
c2.metric("SHORT", short_count)
c3.metric("WAIT", wait_count)
c4.metric("Taranan Parite", f"{len(valid)}/{len(MARKETS)}")

st.divider()

# ---------------- MARKET TABLE ----------------

st.subheader("Tüm Piyasalar")

table_rows = []

for item in results:
    table_rows.append({
        "PARİTE": item["pair"],
        "FİYAT": round(item["price"], 5) if item["price"] is not None else "—",
        "SİNYAL": item["signal"],
        "GÜÇ": f"%{item['score']}",
        "RSI": round(item["rsi"], 2) if item["rsi"] is not None else "—",
        "EMA TRENDİ": item["ema"]
    })

table = pd.DataFrame(table_rows)

def color_signal(value):
    if value == "LONG":
        return "background-color: #dcfce7; color: #15803d; font-weight: bold"
    if value == "SHORT":
        return "background-color: #fee2e2; color: #b91c1c; font-weight: bold"
    if value == "WAIT":
        return "background-color: #f1f5f9; color: #475569; font-weight: bold"
    return ""

styled_table = table.style.map(color_signal, subset=["SİNYAL"])

st.dataframe(
    styled_table,
    use_container_width=True,
    hide_index=True,
    height=680
)

st.divider()

# ---------------- SELECTED MARKET ----------------

st.subheader("Detaylı Piyasa Analizi")

available_pairs = [x["pair"] for x in valid]

if available_pairs:
    selected_pair = st.selectbox(
        "Analiz edilecek parite",
        available_pairs
    )

    selected = next(x for x in valid if x["pair"] == selected_pair)

    st.markdown(f"### {selected_pair}")

    a, b, c, d = st.columns(4)

    a.metric(
        "Güncel Fiyat",
        f"{selected['price']:.5f}"
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
        "RSI",
        f"{selected['rsi']:.2f}"
    )

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
        margin=dict(l=10, r=10, t=25, b=10),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h")
    )

    st.plotly_chart(fig, use_container_width=True)

    # RSI
    st.markdown("#### RSI Göstergesi")
    st.progress(int(max(0, min(100, selected["rsi"]))))
    st.caption(f"RSI: {selected['rsi']:.2f} | EMA trendi: {selected['ema']}")

    # TRADE LEVELS
    st.markdown("#### İşlem Seviyeleri")

    levels = calculate_levels(selected)

    if levels:
        l1, l2, l3, l4, l5 = st.columns(5)

        l1.metric("ENTRY", f"{levels['entry']:.5f}")
        l2.metric("STOP LOSS", f"{levels['sl']:.5f}")
        l3.metric("TAKE PROFIT 1", f"{levels['tp1']:.5f}")
        l4.metric("TAKE PROFIT 2", f"{levels['tp2']:.5f}")
        l5.metric("TAKE PROFIT 3", f"{levels['tp3']:.5f}")

        st.caption(
            "Seviyeler ATR tabanlı örnek teknik seviyelerdir. "
            "Spread, komisyon, kayma ve piyasa koşulları dahil değildir."
        )
    else:
        st.info("Şu anda işlem seviyesi üretmek için yeterli LONG veya SHORT koşulu yok.")

else:
    st.warning("Şu anda analiz edilebilir piyasa verisi alınamadı.")

st.divider()

# ---------------- RISK CALCULATOR ----------------

st.subheader("Risk Hesaplayıcı")

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
        max_value=10.0,
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

st.metric("Risk Tutarı", f"${risk_amount:.2f}")
st.metric("Gerekli pip başına değer", f"${pip_value:.2f}")

st.caption(
    "Bu hesaplayıcı basitleştirilmiş bir örnektir. "
    "Lot büyüklüğü hesaplamasında parite, hesap para birimi ve broker pip değeri ayrıca dikkate alınmalıdır."
)

st.divider()

# ---------------- FOOTER ----------------

st.caption(
    "FOREX RADAR | Otomatik teknik analiz aracı | "
    "Yatırım tavsiyesi değildir. Hiçbir sinyal kâr veya işlem başarısı garantisi vermez."
)
