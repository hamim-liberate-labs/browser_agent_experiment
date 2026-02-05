# Browser Agent Experiment

AI-powered course discovery system for Udemy, featuring conversational search, comparison, and learning path recommendations.

## Project Structure

```
Browser Agent Experiment/
├── udemy_gpt/                  # Main application package
│   ├── __init__.py             # Package exports
│   ├── __main__.py             # Entry point: python -m udemy_gpt
│   ├── cli.py                  # Command-line interface
│   ├── exceptions.py           # Custom exception classes
│   │
│   ├── config/                 # Configuration management
│   │   ├── __init__.py
│   │   └── settings.py         # Pydantic settings with env support
│   │
│   ├── core/                   # Core agent logic
│   │   ├── __init__.py
│   │   ├── agent.py            # Main UdemyGPT orchestrator
│   │   └── handlers/           # Intent handlers
│   │       ├── search.py       # Search/recommend handler
│   │       ├── compare.py      # Comparison handler
│   │       ├── details.py      # Course details handler
│   │       ├── learning_path.py
│   │       └── chat.py         # General chat handler
│   │
│   ├── data/                   # Data access layer
│   │   ├── repository.py       # CSV loading and caching
│   │   └── topic_index.py      # Topic indexing and validation
│   │
│   ├── models/                 # Data models
│   │   ├── course.py           # Course, TopicStats, CourseDetails
│   │   ├── intent.py           # IntentClassification
│   │   └── state.py            # ConversationState
│   │
│   ├── prompts/                # LLM prompt templates
│   │   ├── loader.py           # YAML prompt loader
│   │   └── templates/          # YAML prompt files
│   │       ├── intent.yml
│   │       ├── analysis.yml
│   │       └── response.yml
│   │
│   ├── services/               # Business logic services
│   │   ├── llm_service.py      # LLM client with retry
│   │   ├── browser_service.py  # Playwright automation
│   │   ├── course_service.py   # Course operations
│   │   └── intent_service.py   # Intent classification
│   │
│   └── utils/                  # Utility functions
│       ├── parsers.py          # JSON, filter, rating parsers
│       └── formatters.py       # Course display formatters
│
├── udemy_scraper/              # Course scraping module
│   ├── __init__.py             # Package exports
│   ├── __main__.py             # Entry point: python -m udemy_scraper
│   ├── cli.py                  # Command-line interface
│   ├── exceptions.py           # Custom exceptions
│   │
│   ├── config/                 # Configuration management
│   │   └── settings.py         # Pydantic settings
│   │
│   ├── core/                   # Core scraping logic
│   │   └── scraper.py          # UdemyScraper orchestrator
│   │
│   ├── data/                   # Data access layer
│   │   ├── topic_repository.py # Topic loading from CSV
│   │   └── course_writer.py    # Course CSV output
│   │
│   ├── models/                 # Data models
│   │   ├── topic.py            # Topic model
│   │   ├── course.py           # ScrapedCourse model
│   │   └── result.py           # ScrapeResult, ScrapeSummary
│   │
│   └── services/               # Services
│       ├── browser_service.py  # Playwright automation
│       └── extraction_service.py # DOM extraction
│
├── udemy_agent/            # LangGraph multi-agent system
│   ├── __init__.py             # Package exports
│   ├── __main__.py             # Entry point: python -m udemy_agent
│   ├── cli.py                  # Command-line interface
│   ├── exceptions.py           # Custom exceptions
│   │
│   ├── config/                 # Configuration management
│   │   └── settings.py         # Pydantic settings
│   │
│   ├── core/                   # Core agent logic
│   │   ├── agent.py            # UdemyAgent class
│   │   └── workflows/          # LangGraph workflows
│   │       ├── chat.py         # Chat supervisor workflow
│   │       ├── browser.py      # Browser worker workflow
│   │       └── detail.py       # Course detail workflow
│   │
│   ├── data/                   # Data access layer
│   │   └── knowledge_base.py   # Topics, URLs, selectors
│   │
│   ├── models/                 # Data models
│   │   ├── filters.py          # BrowserFilters
│   │   └── state.py            # Chat and Browser state
│   │
│   ├── prompts/                # LLM prompts
│   │   └── templates.py        # All prompt templates
│   │
│   └── services/               # Services
│       ├── llm_service.py      # LLM client
│       └── browser_service.py  # Browser automation
│
├── udemy_data/                 # Course data directory
│   ├── courses/                # Course CSV files by section
│   └── udemy_topics_from_network.csv
│
├── pyproject.toml              # Project configuration
├── .env.example                # Environment template
└── README.md                   # This file
```

## Quick Start

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
```

2. Install dependencies:
```bash
uv sync
```

3. Install Playwright browsers:
```bash
uv run playwright install chromium
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your API keys
```

### Running the Modules

This project contains three modules. Here's how to run each:

#### 1. Udemy GPT (CSV-based conversational agent)
```bash
uv run python -m udemy_gpt          # Run as module
uv run udemy-gpt                    # Run as CLI script
uv run udemy-gpt --help             # Show help
```

#### 2. Udemy Scraper (Course data scraper)
```bash
uv run python -m udemy_scraper      # Run as module
uv run udemy-scraper                # Run as CLI script
uv run udemy-scraper --help         # Show help
uv run udemy-scraper --headless     # Run headless
uv run udemy-scraper --no-skip      # Re-scrape existing
```

#### 3. Udemy Agent (Live browser agent)
```bash
uv run python -m udemy_agent    # Run as module
uv run udemy-agent              # Run as CLI script
uv run udemy-agent --help       # Show help
uv run udemy-agent --headless   # Run headless
uv run udemy-agent -v           # Verbose logging
```

### Which Module to Use?

| Module | Use Case | Data Source |
|--------|----------|-------------|
| **udemy_gpt** | Conversational search, comparisons, learning paths | Pre-scraped CSV files |
| **udemy_scraper** | Populate/refresh the CSV knowledge base | Live Udemy website |
| **udemy_agent** | Real-time queries with latest data | Live Udemy website |

**Recommended workflow:**
1. Run `udemy-scraper` to populate the knowledge base
2. Use `udemy-gpt` for fast conversational queries (uses cached data)
3. Use `udemy-agent` when you need real-time data from Udemy

---

## Udemy GPT

The main conversational agent for course discovery using pre-scraped CSV data.

### CLI Commands

| Command    | Description                    |
|------------|--------------------------------|
| `/help`    | Show help information          |
| `/topics`  | List available topics          |
| `/stats`   | Show knowledge base statistics |
| `/session` | Show current session stats     |
| `/clear`   | Clear conversation history     |
| `/quit`    | Exit the application           |

### Example Queries

**Search:**
```
Find Python courses for beginners
Top 10 AI courses with rating 4.5+
Machine learning courses under $50
```

**Comparisons:**
```
Compare course 1 and 2
Python vs JavaScript courses
```

**Learning Paths:**
```
How to become a data scientist
Learning path for full-stack developer
```

**Course Details:**
```
Tell me about course 3
Get live details for course 1
```

### Programmatic Usage

```python
import asyncio
from udemy_gpt import UdemyGPT

async def main():
    agent = UdemyGPT()

    response = await agent.chat("Find Python courses for beginners")
    print(response)

    response = await agent.chat("Compare course 1 and 2")
    print(response)

    await agent.close()

asyncio.run(main())
```

## Configuration

Environment variables:

| Variable           | Default                          | Description              |
|--------------------|----------------------------------|--------------------------|
| `GROQ_API_KEY`     | (required)                       | Groq API key             |
| `LLM_BASE_URL`     | `https://api.groq.com/openai/v1` | LLM API endpoint         |
| `LLM_MODEL`        | `openai/gpt-oss-20b`             | Model to use             |
| `UDEMY_DATA_DIR`   | `./udemy_data`                   | Data directory path      |
| `BROWSER_HEADLESS` | `true`                          | Run browser headless     |
| `LOG_LEVEL`        | `INFO`                           | Logging level            |

Optional for LangSmith tracing:
```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=udemy-agent
```

## Architecture

### Request Flow

```
User Query
    │
    ▼
UdemyGPT.chat()
    │
    ▼
IntentService.classify()  ──► LLMService
    │
    ▼
Handler (search/compare/details/...)
    │
    ├──► CourseService ──► Data Layer (CSV)
    │
    ├──► BrowserService (if live data needed)
    │
    ▼
LLMService.call() ──► Generate Response
    │
    ▼
Formatted Response
```

### Layer Responsibilities

| Layer    | Purpose                                    |
|----------|--------------------------------------------|
| Core     | Agent orchestration, intent routing        |
| Services | Business logic (LLM, browser, courses)     |
| Data     | CSV loading, caching, topic management     |
| Models   | Type-safe data structures                  |
| Utils    | Parsing and formatting utilities           |

---

## Udemy Scraper

Scrapes Udemy course listings and saves them to CSV files organized by topic. Run this first to populate the knowledge base for `udemy_gpt`.

**Running:**
```bash
# Run scraper with defaults
uv run python -m udemy_scraper

# Or using CLI script
uv run udemy-scraper

# CLI options
udemy-scraper --help          # Show help
udemy-scraper --no-skip       # Re-scrape existing topics
udemy-scraper --headless      # Run browser headless
```

**Configuration:**
| Variable                 | Default | Description                    |
|--------------------------|---------|--------------------------------|
| `BROWSER_HEADLESS`       | `false` | Run browser headless           |
| `BROWSER_TIMEOUT`        | `30000` | Browser timeout in ms          |
| `SCRAPER_CLOUDFLARE_WAIT`| `30`    | Cloudflare wait time (seconds) |
| `SCRAPER_MIN_DELAY`      | `1.5`   | Min delay between requests     |
| `SCRAPER_MAX_DELAY`      | `2.5`   | Max delay between requests     |
| `SCRAPER_PAGES_PER_TOPIC`| `2`     | Pages to scrape per topic      |

**Programmatic Usage:**
```python
import asyncio
from udemy_scraper import UdemyScraper

async def main():
    scraper = UdemyScraper()
    summary = await scraper.run(skip_existing=True)
    print(f"Scraped {summary.total_courses} courses")

asyncio.run(main())
```

---

## Udemy Agent

Multi-agent system using LangGraph for complex queries with live browser data. Unlike `udemy_gpt`, this fetches real-time data from Udemy.

**Running:**
```bash
# Run interactive CLI
uv run python -m udemy_agent

# Or using CLI script
uv run udemy-agent

# CLI options
udemy-agent --help          # Show help
udemy-agent --headless      # Run browser headless
udemy-agent -v              # Verbose logging
```

**Configuration:**
| Variable              | Default                | Description              |
|-----------------------|------------------------|--------------------------|
| `GROQ_API_KEY`        | (required)             | Groq API key             |
| `LLM_MODEL`           | `openai-gpt-oss-20b`   | Model name               |
| `BROWSER_HEADLESS`    | `false`                | Run browser headless     |
| `LANGCHAIN_TRACING_V2`| `false`                | Enable LangSmith tracing |
| `LANGCHAIN_API_KEY`   | (optional)             | LangSmith API key        |
| `LANGCHAIN_PROJECT`   | `udemy-agent`          | LangSmith project name   |

**Programmatic Usage:**
```python
import asyncio
from udemy_agent import UdemyAgent

async def main():
    agent = UdemyAgent()
    response = await agent.chat("Find trending Python courses")
    print(response)
    await agent.close()

asyncio.run(main())
```

---

## Development

### Code Style
```bash
uv run ruff check .
uv run ruff format .
```

### Type Checking
```bash
uv run mypy udemy_gpt
```

## License

MIT License
