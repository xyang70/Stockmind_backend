
# from pandas import DataFrame
# from pydantic import BaseModel, ConfigDict

# class FinancialNewsItem(BaseModel):               
#     summary:str
#     title:str
#     source:str
#     canonicalUrl: str

# class FinancialDataModel(BaseModel):
#     symbol: str
#     # pandas.DataFrame is not a built-in Pydantic type; allow arbitrary types
#     model_config = ConfigDict(arbitrary_types_allowed=True)
#     history: DataFrame
#     news: list[FinancialNewsItem]

import json
from typing import Any

import pandas as pd
from pandas import DataFrame
from pydantic import BaseModel, ConfigDict


class FinancialNewsItem(BaseModel):
    summary: str
    title: str
    source: str
    canonicalUrl: str


class FinancialDataModel(BaseModel):
    symbol: str
    model_config = ConfigDict(arbitrary_types_allowed=True)
    history: DataFrame
    news: list[FinancialNewsItem]


class FinancialDataJsonConverter:
    @staticmethod
    def model_to_dict(model: FinancialDataModel) -> dict:
        return {
            "symbol": model.symbol,
            "news": [item.model_dump() for item in model.news],
        }

    @staticmethod
    def model_to_json(model: FinancialDataModel, indent: int = 2) -> str:
        data = FinancialDataJsonConverter.model_to_dict(model)
        return json.dumps(data, indent=indent, ensure_ascii=False)