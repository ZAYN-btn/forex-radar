import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import feedparser
from datetime import datetime, timezone
from urllib.parse import quote
import requests

st.set_page_config(page_title="Forex Radar", page_icon="📊", layout="wide")
st.title("📊 Forex Radar — Forex analiz paneli")
st.caption("Mobil uyumlu karar destek paneli • Emir göndermez • Risk kontrolü ve haber takibi")

PAIRS = {
    "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "JPY=X",
    "USD/CHF": "CHF=X", "AUD/USD": "AUDUSD=X", "USD/CAD": "CAD=X",
    "NZD/USD": "NZDUSD=X", "EUR/GBP": "EURGBP=X", "EUR/JPY": "EURJPY=X",
    "GBP/JPY": "GBPJPY=X",
}
NEWS_TERMS = {
    "positive": ["rises", "gain", "gains", "surge", "strong", "growth", "beats", "hawkish", " yükseldi", "artış", "güçlü"],
    "negative": ["falls", "fall", "drop", "drops", "decline", "weak", "recession", "miss", "dovish", "düşüş", "geriledi", "zayıf"],
    "risk": ["war", "attack", "crisis", "emergency", "sanction", "default", "intervention", "shock", "savaş", "kriz", "müdahale"]
}

@st.cache_data(ttl=90, show_spinner=False)
def get_prices(symbol, interval, period):
    try:
        df = yf.download(symbol, interval=interval, period=period, auto_adjust=False, progress=False, threads=False)
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
        need = ["open", "high", "low", "close"]
        if not all(c in df.columns for c in need):
            return pd.DataFrame()
        return df.dropna(subset=need)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def get_news(pair):
    # Google News RSS is a headline discovery source, not a complete economic calendar.
    query = quote(f"{pair} forex central bank inflation interest rates economy")
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    try:
        feed = feedparser.parse(url)
        items = []
        for e in feed.entries[:15]:
            title = e.get("title", "")
            summary = e.get("summary", "")
            text = (title + " " + summary).lower()
            pos = sum(w in text for w in NEWS_TERMS["positive"])
            neg = sum(w in text for w in NEWS_TERMS["negative"])
            risk = sum(w in text for w in NEWS_TERMS["risk"])
            sentiment = "Olumlu" if pos > neg else ("Olumsuz" if neg > pos else "Belirsiz")
            items.append({
                "title": title,
                "source": e.get("source", {}).get("title", "Haber kaynağı"),
                "published": e.get("published", ""),
                "link": e.get("link", ""),
                "sentiment": sentiment,
                "risk": risk > 0
            })
        return items
    except Exception:
        return []

def indicators(df):
    d = df.copy()
    c, h, l = d.close, d.high, d.low
    d["ema20"] = c.ewm(span=20, adjust=False).mean()
    d["ema50"] = c.ewm(span=50, adjust=False).mean()
    delta = c.diff()
    up = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    d["rsi"] = 100 - 100/(1 + up/down.replace(0, np.nan))
    m = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    d["macd"] = m
    d["macd_sig"] = m.ewm(span=9, adjust=False).mean()
    d["bb_mid"] = c.rolling(20).mean()
    sd = c.rolling(20).std()
    d["bb_hi"], d["bb_lo"] = d.bb_mid + 2*sd, d.bb_mid - 2*sd
    prev = c.shift(1)
    tr = pd.concat([(h-l), (h-prev).abs(), (l-prev).abs()], axis=1).max(axis=1)
    d["atr"] = tr.rolling(14).mean()
    if "volume" in d:
        d["vol_avg"] = d.volume.rolling(20).mean()
        d["vol_ratio"] = d.volume / d.vol_avg.replace(0, np.nan)
    else:
        d["vol_ratio"] = np.nan
    d["bar_range"] = (h-l) / c
    d["range_avg"] = d.bar_range.rolling(30).mean()
    return d

def calc_signal(d, higher=None):
    x, p = d.iloc[-1], d.iloc[-2]
    score, why, flags = 0, [], []
    if x.ema20 > x.ema50: score += 2; why.append("EMA20 > EMA50: kısa/orta trend pozitif")
    else: score -= 2; why.append("EMA20 < EMA50: kısa/orta trend negatif")
    if 50 < x.rsi < 68: score += 1; why.append("RSI pozitif bölgede, aşırı alımda değil")
    elif 32 < x.rsi < 50: score -= 1; why.append("RSI negatif bölgede, aşırı satımda değil")
    elif x.rsi >= 68: flags.append("RSI yüksek: LONG kovalamak riskli")
    elif x.rsi <= 32: flags.append("RSI düşük: SHORT kovalamak riskli")
    if x.macd > x.macd_sig and x.macd > p.macd: score += 1; why.append("MACD yukarı ivmeyi destekliyor")
    elif x.macd < x.macd_sig and x.macd < p.macd: score -= 1; why.append("MACD aşağı ivmeyi destekliyor")
    if x.close > x.bb_mid: score += 1
    else: score -= 1
    if pd.notna(x.vol_ratio):
        if x.vol_ratio >= 2:
            flags.append(f"Anormal tick-volume: ortalamanın {x.vol_ratio:.1f} katı")
        elif x.vol_ratio >= 1.25:
            score += 1 if x.close > p.close else -1
            why.append("Tick-volume artışı fiyat yönünü destekliyor")
    else:
        flags.append("Hacim alanı yok: hacim teyidi yapılamadı")
    if pd.notna(x.range_avg) and x.bar_range > x.range_avg * 2.5:
        flags.append("Anormal geniş mum: volatilite sıçraması")
    if higher is not None and len(higher) and higher.iloc[-1].close > higher.iloc[-1].ema50:
        score += 1; why.append("Üst zaman dilimi EMA50 üzerinde")
    elif higher is not None and len(higher):
        score -= 1; why.append("Üst zaman dilimi EMA50 altında")
    signal = "LONG" if score >= 3 else ("SHORT" if score <= -3 else "BEKLE")
    atr = float(x.atr) if pd.notna(x.atr) else np.nan
    entry = float(x.close)
    if np.isfinite(atr) and atr > 0 and signal == "LONG":
        sl, tp1, tp2 = entry-1.5*atr, entry+1.5*atr, entry+2.5*atr
    elif np.isfinite(atr) and atr > 0 and signal == "SHORT":
        sl, tp1, tp2 = entry+1.5*atr, entry-1.5*atr, entry-2.5*atr
    else: sl = tp1 = tp2 = np.nan
    recent = d.iloc[-51:-1]
    support = float(recent.low.min()) if len(recent) else np.nan
    resistance = float(recent.high.max()) if len(recent) else np.nan
    return dict(score=score, signal=signal, entry=entry, sl=sl, tp1=tp1, tp2=tp2,
                atr=atr, rsi=float(x.rsi), support=support, resistance=resistance,
                vol_ratio=float(x.vol_ratio) if pd.notna(x.vol_ratio) else np.nan,
                why=why, flags=flags)

def fmt(v):
    return "—" if not np.isfinite(v) else f"{v:.5f}"

with st.sidebar:
    st.header("Kontrol paneli")
    pair = st.selectbox("Parite", list(PAIRS.keys()))
    tf = st.selectbox("Ana zaman dilimi", ["15 dakika", "30 dakika", "1 saat", "4 saat"], index=2)
    balance = st.number_input("Demo hesap bakiyesi", min_value=0.0, value=1000.0, step=100.0)
    risk_pct = st.slider("İşlem başına teorik risk (%)", 0.1, 1.0, 0.5, 0.1)
    st.caption("Risk hesabı yaklaşık pip/lot dönüşümü içermez; broker sözleşme özellikleri gerekir.")
    if st.button("Verileri yenile"):
        st.cache_data.clear()

cfg = {
    "15 dakika": ("15m", "5d"),
    "30 dakika": ("30m", "5d"),
    "1 saat": ("1h", "1mo"),
    "4 saat": ("1h", "3mo")
}
interval, period = cfg[tf]
with st.spinner("Piyasa verileri alınıyor..."):
    raw = get_prices(PAIRS[pair], interval, period)
    higher_raw = get_prices(PAIRS[pair], "1d", "6mo")
    news = get_news(pair)

if raw.empty or len(raw) < 60:
    st.error("Bu parite için yeterli veri alınamadı. Yahoo Finance veri kısıtları olabilir; daha sonra tekrar deneyin.")
    st.stop()
if tf == "4 saat":
    agg = {"open":"first","high":"max","low":"min","close":"last"}
    if "volume" in raw: agg["volume"] = "sum"
    raw = raw.resample("4h").agg(agg).dropna()
d = indicators(raw).dropna(subset=["ema50","rsi","atr"])
hd = indicators(higher_raw).dropna(subset=["ema50"]) if not higher_raw.empty else pd.DataFrame()
r = calc_signal(d, hd if len(hd) else None)

st.subheader(f"{pair} · {tf}")
a,b,c,dcol = st.columns(4)
a.metric("Sinyal", r["signal"], f"Puan {r['score']:+}")
b.metric("Son fiyat", fmt(r["entry"]))
c.metric("RSI", f"{r['rsi']:.1f}")
dcol.metric("ATR", fmt(r["atr"]))

chart = go.Figure([go.Candlestick(x=d.index, open=d.open, high=d.high, low=d.low, close=d.close, name="Fiyat")])
chart.add_trace(go.Scatter(x=d.index, y=d.ema20, name="EMA20"))
chart.add_trace(go.Scatter(x=d.index, y=d.ema50, name="EMA50"))
chart.add_trace(go.Scatter(x=d.index, y=d.bb_hi, name="BB üst"))
chart.add_trace(go.Scatter(x=d.index, y=d.bb_lo, name="BB alt"))
if np.isfinite(r["support"]): chart.add_hline(y=r["support"], line_dash="dot", annotation_text="Yakın destek")
if np.isfinite(r["resistance"]): chart.add_hline(y=r["resistance"], line_dash="dot", annotation_text="Yakın direnç")
chart.update_layout(height=480, xaxis_rangeslider_visible=False, margin=dict(l=5,r=5,t=25,b=5))
st.plotly_chart(chart, use_container_width=True)

st.subheader("Sinyal ve risk planı")
x1,x2 = st.columns(2)
with x1:
    st.write("**Giriş referansı:**", fmt(r["entry"]))
    st.write("**Stop-loss örneği:**", fmt(r["sl"]))
    st.write("**TP1 / TP2:**", fmt(r["tp1"]), "/", fmt(r["tp2"]))
with x2:
    st.write("**Destek / direnç:**", fmt(r["support"]), "/", fmt(r["resistance"]))
    st.write("**Tick-volume oranı:**", "—" if not np.isfinite(r["vol_ratio"]) else f"{r['vol_ratio']:.2f}x")
    st.write("**Teorik risk bütçesi:**", f"{balance*risk_pct/100:.2f} hesap para birimi")
st.caption("Lot büyüklüğü otomatik verilmez: pip değeri, hesap para birimi, broker kontratı ve spread bilinmeden güvenli hesap yapılamaz.")

st.subheader("Neden bu yönde?")
for item in r["why"]: st.write("• " + item)
if r["flags"]:
    st.subheader("Risk / anomali uyarıları")
    for item in r["flags"]: st.warning(item)

st.subheader("Piyasa haberleri")
st.caption("Başlıklar Google News RSS aramasından gelir. Otomatik duygu etiketi basit anahtar kelime taramasıdır; haberin doğruluğunu veya etkisini teyit etmez.")
if not news:
    st.info("Haber akışı alınamadı. Bağlantıyı kontrol edip yenileyin.")
else:
    for item in news[:12]:
        tag = "⚠️ Risk kelimesi" if item["risk"] else item["sentiment"]
        st.markdown(f"**{tag} · {item['source']}**  \n[{item['title']}]({item['link']})  \n<small>{item['published']}</small>", unsafe_allow_html=True)

st.subheader("Anomali tespiti neyi görebilir?")
st.write("Bu sürüm, veri sağlayıcının hacim alanı mevcutsa ortalamaya göre ani tick-volume artışını ve olağandışı geniş mumları işaretler.")
st.error("Bu, 'şüpheli işlem' veya piyasa manipülasyonu tespiti değildir. Spot Forex parçalı/OTC bir piyasadır; tek veri akışından gerçek emir defteri, büyük oyuncu işlemi veya spoofing doğrulanamaz.")

with st.expander("Kaynak, sınırlar ve güvenlik"):
    st.markdown("""
    - **Garanti işlem yoktur.** Hiçbir bot kârı veya düşük riski garanti edemez. Sinyal, olasılık tahmini değil karar destek çıktısıdır.
    - Yahoo Finance verisi gecikmeli/eksik olabilir; broker fiyatı, spread, swap, komisyon ve kayma farklıdır.
    - Spot Forex'te merkezi hacim yoktur. Tick-volume, gerçek toplam işlem hacmi değildir.
    - Haber akışı ekonomik takvim değildir. Faiz kararı, enflasyon, istihdam ve merkez bankası açıklamalarının saatleri ayrıca güvenilir takvimden kontrol edilmelidir.
    - Haber duygu etiketi basit anahtar kelime eşleştirmesidir; AI doğrulaması değildir.
    - Destek/direnç son 50 mumun ekstrem seviyeleridir; kesin seviyeler değildir.
    - Uygulama broker hesabına bağlanmaz, emir göndermez. Önce demo hesapta ve geçmiş veri üzerinde test edin.
    """)

st.download_button("Analiz verisini CSV indir", d.tail(300).to_csv().encode("utf-8"), file_name=f"{pair.replace('/','')}_analysis.csv", mime="text/csv")
