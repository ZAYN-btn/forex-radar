
import os
import json
import urllib.request
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

MARKETS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "XAU/USD": "XAUUSD=X",
}


def get_market_data(symbol):
    df = yf.Ticker(symbol).history(
        period="5d",
        interval="5m",
        auto_adjust=False
    )

    if df.empty or len(df) < 60:
        raise ValueError("Yeterli piyasa verisi alınamadı")

    df = df.dropna(subset=["Close", "High", "Low"]).copy()

    # EMA
    df["EMA20"] = df["Close"].ewm(span=20).mean()
    df["EMA50"] = df["Close"].ewm(span=50).mean()

    # RSI
    change = df["Close"].diff()
    gain = change.clip(lower=0).ewm(alpha=1/14).mean()
    loss = (-change.clip(upper=0)).ewm(alpha=1/14).mean()
    rs = gain / loss.replace(0, float("nan"))
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df["Close"].ewm(span=12).mean()
    ema26 = df["Close"].ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    df["MACD_HIST"] = macd - signal

    # ATR
    previous = df["Close"].shift(1)
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - previous).abs(),
        (df["Low"] - previous).abs()
    ], axis=1).max(axis=1)

    df["ATR"] = tr.rolling(14).mean()

    return df.dropna()


def analyze_market(name, symbol):
    try:
        df = get_market_data(symbol)
        row = df.iloc[-1]

        price = float(row["Close"])
        ema20 = float(row["EMA20"])
        ema50 = float(row["EMA50"])
        rsi = float(row["RSI"])
        macd = float(row["MACD_HIST"])
        atr = float(row["ATR"])

        direction = "WAIT"
        score = 0

        if price > ema20 > ema50 and 50 < rsi < 70 and macd > 0:
            direction = "LONG"
            score = 70
            score += 10 if rsi > 55 else 0
            score += 10 if price > ema20 else 0

        elif price < ema20 < ema50 and 30 < rsi < 50 and macd < 0:
            direction = "SHORT"
            score = 70
            score += 10 if rsi < 45 else 0
            score += 10 if price < ema20 else 0

        entry = price
        stop_loss = None
        take_profit_1 = None
        take_profit_2 = None

        if direction == "LONG":
            stop_loss = entry - (1.5 * atr)
            take_profit_1 = entry + (1.5 * atr)
            take_profit_2 = entry + (2.5 * atr)

        elif direction == "SHORT":
            stop_loss = entry + (1.5 * atr)
            take_profit_1 = entry - (1.5 * atr)
            take_profit_2 = entry - (2.5 * atr)

        return {
            "market": name,
            "direction": direction,
            "score": min(score, 100),
            "price": entry,
            "rsi": rsi,
            "ema20": ema20,
            "ema50": ema50,
            "stop_loss": stop_loss,
            "tp1": take_profit_1,
            "tp2": take_profit_2,
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
        raise RuntimeError("Telegram secrets eksik!")

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
        "📡 FOREX RADAR",
        "5 DAKİKALIK PİYASA ANALİZİ",
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        ""
    ]

    for item in results:
        lines.append(f"📊 {item['market']}")

        if item["status"] == "ERROR":
            lines.append("⚠️ Veri alınamadı: " + item["error"][:150])
            lines.append("")
            continue

        lines.append(f"Sinyal: {item['direction']}")
        lines.append(f"Sinyal puanı: {item['score']}/100")
        lines.append(f"Fiyat: {item['price']:.5f}")
        lines.append(f"RSI: {item['rsi']:.2f}")

        if item["direction"] != "WAIT":
            lines.append(f"Giriş: {item['price']:.5f}")
            lines.append(f"Stop Loss: {item['stop_loss']:.5f}")
            lines.append(f"TP1: {item['tp1']:.5f}")
            lines.append(f"TP2: {item['tp2']:.5f}")

        lines.append("")

    lines.append("Bilgi amaçlı teknik analizdir; garanti veya yatırım tavsiyesi değildir.")

    send_telegram("\n".join(lines))


if __name__ == "__main__":
    main()
