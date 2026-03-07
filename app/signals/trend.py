# app/signals/trend.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Literal, Optional, Dict, Any

import pandas as pd

from app.indicators.calculate_ema import calculate_ema


Bias = Literal["bullish", "neutral", "bearish"]
Position = Literal["above", "below", "near"]
Cross = Literal["none", "golden", "death"]
Slope = Literal["up", "flat", "down"]
TrendQuality = Literal["strong", "moderate", "weak"]


@dataclass(frozen=True)
class TrendSignal:
    # raw values (helpful for logging/UI)
    price: float
    ema_fast: float
    ema_slow: float

    # discrete features (best for LLM + rules)
    price_vs_fast: Position
    price_vs_slow: Position
    fast_vs_slow: Position

    cross: Cross          # golden/death if occurred within lookback window
    bias: Bias            # bullish/neutral/bearish based on alignment
    slow_slope: Slope     # slope of slow EMA (ema20) over slope_window
    trend_quality: TrendQuality

    # small metadata
    as_of: Optional[str] = None
    fast_period: int = 5
    slow_period: int = 20

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _position(value: float, ref: float, near_pct: float) -> Position:
    """
    Classify value relative to ref as above/below/near.
    near_pct is relative tolerance e.g. 0.002 = 0.2%
    """
    if ref == 0:
        return "near"
    diff_pct = (value - ref) / ref
    if abs(diff_pct) <= near_pct:
        return "near"
    return "above" if diff_pct > 0 else "below"


def _slope_label(series: pd.Series, window: int, flat_pct: float) -> Slope:
    """
    Determine slope direction over the last `window` bars.
    flat_pct is relative threshold for considering slope 'flat'.
    """
    if len(series) < window + 1:
        # not enough data; treat as flat
        return "flat"

    start = float(series.iloc[-(window + 1)])
    end = float(series.iloc[-1])

    if start == 0:
        return "flat"

    change_pct = (end - start) / abs(start)
    if abs(change_pct) <= flat_pct:
        return "flat"
    return "up" if change_pct > 0 else "down"


def _cross_event(
    fast: pd.Series, slow: pd.Series, lookback: int
) -> Cross:
    """
    Detect if a cross happened within the last `lookback` bars.
    - golden: fast crosses above slow
    - death: fast crosses below slow
    """
    n = min(len(fast), len(slow))
    if n < 2:
        return "none"

    lookback = max(1, min(lookback, n - 1))
    f = fast.iloc[-(lookback + 1):].astype(float)
    s = slow.iloc[-(lookback + 1):].astype(float)

    prev_diff = (f - s).shift(1)
    curr_diff = (f - s)

    # golden cross: prev < 0 and curr >= 0
    if ((prev_diff < 0) & (curr_diff >= 0)).any():
        return "golden"
    # death cross: prev > 0 and curr <= 0
    if ((prev_diff > 0) & (curr_diff <= 0)).any():
        return "death"
    return "none"


def _bias(price_vs_fast: Position, price_vs_slow: Position, fast_vs_slow: Position) -> Bias:
    """
    Alignment-based bias:
    bullish if price above both and fast above slow
    bearish if price below both and fast below slow
    otherwise neutral
    """
    if price_vs_fast in ("above", "near") and price_vs_slow in ("above", "near") and fast_vs_slow in ("above", "near"):
        return "bullish"
    if price_vs_fast in ("below", "near") and price_vs_slow in ("below", "near") and fast_vs_slow in ("below", "near"):
        return "bearish"
    return "neutral"


def _trend_quality(bias: Bias, slow_slope: Slope, cross: Cross, price_vs_slow: Position) -> TrendQuality:
    """
    Simple quality heuristic:
    - strong: bullish + slow up + price above/near slow, or bearish + slow down + price below/near slow
    - moderate: bias aligns but slow is flat, or recent cross with supportive position
    - weak: otherwise
    """
    if bias == "bullish" and slow_slope == "up" and price_vs_slow in ("above", "near"):
        return "strong"
    if bias == "bearish" and slow_slope == "down" and price_vs_slow in ("below", "near"):
        return "strong"

    if bias in ("bullish", "bearish") and slow_slope == "flat":
        return "moderate"
    if cross in ("golden", "death") and price_vs_slow in ("above", "below", "near"):
        return "moderate"

    return "weak"


def ema_trend_signal(
    df: pd.DataFrame,
    fast_period: int = 5,
    slow_period: int = 20,
    *,
    price_col: str = "Close",
    as_of: Optional[str] = None,
    near_pct: float = 0.002,     # 0.2% within EMA treated as "near"
    cross_lookback: int = 3,     # detect cross within last N bars
    slope_window: int = 3,       # slope over last N bars
    slope_flat_pct: float = 0.001 # 0.1% treated as flat
) -> TrendSignal:
    """
    Compute EMA fast/slow and derive trend features.
    Designed for EMA5/EMA20 but configurable.
    """
    if price_col not in df.columns:
        raise ValueError(f"Missing required column: {price_col}")

    close = df[price_col].astype(float)
    if len(close) < max(fast_period, slow_period) + 2:
        raise ValueError("Not enough rows to compute EMA signals reliably")

    ema_fast = calculate_ema(close, fast_period)
    ema_slow = calculate_ema(close, slow_period)

    price = float(close.iloc[-1])
    fast_v = float(ema_fast.iloc[-1])
    slow_v = float(ema_slow.iloc[-1])

    price_vs_fast = _position(price, fast_v, near_pct)
    price_vs_slow = _position(price, slow_v, near_pct)
    fast_vs_slow = _position(fast_v, slow_v, near_pct)

    cross = _cross_event(ema_fast, ema_slow, cross_lookback)
    slow_slope = _slope_label(ema_slow, slope_window, slope_flat_pct)
    bias = _bias(price_vs_fast, price_vs_slow, fast_vs_slow)
    quality = _trend_quality(bias, slow_slope, cross, price_vs_slow)

    return TrendSignal(
        price=round(price, 6),
        ema_fast=round(fast_v, 6),
        ema_slow=round(slow_v, 6),
        price_vs_fast=price_vs_fast,
        price_vs_slow=price_vs_slow,
        fast_vs_slow=fast_vs_slow,
        cross=cross,
        bias=bias,
        slow_slope=slow_slope,
        trend_quality=quality,
        as_of=as_of,
        fast_period=fast_period,
        slow_period=slow_period,
    )

"""
signal = ema_trend_signal(df, fast_period=5, slow_period=20, as_of=df.index[-1].isoformat())
payload = signal.to_dict()  # 直接喂给 LLM 或存 DB
"""