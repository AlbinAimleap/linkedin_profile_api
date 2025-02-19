
# LinkedIn Profile Scraper API

A FastAPI-based service for scraping LinkedIn profiles with caching and background task processing capabilities.

## Features

- Profile search and scraping from LinkedIn
- Redis-based caching of search results
- Background task processing
- Streaming API responses
- Docker containerization
- Rate limiting and error handling

## Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.9+
- Redis

### Environment Variables

Create a `.env` file based on `.env.example`:


LINKEDIN_EMAIL = 'your-linkedin-email'
LINKEDIN_PASSWORD = 'your-linkedin-password'
GOOGLE_SEARCH_ENGINE_APIKEY = "your-google-api-key"


### Installation

1. Clone the repository:

git clone <repository-url>
cd linkedin-scraper


2. Start the services using Docker Compose:

docker-compose up -d


The API will be available at `http://localhost:8000`

## API Endpoints

### 1. Stream Profile Search

GET /stream?query={search_query}

Streams profile results as they are scraped.

### 2. Batch Profile Search

GET /search?query={search_query}

Returns all profile results in a single response.

### 3. Queue Background Task

GET /queue?query={search_query}

Queues a scraping task and returns a task ID.

### 4. Get Task Status

GET /tasks

Returns the status of all tasks.

## Project Structure

- `linkedin_search/`
  - `api.py`: FastAPI application and endpoints
  - `linkedin.py`: LinkedIn scraping implementation
  - `tasks.py`: Redis-based task management

## Technical Details

### LinkedIn Scraping (`linkedin.py`)
- Uses `linkedin-api` package for authentication and profile access
- Implements profile data extraction and formatting
- Supports company and profile search

### API Implementation (`api.py`)
- FastAPI framework for REST endpoints
- Streaming response support
- Background task processing
- Search history caching

### Task Management (`tasks.py`)
- Redis-based task queue
- Async task processing
- Search history persistence

### Docker Configuration
- Multi-container setup with Docker Compose
- Redis container for caching and task queue
- Hot-reloading development environment

## Dependencies

Key packages used:
- FastAPI
- Uvicorn
- Python-dotenv
- LinkedIn-API
- Pydantic
- Aioredis
- Aiohttp

## Development

### Local Setup

1. Create a virtual environment:

python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate  # Windows


2. Install dependencies:

pip install -r requirements.txt


3. Run the development server:

uvicorn linkedin_search.api:app --reload


### Docker Development

Build and run containers:

docker-compose up --build


## Error Handling

The API implements proper error handling for:
- LinkedIn API rate limits
- Invalid search queries
- Network errors
- Redis connection issues

## Caching

Search results are cached in Redis to:
- Reduce LinkedIn API calls
- Improve response times
- Maintain search history

## Security Considerations

- Environment variables for sensitive credentials
- Rate limiting implementation
- Proper error handling
- Secure Redis configuration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Push to the branch
5. Create a Pull Request

## License

[MIT License](LICENSE)
