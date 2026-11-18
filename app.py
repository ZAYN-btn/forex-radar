
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
import requests
import sqlite3
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from pathlib import Path
from streamlit_autorefresh import st_autorefresh

from forex_engine import MARKETS, analyze_market


# ==========================================
# SAYFA AYARLARI
# ==========================================

st.set_page_config(
    page_title="FOREX RADAR PRO",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

DB = Path("forex_history.db")


# ==========================================
# SİYAH - BEYAZ TASARIM
# ==========================================

st.markdown("""
<style>
.stApp {
    background: #050505;
    color: #FFFFFF;
}

.block-container {
    max-width: 1250px;
    padding-top: 1.2rem;
    padding-bottom: 2rem;
}

header[data-testid="stHeader"] {
    background: #050505;
}

h1, h2, h3, h4, p, label, span {
    color: #FFFFFF;
}

.main-card {
    background: #111111;
    border: 1px solid #383838;
    border-radius: 16px;
    padding: 22px;
    margin-bottom: 15px;
}

.market-row {
    background: #111111;
    border: 1px solid #303030;
    border-radius: 10px;
    padding: 10px;
    margin-bottom: 5px;
}

.big-price {
    font-size: 35px;
    font-weight: 850;
    color: #FFFFFF;
}

.muted {
    color: #999999 !important;
    font-size: 12px;
}

.signal-label {
    background: #222222;
    border: 1px solid #555555;
    color: white;
    padding: 6px 12px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 800;
}

div[data-testid="stMetric"] {
    background: #111111;
    border: 1px solid #303030;
    border-radius: 11px;
    padding: 12px;
}

div[data-testid="stMetricLabel"] {
    color: #AAAAAA !important;
}

div[data-testid="stMetricValue"] {
    color: #FFFFFF !important;
}

.stButton button {
    background: #151515;
    color: #FFFFFF;
    border: 1px solid #444444;
    border-radius: 9px;
    font-weight: 700;
    text-align: left;
}

.stButton button:hover {
    background: #292929;
    color: white;
    border-color: white;
}

div[data-testid="stTabs"] button {
    color: white;
}

div[data-testid="stExpander"] {
    background: #111111;
    border: 1px solid #333333;
    border-radius: 10px;
}

[data-testid="stDataFrame"] {
    border: 1px solid #333333;
    border-radius: 10px;
}

hr {
    border-color: #333333;
}

footer {
    visibility: hidden;
}
</style>
""", unsafe_allow_html=True)


# ==========================================
# VERİ TABANI
# ==========================================

def connect_db():
    return sqlite3.connect(DB)


def init_db():
    with connect_db() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            market TEXT,
            direction TEXT,
            entry REAL,
            sl REAL,
            tp1 REAL,
            tp2 REAL,
            status TEXT DEFAULT 'ACTIVE'
        )
        """)


init_db()


def save_signals(results):
    with connect_db() as con:
        for item in results:

            if item.get("status") != "OK":
                continue

            if item["direction"] not in ("LONG", "SHORT"):
                continue

            active = con.execute("""
                SELECT id FROM signals
                WHERE market=? AND status='ACTIVE'
            """, (item["market"],)).fetchone()

            if active:
                continue

            con.execute("""
                INSERT INTO signals
                (created_at, market, direction, entry, sl, tp1, tp2)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(timezone.utc).isoformat(),
                item["market"],
                item["direction"],
                item["price"],
                item["stop_loss"],
                item["tp1"],
                item["tp2"]
            ))


def update_signals(results):
    current = {
        item["market"]: item
        for item in results
        if item.get("status") == "OK"
    }

    with connect_db() as con:

        rows = con.execute("""
            SELECT id, market, direction, sl, tp1, tp2
            FROM signals
            WHERE status='ACTIVE'
        """).fetchall()

        for row in rows:

            sid, market, direction, sl, tp1, tp2 = row

            if market not in current:
                continue

            item = current[market]

            high = item["bar_high"]
            low = item["bar_low"]

            if direction == "LONG":
                hit_sl = low <= sl
                hit_tp1 = high >= tp1
                hit_tp2 = high >= tp2
            else:
                hit_sl = high >= sl
                hit_tp1 = low <= tp1
                hit_tp2 = low <= tp2

            if hit_sl and (hit_tp1 or hit_tp2):
                status = "AMBIGUOUS"
            elif hit_sl:
                status = "SL"
            elif hit_tp2:
                status = "TP2"
            elif hit_tp1:
                status = "TP1"
            else:
                status = "ACTIVE"

            if status != "ACTIVE":
                con.execute(
                    "UPDATE signals SET status=? WHERE id=?",
                    (status, sid)
                )


def get_history():
    with connect_db() as con:
        return pd.read_sql_query(
            "SELECT * FROM signals ORDER BY id DESC",
            con
        )


# ==========================================
# PİYASA VERİLERİ
# ==========================================

@st.cache_data(ttl=240)
def load_results():
    return [
        analyze_market(name, symbol)
        for name, symbol in MARKETS.items()
    ]


results = load_results()

save_signals(results)
update_signals(results)

valid = [
    item for item in results
    if item.get("status") == "OK"
]


# ==========================================
# EN GÜÇLÜ SİNYALİ BUL
# ==========================================

signal_results = [
    item for item in valid
    if item["direction"] in ("LONG", "SHORT")
]

signal_results.sort(
    key=lambda x: x["score"],
    reverse=True
)

if "selected_market" not in st.session_state:

    if signal_results:
        st.session_state.selected_market = (
            signal_results[0]["market"]
        )
    else:
        st.session_state.selected_market = "EUR/USD"


selected_market = st.session_state.selected_market

selected = next(
    (
        item for item in results
        if item["market"] == selected_market
    ),
    None
)


# ==========================================
# OTOMATİK YENİLEME
# ==========================================

st_autorefresh(
    interval=300000,
    key="forex_refresh"
)


# ==========================================
# ÜST BAŞLIK
# ==========================================

st.markdown("""
<div style="
background:#111111;
border:1px solid #383838;
border-radius:14px;
padding:17px;
margin-bottom:18px;
">
<div style="
font-size:11px;
letter-spacing:3px;
color:#AAAAAA;
">
MARKET INTELLIGENCE
</div>

<div style="
font-size:29px;
font-weight:900;
color:white;
">
◈ FOREX RADAR
</div>

<div style="font-size:12px;color:#999999;">
19 PİYASA · TEKNİK ANALİZ · SİNYAL TAKİBİ
</div>
</div>
""", unsafe_allow_html=True)

left, right = st.columns([3, 1])

with left:
    st.caption(
        "Son güncelleme: "
        + datetime.now().strftime("%d.%m.%Y %H:%M")
    )

with right:
    if st.button("YENİLE", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ==========================================
# MENÜ
# ==========================================

tabs = st.tabs([
    "PİYASALAR",
    "GRAFİK",
    "HABERLER",
    "GEÇMİŞ"
])


# ==========================================
# 1. PİYASALAR
# ==========================================

with tabs[0]:

    st.markdown("### Piyasa özeti")

    long_count = sum(
        x["direction"] == "LONG" for x in valid
    )

    short_count = sum(
        x["direction"] == "SHORT" for x in valid
    )

    wait_count = sum(
        x["direction"] == "WAIT" for x in valid
    )

    a, b, c = st.columns(3)

    a.metric("LONG", long_count)
    b.metric("SHORT", short_count)
    c.metric("WAIT", wait_count)

    st.divider()

    # ANA PARİTE

    st.markdown("### Seçili piyasa")

    if selected is None or selected.get("status") != "OK":

        st.error(
            "Bu piyasa için şu anda güvenilir veri alınamıyor."
        )

    else:

        direction = selected["direction"]

        st.markdown(
            f"""
            <div class="main-card">
                <div style="font-size:13px;color:#999999;">
                    PİYASA ANALİZİ
                </div>
                <div style="
                    display:flex;
                    justify-content:space-between;
                    align-items:center;
                    margin-top:8px;
                ">
                    <div style="font-size:23px;font-weight:850;">
                        {selected["market"]}
                    </div>
                    <div class="signal-label">
                        {direction}
                    </div>
                </div>
                <div class="big-price">
                    {selected["price"]:.5f}
                </div>
                <div class="muted">
                    Teknik uyum puanı: {selected["score"]}/100
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.progress(
            min(selected["score"], 100) / 100
        )

        a, b, c = st.columns(3)

        a.metric("5 DAKİKA", selected["trend5"])
        b.metric("15 DAKİKA", selected["trend15"])
        c.metric("1 SAAT", selected["trend1"])

        if direction in ("LONG", "SHORT"):

            st.markdown("#### İşlem seviyeleri")

            a, b = st.columns(2)

            a.metric(
                "Giriş referansı",
                f'{selected["price"]:.5f}'
            )

            b.metric(
                "Stop Loss",
                f'{selected["stop_loss"]:.5f}'
            )

            a, b = st.columns(2)

            a.metric(
                "Take Profit 1",
                f'{selected["tp1"]:.5f}'
            )

            b.metric(
                "Take Profit 2",
                f'{selected["tp2"]:.5f}'
            )

        else:
            st.info(
                "Şu anda yeterli teknik uyum yok. "
                "Beklemek daha mantıklı olabilir."
            )

        with st.expander("Teknik detayları göster"):

            a, b = st.columns(2)

            a.metric("RSI", f'{selected["rsi"]:.2f}')
            b.metric("ATR", f'{selected["atr"]:.5f}')

            a, b = st.columns(2)

            a.metric(
                "Destek",
                f'{selected["support"]:.5f}'
                if selected["support"] is not None
                else "Bulunamadı"
            )

            b.metric(
                "Direnç",
                f'{selected["resistance"]:.5f}'
                if selected["resistance"] is not None
                else "Bulunamadı"
            )

            st.caption(
                f'Veri yaşı: {selected["data_age"]} dakika'
            )

    # DİĞER PİYASALAR

    st.divider()

    st.markdown("### Diğer piyasalar")

    st.caption(
        "Bir piyasaya dokunarak ana analiz ekranına geçebilirsin."
    )

    other_results = [
        item for item in results
        if item["market"] != selected_market
    ]

    other_results.sort(
        key=lambda x: (
            x.get("status") != "OK",
            -x.get("score", 0)
        )
    )

    columns = st.columns(2)

    for index, item in enumerate(other_results):

        col = columns[index % 2]

        if item.get("status") != "OK":

            label = (
                f'{item["market"]}  |  VERİ YOK'
            )

        else:

            label = (
                f'{item["market"]}  |  '
                f'{item["price"]:.5f}  |  '
                f'{item["direction"]}'
            )

        with col:

            if st.button(
                label,
                key=f'choose_{item["market"]}',
                use_container_width=True
            ):

                st.session_state.selected_market = (
                    item["market"]
                )

                st.rerun()

    st.caption(
        "Teknik uyum puanı kazanma olasılığı değildir. "
        "Sinyaller kesin işlem tavsiyesi değildir."
    )


# ==========================================
# 2. GRAFİK
# ==========================================

with tabs[1]:

    st.markdown("### Piyasa grafiği")

    chart_market = st.selectbox(
        "Parite seç",
        list(MARKETS.keys()),
        index=list(MARKETS.keys()).index(
            selected_market
        ) if selected_market in MARKETS else 0
    )

    timeframe = st.selectbox(
        "Zaman dilimi",
        ["5m", "15m", "1h", "1d"],
        format_func=lambda x: {
            "5m": "5 dakika",
            "15m": "15 dakika",
            "1h": "1 saat",
            "1d": "1 gün"
        }[x]
    )

    @st.cache_data(ttl=240)
    def get_chart(symbol, interval):

        periods = {
            "5m": "5d",
            "15m": "10d",
            "1h": "30d",
            "1d": "1y"
        }

        return yf.Ticker(symbol).history(
            period=periods[interval],
            interval=interval,
            auto_adjust=False
        )

    try:

        df = get_chart(
            MARKETS[chart_market],
            timeframe
        )

        if df.empty:

            st.warning("Grafik verisi bulunamadı.")

        else:

            df["EMA20"] = df["Close"].ewm(
                span=20,
                adjust=False
            ).mean()

            df["EMA50"] = df["Close"].ewm(
                span=50,
                adjust=False
            ).mean()

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
                name="EMA20"
            ))

            fig.add_trace(go.Scatter(
                x=df.index,
                y=df["EMA50"],
                name="EMA50"
            ))

            fig.update_layout(
                template="plotly_dark",
                height=480,
                paper_bgcolor="#050505",
                plot_bgcolor="#050505",
                font=dict(color="white"),
                xaxis_rangeslider_visible=False,
                margin=dict(l=10, r=10, t=30, b=10)
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

    except Exception as e:

        st.error("Grafik yüklenemedi: " + str(e))


# ==========================================
# 3. HABERLER
# ==========================================

with tabs[2]:

    st.markdown("### Ekonomik haber takvimi")

    st.caption(
        "Forex Factory ekonomik takvim kaynağı."
    )

    @st.cache_data(ttl=900)
    def get_news():

        url = (
            "https://nfs.faireconomy.media/"
            "ff_calendar_thisweek.xml"
        )

        response = requests.get(
            url,
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        response.raise_for_status()

        root = ET.fromstring(response.content)

        rows = []

        for event in root.findall(".//event"):

            item = {}

            for child in event:

                item[child.tag] = (
                    child.text.strip()
                    if child.text
                    else ""
                )

            rows.append(item)

        return pd.DataFrame(rows)

    try:

        news = get_news()

        if news.empty:

            st.info("Şu anda haber bulunamadı.")

        else:

            rename = {
                "title": "Haber",
                "country": "Para birimi",
                "date": "Tarih",
                "time": "Saat",
                "impact": "Önem",
                "forecast": "Beklenti",
                "previous": "Önceki",
                "actual": "Gerçekleşen"
            }

            news = news.rename(columns=rename)

            wanted = [
                "Tarih",
                "Saat",
                "Para birimi",
                "Önem",
                "Haber",
                "Beklenti",
                "Gerçekleşen",
                "Önceki"
            ]

            columns = [
                x for x in wanted
                if x in news.columns
            ]

            st.dataframe(
                news[columns],
                use_container_width=True,
                hide_index=True
            )

    except Exception as e:

        st.error(
            "Haber kaynağına şu anda erişilemiyor."
        )

        st.caption(str(e))

    st.warning(
        "Haberler bilgilendirme amaçlıdır. "
        "Haber öncesi otomatik sinyal engellemesi henüz aktif değildir."
    )


# ==========================================
# 4. SİNYAL GEÇMİŞİ
# ==========================================

with tabs[3]:

    st.markdown("### Sinyal geçmişi")

    history = get_history()

    if history.empty:

        st.info("Henüz kayıtlı sinyal bulunmuyor.")

    else:

        total = len(history)

        tp = history["status"].isin(
            ["TP1", "TP2"]
        ).sum()

        sl = (
            history["status"] == "SL"
        ).sum()

        active = (
            history["status"] == "ACTIVE"
        ).sum()

        ambiguous = (
            history["status"] == "AMBIGUOUS"
        ).sum()

        a, b, c = st.columns(3)

        a.metric("Toplam sinyal", total)
        b.metric("Hedefe ulaşan", int(tp))
        c.metric("Stop olan", int(sl))

        st.metric("Aktif sinyaller", int(active))

        closed = tp + sl

        if closed:

            st.metric(
                "Hedefe ulaşma oranı",
                f"%{tp / closed * 100:.1f}"
            )

        if ambiguous:

            st.warning(
                f"{ambiguous} sinyalde aynı mum içinde "
                "hem stop hem hedef seviyesi görülmüş. "
                "Sonuç belirsiz."
            )

        st.dataframe(
            history,
            use_container_width=True,
            hide_index=True
        )

    st.caption(
        "Geçmiş kayıtlar otomatik takip edilir. "
        "Gerçek broker işlem geçmişi değildir."
    )


# ==========================================
# ALT BİLGİ
# ==========================================

st.divider()

st.markdown("""
<div style="
text-align:center;
color:#888888;
font-size:12px;
padding:12px;
">
FOREX RADAR PRO<br>
Sadece analiz ve karar destek sistemi.<br>
Otomatik emir göndermez. Kâr garantisi vermez.
</div>
""", unsafe_allow_html=True)
