# LLM Stock Analysis Platform

A **production-grade, enterprise-level stock analysis platform** that leverages large language models (LLMs) combined with real-time financial data and advanced technical indicators to deliver AI-powered trading insights.

---

## 🔧 Getting Started

### **Prerequisites**
- Python 3.9+
- Redis server (for job queue)
- API Keys: Google Gemini, OpenRouter (optional)

### **Installation**
```bash
# Clone repository
git clone <repo_url>
cd llm_stock_analysis

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys and configuration
```

### **Running the Application**

**Start API Server:**
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Start Background Worker:**
```bash
arq app.worker.WorkerSettings     
```

**API Documentation:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### **Example Usage**
```bash
# Submit analysis job
POST http://localhost:8000/us/stocks/analysis
Body
{
    "symbol": "rklb",
    "llm_agent_request": {
        "agent_name": "open_router",
        "model": "openrouter/elephant-alpha"
    }
}

# Response:
{
    "success": true,
    "message": "Analysis job queued successfully",
    "data": {
        "job_id": {{job_id}},
        "status": "queued"
    },
    "error": null,
    "timestamp": "timestamp"
}

## To get/poll result, retreive job_id from above:
  GET localhost:8000/us/stocks/analysis/{{job_id}}

```
*Project uses OpenRouter api for quick LLMs swapping, please update/refer to list of supported LLMs in app/config/open_router.yml*


---
## Project Overview

This project demonstrates **full-stack software engineering** with emphasis on:
- **Scalable async architecture** built with FastAPI
- **Multi-LLM integration** with dynamic provider selection
- **Advanced financial analysis** combining technical indicators with AI
- **Microservices-ready design** with distributed job processing
- **Production-grade code quality** with clean architecture patterns

### Key Capabilities
- Real-time stock analysis with AI-generated trading recommendations (bilingual support)
- Comprehensive technical analysis (10+ indicators: EMA, MACD, RSI, ATR, Bollinger Bands, etc.)
- Non-blocking async job queue for long-running analysis tasks
- Multi-provider LLM support (Google Gemini, OpenRouter)
- RESTful API with structured JSON responses

---

## 🛠 Technology Stack

### **Backend & Web Framework**
- **FastAPI** (0.129.0) - Modern async REST API framework with automatic OpenAPI docs
- **Uvicorn** (0.41.0) - Production ASGI application server
- **Pydantic** (2.12.5) - Runtime data validation with type safety
- **Python 3.9+** - Language

### **Data Processing & Analysis**
- **Pandas** (3.0.0) - Data manipulation and analysis
- **NumPy** (2.2.6) - Numerical computing
- **pandas-ta** (0.4.71b0) - Technical analysis indicators library
- **yfinance** (1.2.0) - Yahoo Finance real-time data provider
- **Numba** (0.61.2) - JIT compilation for numerical optimization

### **LLM Integration**
- **Google GenAI** (1.64.0) - Gemini API client
- **OpenAI** (2.26.0) - OpenAI API integration
- **httpx** (0.28.1) - Async HTTP client with connection pooling

### **Async Job Queue & Caching**
- **ARQ** - Redis-based distributed async task queue
- **Redis** - In-memory data store for job state management
- **asyncio** - Python's async/await framework

### **Configuration & Security**
- **Pydantic Settings** - Environment-based configuration management
- **python-dotenv** - Environment variable loading
- **PyYAML** (6.0.3) - Structured configuration parsing

### **Utilities**
- **tenacity** (9.1.4) - Retry logic with exponential backoff
- **BeautifulSoup4** (4.14.3) - Web scraping support
- **tqdm** - Progress tracking

---

## 🏗 Architecture

### **System Design**
```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Server                        │
│  (RESTful API Gateway with request orchestration)       │
│  - CORS middleware for cross-origin requests            │
│  - Health checks and status monitoring                  │
└──────────────────┬──────────────────────────────────────┘
                   │
        ┌──────────┴──────────┬─────────────────┐
        │                     │                 │
   ┌────▼────┐         ┌────▼────┐      ┌─────▼──────┐
   │ Redis   │         │ yFinance │      │ LLM Router │
   │ Job     │         │ Data     │      │ (Multi-    │
   │ Queue   │         │ Provider │      │  Provider) │
   └────┬────┘         └────┬────┘      └─────┬──────┘
        │                   │                  │
   ┌────▼──────────────────▼──────────────────▼────┐
   │        ARQ Worker (Background Task Processor)  │
   │  - Dequeues analysis tasks                     │
   │  - Orchestrates data retrieval                 │
   │  - Computes technical indicators               │
   │  - Routes to LLM provider                      │
   │  - Persists structured results                 │
   └─────────────────────────────────────────────────┘
```

### **Design Patterns Implemented**
| Pattern | Purpose | Benefit |
|---------|---------|---------|
| **Factory Pattern** | LLMModelFactory, DataProviderFactory | Abstraction, loose coupling, runtime selection |
| **Dependency Injection** | FastAPI dependencies, constructor injection | Testability, flexibility, mocking support |
| **Abstract Base Classes** | Interface contracts (AnalysisService, BaseDataProvider) | Polymorphism, contract enforcement |
| **Builder Pattern** | LLMConfigBuilder | Centralized configuration construction |
| **Singleton Pattern** | App lifecycle objects (redis, llm_factory) | Single instance per application |
| **Strategy Pattern** | Multiple LLM strategies | Interchangeable algorithm implementations |

### **API Endpoints**
```
POST   /us/stocks/analysis          - Submit async analysis job
GET    /us/stocks/analysis/{job_id} - Poll job status and results
GET    /health                      - Health check
GET    /status                      - Server and worker status
GET    /available-models            - List configured LLM models
```

### **Data Flow**
```
1. API Request (ticker, timeframe)
        ↓
2. Job Enqueue to Redis Queue
        ↓
3. ARQ Worker Pickup
        ↓
4. Fetch Financial Data (yFinance)
        ↓
5. Calculate Technical Indicators (EMA, RSI, MACD, etc.)
        ↓
6. Build LLM Prompt with Market Context
        ↓
7. Route to Multi-LLM Factory (Gemini/OpenRouter)
        ↓
8. Generate AI Trading Recommendations
        ↓
9. Structure & Persist Results (JSON)
        ↓
10. Client Poll for Results
```

---

## ⚡ Performance Optimizations

### **Async-First Architecture**
- **Non-blocking I/O** - All network calls use async/await
- **Concurrent Processing** - Multiple requests processed simultaneously
- **Event Loop Optimization** - AsyncClient connection pooling (15s timeout)
- **Worker Scalability** - Multiple ARQ workers can process jobs in parallel

### **Database & Caching**
- **Redis Connection Pooling** - Reusable connections prevent overhead
- **Technical Indicator Caching** - Pre-computed once per analysis cycle
- **Result Persistence** - Async writes to Redis store

### **Numerical Computation**
- **Numba JIT Compilation** - C-speed execution for numerical loops
- **NumPy Vectorization** - Bulk operations instead of Python loops
- **Batch Processing** - Technical analysis computed on entire OHLCV arrays

### **Threading for Blocking I/O**
- `asyncio.to_thread()` - Prevents event loop blocking
- Worker uses thread pool for blocking analysis operations

### **HTTP Client Optimization**
- **httpx.AsyncClient** - Connection reuse and keep-alive
- **Request Timeout** - 15 second deadline for external APIs
- **Retry Logic** - Tenacity with exponential backoff

### **Code-Level Optimizations**
- Pydantic model caching for validation
- Lazy loading of LLM models
- Configuration externalization (avoid runtime parsing)

---

## 📊 Technical Features

### **Technical Indicators Computed**
Market regime classification based on:
- **Trend**: EMA20, EMA50, EMA200, MACD, ADX, slope analysis
- **Volatility**: ATR (14), Bollinger Bands (20, 2σ), Keltner Channels
- **Momentum**: RSI (14), CHOP, Stochastic Oscillator
- **Volume**: OBV, VWAP, CMF (20), Volume MA (20)
- **Market Regime**: Uptrend, Downtrend, Range-bound, Consolidation classification

### **LLM Analysis Output** (JSON Schema)
```json
{
  "summary": "Market analysis with actionable insights (Chinese/English)",
  "sentiment": "bullish | neutral | bearish",
  "current_trend": "uptrend | downtrend | rangebound | consolidation",
  "key_support_resistance_levels": ["level1", "level2", ...],
  "confidence": 0.85,
  "trade_bias": "long | short | wait | swing trade",
  "trade_action": "enter | exit | hold",
  "entry_or_exit_price": 150.25,
  "stop_loss": 148.50,
  "take_profit": 155.75,
  "rationale": "Detailed explanation"
}
```

---

## 🚀 Key Achievements

✅ **Enterprise Architecture** - Clean code with clear separation of concerns  
✅ **Async-Driven Performance** - 100% non-blocking I/O for scalability  
✅ **Multi-LLM Support** - Abstracted provider interface supporting Gemini, OpenAI, custom models  
✅ **Distributed Job Processing** - Redis + ARQ for horizontal scaling  
✅ **Type Safety** - Full Pydantic validation with static type hints  
✅ **Technical Analysis Engine** - 10+ indicators with real-time computation  
✅ **Production Readiness** - Error handling, logging, health checks  
✅ **Configuration Management** - Environment-driven, DRY principle  
✅ **Microservices-Ready** - Separate API and worker processes  
✅ **Real-Time Data Integration** - Live Yahoo Finance feeds  

---

## 📁 Project Structure

```
app/
├── main.py                      # Application entry point
├── server.py                    # FastAPI app initialization
├── worker.py                    # ARQ job worker
├── settings.py                  # Pydantic settings (env config)
├── config_builder.py            # Configuration factory
├── dependencies.py              # FastAPI dependency injection
│
├── services/
│   ├── analysis_service.py      # Service interface
│   └── impl/
│       ├── analysis_service_impl.py    # Business logic
│       └── impl_data_processing.py     # Technical analysis
│
├── llm_models/
│   ├── llm_model_factory.py     # LLM provider factory
│   ├── LLM_communications.py    # LLM interface
│   ├── gemini_agent_comm.py     # Gemini implementation
│   └── open_router_agent_communication.py  # OpenRouter impl
│
├── data_providers/
│   ├── data_provider_factory.py # Data provider factory
│   ├── data_provider.py         # Provider interface
│   ├── yfinance_data_provider.py # Yahoo Finance impl
│   └── data_model/
│       └── financial_data_model.py  # Data structures
│
├── llm_prompt/
│   └── analysis_data_prompt.py  # Prompt engineering
│
├── request_models/
│   └── analysis_request.py      # API request schemas
│
├── context/
│   └── stock_LLM_context.py     # LLM context building
│
├── signals/
│   ├── trend.py                 # Market regime detection
│   └── indicators/
│       └── calculate_ema.py     # Indicator calculations
│
├── config/
│   └── open_router.yml          # LLM model configuration
│
└── mocks/
    └── mock_llm_context.py      # Testing utilities
```



## 📈 Why This Project Stands Out

1. **Full-Stack Engineering** - Demonstrates backend, data processing, ML integration, and deployment knowledge
2. **Production-Ready Code** - Error handling, logging, configuration management
3. **Advanced Design Patterns** - Factory, DI, Builder patterns for maintainability
4. **Scalable Architecture** - Async + job queue = horizontal scaling
5. **Real-World Application** - Solves actual fintech use case
6. **Multi-Provider Integration** - Shows API abstraction and integration skills
7. **Performance Conscious** - Async, caching, JIT compilation considerations
8. **Type Safety** - Pydantic validation and type hints throughout

---

## 📝 License

[Specify your license here]

---

**Built with**: FastAPI • Redis • Pandas • Google Gemini • OpenAI • Python Async • Clean Architecture
