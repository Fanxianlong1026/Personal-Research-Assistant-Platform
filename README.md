# Personal Research Assistant Platform

> An AI-ready workspace for researchers: manage papers, notes, experiments, tasks, full-text search, and research chat in one local-first web app.

[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-Frontend-61DAFB?style=flat-square&logo=react&logoColor=111)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-Ready-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![SQLite](https://img.shields.io/badge/SQLite-Local--first-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Ant Design](https://img.shields.io/badge/Ant%20Design-UI-1677FF?style=flat-square&logo=antdesign&logoColor=white)](https://ant.design/)

If you like building personal research systems, paper workflows, or local AI tools, this project is meant to be forked, customized, and improved.

## Why This Exists

Research work usually scatters across PDF folders, browser tabs, spreadsheets, note apps, chat histories, and half-finished experiment logs. This platform puts the core loop into one place:

- collect and tag papers
- extract and search PDF full text
- write linked Markdown notes
- track experiments and compare runs
- manage research tasks with a Kanban board
- ask an AI assistant questions with saved sessions

It is designed as a practical personal research dashboard, not a toy demo.

## Highlights

- **Paper library**: metadata, authors, DOI, tags, rating, status, PDF upload, PDF preview, PDF text extraction, BibTeX import/export, DOI/arXiv metadata import.
- **Full-text search**: SQLite FTS5 index across papers and notes, with Chinese-friendly token handling and ranked snippets.
- **Knowledge notes**: Markdown notes, folders, tags, pinned notes, and optional paper linking.
- **Experiment tracking**: experiment groups, repeated runs, ablation-style comparisons, JSON parameters, JSON metrics, and chart visualization with ECharts.
- **Task board**: todo / in progress / done workflow with priorities and ordering.
- **AI chat**: streaming responses, persisted sessions, local model mode, and OpenAI-compatible API mode.
- **Local-first storage**: SQLite database and local upload folders by default.
- **Modern stack**: FastAPI + SQLAlchemy + React + Vite + TypeScript + Ant Design.

## Tech Stack

| Layer | Choice |
| --- | --- |
| Frontend | React, TypeScript, Vite, Ant Design, ECharts |
| Backend | FastAPI, SQLAlchemy, Pydantic Settings |
| Database | SQLite, SQLite FTS5 |
| AI | Local Qwen-style model or OpenAI-compatible API |
| File handling | Local PDF and experiment attachments |

## Project Structure

```text
.
|-- backend/
|   |-- app/
|   |   |-- main.py                 # FastAPI app, CORS, routes, startup hooks
|   |   |-- config.py               # environment-based settings
|   |   |-- database.py             # SQLAlchemy + SQLite
|   |   |-- search_index.py         # SQLite FTS5 indexing and search
|   |   |-- pdf_extract.py          # PDF text extraction helper
|   |   |-- paper_import.py         # DOI/arXiv metadata import
|   |   |-- bibtex.py               # BibTeX import/export
|   |   |-- models/                 # database models
|   |   |-- routers/                # REST and AI endpoints
|   |   `-- schemas/                # Pydantic schemas
|   |-- requirements.txt
|   `-- run.py
|-- frontend/
|   |-- src/
|   |   |-- pages/                  # Papers, Notes, Experiments, Tasks, AIChat, Search
|   |   |-- layouts/                # main app shell
|   |   |-- components/             # charts and reusable UI
|   |   `-- services/api.ts         # API client
|   |-- package.json
|   `-- vite.config.ts
`-- Qoder.md                        # development notes
```

## Quick Start

### 1. Clone

```bash
git clone https://github.com/Fanxianlong1026/Personal-Research-Assistant-Platform.git
cd Personal-Research-Assistant-Platform
```

### 2. Start The Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
# source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

On Windows PowerShell, use `copy .env.example .env` instead of `cp .env.example .env`.

Backend docs:

```text
http://127.0.0.1:8000/docs
```

### 3. Start The Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://127.0.0.1:5173
```

## AI Configuration

The backend reads configuration from `backend/.env`.

Use a local model:

```env
AI_MODE=local
AI_LOCAL_MODEL_PATH=D:\NewCode\Qwen2.5\model
AI_LOCAL_DEVICE=auto
AI_MAX_NEW_TOKENS=1024
```

Use an OpenAI-compatible API:

```env
AI_MODE=api
AI_API_KEY=your-api-key
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-3.5-turbo
```

Any provider compatible with the OpenAI chat completions format can be wired through `AI_BASE_URL` and `AI_MODEL`.

## Core API Modules

All application endpoints are mounted under `/api/v1`.

| Module | Endpoints |
| --- | --- |
| Papers | `/papers`, upload PDF, extract full text, import DOI/arXiv metadata, BibTeX import/export |
| Notes | `/notes`, folders, tags, paper-linked notes |
| Experiments | `/experiments`, attachments, grouped runs |
| Experiment Groups | `/experiment-groups`, comparison, add run |
| Tasks | `/tasks`, `/tasks/board`, reorder |
| Search | `/search?q=...&type=all\|paper\|note` |
| AI | `/ai/chat`, sessions, model status/load |

## Data Model

| Table | Purpose |
| --- | --- |
| `papers` | paper metadata, tags, local PDF path, extracted full text, status, rating |
| `notes` | Markdown knowledge notes, folders, tags, optional paper relation |
| `experiments` | experiment records, parameters, metrics, run number, variant, status |
| `experiment_groups` | reusable experiment grouping and comparison metadata |
| `tasks` | Kanban-style research tasks |
| `chat_messages` | AI chat session messages |

## What Makes It Interesting

- **Research-specific workflow** instead of a generic CRUD dashboard.
- **PDF full-text search** integrated into the paper library.
- **Experiment comparison** for repeated runs and ablation-style records.
- **Streaming AI chat** with both local and remote model options.
- **Readable, hackable architecture** suitable for students, researchers, and indie builders.

## Roadmap

- [ ] Add user authentication and multi-user workspaces
- [ ] Add Docker and docker-compose deployment
- [ ] Add richer paper recommendation and citation graph views
- [ ] Add note backlinks and graph visualization
- [ ] Add drag-and-drop task board interactions
- [ ] Add cloud/object storage adapter for uploaded files
- [ ] Add test coverage and CI workflow

## Contributing

Issues, ideas, and pull requests are welcome.

Good first contributions:

- improve README screenshots and demo data
- add Docker support
- polish the PDF import workflow
- add tests for API routes
- improve search ranking and snippets
- add deployment documentation

## Star History

If this project helps your research workflow or gives you ideas for your own AI research assistant, a star would mean a lot.

## License

No license has been declared yet. Add one before using this project in production or redistributing it.
