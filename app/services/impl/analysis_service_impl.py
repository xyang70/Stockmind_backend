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
        self.data_processor = data_processor or DataProcessingImpl()  # Initialize your data processing implementation
        self.llm_agent = llm_agent or GeminiAgentCommunication(model_name="gemini-2.5-flash")  # Initialize your Gemini Agent communication implementation
        self.data_provider = data_provider  or YFinanceDataProvider()# Initialize your data provider implementation
        logger.info("AnalysisServiceImpl initialized with data_processor: %s, llm_agent: %s, data_provider: %s",
                    self.data_processor.__class__.__name__,
                    self.llm_agent.__class__.__name__,
                    self.data_provider.__class__.__name__)
    def _retrieve_data(self,symbol,period,interval):
        # Implement your data retrieval logic here
        # For example, you can fetch data from an API, a database, or any other source
        return self.data_provider.get_data(symbol=symbol,period=period,interval=interval)  # Replace with actual data retrieval logic

    def analyze_data(self, symbol):

        _temp_financial_data_model = self.data_provider.get_financial_data(ticker_symbol=symbol)  # Example of using the data provider to get financial data
        _indicators_payload = self.data_processor.process_data(_temp_financial_data_model.symbol,_temp_financial_data_model.history)  # Process the financial data to extract technical indicators or other insights.
        # Pass the raw financial model and indicators separately so _send_context_to_agent
        # can combine them into the final payload. Previously we passed an already
        # combined dict which caused double-combination and attribute errors.
        result = self._send_context_to_agent(_temp_financial_data_model, _indicators_payload)  # Send processed data to the Gemini Agent for analysis
        return result  # Return the result from the LLM agent instead of processed data
    
    def _combine_context(self, financial_data, indicators_payload):
        # Implement your context combination logic here
        # For example, you can combine financial data with other information
        payload = mock_stock_context()  # Replace with actual context retrieval logic
        final_payload ={
            "financial_data": FinancialDataJsonConverter.model_to_dict(financial_data),
            "technical_indicators": indicators_payload,
        }
        return final_payload
    
    def _send_context_to_agent(self, financial_context,indicators_payload=None):
        context = self._combine_context(financial_context, indicators_payload)  # Combine financial context and indicators into a single context object
        prompt = build_prompt(context)  # Build a prompt based on the context
        response = self.llm_agent.send_request(prompt)  # Replace with actual method to send context to the agent
        return response
    def get_results(self, query):
        # Implement your result retrieval logic here
        # For example, you can query a database or an in-memory store for results based on the query
        return {"query": query, "results": "Sample results based on the query"}  # Replace with actual retrieval logic
