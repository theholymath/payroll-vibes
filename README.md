# Payroll Vibes

Upload a payroll spreadsheet and let Claude find the errors. The app ingests `.xls`/`.xlsx` files, runs Claude with code execution to analyze the data, and presents a report of what it found. You can then ask follow-up questions in a chat interface.

## Tech Stack

- **Backend:** FastAPI + Uvicorn
- **AI:** Anthropic Claude API (Files API + Code Execution beta)
- **Frontend:** Vanilla HTML/CSS/JS

## Quick Start

**Prerequisites:** Python 3.11+, [uv](https://docs.astral.sh/uv/), an [Anthropic API key](https://console.anthropic.com/)

```bash
# Clone and enter the project
git clone https://github.com/theholymath/payroll-vibes.git
cd payroll-vibes

# Set up environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Install dependencies and run
uv sync
uv run uvicorn app.main:app --reload
```

Open http://localhost:8000, upload a spreadsheet, and start chatting.

## Configuration

Set these in `.env`:

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(required)* | Your Anthropic API key |
| `CLAUDE_MODEL` | `claude-sonnet-4-5-20250929` | Claude model to use |
| `MAX_TOKENS` | `16384` | Max tokens per response |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Web UI |
| `POST` | `/api/upload` | Upload a spreadsheet |
| `POST` | `/api/chat` | Send a message / follow-up |
| `GET` | `/api/health/metrics` | Health check |
