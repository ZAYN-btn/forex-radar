
import os
import json
import urllib.request
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

BALANCE_USD = 10000
RISK_PERCENT = 0.5
RISK_USD = BALANCE_USD * RISK_PERCENT / 100

MARKETS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "XAU/USD": "XAUUSD=X",
}


def get_data(symbol, period, interval):
    df = yf.Ticker(symbol).history(
        period=period,
        interval=interval,
        auto_adjust=False
    )

    if df.empty or len(df) < 55:
        raise ValueError("Yeterli veri alınamadı")

    df = df.dropna(subset=["Close", "High", "Low"]).copy()

    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()

    change = df["Close"].diff()
    gain = change.clip(lower=0).ewm(
        alpha=1/14, adjust=False
    ).mean()
    loss = (-change.clip(upper=0)).ewm(
        alpha=1/14, adjust=False
    ).mean()

    rs = gain / loss.replace(0, float("nan"))
    df["RSI"] = 100 - (100 / (1 + rs))

    previous = df["Close"].shift(1)
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - previous).abs(),
        (df["Low"] - previous).abs()
    ], axis=1).max(axis=1)

    df["ATR"] = tr.rolling(14).mean()

    return df.dropna()


def get_trend(row):
    if row["Close"] > row["EMA20"] > row["EMA50"]:
        return "LONG"

    if row["Close"] < row["EMA20"] < row["EMA50"]:
        return "SHORT"

    return "NEUTRAL"


def analyze_market(name, symbol):
    try:
        source_note = "Yahoo Finance"

        try:
            m5 = get_data(symbol, "5d", "5m")
        except Exception:
            if name != "XAU/USD":
                raise

            # GC=F altın vadeli işlemidir; spot altın değildir.
            m5 = get_data("GC=F", "5d", "5m")
            source_note = "GC=F altın vadeli proxy"

        if name == "XAU/USD" and source_note == "Yahoo Finance":
            source_note = "XAU/USD veri kaynağı"

        m15 = get_data(symbol, "10d", "15m")
        h1 = get_data(symbol, "30d", "1h")

        r5 = m5.iloc[-1]
        r15 = m15.iloc[-1]
        r1 = h1.iloc[-1]

        price = float(r5["Close"])
        rsi = float(r5["RSI"])
        atr = float(r5["ATR"])

        last_time = m5.index[-1]
        if last_time.tzinfo is None:
            last_time = last_time.tz_localize("UTC")

        age_minutes = (
            datetime.now(timezone.utc) - last_time.to_pydatetime()
        ).total_seconds() / 60

        if age_minutes > 30:
            raise ValueError("Piyasa verisi güncel değil")

        trend5 = get_trend(r5)
        trend15 = get_trend(r15)
        trend1 = get_trend(r1)

        direction = "WAIT"
        score = 0

        if (
            trend5 == "LONG"
            and trend15 == "LONG"
            and trend1 == "LONG"
            and 45 < rsi < 68
        ):
            direction = "LONG"
            score = 85

            if 50 < rsi < 62:
                score += 5

        elif (
            trend5 == "SHORT"
            and trend15 == "SHORT"
            and trend1 == "SHORT"
            and 32 < rsi < 55
        ):
            direction = "SHORT"
            score = 85

            if 38 < rsi < 50:
                score += 5

        recent = m5.tail(60)

        supports = recent.loc[
            recent["Low"] < price, "Low"
        ]
        resistances = recent.loc[
            recent["High"] > price, "High"
        ]

        support = float(supports.max()) if not supports.empty else None
        resistance = (
            float(resistances.min())
            if not resistances.empty else None
        )

        stop_loss = None
        tp1 = None
        tp2 = None

        if direction == "LONG":
            stop_loss = price - (1.5 * atr)
            tp1 = price + (1.5 * atr)
            tp2 = price + (3 * atr)

        elif direction == "SHORT":
            stop_loss = price + (1.5 * atr)
            tp1 = price - (1.5 * atr)
            tp2 = price - (3 * atr)

        return {
            "market": name,
            "direction": direction,
            "score": score,
            "price": price,
            "rsi": rsi,
            "trend5": trend5,
            "trend15": trend15,
            "trend1": trend1,
            "support": support,
            "resistance": resistance,
            "stop_loss": stop_loss,
            "tp1": tp1,
            "tp2": tp2,
            "risk_usd": RISK_USD,
            "source": source_note,
            "status": "OK"
        }

    except Exception as error:
        return {
            "market": name,
            "direction": "WAIT",
            "status": "ERROR",
            "error": str(error)
        }


def send_telegram(message):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise RuntimeError("Telegram ayarları eksik!")

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": message
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        result = json.loads(response.read())

    if not result.get("ok"):
        raise RuntimeError("Telegram mesajı gönderilemedi")


def main():
    results = []

    for name, symbol in MARKETS.items():
        results.append(analyze_market(name, symbol))

    lines = [
        "📡 FOREX RADAR PRO",
        "ÇOKLU ZAMAN DİLİMİ ANALİZİ",
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        f"Demo bakiye: ${BALANCE_USD:,.0f}",
        f"İşlem başına planlanan risk: ${RISK_USD:.2f}",
        ""
    ]

    for item in results:
        lines.append("━━━━━━━━━━━━━━")
        lines.append(f"📊 {item['market']}")

        if item["status"] == "ERROR":
            lines.append("⚠️ İŞLEM ÖNERİSİ YOK")
            lines.append(item["error"][:150])
            continue

        lines.append(f"Karar: {item['direction']}")
        lines.append(f"Uyum puanı: {item['score']}/100")
        lines.append(f"Fiyat: {item['price']:.5f}")
        lines.append(f"RSI: {item['rsi']:.2f}")
        lines.append(
            f"Trend 5m / 15m / 1h: "
            f"{item['trend5']} / {item['trend15']} / {item['trend1']}"
        )

        if item["support"] is not None:
            lines.append(f"Destek: {item['support']:.5f}")

        if item["resistance"] is not None:
            lines.append(f"Direnç: {item['resistance']:.5f}")

        if item["direction"] != "WAIT":
            lines.append(f"Giriş referansı: {item['price']:.5f}")
            lines.append(f"Stop Loss: {item['stop_loss']:.5f}")
            lines.append(f"TP1: {item['tp1']:.5f}")
            lines.append(f"TP2: {item['tp2']:.5f}")
            lines.append(f"Planlanan risk bütçesi: ${RISK_USD:.2f}")
            lines.append("Lot miktarı: Aracı kurum bilgisi bekleniyor")

        lines.append(f"Veri kaynağı: {item['source']}")

    lines.extend([
        "",
        "⚠️ Ekonomik haber takvimi henüz bağlı değil.",
        "⚠️ Uyum puanı kazanma olasılığı değildir.",
        "⚠️ Fiyatlar gecikmeli olabilir.",
        "Bu sistem emir açmaz; yalnızca analiz sunar."
    ])

    send_telegram("\n".join(lines))


if __name__ == "__main__":
    main()
