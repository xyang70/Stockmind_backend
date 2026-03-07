import yfinance as yf
import logging
from app.data_providers.data_provider import BaseDataProvider
from datetime import date
from ..signals.trend import ema_trend_signal
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YFinanceDataProvider(BaseDataProvider):
    def __init__(self, config):
        try:
            self.ticker = config['ticker']
            # self.start_date = config['start_date']
            # self.end_date = config['end_date']
            # self.period = config['period']
            
            # Make single API call to fetch all ticker info
            logger.info(f"Initializing YFinanceDataProvider for ticker: {self.ticker}")
            self.ticker_obj = yf.Ticker(self.ticker)
            logger.info(f"Successfully initialized ticker: {self.ticker}")
        
        except KeyError as e:
            logger.error(f"Missing required config key: {e}")
            raise ValueError(f"Config missing required key: {e}")
        except Exception as e:
            logger.error(f"Error initializing YFinanceDataProvider: {e}")
            raise

    def get_data(self):
        try:
            logger.info(f"Fetching historical data for {self.ticker}")
            data = self.ticker_obj.history(period=self.period, interval='1d')
            
            if data.empty:
                logger.warning(f"No data returned for ticker {self.ticker}")
                return None
            
            logger.info(f"Successfully fetched {len(data)} records")
            return data
        
        except Exception as e:
            logger.error(f"Error fetching data for {self.ticker}: {e}")
            return None
    
    def get_news(self):
        try:
            logger.info(f"Fetching news for {self.ticker}")
            news_summary = []
            news = self.ticker_obj.news
            
            if not news:
                logger.warning(f"No news available for {self.ticker}")
                return []
            
            for idx, item in enumerate(news):
                try:
                    content = item.get('content', {})
                    summary = content.get('summary', 'N/A')
                    title = content.get('title', 'N/A')
                    source = content.get('provider', {}).get('displayName', 'N/A')
                    canonicalUrl = content.get('canonicalUrl', 'N/A').get('url', 'N/A')
                    print(source)
                    news_summary.append({
                        'summary': summary,
                        'title': title,
                        'source': source,
                        'url': canonicalUrl
                    })
                except (KeyError, TypeError) as e:
                    logger.warning(f"Error parsing news item {idx}: {e}")
                    continue
            
            logger.info(f"Successfully extracted {len(news_summary)} news summaries")
            return news_summary
        
        except Exception as e:
            logger.error(f"Error fetching news for {self.ticker}: {e}")
            return []
    



# if __name__ == "__main__":
#     try:
#         financial = YFinanceDataProvider({
#             'ticker': 'NVDA',
#             'start_date': '2020-01-01',
#             'end_date': date.today().strftime('%Y-%m-%d'),
#             'period': '1d'
#         })
        
#         financial_news = financial.get_news()
        
#         if financial_news:
#             print(f"\n{'='*80}")
#             print(f"News Summaries for NVDA")
#             print(f"{'='*80}\n")
            
#             for idx, news_item in enumerate(financial_news, 1):
#                 print(f"News #{idx}")
#                 print(f"Title: {news_item.get('title', 'N/A')}")
#                 print(f"Summary: {news_item.get('summary', 'N/A')}")
#                 print(f"Source: {news_item.get('source', 'N/A')}")
#                 print(f"URL: {news_item.get('url', 'N/A')}")
#                 print(f"-" * 80)
#         else:
#             print("No news available")
    
#     except ValueError as e:
#         logger.error(f"Configuration error: {e}")
#         print(f"Error: {e}")
#     except Exception as e:
#         logger.error(f"Unexpected error: {e}")
#         print(f"Unexpected error: {e}")

