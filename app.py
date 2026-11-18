
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone

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

def indicators(df):
    df = df.copy()

    df["EMA20"] = df["Close"].ewm(
        span=20, adjust=False
    ).mean()

    df["EMA50"] = df["Close"].ewm(
        span=50, adjust=False
    ).mean()

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


def resample_data(df, timeframe):
    result = df.resample(timeframe).agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum"
    })

    return result.dropna()


def get_trend(row):
    if row["Close"] > row["EMA20"] > row["EMA50"]:
        return "LONG"

    if row["Close"] < row["EMA20"] < row["EMA50"]:
        return "SHORT"

    return "NEUTRAL"


def analyze_market(name, symbol):
    try:
        raw = yf.Ticker(symbol).history(
            period="5d",
            interval="5m",
            auto_adjust=False
        )

        if raw.empty or len(raw) < 100:
            raise ValueError("Yeterli 5 dakikalık veri yok")

        raw = raw.dropna(
            subset=["Open", "High", "Low", "Close"]
        )

        if raw.empty:
            raise ValueError("Eksik fiyat verisi")

        last_time = raw.index[-1]

        if last_time.tzinfo is None:
            last_time = last_time.tz_localize("UTC")

        age = (
            datetime.now(timezone.utc)
            - last_time.to_pydatetime()
        ).total_seconds() / 60

        if age > 30:
            raise ValueError("Fiyat verisi güncel değil")

        m5 = indicators(raw)
        m15 = indicators(resample_data(raw, "15min"))
        h1 = indicators(resample_data(raw, "1h"))

        if len(m5) < 2 or len(m15) < 55 or len(h1) < 55:
            raise ValueError("Zaman dilimleri için veri yetersiz")

        r5 = m5.iloc[-1]
        r15 = m15.iloc[-1]
        r1 = h1.iloc[-1]

        price = float(r5["Close"])
        rsi = float(r5["RSI"])
        atr = float(r5["ATR"])

        if atr <= 0:
            raise ValueError("ATR hesaplanamadı")

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

        support = (
            float(supports.max())
            if not supports.empty else None
        )

        resistance = (
            float(resistances.min())
            if not resistances.empty else None
        )

        sl = None
        tp1 = None
        tp2 = None

        if direction == "LONG":
            sl = price - 1.5 * atr
            tp1 = price + 1.5 * atr
            tp2 = price + 3 * atr

        elif direction == "SHORT":
            sl = price + 1.5 * atr
            tp1 = price - 1.5 * atr
            tp2 = price - 3 * atr

        return {
            "market": name,
            "direction": direction,
            "score": min(score, 100),
            "price": price,
            "rsi": rsi,
            "atr": atr,
            "trend5": trend5,
            "trend15": trend15,
            "trend1": trend1,
            "support": support,
            "resistance": resistance,
            "stop_loss": sl,
            "tp1": tp1,
            "tp2": tp2,
            "bar_high": float(r5["High"]),
            "bar_low": float(r5["Low"]),
            "data_age": round(age, 1),
            "status": "OK"
        }

    except Exception as error:
        return {
            "market": name,
            "direction": "WAIT",
            "status": "ERROR",
            "error": str(error)
        }
