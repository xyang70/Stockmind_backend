import json


def build_prompt(payload: dict) -> str:
    return f"""
You are a professional stock market analysis assistant.

Analyze the following structured market data.

Rules:
- Base analysis ONLY on provided data
- Return STRICT JSON
- No markdown
- No explanation outside JSON
- Do not include any text outside the JSON response
- Based on trend trader/right side trader principles, provide a concise analysis of the stock's current situation and potential future movements.
- Based on mid to long-term analysis
- Analyze the news, highlighting any significant events or trends that may impact the stock's performance.
- Use the following JSON schema for your response:
- Return payload should be in Chinese-simplified

Payload:
{json.dumps(payload, indent=2)}

Return JSON schema:

{{
  "summary": string,
  "sentiment": "bullish" | "neutral" | "bearish",
  "confidence": number,
  "trade_bias": "long" | "short" | "wait",
  "Should_enter_trade_now": boolean,
  "position_size": number,
  "entry_or_exit_price": number,
  "stop_loss": number,
  "take_profit": number
}}
"""