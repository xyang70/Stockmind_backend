from dataclasses import asdict
from app.context.stock_LLM_context import StockLLMContext, NewsItem

def mock_stock_context() -> dict:
    context = StockLLMContext(
        symbol="AAPL",
        today_open=185.2,
        today_close=188.7,
        today_high=189.5,
        today_low=184.9,
        today_volume=72_500_000,
        ema_20=182.3,
        ema_50=176.8,
        trend="bullish",
        today_volume_change=0.18,
        volume_state="above_avg",
        news=[
            NewsItem(
                title="Apple announces new AI features",
                summary="Apple Inc. unveiled new AI-powered features in its latest product update, aiming to enhance user experience across its ecosystem.",
                source="Reuters",
                url="https://www.reuters.com/technology/apple-announces-new-ai-features-2024-06-01/",
            ),
            NewsItem(
                title="Analysts raise Apple price target",
                summary="Several analysts have raised their price targets for Apple Inc. following strong sales reports and optimistic forecasts for the upcoming quarter.",
                source="Bloomberg",
                url="https://www.bloomberg.com/news/articles/2024-06-02/analysts-raise-apple-price-target-on-strong-sales",
            ),
        ],
    )
    return asdict(context)