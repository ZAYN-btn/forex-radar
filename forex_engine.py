
import os
import json
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

STATE_FILE = "signal_state.json"

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


def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram bilgileri eksik.")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        response = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": message,
                "disable_web_page_preview": True
            },
            timeout=20
        )

        response.raise_for_status()
        result = response.json()

        if not result.get("ok"):
            print("Telegram API mesajı kabul etmedi:", result)
            return False

        return True

    except Exception as error:
        print("Telegram gönderim hatası:", error)
        return False


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(state, file, indent=2, ensure_ascii=False)


def analyze_market(name, symbol):
    try:
        df = yf.Ticker(symbol).history(
            period="5d",
            interval="15m",
            auto_adjust=True
        )

        if df is None or df.empty or len(df) < 55:
            print(f"{name}: Yetersiz veri.")
            return None

        df = df.dropna(subset=["Close", "High", "Low"])

        if len(df) < 55:
            return None

        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        ema20 = close.ewm(span=20, adjust=False).mean()
        ema50 = close.ewm(span=50, adjust=False).mean()

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

        rs = avg_gain / avg_loss.replace(0, float("nan"))
        rsi = 100 - (100 / (1 + rs))

        true_range = pd.concat(
            [
                high - low,
                (high - close.shift()).abs(),
                (low - close.shift()).abs()
            ],
            axis=1
        ).max(axis=1)

        atr = true_range.ewm(
            alpha=1/14,
            adjust=False,
            min_periods=14
        ).mean()

        price = float(close.iloc[-1])
        e20 = float(ema20.iloc[-1])
        e50 = float(ema50.iloc[-1])
        current_rsi = float(rsi.iloc[-1])
        current_atr = float(atr.iloc[-1])

        if not all(map(
            lambda x: pd.notna(x) and x > 0,
            [price, e20, e50, current_atr]
        )):
            return None

        if pd.isna(current_rsi):
            return None

        score = 50

        if e20 > e50:
            score += 20
        else:
            score -= 20

        if price > e20:
            score += 15
        else:
            score -= 15

        if current_rsi > 55:
            score += 15
        elif current_rsi < 45:
            score -= 15

        score = max(0, min(100, score))

        if score >= 65:
            signal = "LONG"
        elif score <= 35:
            signal = "SHORT"
        else:
            signal = "WAIT"

        if signal == "LONG":
            stop = price - (current_atr * 1.5)
            target1 = price + (current_atr * 1.5)
            target2 = price + (current_atr * 3)
        elif signal == "SHORT":
            stop = price + (current_atr * 1.5)
            target1 = price - (current_atr * 1.5)
            target2 = price - (current_atr * 3)
        else:
            stop = None
            target1 = None
            target2 = None

        return {
            "signal": signal,
            "price": price,
            "score": score,
            "rsi": current_rsi,
            "atr": current_atr,
            "stop": stop,
            "target1": target1,
            "target2": target2
        }

    except Exception as error:
        print(f"{name} analiz hatası: {error}")
        return None


def format_price(price):
    if price is None:
        return "-"
    if price >= 100:
        return f"{price:,.3f}"
    return f"{price:.5f}"


def create_message(name, result):
    signal = result["signal"]

    if signal == "LONG":
        emoji = "🟢"
    elif signal == "SHORT":
        emoji = "🔴"
    else:
        emoji = "🟡"

    message = (
        f"{emoji} FOREX RADAR SİNYALİ\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Parite: {name}\n"
        f"Sinyal: {signal}\n"
        f"Fiyat: {format_price(result['price'])}\n"
        f"Teknik skor: {result['score']}/100\n"
        f"RSI: {result['rsi']:.1f}\n"
    )

    if signal != "WAIT":
        message += (
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Stop Loss: {format_price(result['stop'])}\n"
            f"Hedef 1: {format_price(result['target1'])}\n"
            f"Hedef 2: {format_price(result['target2'])}\n"
        )

    message += (
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Zaman: {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')}\n"
        f"Periyot: 15 dakika\n\n"
        f"Not: Teknik analiz sinyalidir, garanti işlem değildir. "
        f"Spread, kayma ve ekonomik haberleri ayrıca kontrol et."
    )

    return message


def main():
    print("FOREX RADAR taraması başladı.")

    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError("Telegram GitHub Secrets eksik.")

    old_state = load_state()
    new_state = {}
    results = {}

    for name, symbol in MARKETS.items():
        print(f"{name} analiz ediliyor...")
        result = analyze_market(name, symbol)

        if result is None:
            continue

        results[name] = result
        new_state[name] = {
            "signal": result["signal"],
            "price": result["price"],
            "updated": datetime.now(timezone.utc).isoformat()
        }

    if not results:
        raise RuntimeError("Hiçbir pariteden geçerli veri alınamadı.")

    # İlk çalıştırmada mevcut sinyalleri tek özet mesajla bildir.
    if not old_state:
        actionable = [
            (name, result)
            for name, result in results.items()
            if result["signal"] in ("LONG", "SHORT")
        ]

        if actionable:
            lines = [
                "🚀 FOREX RADAR İLK TARAMA",
                "━━━━━━━━━━━━━━━━━━"
            ]

            for name, result in actionable:
                lines.append(
                    f"{name}: {result['signal']} | "
                    f"{format_price(result['price'])} | "
                    f"Skor: {result['score']}/100"
                )

            lines.append(
                "\nBu ilk tarama özetidir. "
                "Sinyaller garanti işlem değildir."
            )

            send_telegram("\n".join(lines))
        else:
            send_telegram(
                "🟡 FOREX RADAR aktif.\n"
                "İlk tarama tamamlandı. Şu anda LONG veya SHORT "
                "eşiklerini geçen sinyal bulunamadı."
            )

    else:
        # Yalnızca sinyal değiştiğinde mesaj gönder.
        for name, result in results.items():
            previous = old_state.get(name, {}).get("signal")
            current = result["signal"]

            if previous != current:
                message = create_message(name, result)

                if send_telegram(message):
                    print(f"{name}: Yeni sinyal gönderildi.")
                else:
                    print(f"{name}: Telegram mesajı gönderilemedi.")

    save_state(new_state)

    print(
        f"Tarama tamamlandı. "
        f"{len(results)}/{len(MARKETS)} pariteden veri alındı."
    )


if __name__ == "__main__":
    main()
