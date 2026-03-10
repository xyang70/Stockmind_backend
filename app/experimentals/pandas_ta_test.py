import pandas as pd
import numpy as np
import yfinance as yf
import pandas_ta as ta
import json


class MarketAnalyzer:
    def __init__(
        self,

    ):
        self.ticker = None
        self.interval = '1d'
        self.period = '1y'
        self.df = pd.DataFrame()
    def load_data(self, symbol: str, df: pd.DataFrame = None) -> pd.DataFrame:
        self.ticker = symbol
        if df is not None:
            self.df = df.copy()

        if df.empty:
            raise ValueError(f"No data returned for ticker={self.ticker}")

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        self.df = df.copy()
        return self.df

    def add_indicators(self) -> pd.DataFrame:
        if self.df.empty:
            raise ValueError("DataFrame is empty. Call load_data() first.")

        df = self.df.copy()

        df["ema20"] = ta.ema(df["Close"], length=20)
        df["ema50"] = ta.ema(df["Close"], length=50)
        df["rsi14"] = ta.rsi(df["Close"], length=14)
        df["atr14"] = ta.atr(df["High"], df["Low"], df["Close"], length=14)
        df["chop14"] = ta.chop(df["High"], df["Low"], df["Close"], length=14)

        macd = ta.macd(df["Close"], fast=12, slow=26, signal=9)
        if macd is not None and not macd.empty:
            df = df.join(macd)

        adx = ta.adx(df["High"], df["Low"], df["Close"], length=14)
        if adx is not None and not adx.empty:
            df = df.join(adx)

        bb = ta.bbands(df["Close"], length=20, std=2)
        if bb is not None and not bb.empty:
            df = df.join(bb)

            upper_cols = [c for c in bb.columns if c.startswith("BBU_")]
            middle_cols = [c for c in bb.columns if c.startswith("BBM_")]
            lower_cols = [c for c in bb.columns if c.startswith("BBL_")]

            if upper_cols and middle_cols and lower_cols:
                upper = upper_cols[0]
                middle = middle_cols[0]
                lower = lower_cols[0]
                df["bb_upper"] = df[upper]
                df["bb_middle"] = df[middle]
                df["bb_lower"] = df[lower]
                df["bb_width"] = (df[upper] - df[lower]) / df[middle]
            else:
                df["bb_upper"] = np.nan
                df["bb_middle"] = np.nan
                df["bb_lower"] = np.nan
                df["bb_width"] = np.nan
        else:
            df["bb_upper"] = np.nan
            df["bb_middle"] = np.nan
            df["bb_lower"] = np.nan
            df["bb_width"] = np.nan

        df["ema20_slope"] = (df["ema20"] - df["ema20"].shift(5)) / 5
        df["ema50_slope"] = (df["ema50"] - df["ema50"].shift(5)) / 5
        df["ema_gap_pct"] = (df["ema20"] - df["ema50"]).abs() / df["Close"]

        self.df = df
        return self.df

    def classify_market_regime(
        self,
        adx_threshold: float = 20,
        chop_threshold: float = 55,
        ema_gap_threshold: float = 0.01,
        slope_threshold_ratio: float = 0.002,
    ) -> pd.DataFrame:
        if self.df.empty:
            raise ValueError("DataFrame is empty. Call load_data() and add_indicators() first.")

        df = self.df.copy()
        df["market_regime"] = "unclear"

        range_cond = (
            (df["ADX_14"] < adx_threshold) &
            (df["chop14"] > chop_threshold) &
            (df["ema_gap_pct"] < ema_gap_threshold) &
            (df["ema20_slope"].abs() < df["Close"] * slope_threshold_ratio)
        )

        uptrend_cond = (
            (df["ADX_14"] >= adx_threshold) &
            (df["chop14"] < chop_threshold) &
            (df["Close"] > df["ema20"]) &
            (df["ema20"] > df["ema50"])
        )

        downtrend_cond = (
            (df["ADX_14"] >= adx_threshold) &
            (df["chop14"] < chop_threshold) &
            (df["Close"] < df["ema20"]) &
            (df["ema20"] < df["ema50"])
        )

        df.loc[range_cond, "market_regime"] = "range"
        df.loc[uptrend_cond, "market_regime"] = "uptrend"
        df.loc[downtrend_cond, "market_regime"] = "downtrend"

        self.df = df
        return self.df

    @staticmethod
    def _find_swing_points(df: pd.DataFrame, left: int = 3, right: int = 3) -> pd.DataFrame:
        df = df.copy()
        df["swing_high"] = np.nan
        df["swing_low"] = np.nan

        for i in range(left, len(df) - right):
            high = df["High"].iloc[i]
            low = df["Low"].iloc[i]

            left_highs = df["High"].iloc[i-left:i]
            right_highs = df["High"].iloc[i+1:i+1+right]

            left_lows = df["Low"].iloc[i-left:i]
            right_lows = df["Low"].iloc[i+1:i+1+right]

            if high > left_highs.max() and high > right_highs.max():
                df.iloc[i, df.columns.get_loc("swing_high")] = high

            if low < left_lows.min() and low < right_lows.min():
                df.iloc[i, df.columns.get_loc("swing_low")] = low

        return df

    @staticmethod
    def _cluster_prices(prices: list[float], tolerance_pct: float = 0.01) -> list[dict]:
        if not prices:
            return []

        prices = sorted(prices)
        clusters = [[prices[0]]]

        for p in prices[1:]:
            cluster_mean = float(np.mean(clusters[-1]))
            if abs(p - cluster_mean) / cluster_mean <= tolerance_pct:
                clusters[-1].append(p)
            else:
                clusters.append([p])

        zones = []
        for c in clusters:
            zones.append({
                "center": float(np.mean(c)),
                "low": float(np.min(c)),
                "high": float(np.max(c)),
                "touches": len(c),
            })

        return zones

    @staticmethod
    def _score_support_zones(df: pd.DataFrame, zones: list[dict]) -> list[dict]:
        current_price = float(df["Close"].iloc[-1])
        scored = []

        for z in zones:
            center = z["center"]
            touches = z["touches"]
            distance_pct = abs(current_price - center) / current_price
            score = touches * 10 - distance_pct * 100

            scored.append({
                "type": "support",
                "center": center,
                "zone_low": z["low"],
                "zone_high": z["high"],
                "touches": touches,
                "distance_pct": distance_pct,
                "score": score,
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    @staticmethod
    def _score_resistance_zones(df: pd.DataFrame, zones: list[dict]) -> list[dict]:
        current_price = float(df["Close"].iloc[-1])
        scored = []

        for z in zones:
            center = z["center"]
            touches = z["touches"]
            distance_pct = abs(current_price - center) / current_price
            score = touches * 10 - distance_pct * 100

            scored.append({
                "type": "resistance",
                "center": center,
                "zone_low": z["low"],
                "zone_high": z["high"],
                "touches": touches,
                "distance_pct": distance_pct,
                "score": score,
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    def find_support_resistance_zones(
        self,
        swing_left: int = 3,
        swing_right: int = 3,
        lookback: int = 180,
        tolerance_pct: float = 0.01,
    ) -> tuple[list[dict], list[dict]]:
        if self.df.empty:
            raise ValueError("DataFrame is empty. Call previous steps first.")

        df = self._find_swing_points(self.df, left=swing_left, right=swing_right)
        recent = df.tail(lookback)

        swing_lows = recent["swing_low"].dropna().tolist()
        swing_highs = recent["swing_high"].dropna().tolist()

        support_zones = self._cluster_prices(swing_lows, tolerance_pct=tolerance_pct)
        resistance_zones = self._cluster_prices(swing_highs, tolerance_pct=tolerance_pct)

        scored_supports = self._score_support_zones(df, support_zones)
        scored_resistances = self._score_resistance_zones(df, resistance_zones)

        self.df = df
        return scored_supports, scored_resistances

    def get_nearest_levels(
        self,
        support_zones: list[dict],
        resistance_zones: list[dict]
    ) -> tuple[dict | None, dict | None]:
        current_price = float(self.df["Close"].iloc[-1])

        below_supports = [z for z in support_zones if z["center"] < current_price]
        above_resistances = [z for z in resistance_zones if z["center"] > current_price]

        nearest_support = max(below_supports, key=lambda z: z["center"]) if below_supports else None
        nearest_resistance = min(above_resistances, key=lambda z: z["center"]) if above_resistances else None

        return nearest_support, nearest_resistance

    @staticmethod
    def _safe_float(value):
        if pd.isna(value):
            return None
        return float(value)

    @staticmethod
    def _safe_timestamp(value):
        if pd.isna(value):
            return None
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return str(value)

    def build_llm_payload(
        self,
        recent_bars_count: int = 40,
        top_zone_count: int = 5,
        include_full_zone_list: bool = False,
    ) -> dict:
        if self.df.empty:
            raise ValueError("DataFrame is empty. Run the analysis first.")

        support_zones, resistance_zones = self.find_support_resistance_zones(
            swing_left=3,
            swing_right=3,
            lookback=180,
            tolerance_pct=0.01
        )
        nearest_support, nearest_resistance = self.get_nearest_levels(
            support_zones,
            resistance_zones
        )

        df = self.df.copy()
        latest = df.iloc[-1]
        current_price = float(latest["Close"])

        macd_col = next((c for c in df.columns if c.startswith("MACD_")), None)
        macds_col = next((c for c in df.columns if c.startswith("MACDs_")), None)
        macdh_col = next((c for c in df.columns if c.startswith("MACDh_")), None)

        recent_cols = [
            "Open", "High", "Low", "Close", "Volume",
            "ema20", "ema50", "rsi14", "ADX_14", "DMP_14", "DMN_14",
            "chop14", "atr14", "bb_upper", "bb_middle", "bb_lower",
            "bb_width", "ema20_slope", "ema50_slope", "ema_gap_pct",
            "market_regime", "swing_high", "swing_low"
        ]

        if macd_col:
            recent_cols.append(macd_col)
        if macds_col:
            recent_cols.append(macds_col)
        if macdh_col:
            recent_cols.append(macdh_col)

        recent_cols = [c for c in recent_cols if c in df.columns]

        recent_bars_df = df[recent_cols].tail(recent_bars_count).copy()

        recent_bars = []
        for idx, row in recent_bars_df.iterrows():
            bar = {
                "timestamp": self._safe_timestamp(idx)
            }
            for col in recent_cols:
                if col == "market_regime":
                    bar[col] = None if pd.isna(row[col]) else str(row[col])
                else:
                    bar[col] = self._safe_float(row[col])
            recent_bars.append(bar)

        distance_to_support_pct = None
        if nearest_support is not None:
            distance_to_support_pct = (current_price - nearest_support["center"]) / current_price

        distance_to_resistance_pct = None
        if nearest_resistance is not None:
            distance_to_resistance_pct = (nearest_resistance["center"] - current_price) / current_price

        payload = {
            "ticker": self.ticker,
            "timeframe": self.interval,
            "period": self.period,
            "current_price": current_price,
            "current_timestamp": self._safe_timestamp(df.index[-1]),
            "market_regime": None if pd.isna(latest.get("market_regime")) else str(latest.get("market_regime")),
            "latest_indicator_snapshot": {
                "ema20": self._safe_float(latest.get("ema20")),
                "ema50": self._safe_float(latest.get("ema50")),
                "rsi14": self._safe_float(latest.get("rsi14")),
                "adx14": self._safe_float(latest.get("ADX_14")),
                "dmp14": self._safe_float(latest.get("DMP_14")),
                "dmn14": self._safe_float(latest.get("DMN_14")),
                "chop14": self._safe_float(latest.get("chop14")),
                "atr14": self._safe_float(latest.get("atr14")),
                "ema20_slope": self._safe_float(latest.get("ema20_slope")),
                "ema50_slope": self._safe_float(latest.get("ema50_slope")),
                "ema_gap_pct": self._safe_float(latest.get("ema_gap_pct")),
                "macd": self._safe_float(latest.get(macd_col)) if macd_col else None,
                "macd_signal": self._safe_float(latest.get(macds_col)) if macds_col else None,
                "macd_hist": self._safe_float(latest.get(macdh_col)) if macdh_col else None,
                "bb_upper": self._safe_float(latest.get("bb_upper")),
                "bb_middle": self._safe_float(latest.get("bb_middle")),
                "bb_lower": self._safe_float(latest.get("bb_lower")),
                "bb_width": self._safe_float(latest.get("bb_width")),
            },
            "level_summary": {
                "nearest_support": nearest_support,
                "nearest_resistance": nearest_resistance,
                "distance_to_support_pct": distance_to_support_pct,
                "distance_to_resistance_pct": distance_to_resistance_pct,
                "top_support_zones": support_zones[:top_zone_count],
                "top_resistance_zones": resistance_zones[:top_zone_count],
            },
            "recent_bars": recent_bars,
        }

        if include_full_zone_list:
            payload["all_support_zones"] = support_zones
            payload["all_resistance_zones"] = resistance_zones

        return payload

    def run_analysis(self) -> dict:
        self.load_data()
        self.add_indicators()
        self.classify_market_regime()

        support_zones, resistance_zones = self.find_support_resistance_zones(
            swing_left=3,
            swing_right=3,
            lookback=180,
            tolerance_pct=0.01
        )

        nearest_support, nearest_resistance = self.get_nearest_levels(
            support_zones, resistance_zones
        )

        current_price = float(self.df["Close"].iloc[-1])
        current_regime = self.df["market_regime"].iloc[-1]

        return {
            "ticker": self.ticker,
            "current_price": current_price,
            "current_regime": current_regime,
            "nearest_support": nearest_support,
            "nearest_resistance": nearest_resistance,
            "support_zones": support_zones,
            "resistance_zones": resistance_zones,
            "data": self.df
        }
    def analyze_technical_indicators(self,symbol,df)-> dict:
        self.load_data(symbol, df)
        self.add_indicators()
        self.classify_market_regime()

        payload = self.build_llm_payload(
            recent_bars_count=30,
            top_zone_count=3,
            include_full_zone_list=False
        )

        return payload

# def test_pandas_ta():
#     analyzer = MarketAnalyzer(
#         ticker="INTU",
#         period="1y",
#         interval="1d",
#         auto_adjust=True
#     )

#     analyzer.load_data()
#     analyzer.add_indicators()
#     analyzer.classify_market_regime()

#     payload = analyzer.build_llm_payload(
#         recent_bars_count=30,
#         top_zone_count=3,
#         include_full_zone_list=False
#     )

#     print(json.dumps(payload, indent=2, ensure_ascii=False))


# if __name__ == "__main__":
#     test_pandas_ta()

