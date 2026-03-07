from dataclasses import dataclass,asdict
from typing_extensions import List, Optional, Literal, Dict, Any
Bias = Literal["bullish", "neutral", "bearish"]
Position = Literal["above", "below", "near"]
Cross = Literal["none", "golden", "death"]
VolumeState = Literal["below_avg", "avg", "above_avg", "spike"]
Timeframe = Literal["1m", "5m", "15m", "1h", "1d", "1wk"]


@dataclass
class NewsItem:
    title: str
    summary: str
    source: str
    url: Optional[str] = None
    
@dataclass
class TrendFeatures:
    timeframe: Timeframe
    price: float
    ema5: float
    ema20: float

    price_vs_ema5: Position
    price_vs_ema20: Position
    ema5_vs_ema20: Position

    cross: Cross                   # "golden" if ema5 crossed above ema20 recently
    bias: Bias                     # bullish/neutral/bearish
    ema20_slope: Literal["up", "flat", "down"]  # very useful filter

@dataclass
class SupportResistance:
    # give zones instead of one exact value to reduce false precision
    support_zone: Optional[List[float]] = None     # [low, high]
    resistance_zone: Optional[List[float]] = None  # [low, high]
    invalidation_level: Optional[float] = None     # where idea breaks (optional)

@dataclass
class RiskContext:
    # light, non-token-heavy risk flags
    earnings_within_days: Optional[int] = None
    high_volatility: Optional[bool] = None
    gap_risk: Optional[bool] = None
    liquidity_risk: Optional[bool] = None
@dataclass
class StockLLMContext:
    symbol: str
    today_open: float
    today_close: float
    today_high: float
    today_low: float
    today_volume: int
    ema_20: float
    ema_50: float
    trend: str
    today_volume_change: float
    volume_state : str
    news: list[NewsItem]
