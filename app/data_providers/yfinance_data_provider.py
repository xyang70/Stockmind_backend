import yfinance as yf
import logging
from app.data_providers.data_provider import BaseDataProvider
from datetime import date
from ..signals.trend import ema_trend_signal
from app.data_providers.data_model.financial_data_model import FinancialDataModel, FinancialNewsItem
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YFinanceDataProvider(BaseDataProvider):
    def __init__(self, config):
        try:
            self.ticker = config['ticker']
            # self.start_date = config['start_date']
            # self.end_date = config['end_date']
            self.period = '1y'
        
        except KeyError as e:
            logger.error(f"Missing required config key: {e}")
            raise ValueError(f"Config missing required key: {e}")
        except Exception as e:
            logger.error(f"Error initializing YFinanceDataProvider: {e}")
            raise
    
    def get_financial_data(self,ticker_symbol) -> FinancialDataModel:
        history = self._get_data(ticker_symbol=ticker_symbol)
        news = self._get_news(ticker_symbol=ticker_symbol)
        return FinancialDataModel(
            symbol=ticker_symbol,
            history=history,
            news=news
        )
    def get_financial_data_multiple(self,ticker_symbols: list) -> list[FinancialDataModel]:
        results: list[FinancialDataModel] = []
        if not ticker_symbols:
            return results

        # batch fetch using yfinance; keep the original batch call shape
        joined = ' '.join(ticker_symbols)
        _tickers = yf.Tickers(joined)
        try:
            tickers_history = yf.download(_tickers, period=self.period)
        except Exception as e:
            logger.error(f"Batch download failed: {e}")
            tickers_history = None

        for t in ticker_symbols:
            # extract per-ticker history from the batch DataFrame when available
            history = None
            if tickers_history is not None:
                try:
                    history = tickers_history[t]
                except Exception:
                    # try MultiIndex selection (ticker as second level)
                    try:
                        history = tickers_history.xs(t, axis=1, level=1)
                    except Exception:
                        history = None

            news = self._get_news(ticker_symbol=t)
            try:
                model = FinancialDataModel(symbol=t, history=history, news=news)
                results.append(model)
            except Exception as e:
                logger.error(f"Failed to construct model for {t}: {e}")
                continue

        return results
        
    def _get_data(self,ticker_symbol):
        try:
            _ticker_obj = yf.Ticker(ticker_symbol)
            logger.info(f"Fetching historical data for {ticker_symbol}")
            data = _ticker_obj.history(period='6mo', interval='1d')
            logger.info(f"Data type: {type(data)}")
            if data.empty:
                logger.warning(f"No data returned for ticker {ticker_symbol}")
                return None
            
            logger.info(f"Successfully fetched {len(data)} records")
            return data
        
        except Exception as e:
            logger.error(f"Error fetching data for {ticker_symbol}: {e}")
            return None
    
    def _get_news(self,ticker_symbol):
        try:
            logger.info(f"Fetching news for {ticker_symbol}")
            news_summary = []
            news = yf.Ticker(ticker_symbol).news
            
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
                    news_summary.append(
                        FinancialNewsItem(
                            summary=summary,
                            title=title,
                            source=source,
                            canonicalUrl=canonicalUrl
                        )
                    )
                except (KeyError, TypeError) as e:
                    logger.warning(f"Error parsing news item {idx}: {e}")
                    continue
            
            logger.info(f"Successfully extracted {len(news_summary)} news summaries")
            return news_summary
        
        except Exception as e:
            logger.error(f"Error fetching news for {self.ticker}: {e}")
            return []
    



