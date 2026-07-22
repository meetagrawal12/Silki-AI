<div align="center">

# 🤖 Silki AI — Full-Stack Conversational Platform

An enterprise-grade, multi-modal AI platform supporting low-latency multi-provider LLM chats, real-time response streaming (SSE), Retrieval-Augmented Generation (RAG) over user documents, speech processing (STT/TTS), and FLUX.1 vision generation.

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![SQLite](https://img.shields.io/badge/Database-SQLite%20Async-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

</div>

---

## 🏗️ System Architecture & Data Flow

### 1. High-Level Component Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Frontend Client (Vite / ES Modules)               │
│                   ┌───────────────────┬───────────────────┐                 │
│                   │   Chat & Streaming│   Voice & Audio   │                 │
│                   └─────────┬─────────┴─────────┬─────────┘                 │
└─────────────────────────────┼───────────────────┼───────────────────────────┘
                              │ HTTP / SSE        │ REST / Form-Data
                              ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FastAPI Backend Application                       │
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐  │
│  │ JWT Auth &      │    │ SlowAPI Rate    │    │ CORS & Security         │  │
│  │ User Middleware │    │ Limiter         │    │ Headers                 │  │
│  └────────┬────────┘    └────────┬────────┘    └────────────┬────────────┘  │
│           │                      │                          │               │
│  ┌────────▼──────────────────────▼──────────────────────────▼────────────┐  │
│  │                          API Routers                                  │  │
│  │      (/auth, /ai/chat, /ai/rag, /voice/stt, /voice/tts)             │  │
│  └────────┬──────────────────────┬──────────────────────────┬────────────┘  │
│           │                      │                          │               │
│  ┌────────▼────────┐    ┌────────▼────────┐    ┌────────────▼────────────┐  │
│  │ Auth & User     │    │ AI & RAG        │    │ Voice & Media           │  │
│  │ Service         │    │ Service         │    │ Service                 │  │
│  └────────┬────────┘    └────────┬────────┘    └────────────┬────────────┘  │
└───────────┼──────────────────────┼──────────────────────────┼───────────────┘
            │                      │                          │
            ▼                      ▼                          ▼
┌─────────────────────┐  ┌────────────────────┐  ┌───────────────────────────┐
│ Async SQLite DB     │  │ AI Service APIs    │  │ Voice & Media APIs        │
│ (Users, Sessions,   │  │ • Groq Llama 3.3   │  │ • HF Whisper-Large-v3     │
│ Message History)    │  │ • Google Gemini    │  │ • FLUX.1 Image Gen        │
│                     │  │ • Tavily Web Search│  │ • Async TTS Engine        │
└─────────────────────┘  └────────────────────┘  └───────────────────────────┘

-------------------------------------------------------------------------------------------------------------------------------------------------------------------------

User Client               FastAPI Server               RAG / Vector Engine            Groq / Gemini API
    │                            │                              │                             │
    │─── Send Chat + Doc ───────►│                              │                             │
    │                            │── Extract & Chunk Text ─────►│                             │
    │                            │                              │                             │
    │                            │◄── Return Relevant Context ──│                             │
    │                            │                                                            │
    │                            │────── Formulate Prompt + Context Vector ---------─────────►│
    │                            │                                                            │
    │◄── Server-Sent Events (SSE)│◄───── Stream Response Chunks (Word-by-Word) ───────────────│
    │    (Real-time Token Stream)│                                                            │
    │                            │                                                            │
    │                            │─── Persist Async History to SQLite ───────────────────────┐│
    │                            │                                                           ││
    │                            │◄──────────────────────────────────────────────────────────┘│

    -----------------------------------------------------------------------------------------------------------------------------------------------------------------

📂 Project Directory Structure
   Silki-AI/
├── .gitignore                   # Excludes .env, silki.db, venv, node_modules
├── .env.example                 # Template for environment variables
├── README.md                    # Project documentation & setup instructions
│
└── silki-Backend/
    ├── app/
    │   ├── main.py              # FastAPI application initialization & CORS middleware
    │   ├── core/                # Application configuration (config.py) & security secrets
    │   ├── db/                  # Database connections, Async Engines, and SQLite setup
    │   ├── middleware/          # Slowapi rate limiters & request processing
    │   ├── models/              # SQLAlchemy database models (User, ChatSession, Message)
    │   ├── repositories/        # Abstraction layer for database CRUD operations
    │   ├── routers/             # API Endpoints (/auth, /ai, /sessions, /voice)
    │   ├── schemas/             # Pydantic models for request/response validation
    │   └── services/            # Business logic (AuthService, AIService, RAG Engine)
    ├── silki.db                 # Local SQLite database (Auto-generated)
    └── requirements.txt         # Backend Python dependencies


    ------------------------------------------------------------------------------------------------------------------------------------------------------------------

    🛠️ Tech Stack & Dependencies
Backend Framework: FastAPI, Uvicorn (ASGI Server)

Database & ORM: SQLite, SQLAlchemy (aiosqlite for Async Support)

Auth & Security: PyJWT, Passlib (bcrypt), SlowAPI

AI Models & Integrations:

LLM: Groq SDK (llama-3.3-70b-versatile, mixtral-8x7b-32768, gemma2-9b-it), Google Gemini

Speech-to-Text: OpenAI Whisper Large v3 (HuggingFace Inference API)

Image Generation: black-forest-labs/FLUX.1-schnell

Web Search: Tavily API

🚀 Local Installation & Setup Guide
Prerequisites
Python 3.10+

Git

1. Clone the Repository
Bash
git clone [https://github.com/meetagrawal12/Silki-AI.git](https://github.com/meetagrawal12/Silki-AI.git)
cd Silki-AI
2. Set Up Virtual Environment
PowerShell
# Navigate into the backend directory
cd silki-Backend

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1
3. Install Dependencies
Bash
pip install -r requirements.txt
4. Configure Environment Variables
Create a .env file in the silki-Backend directory by copying .env.example:

Bash
cp .env.example .env
Fill in your secrets and API keys inside .env:

Code snippet
APP_NAME="Silki AI"
ENVIRONMENT=development
DEBUG=true

SECRET_KEY=your_generated_hex_secret_key
CORS_ORIGINS=http://localhost:5173,[http://127.0.0.1:5173](http://127.0.0.1:5173),[http://127.0.0.1:5500](http://127.0.0.1:5500)

DATABASE_URL=sqlite+aiosqlite:///./silki.db

# API Credentials
GROQ_API_KEY=your_groq_api_key_here
HF_TOKEN=your_huggingface_token_here
GEMINI_API_KEY=your_gemini_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
5. Run the Server
PowerShell
$env:PYTHONPATH="."
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir app
The application will start at http://127.0.0.1:8000.

📖 API Documentation
Access the interactive API documentation directly in your browser:

Swagger UI: http://127.0.0.1:8000/docs

ReDoc: http://127.0.0.1:8000/redoc

🛡️ License
This project is licensed under the MIT License.


---

### Update your GitHub Repository

Once updated locally, push the changes to GitHub with these commands:

```powershell
git add README.md
git commit -m "docs: add detailed system diagrams and structured information to README"
git push
