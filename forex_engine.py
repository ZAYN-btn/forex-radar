
import os
import json
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

STATE_FILE = "signal_state.json"
MAX_HISTORY = 500
MAX_TRADE_BARS = 96

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


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram bilgileri eksik.")
        return False

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
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
            print("Telegram API hatası:", result)
            return False

        return True

    except Exception as error:
        print("Telegram gönderim hatası:", error)
        return False


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)

        # Eski sürümdeki sinyal kayıtlarını yeni yapıya dönüştür.
        if "last_signals" not in raw:
            return {
                "last_signals": raw,
                "active_trades": {},
                "history": []
            }

        raw.setdefault("active_trades", {})
        raw.setdefault("history", [])
        return raw

    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "last_signals": {},
            "active_trades": {},
            "history": []
        }


def save_state(state):
    temporary = STATE_FILE + ".tmp"

    with open(temporary, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    os.replace(temporary, STATE_FILE)


def format_price(value):
    if value is None:
        return "-"
    if value >= 100:
        return f"{value:,.3f}"
    return f"{value:.5f}"


def analyze_market(name, symbol):
    try:
        df = yf.Ticker(symbol).history(
            period="5d",
            interval="15m",
            auto_adjust=True
        )

        if df is None or df.empty:
            return None

        df = df.dropna(subset=["Open", "High", "Low", "Close"])

        if len(df) < 55:
            print(f"{name}: Veri yetersiz.")
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
            alpha=1/14, adjust=False, min_periods=14
        ).mean()

        avg_loss = loss.ewm(
            alpha=1/14, adjust=False, min_periods=14
        ).mean()

        rs = avg_gain / avg_loss.replace(0, float("nan"))
        rsi = 100 - (100 / (1 + rs))

        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ], axis=1).max(axis=1)

        atr = tr.ewm(
            alpha=1/14, adjust=False, min_periods=14
        ).mean()

        price = float(close.iloc[-1])
        e20 = float(ema20.iloc[-1])
        e50 = float(ema50.iloc[-1])
        current_rsi = float(rsi.iloc[-1])
        current_atr = float(atr.iloc[-1])

        values = [price, e20, e50, current_rsi, current_atr]

        if not all(pd.notna(x) for x in values):
            return None

        if price <= 0 or current_atr <= 0:
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

        return {
            "signal": signal,
            "price": price,
            "score": score,
            "rsi": current_rsi,
            "atr": current_atr,
            "ema20": e20,
            "ema50": e50,
            "df": df
        }

    except Exception as error:
        print(f"{name} analiz hatası: {error}")
        return None


def open_trade(name, result):
    direction = result["signal"]
    entry = result["price"]
    atr = result["atr"]

    if direction == "LONG":
        stop = entry - 1.5 * atr
        tp1 = entry + 1.5 * atr
        tp2 = entry + 3.0 * atr
    else:
        stop = entry + 1.5 * atr
        tp1 = entry - 1.5 * atr
        tp2 = entry - 3.0 * atr

    return {
        "pair": name,
        "direction": direction,
        "entry": entry,
        "stop": stop,
        "tp1": tp1,
        "tp2": tp2,
        "score": result["score"],
        "entry_time": result["df"].index[-1].isoformat(),
        "created_at": now_iso(),
        "status": "OPEN"
    }


def close_trade(state, name, trade, exit_price, reason):
    direction = trade["direction"]
    entry = trade["entry"]

    if direction == "LONG":
        pnl_pct = (exit_price - entry) / entry * 100
    else:
        pnl_pct = (entry - exit_price) / entry * 100

    record = {
        **trade,
        "status": "CLOSED",
        "exit": exit_price,
        "exit_reason": reason,
        "pnl_pct": pnl_pct,
        "closed_at": now_iso()
    }

    state["history"].append(record)
    state["history"] = state["history"][-MAX_HISTORY:]

    del state["active_trades"][name]

    outcome = "KÂR" if pnl_pct > 0 else (
        "ZARAR" if pnl_pct < 0 else "BAŞABAŞ"
    )

    message = (
        f"📊 FOREX RADAR İŞLEM SONUCU\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Parite: {name}\n"
        f"Yön: {direction}\n"
        f"Giriş: {format_price(entry)}\n"
        f"Çıkış: {format_price(exit_price)}\n"
        f"Sonuç: {reason}\n"
        f"Durum: {outcome}\n"
        f"Fiyat değişimi: %{pnl_pct:.3f}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Bu sanal takip sonucudur; hesap bakiyesi "
        f"ve gerçek işlem maliyetleri dahil değildir."
    )

    send_telegram(message)
    print(f"{name}: İşlem kapandı: {reason}, %{pnl_pct:.3f}")


def check_open_trade(state, name, result):
    trade = state["active_trades"].get(name)

    if not trade:
        return

    df = result["df"]
    entry_time = pd.Timestamp(trade["entry_time"])

    try:
        if df.index.tz is None and entry_time.tzinfo is not None:
            entry_time = entry_time.tz_localize(None)
        elif df.index.tz is not None and entry_time.tzinfo is None:
            entry_time = entry_time.tz_localize("UTC")
    except Exception:
        pass

    candles = df[df.index > entry_time]

    # Önceki taramada kontrol edilmiş mumları tekrar sayma.
    last_checked = trade.get("last_checked")
    if last_checked:
        last_time = pd.Timestamp(last_checked)
        candles = candles[candles.index > last_time]

    for timestamp, candle in candles.iterrows():
        high = float(candle["High"])
        low = float(candle["Low"])

        direction = trade["direction"]
        stop = trade["stop"]
        tp1 = trade["tp1"]
        tp2 = trade["tp2"]

        if direction == "LONG":
            stop_hit = low <= stop
            tp2_hit = high >= tp2
            tp1_hit = high >= tp1
        else:
            stop_hit = high >= stop
            tp2_hit = low <= tp2
            tp1_hit = low <= tp1

        # Aynı mumda stop ve hedef birlikte görülürse
        # temkinli varsayımla stop önce gerçekleşmiş sayılır.
        if stop_hit:
            close_trade(state, name, trade, stop, "STOP LOSS")
            return

        if tp2_hit:
            close_trade(state, name, trade, tp2, "HEDEF 2")
            return

        if tp1_hit and not trade.get("tp1_notified"):
            trade["tp1_notified"] = True

            send_telegram(
                f"🎯 HEDEF 1 ULAŞILDI\n"
                f"Parite: {name}\n"
                f"Yön: {direction}\n"
                f"Hedef: {format_price(tp1)}\n"
                f"İşlem takip edilmeye devam ediyor."
            )

        trade["last_checked"] = timestamp.isoformat()

        # 24 saatlik yaklaşık takip süresi.
        if trade.get("bars_checked", 0) + 1 >= MAX_TRADE_BARS:
            close_trade(
                state, name, trade,
                float(candle["Close"]),
                "SÜRE DOLDU"
            )
            return

        trade["bars_checked"] = trade.get("bars_checked", 0) + 1

    state["active_trades"][name] = trade


def report_stats(state):
    history = state["history"]

    wins = sum(1 for x in history if x["pnl_pct"] > 0)
    losses = sum(1 for x in history if x["pnl_pct"] < 0)
    closed = len(history)

    win_rate = (wins / closed * 100) if closed else 0
    total_return = sum(x["pnl_pct"] for x in history)

    return (
        f"📈 FOREX RADAR PERFORMANS\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Kapanan takip: {closed}\n"
        f"Kârlı: {wins}\n"
        f"Zararlı: {losses}\n"
        f"Başarı oranı: %{win_rate:.1f}\n"
        f"Toplam fiyat değişimi: %{total_return:.3f}\n"
        f"Açık takip: {len(state['active_trades'])}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Bu oran geçmiş sanal takip sonuçlarına dayanır."
    )


def main():
    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError("Telegram Secrets eksik.")

    print("FOREX RADAR takip taraması başladı.")

    state = load_state()
    results = {}

    for name, symbol in MARKETS.items():
        print(f"{name} taranıyor...")
        result = analyze_market(name, symbol)

        if result is not None:
            results[name] = result

    if not results:
        raise RuntimeError("Hiçbir pariteden veri alınamadı.")

    # Önce açık sanal işlemleri kontrol et.
    for name, result in results.items():
        check_open_trade(state, name, result)

    # Yeni ve değişen sinyalleri değerlendir.
    for name, result in results.items():
        current = result["signal"]
        previous = state["last_signals"].get(name, {}).get("signal")

        active = state["active_trades"].get(name)

        # Ters sinyal gelirse açık işlemi mevcut fiyatla kapat.
        if active and current in ("LONG", "SHORT"):
            if current != active["direction"]:
                close_trade(
                    state,
                    name,
                    active,
                    result["price"],
                    "TERS SİNYAL"
                )
                active = None

        # Yeni sinyalde sanal takip başlat.
        if current in ("LONG", "SHORT") and active is None:
            if previous != current:
                trade = open_trade(name, result)
                trade["bars_checked"] = 0
                state["active_trades"][name] = trade

                send_telegram(
                    f"🆕 YENİ SANAL İŞLEM TAKİBİ\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"Parite: {name}\n"
                    f"Yön: {current}\n"
                    f"Giriş: {format_price(trade['entry'])}\n"
                    f"Stop: {format_price(trade['stop'])}\n"
                    f"Hedef 1: {format_price(trade['tp1'])}\n"
                    f"Hedef 2: {format_price(trade['tp2'])}\n"
                    f"Skor: {trade['score']}/100\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"Bu gerçek emir değil, sanal performans takibidir."
                )

        state["last_signals"][name] = {
            "signal": current,
            "price": result["price"],
            "updated": now_iso()
        }

    save_state(state)

    print(f"Tarama tamamlandı: {len(results)} parite.")

    # Sonuç özeti günlük değil, her taramada isteğe bağlıdır.
    print(report_stats(state))


if __name__ == "__main__":
    main()
