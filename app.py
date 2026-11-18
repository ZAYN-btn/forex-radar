
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

st.set_page_config(
    page_title="FOREX RADAR PRO",
    page_icon="📡",
    layout="wide"
)

DB = Path("forex_history.db")

# ---------------- STYLE ----------------

st.markdown("""
<style>
.stApp {background:#101722;color:#F1F5F9;}
.block-container {max-width:1400px;padding-top:1.5rem;}
header[data-testid="stHeader"] {background:transparent;}

div[data-testid="stMetric"] {
    background:#1B2736;
    border:1px solid #34445A;
    border-radius:12px;
    padding:13px;
}

div[data-testid="stMetricLabel"] {color:#C3D0E0 !important;}
div[data-testid="stMetricValue"] {color:white !important;}

.market-card {
    background:#1B2736;
    border:1px solid #34445A;
    border-radius:14px;
    padding:17px;
    margin-bottom:12px;
}

.long {color:#36E0A1;font-weight:800;}
.short {color:#FF7888;font-weight:800;}
.wait {color:#FFD166;font-weight:800;}
.muted {color:#B6C4D6;font-size:13px;}
.price {font-size:27px;font-weight:800;color:white;}

.stButton button {
    background:#36D9A0;
    color:#10231D;
    border:0;
    border-radius:9px;
    font-weight:800;
}

h1,h2,h3,p,label {color:#F1F5F9;}
</style>
""", unsafe_allow_html=True)

# ---------------- DATABASE ----------------

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
        for x in results:
            if x.get("status") != "OK":
                continue

            if x["direction"] not in ("LONG", "SHORT"):
                continue

            active = con.execute("""
                SELECT id FROM signals
                WHERE market=? AND status='ACTIVE'
            """, (x["market"],)).fetchone()

            if active:
                continue

            con.execute("""
                INSERT INTO signals
                (created_at, market, direction, entry, sl, tp1, tp2)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(timezone.utc).isoformat(),
                x["market"],
                x["direction"],
                x["price"],
                x["stop_loss"],
                x["tp1"],
                x["tp2"]
            ))

def update_signals(results):
    current = {
        x["market"]: x
        for x in results
        if x.get("status") == "OK"
    }

    with connect_db() as con:
        rows = con.execute("""
            SELECT id, market, direction, sl, tp1, tp2
            FROM signals WHERE status='ACTIVE'
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

# ---------------- DATA ----------------

@st.cache_data(ttl=240)
def load_results():
    return [
        analyze_market(name, symbol)
        for name, symbol in MARKETS.items()
    ]

results = load_results()

save_signals(results)
update_signals(results)

# ---------------- HEADER ----------------

st.markdown("""
<div class="market-card">
<div style="color:#36E0A1;letter-spacing:3px;font-size:12px;">
MARKET INTELLIGENCE
</div>
<div style="font-size:30px;font-weight:800;">
📡 FOREX RADAR <span style="color:#36E0A1;">PRO</span>
</div>
<div class="muted">
19 PİYASA • TEKNİK ANALİZ • HABERLER • RİSK TAKİBİ
</div>
</div>
""", unsafe_allow_html=True)

# 5 dakikada bir sayfayı yenile
refresh_count = st_autorefresh(
    interval=300000,
    key="forex_auto_refresh"
)

st.caption(
    "Son güncelleme: " +
    datetime.now().strftime("%d.%m.%Y %H:%M:%S")
)

if st.button("🔄 Şimdi yenile"):
    st.cache_data.clear()
    st.rerun()

# ---------------- MENU ----------------

tabs = st.tabs([
    "📊 Genel Bakış",
    "📈 Grafikler",
    "📰 Haberler",
    "📚 Sinyal Geçmişi",
    "🛡️ Risk Analizi"
])

# ---------------- OVERVIEW ----------------

with tabs[0]:

    st.header("Piyasa genel görünümü")

    valid = [
        x for x in results if x.get("status") == "OK"
    ]

    long_count = sum(
        x["direction"] == "LONG" for x in valid
    )
    short_count = sum(
        x["direction"] == "SHORT" for x in valid
    )
    wait_count = sum(
        x["direction"] == "WAIT" for x in valid
    )

    a,b,c,d = st.columns(4)
    a.metric("Toplam piyasa", len(MARKETS))
    b.metric("LONG", long_count)
    c.metric("SHORT", short_count)
    d.metric("WAIT", wait_count)

    st.subheader("İşlem yönleri")

    for item in results:

        if item.get("status") != "OK":
            st.warning(
                item["market"] + ": " +
                item.get("error", "Veri alınamadı")
            )
            continue

        direction = item["direction"]
        color = {
            "LONG":"#36E0A1",
            "SHORT":"#FF7888",
            "WAIT":"#FFD166"
        }[direction]

        st.markdown(f"""
        <div class="market-card">
        <div style="display:flex;justify-content:space-between;">
        <b style="font-size:21px;">{item["market"]}</b>
        <b style="color:{color};font-size:19px;">{direction}</b>
        </div>
        <div class="price">{item["price"]:.5f}</div>
        <div class="muted">
        Teknik uyum puanı: {item["score"]}/100
        </div>
        </div>
        """, unsafe_allow_html=True)

        a,b,c = st.columns(3)
        a.metric("5 DAKİKA",item["trend5"])
        b.metric("15 DAKİKA",item["trend15"])
        c.metric("1 SAAT",item["trend1"])

        a,b,c = st.columns(3)
        a.metric("RSI",f'{item["rsi"]:.2f}')
        b.metric("ATR",f'{item["atr"]:.5f}')
        c.metric("Veri yaşı",f'{item["data_age"]:.1f} dk')

        a,b = st.columns(2)
        a.metric(
            "Destek",
            f'{item["support"]:.5f}'
            if item["support"] is not None else "—"
        )
        b.metric(
            "Direnç",
            f'{item["resistance"]:.5f}'
            if item["resistance"] is not None else "—"
        )

        if direction != "WAIT":
            st.markdown("**İşlem önerisi seviyeleri**")
            st.dataframe(pd.DataFrame([
                {"Seviye":"Giriş referansı","Fiyat":item["price"]},
                {"Seviye":"Stop Loss","Fiyat":item["stop_loss"]},
                {"Seviye":"TP1","Fiyat":item["tp1"]},
                {"Seviye":"TP2","Fiyat":item["tp2"]}
            ]),use_container_width=True,hide_index=True)

        st.divider()

    st.caption(
        "Uyum puanı kazanma olasılığı değildir. "
        "Fiyatlar gecikmeli olabilir."
    )

# ---------------- CHARTS ----------------

with tabs[1]:

    st.header("Teknik grafikler")

    market = st.selectbox(
        "Piyasa",
        list(MARKETS.keys()),
        key="chart_market"
    )

    timeframe = st.selectbox(
        "Zaman dilimi",
        ["5m","15m","1h","1d"],
        format_func=lambda x:{
            "5m":"5 dakika",
            "15m":"15 dakika",
            "1h":"1 saat",
            "1d":"1 gün"
        }[x]
    )

    @st.cache_data(ttl=240)
    def get_chart(symbol, interval):
        periods = {
            "5m":"5d",
            "15m":"10d",
            "1h":"30d",
            "1d":"1y"
        }

        return yf.Ticker(symbol).history(
            period=periods[interval],
            interval=interval,
            auto_adjust=False
        )

    try:
        df = get_chart(MARKETS[market],timeframe)

        if df.empty:
            st.warning("Grafik verisi bulunamadı.")
        else:
            df["EMA20"] = df["Close"].ewm(
                span=20,adjust=False
            ).mean()

            df["EMA50"] = df["Close"].ewm(
                span=50,adjust=False
            ).mean()

            fig = go.Figure()

            fig.add_trace(go.Candlestick(
                x=df.index,
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name="Fiyat",
                increasing_line_color="#36E0A1",
                decreasing_line_color="#FF7888"
            ))

            fig.add_trace(go.Scatter(
                x=df.index,
                y=df["EMA20"],
                name="EMA20",
                line=dict(color="#FFD166")
            ))

            fig.add_trace(go.Scatter(
                x=df.index,
                y=df["EMA50"],
                name="EMA50",
                line=dict(color="#66A8FF")
            ))

            fig.update_layout(
                template="plotly_dark",
                height=520,
                paper_bgcolor="#101722",
                plot_bgcolor="#101722",
                xaxis_rangeslider_visible=False
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

    except Exception as e:
        st.error("Grafik hatası: " + str(e))

# ---------------- NEWS ----------------

with tabs[2]:

    st.header("Ekonomik haber takvimi")

    st.caption(
        "Forex Factory XML takvimi. Kaynak erişimi ve "
        "veri güncelliği ayrıca kontrol edilmelidir."
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
            headers={"User-Agent":"Mozilla/5.0"}
        )

        response.raise_for_status()

        root = ET.fromstring(response.content)
        rows = []

        for event in root.findall(".//event"):
            item = {}

            for child in event:
                item[child.tag] = (
                    child.text.strip()
                    if child.text else ""
                )

            rows.append(item)

        return pd.DataFrame(rows)

    try:
        news = get_news()

        if news.empty:
            st.info("Haber bulunamadı.")
        else:
            rename = {
                "title":"Haber",
                "country":"Para birimi",
                "date":"Tarih",
                "time":"Saat",
                "impact":"Önem",
                "forecast":"Beklenti",
                "previous":"Önceki",
                "actual":"Gerçekleşen"
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
                x for x in wanted if x in news.columns
            ]

            st.dataframe(
                news[columns],
                use_container_width=True,
                hide_index=True
            )

    except Exception as e:
        st.error(
            "Haber kaynağına erişilemiyor. "
            "Haber verisi şu an doğrulanamadı."
        )
        st.caption(str(e))

    st.warning(
        "Haber takvimi şu an bilgilendirme amaçlıdır. "
        "Haber öncesi otomatik işlem engelleme henüz aktif değildir."
    )

# ---------------- HISTORY ----------------

with tabs[3]:

    st.header("Sinyal geçmişi")

    history = get_history()

    if history.empty:
        st.info("Henüz sinyal geçmişi oluşmadı.")
    else:
        total = len(history)
        tp = history["status"].isin(["TP1","TP2"]).sum()
        sl = (history["status"]=="SL").sum()
        active = (history["status"]=="ACTIVE").sum()
        ambiguous = (history["status"]=="AMBIGUOUS").sum()

        a,b,c,d = st.columns(4)
        a.metric("Toplam",total)
        b.metric("Hedef",int(tp))
        c.metric("Stop",int(sl))
        d.metric("Aktif",int(active))

        closed = tp + sl

        if closed:
            st.metric(
                "Hedefe ulaşanların oranı",
                f"%{tp/closed*100:.1f}"
            )

        if ambiguous:
            st.warning(
                f"{ambiguous} sinyalde aynı mum içinde hem "
                "stop hem hedef seviyesi görülmüş. "
                "Sıralama bilinmediğinden sonuç belirsiz."
            )

        st.dataframe(
            history,
            use_container_width=True,
            hide_index=True
        )

    st.caption(
        "Geçmiş kayıtları fiyat seviyelerine göre otomatik "
        "takip edilir; gerçek broker işlemi değildir."
    )

# ---------------- RISK ----------------

with tabs[4]:

    st.header("Risk ve volatilite analizi")

    for item in valid:

        st.subheader(item["market"])

        direction = item["direction"]

        if direction == "WAIT":
            st.warning(
                "Şu an işlem önerisi yok. "
                "Trend koşulları yeterince uyumlu değil."
            )
            continue

        distance = abs(
            item["price"] - item["stop_loss"]
        )

        target_distance = abs(
            item["tp2"] - item["price"]
        )

        rr = (
            target_distance / distance
            if distance > 0 else 0
        )

        a,b,c = st.columns(3)

        a.metric("ATR",f'{item["atr"]:.5f}')
        b.metric("Stop mesafesi",f'{distance:.5f}')
        c.metric("TP2 risk/getiri",f"1:{rr:.2f}")

        if item["rsi"] > 70 or item["rsi"] < 30:
            st.warning(
                "RSI aşırı bölgeye yakın. "
                "Fiyat hareketine karşı dikkatli ol."
            )

        if item["atr"] / item["price"] > 0.005:
            st.warning(
                "Volatilite yüksek olabilir. "
                "İşlem riski ayrıca değerlendirilmelidir."
            )

        st.caption(
            "Bu hesaplama spread, komisyon, kayma ve "
            "broker sözleşme büyüklüğünü içermez."
        )

        st.divider()

# ---------------- FOOTER ----------------

st.markdown("""
<div style="text-align:center;padding:25px;color:#A8B6C9;">
FOREX RADAR PRO<br>
Yalnızca analiz ve karar destek sistemi.<br>
Otomatik işlem açılmaz. Hiçbir sinyal kâr garantisi vermez.
</div>
""", unsafe_allow_html=True)
