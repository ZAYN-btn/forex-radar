
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import requests
import sqlite3
from datetime import datetime
from xml.etree import ElementTree as ET
from streamlit_autorefresh import st_autorefresh
from forex_engine import MARKETS, analyze_market

# ---------------- PAGE ----------------

st.set_page_config(
    page_title="FOREX RADAR",
    page_icon="📈",
    layout="wide"
)

st_autorefresh(interval=300000, key="forex_refresh")

st.markdown("""
<style>
.stApp {
    background: #080808;
    color: #f5f5f5;
}
.block-container {
    padding-top: 1.5rem;
    max-width: 1250px;
}
h1, h2, h3 {
    color: white !important;
}
div[data-testid="stMetric"] {
    background: #151515;
    border: 1px solid #292929;
    padding: 14px;
    border-radius: 12px;
}
div.stButton > button {
    width: 100%;
    background: #171717;
    color: white;
    border: 1px solid #333;
    border-radius: 10px;
    min-height: 43px;
}
div.stButton > button:hover {
    border-color: white;
    color: white;
}
.trade-card {
    background: #111111;
    border: 1px solid #333333;
    border-radius: 18px;
    padding: 25px;
    margin: 10px 0 20px 0;
}
.trade-direction {
    font-size: 38px;
    font-weight: 900;
    margin: 8px 0;
}
.price {
    font-size: 34px;
    font-weight: 800;
    margin: 8px 0 20px 0;
}
.trade-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
}
.trade-item {
    background: #1b1b1b;
    border: 1px solid #303030;
    border-radius: 11px;
    padding: 13px;
}
.trade-label {
    color: #999;
    font-size: 12px;
}
.trade-value {
    color: white;
    font-size: 19px;
    font-weight: 700;
    margin-top: 5px;
}
.section-title {
    font-size: 20px;
    font-weight: 800;
    margin: 28px 0 12px 0;
}
.small-muted {
    color: #888;
    font-size: 12px;
}
</style>
""", unsafe_allow_html=True)


# ---------------- DATABASE ----------------

DB = "forex_history.db"

def connect_db():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    with connect_db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market TEXT,
            direction TEXT,
            price REAL,
            score INTEGER,
            created_at TEXT
        )
        """)

def save_signals(results):
    with connect_db() as conn:
        for item in results:
            if item.get("status") == "OK":
                conn.execute("""
                INSERT INTO signals
                (market, direction, price, score, created_at)
                VALUES (?, ?, ?, ?, ?)
                """, (
                    item.get("market"),
                    item.get("direction"),
                    item.get("price"),
                    item.get("score"),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))

def get_history():
    with connect_db() as conn:
        return pd.read_sql_query(
            "SELECT * FROM signals ORDER BY id DESC LIMIT 200",
            conn
        )

init_db()


# ---------------- MARKET DATA ----------------

@st.cache_data(ttl=240)
def load_results():
    results = []
    for name, symbol in MARKETS.items():
        try:
            result = analyze_market(name, symbol)
            results.append(result)
        except Exception as error:
            results.append({
                "market": name,
                "direction": "WAIT",
                "status": "ERROR",
                "error": str(error)
            })
    return results

results = load_results()

if not results:
    st.error("Piyasa verisi alınamadı.")
    st.stop()

save_signals(results)

valid_results = [
    x for x in results if x.get("status") == "OK"
]

# ---------------- HEADER ----------------

st.markdown("# FOREX RADAR")
st.caption("Forex piyasa analiz ve sinyal paneli")

col1, col2 = st.columns([3, 1])

with col1:
    st.caption("Teknik analiz • Çoklu zaman dilimi • Risk takibi")

with col2:
    st.caption(
        "Son yenileme: " +
        datetime.now().strftime("%H:%M:%S")
    )

st.divider()


# ---------------- MARKET SELECTION ----------------

market_names = list(MARKETS.keys())

if "selected_market" not in st.session_state:
    st.session_state.selected_market = (
        "EUR/USD" if "EUR/USD" in market_names
        else market_names[0]
    )

if st.session_state.selected_market not in market_names:
    st.session_state.selected_market = market_names[0]

selected = next(
    (
        x for x in results
        if x.get("market") == st.session_state.selected_market
    ),
    None
)

if selected is None:
    st.error("Seçilen piyasa bulunamadı.")
    st.stop()


# ---------------- MAIN TRADE CARD ----------------

st.markdown(
    '<div class="section-title">ANA İŞLEM ANALİZİ</div>',
    unsafe_allow_html=True
)

direction = selected.get("direction", "WAIT")
price = selected.get("price")
score = selected.get("score", 0)

if direction == "LONG":
    direction_color = "#21c77a"
    direction_text = "LONG"
    direction_desc = "Alış yönlü işlem sinyali"
elif direction == "SHORT":
    direction_color = "#ff5252"
    direction_text = "SHORT"
    direction_desc = "Satış yönlü işlem sinyali"
else:
    direction_color = "#aaaaaa"
    direction_text = "WAIT"
    direction_desc = "Şu an uygun işlem sinyali yok"

def fmt(value):
    if value is None:
        return "—"
    try:
        if pd.isna(value):
            return "—"
        return f"{float(value):.5f}"
    except (TypeError, ValueError):
        return "—"

if selected.get("status") != "OK":
    st.error(
        "Bu paritenin verisi alınamadı: " +
        str(selected.get("error", "Bilinmeyen hata"))
    )
else:
    entry = selected.get("price")
    sl = selected.get("stop_loss")
    tp1 = selected.get("tp1")
    tp2 = selected.get("tp2")

    st.markdown(f"""
    <div class="trade-card">
        <div style="color:#999;font-size:14px;">
            {selected.get("market", "")}
        </div>
        <div class="trade-direction" style="color:{direction_color};">
            {direction_text}
        </div>
        <div style="color:#aaa;font-size:13px;">
            {direction_desc}
        </div>
        <div class="price">{fmt(price)}</div>
        <div class="trade-grid">
            <div class="trade-item">
                <div class="trade-label">GİRİŞ FİYATI</div>
                <div class="trade-value">{fmt(entry)}</div>
            </div>
            <div class="trade-item">
                <div class="trade-label">SİNYAL PUANI</div>
                <div class="trade-value">{score}/100</div>
            </div>
            <div class="trade-item">
                <div class="trade-label">STOP LOSS</div>
                <div class="trade-value">{fmt(sl)}</div>
            </div>
            <div class="trade-item">
                <div class="trade-label">TAKE PROFIT 1</div>
                <div class="trade-value">{fmt(tp1)}</div>
            </div>
            <div class="trade-item">
                <div class="trade-label">TAKE PROFIT 2</div>
                <div class="trade-value">{fmt(tp2)}</div>
            </div>
            <div class="trade-item">
                <div class="trade-label">RSI</div>
                <div class="trade-value">{fmt(selected.get("rsi"))}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if direction == "WAIT":
        st.info(
            "Sistem şu anda yeterli LONG veya SHORT koşulu görmüyor. "
            "İşlem açmak için acele etme."
        )

    st.caption(
        "LONG = alış yönü | SHORT = satış yönü | "
        "WAIT = bekle. Sinyal puanı başarı olasılığı değildir."
    )


# ---------------- MARKET SUMMARY ----------------

st.markdown(
    '<div class="section-title">PİYASA ÖZETİ</div>',
    unsafe_allow_html=True
)

long_count = sum(
    1 for x in valid_results if x.get("direction") == "LONG"
)
short_count = sum(
    1 for x in valid_results if x.get("direction") == "SHORT"
)
wait_count = sum(
    1 for x in results if x.get("direction") == "WAIT"
)

c1, c2, c3 = st.columns(3)

with c1:
    st.metric("ALIŞ SİNYALİ", long_count)

with c2:
    st.metric("SATIŞ SİNYALİ", short_count)

with c3:
    st.metric("BEKLEMEDE", wait_count)


# ---------------- OTHER MARKETS ----------------

st.markdown(
    '<div class="section-title">DİĞER PİYASALAR</div>',
    unsafe_allow_html=True
)

st.caption("Bir pariteye dokunarak ana işlem kartını değiştirebilirsin.")

other_results = [
    x for x in results
    if x.get("market") != st.session_state.selected_market
]

for start in range(0, len(other_results), 2):
    cols = st.columns(2)

    for index, item in enumerate(other_results[start:start + 2]):
        with cols[index]:
            name = item.get("market", "Bilinmeyen")
            direction = item.get("direction", "WAIT")
            price = fmt(item.get("price"))
            score = item.get("score", 0)

            if direction == "LONG":
                symbol = "🟢"
            elif direction == "SHORT":
                symbol = "🔴"
            else:
                symbol = "⚪"

            label = (
                f"{symbol} {name}  |  {direction}  |  "
                f"{price}  |  {score}/100"
            )

            if st.button(label, key=f"market_{name}"):
                st.session_state.selected_market = name
                st.rerun()


# ---------------- TABS ----------------

st.divider()

tab_chart, tab_news, tab_history, tab_risk = st.tabs([
    "GRAFİK",
    "EKONOMİK TAKVİM",
    "SİNYAL GEÇMİŞİ",
    "RİSK ANALİZİ"
])


# ---------------- CHART ----------------

with tab_chart:
    st.subheader("Fiyat grafiği")

    chart_market = st.selectbox(
        "Grafik paritesi",
        market_names,
        index=market_names.index(st.session_state.selected_market),
        key="chart_market"
    )

    symbol = MARKETS[chart_market]

    try:
        chart_data = yf.Ticker(symbol).history(
            period="5d",
            interval="15m"
        )

        if chart_data.empty:
            st.warning("Grafik verisi alınamadı.")
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
                paper_bgcolor="#080808",
                plot_bgcolor="#080808",
                height=500,
                xaxis_rangeslider_visible=False
            )

            st.plotly_chart(fig, use_container_width=True)

    except Exception as error:
        st.error(f"Grafik hatası: {error}")


# ---------------- ECONOMIC CALENDAR ----------------

with tab_news:
    st.subheader("Ekonomik takvim")

    st.caption(
        "Forex Factory takvim kaynağından alınabilen etkinlikler gösterilir. "
        "Kaynak verisi her zaman eksiksiz veya anlık olmayabilir."
    )

    try:
        response = requests.get(
            "https://nfs.faireconomy.media/ff_calendar_thisweek.xml",
            timeout=12,
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
            st.info("Takvimde gösterilecek etkinlik bulunamadı.")

    except Exception as error:
        st.warning(f"Ekonomik takvim alınamadı: {error}")


# ---------------- HISTORY ----------------

with tab_history:
    st.subheader("Sinyal geçmişi")

    history = get_history()

    if history.empty:
        st.info("Henüz kayıtlı sinyal yok.")
    else:
        st.dataframe(
            history,
            use_container_width=True,
            hide_index=True
        )

    st.caption(
        "Bu bölüm geçmiş sinyal kayıtlarını gösterir. "
        "Tek başına kâr veya başarı oranı anlamına gelmez."
    )


# ---------------- RISK ----------------

with tab_risk:
    st.subheader("Risk analizi")

    st.write(
        "Sistem işlem yönü ve teknik seviyeler üretir. "
        "Bunlar kesin sonuç veya garanti kâr anlamına gelmez."
    )

    if selected.get("status") == "OK":
        atr = selected.get("atr")
        price = selected.get("price")

        st.write(f"**Seçili piyasa:** {selected.get('market')}")
        st.write(f"**İşlem yönü:** {selected.get('direction')}")
        st.write(f"**Fiyat:** {fmt(price)}")
        st.write(f"**ATR (oynaklık ölçüsü):** {fmt(atr)}")

        if atr and price:
            atr_percent = float(atr) / float(price) * 100
            st.metric("ATR / Fiyat", f"%{atr_percent:.3f}")

        st.info(
            "ATR yükseldikçe fiyatın hareket alanı genişliyor demektir. "
            "Bu, tek başına işlem açma nedeni değildir."
        )

    st.warning(
        "Bu panel otomatik emir göndermez. İşlem açmadan önce "
        "spread, kaldıraç, haber riski ve kendi zarar sınırını kontrol et."
    )


# ---------------- FOOTER ----------------

st.divider()

st.caption(
    "FOREX RADAR • Analiz amaçlıdır. "
    "Veriler Yahoo Finance üzerinden gelebilir ve gecikmeli olabilir. "
    "Hiçbir LONG veya SHORT sinyali garanti kazanç sağlamaz."
)
