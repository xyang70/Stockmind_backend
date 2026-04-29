import json
import logging
from typing import final

from app.services.analysis_service import AnalysisService
from app.services.impl.impl_data_processing import DataProcessingImpl
from app.llm_models.gemini_agent_comm import GeminiAgentCommunication
from app.data_providers.yfinance_data_provider import YFinanceDataProvider
from app.context.stock_LLM_context import StockLLMContext
from app.mocks.mock_llm_context import mock_stock_context
from app.llm_prompt.analysis_data_prompt import build_prompt
from app.data_providers.data_model.financial_data_model import FinancialDataJsonConverter
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
class AnalysisServiceImpl(AnalysisService):
    def __init__(self, data_processor=None,llm_agent=None,data_provider=None):
        super().__init__()
        self.data_processor = data_processor or DataProcessingImpl()  
        self.llm_agent = llm_agent or GeminiAgentCommunication(model_name="gemini-2.5-flash")  
        self.data_provider = data_provider  or YFinanceDataProvider()
        logger.info("AnalysisServiceImpl initialized with data_processor: %s, llm_agent: %s, data_provider: %s",
                    self.data_processor.__class__.__name__,
                    self.llm_agent.__class__.__name__,
                    self.data_provider.__class__.__name__)
        
    def _retrieve_data(self,symbol,period,interval):
      
        return self.data_provider.get_data(symbol=symbol,period=period,interval=interval) 

    def analyze_data(self, symbol):

        _temp_financial_data_model = self.data_provider.get_financial_data(ticker_symbol=symbol) 
        _indicators_payload = self.data_processor.process_data(_temp_financial_data_model.symbol,_temp_financial_data_model.history)  
        raw_result = self._send_context_to_agent(_temp_financial_data_model, _indicators_payload)  
        if hasattr(raw_result, "choices"):
            content = raw_result.choices[0].message.content
            try:
                print(content)
                content = json.loads(content)
            except (TypeError, json.JSONDecodeError):
                logger.warning("LLM response was not valid JSON; returning raw content.")
            return {
            "symbol": symbol,
            "llm_response": content
            }

        return {
            "symbol": symbol,
            "llm_response": str(raw_result)
        }

    
    def _combine_context(self, financial_data, indicators_payload):

        payload = mock_stock_context()  
        final_payload ={
            "financial_data": FinancialDataJsonConverter.model_to_dict(financial_data),
            "technical_indicators": indicators_payload,
        }
        return final_payload
    
    def _send_context_to_agent(self, financial_context,indicators_payload=None):
        context = self._combine_context(financial_context, indicators_payload)  
        prompt = build_prompt(context)  
        response = self.llm_agent.send_request(prompt)  
        return response
    def get_results(self, query):

        return {"query": query, "results": "Sample results based on the query"} 
