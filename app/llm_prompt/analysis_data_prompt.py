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
- Use the following JSON schema for your response:

Payload:
{json.dumps(payload, indent=2)}

Return JSON schema:

{{
  "summary": string,
  "sentiment": "bullish" | "neutral" | "bearish",
  "confidence": number,
  "trade_bias": "long" | "short" | "wait"
  "entry_or_exit_price": number,
  "stop_loss": number,
  "take_profit": number
}}
"""